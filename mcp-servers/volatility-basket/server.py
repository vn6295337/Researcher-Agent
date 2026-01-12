"""
Volatility Basket MCP Server

Aggregates volatility metrics from multiple free sources for SWOT analysis:
- VIX Index (CBOE) → External Threat indicator
- Beta (Yahoo Finance) → Internal Strength/Weakness
- Implied Volatility (derived) → Upcoming Threat/Opportunity
- Historical Volatility (calculated) → Operational Weakness

Usage:
    python server.py

Or via MCP:
    Add to claude_desktop_config.json
"""

import asyncio
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import statistics

# Load environment variables (later files override earlier ones)
from dotenv import load_dotenv
env_paths = [
    Path.home() / ".env",  # Home directory (base)
    Path(__file__).parent.parent.parent / ".env",  # Project root (overrides)
    Path(__file__).parent / ".env",  # MCP server directory (highest priority)
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Data fetching
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("volatility-basket")

# Initialize MCP server
server = Server("volatility-basket")

# API Keys (optional - enables authoritative sources)
FRED_API_KEY = os.getenv("FRED_API_KEY") or os.getenv("FRED_VIX_API_KEY")  # Get free key: https://fred.stlouisfed.org/docs/api/api_key.html
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")  # Get free key: https://www.alphavantage.co/support/#api-key
TRADIER_API_KEY = os.getenv("TRADIER_API_KEY")  # Get free key: https://developer.tradier.com/

# Alpha Vantage API configuration (Secondary for Beta, Historical Volatility)
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Tradier API configuration (Primary for Implied Volatility)
TRADIER_BASE_URL = "https://api.tradier.com/v1"

# Yahoo Finance requires browser-like headers
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# DATA FETCHERS
# ============================================================

async def fetch_vix_from_fred() -> Optional[dict]:
    """
    Fetch VIX from FRED (Federal Reserve Economic Data).
    Primary/authoritative source. Requires free API key.
    """
    if not FRED_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": "VIXCLS",
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5
            }
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            observations = data.get("observations", [])
            if not observations:
                return None

            # Get latest non-null value
            for obs in observations:
                if obs.get("value") and obs["value"] != ".":
                    current_price = float(obs["value"])
                    break
            else:
                return None

            # Get previous for change calculation
            previous_close = current_price
            if len(observations) > 1 and observations[1].get("value") != ".":
                previous_close = float(observations[1]["value"])

            return {
                "value": current_price,
                "previous_close": previous_close,
                "source": "FRED (Federal Reserve)",
                "date": observations[0].get("date")
            }
    except Exception as e:
        logger.error(f"FRED VIX fetch error: {e}")
        return None


async def fetch_vix_from_yahoo() -> Optional[dict]:
    """
    Fetch VIX from Yahoo Finance (fallback source).
    """
    try:
        async with httpx.AsyncClient() as client:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
            params = {"interval": "1d", "range": "5d"}
            response = await client.get(url, params=params, headers=YAHOO_HEADERS, timeout=10)
            data = response.json()

            result = data["chart"]["result"][0]
            meta = result["meta"]
            current_price = meta.get("regularMarketPrice", 0)
            previous_close = meta.get("previousClose", current_price)

            return {
                "value": current_price,
                "previous_close": previous_close,
                "source": "Yahoo Finance"
            }
    except Exception as e:
        logger.error(f"Yahoo VIX fetch error: {e}")
        return None


def get_default_vix() -> dict:
    """Return reasonable VIX default when all sources fail."""
    return {
        "value": 20.0,  # Historical average around 20
        "previous_close": 20.0,
        "source": "Market Average (estimated)",
        "fallback": True,
        "fallback_reason": "All VIX sources unavailable",
        "estimated": True
    }


# ============================================================
# VXN (NASDAQ-100 VOLATILITY INDEX) FETCHERS
# ============================================================

async def fetch_vxn_from_fred() -> Optional[dict]:
    """
    Fetch VXN (Nasdaq-100 Volatility Index) from FRED.
    VXN is to Nasdaq-100 what VIX is to S&P 500.
    Series ID: VXNCLS
    """
    if not FRED_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": "VXNCLS",
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5
            }
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            observations = data.get("observations", [])
            if not observations:
                return None

            # Get latest non-null value
            for obs in observations:
                if obs.get("value") and obs["value"] != ".":
                    current_price = float(obs["value"])
                    break
            else:
                return None

            # Get previous for change calculation
            previous_close = current_price
            if len(observations) > 1 and observations[1].get("value") != ".":
                previous_close = float(observations[1]["value"])

            return {
                "value": current_price,
                "previous_close": previous_close,
                "source": "FRED (Federal Reserve)",
                "date": observations[0].get("date")
            }
    except Exception as e:
        logger.error(f"FRED VXN fetch error: {e}")
        return None


def get_default_vxn() -> dict:
    """Return reasonable VXN default when all sources fail."""
    return {
        "value": 22.0,  # VXN typically runs slightly higher than VIX
        "previous_close": 22.0,
        "source": "Market Average (estimated)",
        "fallback": True,
        "fallback_reason": "All VXN sources unavailable",
        "estimated": True
    }


async def fetch_vxn() -> dict:
    """
    Fetch VXN (Nasdaq-100 Volatility Index) with fallback chain.
    VXN measures expected volatility of Nasdaq-100 index.
    Use for Nasdaq stocks as market context.
    """
    vxn_data = await fetch_vxn_from_fred()

    if not vxn_data:
        logger.info("FRED VXN failed, using default VXN value")
        vxn_data = get_default_vxn()

    current_price = vxn_data["value"]
    previous_close = vxn_data["previous_close"]
    is_fallback = vxn_data.get("fallback", False)

    # VXN interpretation thresholds (similar to VIX but slightly higher typical values)
    if current_price < 17:
        interpretation = "Low volatility - Complacent tech market"
        swot_impact = "OPPORTUNITY"
    elif current_price < 22:
        interpretation = "Normal volatility - Stable tech conditions"
        swot_impact = "NEUTRAL"
    elif current_price < 32:
        interpretation = "Elevated volatility - Tech sector uncertainty"
        swot_impact = "THREAT"
    else:
        interpretation = "High volatility - Tech fear/crisis mode"
        swot_impact = "SEVERE_THREAT"

    # Use actual observation date from FRED, not query time
    observation_date = vxn_data.get("date")  # YYYY-MM-DD from FRED

    result = {
        "metric": "VXN",
        "description": "Nasdaq-100 Volatility Index",
        "value": round(current_price, 2),
        "previous_close": round(previous_close, 2),
        "change_pct": round((current_price - previous_close) / previous_close * 100, 2) if previous_close else 0,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": vxn_data["source"],
        "as_of": observation_date or datetime.now().strftime("%Y-%m-%d")
    }
    if is_fallback:
        result["fallback"] = True
        result["fallback_reason"] = vxn_data.get("fallback_reason", "Primary source unavailable")
        result["estimated"] = vxn_data.get("estimated", False)
    return result


async def fetch_vix() -> dict:
    """
    Fetch VIX index with fallback chain: FRED → Yahoo Finance → Default.
    Returns current VIX level and interpretation.
    """
    # Try FRED first (authoritative), fallback to Yahoo
    vix_data = await fetch_vix_from_fred()
    if not vix_data:
        logger.info("FRED VIX failed, trying Yahoo fallback")
        vix_data = await fetch_vix_from_yahoo()

    if not vix_data:
        logger.info("Yahoo VIX failed, using default VIX value")
        vix_data = get_default_vix()

    current_price = vix_data["value"]
    previous_close = vix_data["previous_close"]
    is_fallback = vix_data.get("fallback", False)

    # VIX interpretation thresholds
    if current_price < 15:
        interpretation = "Low volatility - Complacent market"
        swot_impact = "OPPORTUNITY"
    elif current_price < 20:
        interpretation = "Normal volatility - Stable conditions"
        swot_impact = "NEUTRAL"
    elif current_price < 30:
        interpretation = "Elevated volatility - Increased uncertainty"
        swot_impact = "THREAT"
    else:
        interpretation = "High volatility - Fear/crisis mode"
        swot_impact = "SEVERE_THREAT"

    # Use actual observation date from FRED, not query time
    observation_date = vix_data.get("date")  # YYYY-MM-DD from FRED

    result = {
        "metric": "VIX",
        "value": round(current_price, 2),
        "previous_close": round(previous_close, 2),
        "change_pct": round((current_price - previous_close) / previous_close * 100, 2) if previous_close else 0,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": vix_data["source"],
        "as_of": observation_date or datetime.now().strftime("%Y-%m-%d")
    }
    if is_fallback:
        result["fallback"] = True
        result["fallback_reason"] = vix_data.get("fallback_reason", "Primary source unavailable")
        result["estimated"] = vix_data.get("estimated", False)
    return result


def get_default_beta(ticker: str) -> dict:
    """Return market average beta when calculation fails."""
    return {
        "metric": "Beta",
        "ticker": ticker.upper(),
        "value": 1.0,  # Market average beta
        "benchmark": "S&P 500",
        "period": "1 year",
        "interpretation": "Market beta - Moves with the market (estimated)",
        "swot_category": "NEUTRAL",
        "source": "Market Average (estimated)",
        "fallback": True,
        "fallback_reason": "Unable to calculate beta from price data",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_beta(ticker: str) -> dict:
    """
    Calculate Beta coefficient from price data.
    Beta = Covariance(stock, market) / Variance(market)
    Uses S&P 500 (^GSPC) as market benchmark.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Fetch stock and market data in parallel
            stock_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            market_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
            params = {"interval": "1d", "range": "1y"}

            stock_resp, market_resp = await asyncio.gather(
                client.get(stock_url, params=params, headers=YAHOO_HEADERS, timeout=10),
                client.get(market_url, params=params, headers=YAHOO_HEADERS, timeout=10)
            )

            stock_data = stock_resp.json()["chart"]["result"][0]
            market_data = market_resp.json()["chart"]["result"][0]

            stock_closes = stock_data["indicators"]["quote"][0]["close"]
            market_closes = market_data["indicators"]["quote"][0]["close"]

            # Filter None values and align lengths
            stock_closes = [c for c in stock_closes if c is not None]
            market_closes = [c for c in market_closes if c is not None]
            min_len = min(len(stock_closes), len(market_closes))
            stock_closes = stock_closes[-min_len:]
            market_closes = market_closes[-min_len:]

            if len(stock_closes) < 30:
                logger.info(f"Insufficient data for beta calculation for {ticker}, using default")
                return get_default_beta(ticker)

            # Calculate daily returns
            stock_returns = [(stock_closes[i] - stock_closes[i-1]) / stock_closes[i-1]
                            for i in range(1, len(stock_closes))]
            market_returns = [(market_closes[i] - market_closes[i-1]) / market_closes[i-1]
                             for i in range(1, len(market_closes))]

            # Calculate Beta = Cov(stock, market) / Var(market)
            n = len(stock_returns)
            mean_stock = sum(stock_returns) / n
            mean_market = sum(market_returns) / n

            covariance = sum((stock_returns[i] - mean_stock) * (market_returns[i] - mean_market)
                            for i in range(n)) / (n - 1)
            variance_market = sum((market_returns[i] - mean_market) ** 2
                                  for i in range(n)) / (n - 1)

            beta = covariance / variance_market if variance_market != 0 else 1.0

            # Beta interpretation
            if beta < 0.8:
                interpretation = "Low beta - Defensive stock, less volatile than market"
                swot_impact = "STRENGTH"
            elif beta < 1.2:
                interpretation = "Market beta - Moves with the market"
                swot_impact = "NEUTRAL"
            elif beta < 1.5:
                interpretation = "High beta - More volatile than market"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high beta - Significantly more volatile"
                swot_impact = "WEAKNESS"

            # Get actual data end date from timestamps (use UTC for correct trading date)
            timestamps = stock_data.get("timestamp", [])
            data_end_date = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).strftime("%Y-%m-%d") if timestamps else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

            return {
                "metric": "Beta",
                "ticker": ticker.upper(),
                "value": round(beta, 3),
                "benchmark": "S&P 500",
                "period": "1 year",
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Calculated from Yahoo Finance data",
                "as_of": data_end_date
            }
    except Exception as e:
        logger.error(f"Beta fetch error for {ticker}: {e}")
        return get_default_beta(ticker)


def get_default_historical_volatility(ticker: str) -> dict:
    """Return market average historical volatility when calculation fails."""
    return {
        "metric": "Historical Volatility",
        "ticker": ticker.upper(),
        "value": 25.0,  # Typical market average ~25% annualized
        "unit": "% annualized",
        "period_days": 30,
        "interpretation": "Moderate volatility - Normal for equities (estimated)",
        "swot_category": "NEUTRAL",
        "source": "Market Average (estimated)",
        "fallback": True,
        "fallback_reason": "Unable to calculate historical volatility",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_historical_volatility(ticker: str, period_days: int = 30) -> dict:
    """
    Calculate historical volatility from price data.
    Uses standard deviation of daily returns annualized.
    """
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {"interval": "1d", "range": "3mo"}
            response = await client.get(url, params=params, headers=YAHOO_HEADERS, timeout=10)
            data = response.json()

            result = data["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]

            # Filter None values and get recent period
            closes = [c for c in closes if c is not None][-period_days:]

            if len(closes) < 10:
                logger.info(f"Insufficient data for HV calculation for {ticker}, using default")
                return get_default_historical_volatility(ticker)

            # Calculate daily returns
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

            # Calculate standard deviation and annualize (252 trading days)
            daily_vol = statistics.stdev(returns)
            annual_vol = daily_vol * (252 ** 0.5) * 100  # As percentage

            # Interpretation
            if annual_vol < 20:
                interpretation = "Low historical volatility - Stable price action"
                swot_impact = "STRENGTH"
            elif annual_vol < 35:
                interpretation = "Moderate volatility - Normal for equities"
                swot_impact = "NEUTRAL"
            elif annual_vol < 50:
                interpretation = "High volatility - Significant price swings"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high volatility - Extreme price movements"
                swot_impact = "WEAKNESS"

            # Get actual data end date from timestamps (use UTC for correct trading date)
            timestamps = result.get("timestamp", [])
            data_end_date = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).strftime("%Y-%m-%d") if timestamps else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

            return {
                "metric": "Historical Volatility",
                "ticker": ticker.upper(),
                "value": round(annual_vol, 2),
                "unit": "% annualized",
                "period_days": period_days,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Calculated from Yahoo Finance data",
                "as_of": data_end_date
            }
    except Exception as e:
        logger.error(f"Historical volatility error for {ticker}: {e}")
        return get_default_historical_volatility(ticker)


def get_default_implied_volatility(ticker: str) -> dict:
    """Return estimated implied volatility when options data unavailable."""
    return {
        "metric": "Implied Volatility",
        "ticker": ticker.upper(),
        "value": 30.0,  # Typical IV for liquid stocks
        "unit": "%",
        "strike": None,
        "expiration": None,
        "interpretation": "Moderate IV - Normal expected movement (estimated)",
        "swot_category": "NEUTRAL",
        "source": "Market Average (estimated)",
        "fallback": True,
        "fallback_reason": "Options data unavailable",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_implied_volatility_proxy(ticker: str) -> dict:
    """
    Estimate implied volatility using options data from Yahoo Finance.
    Uses ATM options IV as proxy.
    """
    try:
        async with httpx.AsyncClient() as client:
            # First get current price
            quote_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            quote_resp = await client.get(quote_url, params={"interval": "1d", "range": "1d"}, headers=YAHOO_HEADERS, timeout=10)
            quote_data = quote_resp.json()
            current_price = quote_data["chart"]["result"][0]["meta"]["regularMarketPrice"]

            # Get options chain
            options_url = f"https://query1.finance.yahoo.com/v7/finance/options/{ticker}"
            options_resp = await client.get(options_url, headers=YAHOO_HEADERS, timeout=10)
            options_data = options_resp.json()

            if "optionChain" not in options_data or not options_data["optionChain"]["result"]:
                logger.info(f"No options data for {ticker}, using default IV")
                return get_default_implied_volatility(ticker)

            result = options_data["optionChain"]["result"][0]
            calls = result.get("options", [{}])[0].get("calls", [])

            if not calls:
                logger.info(f"No calls data for {ticker}, using default IV")
                return get_default_implied_volatility(ticker)

            # Find ATM option (closest to current price)
            atm_call = min(calls, key=lambda x: abs(x.get("strike", 0) - current_price))
            iv = atm_call.get("impliedVolatility", 0) * 100  # Convert to percentage

            # Interpretation
            if iv < 25:
                interpretation = "Low IV - Market expects limited price movement"
                swot_impact = "OPPORTUNITY"
            elif iv < 40:
                interpretation = "Moderate IV - Normal expected movement"
                swot_impact = "NEUTRAL"
            elif iv < 60:
                interpretation = "High IV - Market expects significant movement"
                swot_impact = "THREAT"
            else:
                interpretation = "Very high IV - Extreme movement expected (earnings, event)"
                swot_impact = "THREAT"

            # Get quote date from regularMarketTime (use UTC for correct trading date)
            market_time = quote_data["chart"]["result"][0]["meta"].get("regularMarketTime", 0)
            quote_date = datetime.fromtimestamp(market_time, tz=timezone.utc).strftime("%Y-%m-%d") if market_time else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

            return {
                "metric": "Implied Volatility",
                "ticker": ticker.upper(),
                "value": round(iv, 2),
                "unit": "%",
                "strike": atm_call.get("strike"),
                "expiration": result.get("expirationDates", [None])[0],
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Yahoo Finance Options",
                "as_of": quote_date
            }
    except Exception as e:
        logger.error(f"IV fetch error for {ticker}: {e}")
        return get_default_implied_volatility(ticker)


# ============================================================
# ALPHA VANTAGE FETCHERS (Secondary for Beta, Historical Vol)
# ============================================================

async def fetch_alpha_vantage_beta(ticker: str) -> Optional[dict]:
    """
    Fetch Beta from Alpha Vantage OVERVIEW endpoint.
    Secondary source for Beta validation.
    """
    if not ALPHA_VANTAGE_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "function": "OVERVIEW",
                "symbol": ticker.upper(),
                "apikey": ALPHA_VANTAGE_KEY
            }
            response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
            data = response.json()

            if "Beta" not in data or not data.get("Beta"):
                return None

            beta = float(data["Beta"])

            # Beta interpretation
            if beta < 0.8:
                interpretation = "Low beta - Defensive stock, less volatile than market"
                swot_impact = "STRENGTH"
            elif beta < 1.2:
                interpretation = "Market beta - Moves with the market"
                swot_impact = "NEUTRAL"
            elif beta < 1.5:
                interpretation = "High beta - More volatile than market"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high beta - Significantly more volatile"
                swot_impact = "WEAKNESS"

            return {
                "metric": "Beta",
                "ticker": ticker.upper(),
                "value": round(beta, 3),
                "benchmark": "S&P 500",
                "period": "5 year monthly",
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Alpha Vantage",
                "as_of": data.get("LatestQuarter", datetime.now().strftime("%Y-%m-%d"))
            }

    except Exception as e:
        logger.error(f"Alpha Vantage Beta fetch error for {ticker}: {e}")
        return None


async def fetch_alpha_vantage_historical_volatility(ticker: str, period_days: int = 30) -> Optional[dict]:
    """
    Calculate historical volatility from Alpha Vantage daily prices.
    Secondary source for Historical Volatility validation.
    Formula: std(log returns) × sqrt(252)
    """
    if not ALPHA_VANTAGE_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker.upper(),
                "outputsize": "compact",  # Last 100 data points
                "apikey": ALPHA_VANTAGE_KEY
            }
            response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
            data = response.json()

            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                return None

            # Get sorted dates (most recent first)
            dates = sorted(time_series.keys(), reverse=True)[:period_days + 1]

            if len(dates) < 10:
                return None

            # Get closing prices
            closes = [float(time_series[d]["4. close"]) for d in dates]

            # Calculate log returns
            log_returns = [math.log(closes[i] / closes[i + 1]) for i in range(len(closes) - 1)]

            # Calculate standard deviation and annualize
            daily_vol = statistics.stdev(log_returns)
            annual_vol = daily_vol * math.sqrt(252) * 100  # As percentage

            # Interpretation
            if annual_vol < 20:
                interpretation = "Low historical volatility - Stable price action"
                swot_impact = "STRENGTH"
            elif annual_vol < 35:
                interpretation = "Moderate volatility - Normal for equities"
                swot_impact = "NEUTRAL"
            elif annual_vol < 50:
                interpretation = "High volatility - Significant price swings"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high volatility - Extreme price movements"
                swot_impact = "WEAKNESS"

            # Use most recent date from time series
            data_end_date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")

            return {
                "metric": "Historical Volatility",
                "ticker": ticker.upper(),
                "value": round(annual_vol, 2),
                "unit": "% annualized",
                "period_days": period_days,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Alpha Vantage (calculated)",
                "as_of": data_end_date
            }

    except Exception as e:
        logger.error(f"Alpha Vantage HV fetch error for {ticker}: {e}")
        return None


# ============================================================
# TRADIER FETCHERS (Primary/Secondary for Implied Volatility)
# ============================================================

async def fetch_tradier_implied_volatility(ticker: str) -> Optional[dict]:
    """
    Fetch implied volatility from Tradier options chain.
    Provides stock-specific IV from ATM options.

    API: https://developer.tradier.com/
    Requires free account creation.
    """
    if not TRADIER_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {TRADIER_API_KEY}",
                "Accept": "application/json"
            }

            # First get current quote for ATM strike
            quote_url = f"{TRADIER_BASE_URL}/markets/quotes"
            quote_params = {"symbols": ticker.upper()}
            quote_resp = await client.get(quote_url, params=quote_params, headers=headers, timeout=10)
            quote_data = quote_resp.json()

            quotes = quote_data.get("quotes", {}).get("quote", {})
            if isinstance(quotes, list):
                quotes = quotes[0] if quotes else {}

            current_price = quotes.get("last", 0) or quotes.get("close", 0)
            if not current_price:
                return None

            # Get options expirations
            exp_url = f"{TRADIER_BASE_URL}/markets/options/expirations"
            exp_params = {"symbol": ticker.upper()}
            exp_resp = await client.get(exp_url, params=exp_params, headers=headers, timeout=10)
            exp_data = exp_resp.json()

            expirations = exp_data.get("expirations", {}).get("date", [])
            if not expirations:
                return None

            # Use nearest expiration
            nearest_exp = expirations[0] if isinstance(expirations, list) else expirations

            # Get options chain
            chain_url = f"{TRADIER_BASE_URL}/markets/options/chains"
            chain_params = {
                "symbol": ticker.upper(),
                "expiration": nearest_exp,
                "greeks": "true"
            }
            chain_resp = await client.get(chain_url, params=chain_params, headers=headers, timeout=10)
            chain_data = chain_resp.json()

            options = chain_data.get("options", {}).get("option", [])
            if not options:
                return None

            # Filter calls and find ATM
            calls = [o for o in options if o.get("option_type") == "call"]
            if not calls:
                return None

            # Find ATM call (closest to current price)
            atm_call = min(calls, key=lambda x: abs(x.get("strike", 0) - current_price))

            # Get IV from greeks
            greeks = atm_call.get("greeks", {})
            iv = greeks.get("mid_iv", 0) or greeks.get("ask_iv", 0) or greeks.get("bid_iv", 0)

            if not iv:
                # Fallback to smv_vol if available
                iv = greeks.get("smv_vol", 0)

            if not iv:
                return None

            iv_pct = iv * 100  # Convert to percentage

            # Interpretation
            if iv_pct < 25:
                interpretation = "Low IV - Market expects limited price movement"
                swot_impact = "OPPORTUNITY"
            elif iv_pct < 40:
                interpretation = "Moderate IV - Normal expected movement"
                swot_impact = "NEUTRAL"
            elif iv_pct < 60:
                interpretation = "High IV - Market expects significant movement"
                swot_impact = "THREAT"
            else:
                interpretation = "Very high IV - Extreme movement expected (earnings, event)"
                swot_impact = "THREAT"

            # Use quote trade_date if available, else today
            trade_date = quote.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
            if isinstance(trade_date, str) and "T" in trade_date:
                trade_date = trade_date.split("T")[0]

            return {
                "metric": "Implied Volatility",
                "ticker": ticker.upper(),
                "value": round(iv_pct, 2),
                "unit": "%",
                "strike": atm_call.get("strike"),
                "expiration": nearest_exp,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Tradier",
                "as_of": trade_date
            }

    except Exception as e:
        logger.error(f"Tradier IV fetch error for {ticker}: {e}")
        return None


# ============================================================
# MULTI-SOURCE AGGREGATOR
# ============================================================

async def get_all_sources_volatility(ticker: str) -> dict:
    """
    Fetch volatility from ALL sources in parallel.
    Returns NORMALIZED schema for interpreted_metrics group.

    Source hierarchy:
    - VIX: FRED (primary) - S&P 500 market volatility context
    - VXN: FRED (primary) - Nasdaq-100 market volatility context
    - Beta: Yahoo Finance (primary) → Alpha Vantage (secondary)
    - Historical Vol: Yahoo Finance (primary) → Alpha Vantage (secondary)
    - Implied Vol: Yahoo Finance Options (primary)
    """
    # Fetch from all sources in parallel
    vix_task = fetch_vix()
    vxn_task = fetch_vxn()  # Nasdaq-100 volatility index

    # Beta: Yahoo (primary) + Alpha Vantage (secondary)
    yahoo_beta_task = fetch_beta(ticker)
    av_beta_task = fetch_alpha_vantage_beta(ticker)

    # Historical Volatility: Yahoo (primary) + Alpha Vantage (secondary)
    yahoo_hv_task = fetch_historical_volatility(ticker)
    av_hv_task = fetch_alpha_vantage_historical_volatility(ticker)

    # Implied Volatility: Yahoo Options (primary)
    yahoo_iv_task = fetch_implied_volatility_proxy(ticker)

    (vix, vxn, yahoo_beta, av_beta, yahoo_hv, av_hv, yahoo_iv) = await asyncio.gather(
        vix_task, vxn_task,
        yahoo_beta_task, av_beta_task,
        yahoo_hv_task, av_hv_task,
        yahoo_iv_task
    )

    # Use primary source, fallback to secondary if primary failed
    beta = yahoo_beta if "error" not in yahoo_beta else (av_beta or yahoo_beta)
    hv = yahoo_hv if "error" not in yahoo_hv else (av_hv or yahoo_hv)
    iv = yahoo_iv

    # Build normalized raw_metrics schema with temporal data
    return {
        "group": "raw_metrics",
        "ticker": ticker.upper(),
        "metrics": {
            "vix": {
                "value": vix.get("value"),
                "data_type": "Daily",
                "as_of": vix.get("as_of"),  # FRED observation date
                "source": vix.get("source"),
                "fallback": vix.get("fallback", False)
            },
            "vxn": {
                "value": vxn.get("value"),
                "data_type": "Daily",
                "as_of": vxn.get("as_of"),  # FRED observation date
                "source": vxn.get("source"),
                "fallback": vxn.get("fallback", False)
            },
            "beta": {
                "value": beta.get("value") if beta else None,
                "data_type": "1Y",  # 1 year lookback
                "as_of": beta.get("as_of") if beta else None,
                "source": beta.get("source") if beta else None,
                "fallback": beta.get("fallback", False) if beta else True
            },
            "historical_volatility": {
                "value": hv.get("value") if hv else None,
                "data_type": "30D",  # 30 day lookback
                "as_of": hv.get("as_of") if hv else None,
                "source": hv.get("source") if hv else None,
                "fallback": hv.get("fallback", False) if hv else True
            },
            "implied_volatility": {
                "value": iv.get("value") if iv else None,
                "data_type": "Forward",  # Forward-looking from options
                "as_of": iv.get("as_of") if iv else None,
                "source": iv.get("source") if iv else None,
                "fallback": iv.get("fallback", False) if iv else True
            }
        },
        "source": "volatility-basket",
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def get_full_volatility_basket(ticker: str) -> dict:
    """
    Fetch all volatility metrics for a given ticker.
    Returns aggregated SWOT-ready data.
    """
    # Fetch all metrics concurrently
    vix_task = fetch_vix()
    beta_task = fetch_beta(ticker)
    hv_task = fetch_historical_volatility(ticker)
    iv_task = fetch_implied_volatility_proxy(ticker)

    vix, beta, hv, iv = await asyncio.gather(vix_task, beta_task, hv_task, iv_task)

    # Aggregate SWOT impacts
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    for metric in [vix, beta, hv, iv]:
        if "error" in metric:
            continue
        impact = metric.get("swot_category", "NEUTRAL")
        desc = f"{metric['metric']}: {metric.get('value', 'N/A')} - {metric.get('interpretation', '')}"

        if impact == "STRENGTH":
            swot_summary["strengths"].append(desc)
        elif impact == "WEAKNESS":
            swot_summary["weaknesses"].append(desc)
        elif impact == "OPPORTUNITY":
            swot_summary["opportunities"].append(desc)
        elif impact in ["THREAT", "SEVERE_THREAT"]:
            swot_summary["threats"].append(desc)

    return {
        "ticker": ticker.upper(),
        "metrics": {
            "vix": vix,
            "beta": beta,
            "historical_volatility": hv,
            "implied_volatility": iv
        },
        "swot_summary": swot_summary,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available volatility tools."""
    return [
        Tool(
            name="get_vix",
            description="Get current VIX (S&P 500 Volatility Index) level with SWOT interpretation. Indicates market-wide fear/greed.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_vxn",
            description="Get current VXN (Nasdaq-100 Volatility Index) level with SWOT interpretation. Use for tech/Nasdaq stocks.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_beta",
            description="Get Beta coefficient for a stock ticker. Measures volatility relative to market (S&P 500).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, TSLA)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_historical_volatility",
            description="Calculate historical volatility (annualized) from past price movements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Number of days to calculate volatility over (default: 30)",
                        "default": 30
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_implied_volatility",
            description="Get implied volatility from options market. Indicates expected future price movement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_volatility_basket",
            description="Get full volatility basket (VIX, Beta, HV, IV) with aggregated SWOT summary for a ticker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_all_sources_volatility",
            description="Get volatility from ALL sources (Yahoo + Alpha Vantage) with VIX/VXN market context for side-by-side comparison.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        )
    ]


# Global timeout for all tool operations (seconds)
TOOL_TIMEOUT = 90.0  # Match mcp_client timeout


async def _execute_tool_with_timeout(name: str, arguments: dict) -> dict:
    """Execute a tool with timeout. Returns result dict or error dict."""
    ticker = arguments.get("ticker", "").upper()

    if name == "get_vix":
        return await fetch_vix()
    elif name == "get_vxn":
        return await fetch_vxn()
    elif name == "get_beta":
        if not ticker:
            return {"error": "ticker is required"}
        return await fetch_beta(ticker)
    elif name == "get_historical_volatility":
        if not ticker:
            return {"error": "ticker is required"}
        period = arguments.get("period_days", 30)
        return await fetch_historical_volatility(ticker, period)
    elif name == "get_implied_volatility":
        if not ticker:
            return {"error": "ticker is required"}
        return await fetch_implied_volatility_proxy(ticker)
    elif name == "get_volatility_basket":
        if not ticker:
            return {"error": "ticker is required"}
        return await get_full_volatility_basket(ticker)
    elif name == "get_all_sources_volatility":
        if not ticker:
            return {"error": "ticker is required"}
        return await get_all_sources_volatility(ticker)
    else:
        return {"error": f"Unknown tool: {name}"}


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """
    Handle tool invocations with GUARANTEED JSON-RPC response.

    This function ALWAYS returns a valid TextContent response, even if:
    - External APIs timeout
    - Exceptions occur during processing
    - Any unexpected error happens

    This ensures MCP protocol compliance and prevents client hangs.
    """
    try:
        # Execute tool with global timeout
        try:
            result = await asyncio.wait_for(
                _execute_tool_with_timeout(name, arguments),
                timeout=TOOL_TIMEOUT
            )
        except asyncio.TimeoutError:
            ticker = arguments.get("ticker", "")
            logger.error(f"Tool {name} timed out after {TOOL_TIMEOUT}s for {ticker}")
            result = {
                "error": f"Tool execution timed out after {TOOL_TIMEOUT} seconds",
                "ticker": ticker,
                "tool": name,
                "source": "volatility-basket",
                "fallback": True
            }

        # Ensure result is JSON serializable
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except json.JSONDecodeError as e:
        logger.error(f"JSON serialization error for {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"JSON serialization failed: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "volatility-basket"
        }))]

    except Exception as e:
        # Catch-all: ALWAYS return valid JSON-RPC response
        logger.error(f"Unexpected error in {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "volatility-basket",
            "fallback": True
        }))]


# ============================================================
# MAIN
# ============================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
