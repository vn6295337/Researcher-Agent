"""
Rate Limiter - Token bucket and sliding window implementations for API rate limiting.

Prevents self-DoS during stress testing by enforcing per-API rate limits.
"""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import deque
import threading


@dataclass
class TokenBucket:
    """Token bucket rate limiter.

    Allows bursting up to capacity, refills at steady rate.
    Thread-safe implementation.
    """
    rate: float  # Tokens per second
    capacity: int  # Maximum tokens (burst capacity)
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
            # Wait for estimated refill time
            wait_time = min(0.1, (tokens - self.tokens) / self.rate)
            await asyncio.sleep(max(0.01, wait_time))
        return False

    def tokens_available(self) -> float:
        """Get current available tokens (without modifying state)."""
        with self._lock:
            self._refill()
            return self.tokens


@dataclass
class SlidingWindowLimiter:
    """Sliding window rate limiter.

    Tracks requests in a time window, more accurate than token bucket
    for strict rate limits.
    """
    max_requests: int  # Maximum requests in window
    window_seconds: float  # Window duration
    _requests: deque = field(default_factory=deque, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _cleanup(self):
        """Remove expired timestamps from window."""
        cutoff = time.monotonic() - self.window_seconds
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    def acquire(self) -> bool:
        """Try to acquire a request slot. Returns True if allowed."""
        with self._lock:
            self._cleanup()
            if len(self._requests) < self.max_requests:
                self._requests.append(time.monotonic())
                return True
            return False

    async def acquire_async(self, timeout: float = 30.0) -> bool:
        """Async version - waits until slot available or timeout."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self.acquire():
                return True
            # Estimate wait time until oldest request expires
            with self._lock:
                if self._requests:
                    oldest = self._requests[0]
                    wait_time = max(0.01, oldest + self.window_seconds - time.monotonic())
                else:
                    wait_time = 0.01
            await asyncio.sleep(min(0.5, wait_time))
        return False

    def requests_in_window(self) -> int:
        """Get current request count in window."""
        with self._lock:
            self._cleanup()
            return len(self._requests)


class DailyQuotaTracker:
    """Tracks daily API quota usage.

    For APIs with daily limits (NYT: 500/day, NewsAPI: 100/day).
    """

    def __init__(self, daily_limit: int, name: str = "api"):
        self.daily_limit = daily_limit
        self.name = name
        self.used = 0
        self.reset_date = self._current_date()
        self._lock = threading.Lock()

    def _current_date(self) -> str:
        return time.strftime("%Y-%m-%d")

    def _check_reset(self):
        """Reset counter if day changed."""
        today = self._current_date()
        if today != self.reset_date:
            self.used = 0
            self.reset_date = today

    def acquire(self, count: int = 1) -> bool:
        """Try to use quota. Returns True if within limit."""
        with self._lock:
            self._check_reset()
            if self.used + count <= self.daily_limit:
                self.used += count
                return True
            return False

    def remaining(self) -> int:
        """Get remaining quota for today."""
        with self._lock:
            self._check_reset()
            return max(0, self.daily_limit - self.used)


class RateLimiterRegistry:
    """Registry of rate limiters for different APIs.

    Centralizes rate limit configuration and provides unified access.
    """

    def __init__(self):
        self.limiters: Dict[str, TokenBucket | SlidingWindowLimiter] = {}
        self.quotas: Dict[str, DailyQuotaTracker] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        """Configure default rate limiters based on known API limits."""
        # Token bucket limiters (burst-friendly)
        self.limiters["sec_edgar"] = TokenBucket(rate=10, capacity=10)
        self.limiters["yahoo_finance"] = TokenBucket(rate=5, capacity=20)
        self.limiters["finnhub"] = TokenBucket(rate=1, capacity=5)

        # Sliding window limiters (strict limits)
        self.limiters["fred"] = SlidingWindowLimiter(max_requests=120, window_seconds=60)
        self.limiters["reddit"] = SlidingWindowLimiter(max_requests=100, window_seconds=60)

        # Daily quota trackers
        self.quotas["nyt"] = DailyQuotaTracker(daily_limit=500, name="NYT")
        self.quotas["newsapi"] = DailyQuotaTracker(daily_limit=100, name="NewsAPI")
        self.quotas["tavily"] = DailyQuotaTracker(daily_limit=33, name="Tavily")  # ~1000/month

    def get_limiter(self, api: str) -> Optional[TokenBucket | SlidingWindowLimiter]:
        """Get rate limiter for an API."""
        return self.limiters.get(api.lower())

    def get_quota(self, api: str) -> Optional[DailyQuotaTracker]:
        """Get quota tracker for an API."""
        return self.quotas.get(api.lower())

    async def acquire(self, api: str, timeout: float = 30.0) -> bool:
        """Acquire rate limit and quota for an API.

        Returns True if both rate limit and quota allow the request.
        """
        api_lower = api.lower()

        # Check daily quota first (faster to reject)
        quota = self.quotas.get(api_lower)
        if quota and not quota.acquire():
            return False

        # Then check rate limiter
        limiter = self.limiters.get(api_lower)
        if limiter:
            return await limiter.acquire_async(timeout=timeout)

        # No limiter configured - allow by default
        return True

    def status(self) -> Dict:
        """Get status of all rate limiters and quotas."""
        status = {"limiters": {}, "quotas": {}}

        for name, limiter in self.limiters.items():
            if isinstance(limiter, TokenBucket):
                status["limiters"][name] = {
                    "type": "token_bucket",
                    "available": limiter.tokens_available(),
                    "capacity": limiter.capacity
                }
            elif isinstance(limiter, SlidingWindowLimiter):
                status["limiters"][name] = {
                    "type": "sliding_window",
                    "used": limiter.requests_in_window(),
                    "max": limiter.max_requests
                }

        for name, quota in self.quotas.items():
            status["quotas"][name] = {
                "remaining": quota.remaining(),
                "daily_limit": quota.daily_limit
            }

        return status


# Global registry instance
_registry: Optional[RateLimiterRegistry] = None


def get_rate_limiter_registry() -> RateLimiterRegistry:
    """Get the global rate limiter registry."""
    global _registry
    if _registry is None:
        _registry = RateLimiterRegistry()
    return _registry


if __name__ == "__main__":
    import asyncio

    async def demo():
        registry = get_rate_limiter_registry()
        print("Initial status:", registry.status())

        # Simulate some API calls
        for api in ["sec_edgar", "fred", "nyt"]:
            result = await registry.acquire(api)
            print(f"{api}: {'allowed' if result else 'blocked'}")

        print("\nAfter requests:", registry.status())

    asyncio.run(demo())
