"""
Fetcher Service for Financials-Basket MCP Server

Handles all external API calls with:
- Retry logic with exponential backoff
- Rate limiting (10 req/s for SEC EDGAR)
- Circuit breaker for fault tolerance
- ThreadPoolExecutor for blocking yfinance library
"""

import asyncio
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
from enum import Enum
from collections import deque

import httpx

from config import (
    SEC_EDGAR_TIMEOUT,
    SEC_EDGAR_DOCUMENT_TIMEOUT,
    YAHOO_FINANCE_TIMEOUT,
    CIK_LOOKUP_TIMEOUT,
    SEC_RATE_LIMIT_REQUESTS,
    SEC_RATE_LIMIT_PERIOD,
    RETRY_MAX_ATTEMPTS,
    RETRY_BASE_DELAY,
    RETRY_EXPONENTIAL_BASE,
    RETRY_STATUS_CODES,
    SEC_CB_FAILURE_THRESHOLD,
    SEC_CB_SUCCESS_THRESHOLD,
    SEC_CB_HALF_OPEN_TIMEOUT,
    YAHOO_CB_FAILURE_THRESHOLD,
    YAHOO_CB_SUCCESS_THRESHOLD,
    YAHOO_CB_HALF_OPEN_TIMEOUT,
    SEC_COMPANY_TICKERS_URL,
    SEC_SUBMISSIONS_URL,
    SEC_COMPANY_FACTS_URL,
    SEC_HEADERS,
    YAHOO_HEADERS,
    YFINANCE_THREAD_POOL_SIZE,
    YFINANCE_SEMAPHORE_LIMIT,
)
from models.errors import (
    CIKNotFoundError,
    APITimeoutError,
    CircuitOpenError,
    RateLimitError,
)

logger = logging.getLogger("fundamentals-basket.fetcher")


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5
    success_threshold: int = 3
    half_open_timeout: float = 30.0


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.monotonic)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _transition(self, new_state: CircuitState):
        """Transition to a new state."""
        if self.state != new_state:
            logger.info(f"Circuit breaker {self.name}: {self.state.value} -> {new_state.value}")
            self.state = new_state
            self.last_state_change = time.monotonic()
            if new_state == CircuitState.CLOSED:
                self.failure_count = 0
                self.success_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self.success_count = 0

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        with self._lock:
            now = time.monotonic()

            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if self.last_failure_time:
                    elapsed = now - self.last_failure_time
                    if elapsed >= self.config.half_open_timeout:
                        self._transition(CircuitState.HALF_OPEN)
                        return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return True

        return False

    def record_success(self):
        """Record a successful request."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._transition(CircuitState.CLOSED)
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self, error: Optional[str] = None):
        """Record a failed request."""
        with self._lock:
            self.last_failure_time = time.monotonic()

            if self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    self._transition(CircuitState.OPEN)
            elif self.state == CircuitState.HALF_OPEN:
                self._transition(CircuitState.OPEN)


# =============================================================================
# RATE LIMITER (Token Bucket)
# =============================================================================

@dataclass
class TokenBucket:
    """Token bucket rate limiter."""
    rate: float  # Tokens per second
    capacity: int  # Maximum tokens
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def acquire_async(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """Async version - waits until tokens available or timeout."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self.acquire(tokens):
                return True
            wait_time = min(0.1, (tokens - self.tokens) / self.rate)
            await asyncio.sleep(max(0.01, wait_time))
        return False


# =============================================================================
# FETCHER SERVICE
# =============================================================================

class FetcherService:
    """
    Fetcher service for external API calls.

    Features:
    - Retry logic with exponential backoff
    - Rate limiting for SEC EDGAR (10 req/s)
    - Circuit breakers for SEC and Yahoo
    - ThreadPoolExecutor for blocking yfinance
    """

    def __init__(self):
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        # Rate limiters
        self._sec_rate_limiter = TokenBucket(
            rate=SEC_RATE_LIMIT_REQUESTS,
            capacity=SEC_RATE_LIMIT_REQUESTS
        )

        # Circuit breakers
        self._circuit_breakers = {
            "sec_edgar": CircuitBreaker(
                name="sec_edgar",
                config=CircuitBreakerConfig(
                    failure_threshold=SEC_CB_FAILURE_THRESHOLD,
                    success_threshold=SEC_CB_SUCCESS_THRESHOLD,
                    half_open_timeout=SEC_CB_HALF_OPEN_TIMEOUT,
                )
            ),
            "yahoo_finance": CircuitBreaker(
                name="yahoo_finance",
                config=CircuitBreakerConfig(
                    failure_threshold=YAHOO_CB_FAILURE_THRESHOLD,
                    success_threshold=YAHOO_CB_SUCCESS_THRESHOLD,
                    half_open_timeout=YAHOO_CB_HALF_OPEN_TIMEOUT,
                )
            ),
        }

        # Thread pool for yfinance
        self._yfinance_executor = ThreadPoolExecutor(
            max_workers=YFINANCE_THREAD_POOL_SIZE,
            thread_name_prefix="yfinance-"
        )
        self._yfinance_semaphore = asyncio.Semaphore(YFINANCE_SEMAPHORE_LIMIT)

        # Company tickers cache (loaded once)
        self._company_tickers: Optional[Dict[str, str]] = None
        self._company_tickers_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close resources."""
        if self._client:
            await self._client.aclose()
        self._yfinance_executor.shutdown(wait=False)

    # =========================================================================
    # RETRY LOGIC
    # =========================================================================

    async def _fetch_with_retry(
        self,
        url: str,
        headers: Dict[str, str],
        timeout: float,
        source: str,
        rate_limiter: Optional[TokenBucket] = None,
    ) -> Dict[str, Any]:
        """
        Fetch URL with retry logic and rate limiting.

        Args:
            url: URL to fetch
            headers: Request headers
            timeout: Request timeout in seconds
            source: Source name for logging
            rate_limiter: Optional rate limiter to use

        Returns:
            JSON response as dict

        Raises:
            APITimeoutError: On timeout after retries
            CircuitOpenError: If circuit breaker is open
        """
        circuit_breaker = self._circuit_breakers.get(source.lower().replace(" ", "_"))

        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.allow_request():
            raise CircuitOpenError(source, circuit_breaker.config.half_open_timeout)

        last_error = None
        client = await self._get_client()

        for attempt in range(RETRY_MAX_ATTEMPTS):
            try:
                # Rate limiting
                if rate_limiter:
                    if not await rate_limiter.acquire_async(timeout=5.0):
                        raise RateLimitError(source, 1.0)

                # Make request
                start_time = time.time()
                response = await client.get(url, headers=headers, timeout=timeout)
                latency_ms = (time.time() - start_time) * 1000

                # Check for retry-able status codes
                if response.status_code in RETRY_STATUS_CODES:
                    last_error = f"HTTP {response.status_code}"
                    if attempt < RETRY_MAX_ATTEMPTS - 1:
                        delay = RETRY_BASE_DELAY * (RETRY_EXPONENTIAL_BASE ** attempt)
                        logger.warning(
                            f"{source} returned {response.status_code}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{RETRY_MAX_ATTEMPTS})"
                        )
                        await asyncio.sleep(delay)
                        continue

                response.raise_for_status()
                data = response.json()

                # Record success
                if circuit_breaker:
                    circuit_breaker.record_success()

                logger.debug(f"{source} fetch successful ({latency_ms:.0f}ms)")
                return data

            except httpx.TimeoutException as e:
                last_error = str(e)
                if circuit_breaker:
                    circuit_breaker.record_failure(last_error)
                if attempt < RETRY_MAX_ATTEMPTS - 1:
                    delay = RETRY_BASE_DELAY * (RETRY_EXPONENTIAL_BASE ** attempt)
                    logger.warning(f"{source} timeout, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                if circuit_breaker:
                    circuit_breaker.record_failure(last_error)
                if e.response.status_code in RETRY_STATUS_CODES and attempt < RETRY_MAX_ATTEMPTS - 1:
                    delay = RETRY_BASE_DELAY * (RETRY_EXPONENTIAL_BASE ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise

            except Exception as e:
                last_error = str(e)
                if circuit_breaker:
                    circuit_breaker.record_failure(last_error)
                raise

        # All retries exhausted
        raise APITimeoutError(source, timeout)

    # =========================================================================
    # SEC EDGAR FETCHERS
    # =========================================================================

    async def _load_company_tickers(self) -> Dict[str, str]:
        """Load and cache company tickers mapping (ticker -> CIK)."""
        async with self._company_tickers_lock:
            if self._company_tickers is not None:
                return self._company_tickers

            try:
                data = await self._fetch_with_retry(
                    url=SEC_COMPANY_TICKERS_URL,
                    headers=SEC_HEADERS,
                    timeout=CIK_LOOKUP_TIMEOUT,
                    source="SEC EDGAR",
                    rate_limiter=self._sec_rate_limiter,
                )

                # Build ticker -> CIK mapping
                self._company_tickers = {}
                for entry in data.values():
                    ticker = entry.get("ticker", "").upper()
                    cik = str(entry.get("cik_str", ""))
                    if ticker and cik:
                        self._company_tickers[ticker] = cik

                logger.info(f"Loaded {len(self._company_tickers)} company tickers")
                return self._company_tickers

            except Exception as e:
                logger.error(f"Failed to load company tickers: {e}")
                self._company_tickers = {}
                return self._company_tickers

    async def fetch_cik(self, ticker: str) -> Optional[str]:
        """
        Fetch CIK for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK string (10-digit padded) or None if not found
        """
        ticker = ticker.upper()
        tickers = await self._load_company_tickers()
        cik = tickers.get(ticker)

        if cik:
            # Pad to 10 digits
            return cik.zfill(10)

        logger.warning(f"CIK not found for ticker {ticker}")
        return None

    async def fetch_company_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Fetch company submissions (metadata and filings) from SEC EDGAR.

        Args:
            cik: CIK identifier (10-digit padded)

        Returns:
            Submissions data dict
        """
        url = SEC_SUBMISSIONS_URL.format(cik=cik)
        return await self._fetch_with_retry(
            url=url,
            headers=SEC_HEADERS,
            timeout=SEC_EDGAR_TIMEOUT,
            source="SEC EDGAR",
            rate_limiter=self._sec_rate_limiter,
        )

    async def fetch_company_facts(self, cik: str) -> Dict[str, Any]:
        """
        Fetch company facts (XBRL data) from SEC EDGAR.

        Args:
            cik: CIK identifier (10-digit padded)

        Returns:
            Company facts dict containing us-gaap concepts
        """
        url = SEC_COMPANY_FACTS_URL.format(cik=cik)
        return await self._fetch_with_retry(
            url=url,
            headers=SEC_HEADERS,
            timeout=SEC_EDGAR_TIMEOUT,
            source="SEC EDGAR",
            rate_limiter=self._sec_rate_limiter,
        )

    async def fetch_10k_document(self, url: str) -> str:
        """
        Fetch raw 10-K document text.

        Args:
            url: Full URL to the 10-K document

        Returns:
            Document text content
        """
        client = await self._get_client()

        # Rate limiting
        await self._sec_rate_limiter.acquire_async(timeout=5.0)

        response = await client.get(url, headers=SEC_HEADERS, timeout=SEC_EDGAR_DOCUMENT_TIMEOUT)
        response.raise_for_status()
        return response.text

    # =========================================================================
    # YAHOO FINANCE FETCHER
    # =========================================================================

    def _fetch_yfinance_sync(self, ticker: str) -> Dict[str, Any]:
        """
        Synchronous yfinance fetch (runs in thread pool).

        Args:
            ticker: Stock ticker symbol

        Returns:
            Financials data dict
        """
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or len(info) < 5:
                return {"error": f"No data found for {ticker}"}

            # Convert Unix timestamps to dates (use UTC for correct trading date)
            from datetime import datetime as dt, timezone
            most_recent_quarter = info.get("mostRecentQuarter")
            last_fiscal_year_end = info.get("lastFiscalYearEnd")

            most_recent_quarter_date = None
            last_fiscal_year_end_date = None

            if most_recent_quarter:
                try:
                    most_recent_quarter_date = dt.fromtimestamp(most_recent_quarter, tz=timezone.utc).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    pass

            if last_fiscal_year_end:
                try:
                    last_fiscal_year_end_date = dt.fromtimestamp(last_fiscal_year_end, tz=timezone.utc).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    pass

            regular_market_time = info.get("regularMarketTime")
            regular_market_time_date = None
            if regular_market_time:
                try:
                    regular_market_time_date = dt.fromtimestamp(regular_market_time, tz=timezone.utc).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    pass

            # Extract relevant fields
            return {
                "ticker": ticker.upper(),
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "revenue": info.get("totalRevenue"),
                "gross_profit": info.get("grossProfits"),
                "operating_income": info.get("operatingIncome"),
                "net_income": info.get("netIncomeToCommon"),
                "total_assets": info.get("totalAssets"),
                "total_liabilities": info.get("totalLiab"),
                "stockholders_equity": info.get("totalStockholderEquity"),
                "total_debt": info.get("totalDebt"),
                "cash": info.get("totalCash"),
                "operating_cash_flow": info.get("operatingCashflow"),
                "free_cash_flow": info.get("freeCashflow"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "most_recent_quarter": most_recent_quarter_date,
                "last_fiscal_year_end": last_fiscal_year_end_date,
                "regular_market_time": regular_market_time_date,
                "source": "Yahoo Finance",
            }

        except Exception as e:
            logger.error(f"yfinance error for {ticker}: {e}")
            return {"error": str(e), "ticker": ticker}

    async def fetch_yfinance(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch financials from Yahoo Finance (async wrapper).

        Uses ThreadPoolExecutor since yfinance is blocking.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Financials data dict
        """
        circuit_breaker = self._circuit_breakers["yahoo_finance"]

        # Check circuit breaker
        if not circuit_breaker.allow_request():
            raise CircuitOpenError("Yahoo Finance", circuit_breaker.config.half_open_timeout)

        async with self._yfinance_semaphore:
            loop = asyncio.get_event_loop()
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._yfinance_executor,
                        self._fetch_yfinance_sync,
                        ticker
                    ),
                    timeout=YAHOO_FINANCE_TIMEOUT
                )

                if "error" not in result:
                    circuit_breaker.record_success()
                else:
                    circuit_breaker.record_failure(result.get("error"))

                return result

            except asyncio.TimeoutError:
                circuit_breaker.record_failure("Timeout")
                raise APITimeoutError("Yahoo Finance", YAHOO_FINANCE_TIMEOUT)

            except Exception as e:
                circuit_breaker.record_failure(str(e))
                raise

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get fetcher service status."""
        return {
            "circuit_breakers": {
                name: {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "success_count": cb.success_count,
                }
                for name, cb in self._circuit_breakers.items()
            },
            "rate_limiter": {
                "sec_edgar": {
                    "available_tokens": self._sec_rate_limiter.tokens,
                    "capacity": self._sec_rate_limiter.capacity,
                }
            },
            "company_tickers_loaded": self._company_tickers is not None,
        }


# Global fetcher instance
_fetcher_service: Optional[FetcherService] = None


def get_fetcher_service() -> FetcherService:
    """Get or create the global fetcher service instance."""
    global _fetcher_service
    if _fetcher_service is None:
        _fetcher_service = FetcherService()
    return _fetcher_service
