"""
Cache Service for Financials-Basket MCP Server

Provides in-memory caching with TTL for:
- CIK lookups (24h TTL - rarely changes)
- Company facts (1h TTL - changes with filings)
- Company info (24h TTL)

Thread-safe with asyncio.Lock.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from config import (
    CIK_CACHE_TTL,
    FACTS_CACHE_TTL,
    COMPANY_INFO_CACHE_TTL,
)

logger = logging.getLogger("fundamentals-basket.cache")


@dataclass
class CacheEntry:
    """A cached value with timestamp and TTL."""
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: float = 3600  # Default 1 hour

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return (time.time() - self.timestamp) >= self.ttl


class CacheService:
    """
    In-memory cache service with TTL support.

    Features:
    - Async-safe with locks
    - Automatic expiration checking
    - Separate caches for CIK, facts, and company info
    - Metrics for cache hits/misses
    """

    def __init__(self):
        self._cik_cache: Dict[str, CacheEntry] = {}
        self._facts_cache: Dict[str, CacheEntry] = {}
        self._company_info_cache: Dict[str, CacheEntry] = {}

        self._lock = asyncio.Lock()

        # Metrics
        self._hits = 0
        self._misses = 0

    # =========================================================================
    # CIK CACHE
    # =========================================================================

    async def get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK for a ticker from cache.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK string if cached and not expired, None otherwise
        """
        ticker = ticker.upper()
        async with self._lock:
            entry = self._cik_cache.get(ticker)
            if entry and not entry.is_expired():
                self._hits += 1
                logger.debug(f"Cache HIT: CIK for {ticker}")
                return entry.value
            elif entry:
                # Expired, remove it
                del self._cik_cache[ticker]

            self._misses += 1
            logger.debug(f"Cache MISS: CIK for {ticker}")
            return None

    async def set_cik(self, ticker: str, cik: str) -> None:
        """
        Cache CIK for a ticker.

        Args:
            ticker: Stock ticker symbol
            cik: The CIK value to cache
        """
        ticker = ticker.upper()
        async with self._lock:
            self._cik_cache[ticker] = CacheEntry(
                value=cik,
                ttl=CIK_CACHE_TTL,
            )
            logger.debug(f"Cache SET: CIK for {ticker} = {cik}")

    # =========================================================================
    # FACTS CACHE
    # =========================================================================

    async def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company facts from cache.

        Args:
            cik: CIK identifier (10-digit padded)

        Returns:
            Company facts dict if cached and not expired, None otherwise
        """
        async with self._lock:
            entry = self._facts_cache.get(cik)
            if entry and not entry.is_expired():
                self._hits += 1
                logger.debug(f"Cache HIT: Facts for CIK {cik}")
                return entry.value
            elif entry:
                del self._facts_cache[cik]

            self._misses += 1
            logger.debug(f"Cache MISS: Facts for CIK {cik}")
            return None

    async def set_company_facts(
        self,
        cik: str,
        facts: Dict[str, Any],
        ttl: Optional[float] = None
    ) -> None:
        """
        Cache company facts.

        Args:
            cik: CIK identifier
            facts: Company facts dictionary
            ttl: Optional custom TTL (defaults to FACTS_CACHE_TTL)
        """
        async with self._lock:
            self._facts_cache[cik] = CacheEntry(
                value=facts,
                ttl=ttl or FACTS_CACHE_TTL,
            )
            logger.debug(f"Cache SET: Facts for CIK {cik}")

    # =========================================================================
    # COMPANY INFO CACHE
    # =========================================================================

    async def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company info from cache.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company info dict if cached and not expired, None otherwise
        """
        ticker = ticker.upper()
        async with self._lock:
            entry = self._company_info_cache.get(ticker)
            if entry and not entry.is_expired():
                self._hits += 1
                logger.debug(f"Cache HIT: Info for {ticker}")
                return entry.value
            elif entry:
                del self._company_info_cache[ticker]

            self._misses += 1
            logger.debug(f"Cache MISS: Info for {ticker}")
            return None

    async def set_company_info(
        self,
        ticker: str,
        info: Dict[str, Any],
        ttl: Optional[float] = None
    ) -> None:
        """
        Cache company info.

        Args:
            ticker: Stock ticker symbol
            info: Company info dictionary
            ttl: Optional custom TTL (defaults to COMPANY_INFO_CACHE_TTL)
        """
        ticker = ticker.upper()
        async with self._lock:
            self._company_info_cache[ticker] = CacheEntry(
                value=info,
                ttl=ttl or COMPANY_INFO_CACHE_TTL,
            )
            logger.debug(f"Cache SET: Info for {ticker}")

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    async def clear(self) -> None:
        """Clear all caches."""
        async with self._lock:
            self._cik_cache.clear()
            self._facts_cache.clear()
            self._company_info_cache.clear()
            logger.info("All caches cleared")

    async def clear_expired(self) -> int:
        """
        Remove all expired entries from caches.

        Returns:
            Number of entries removed
        """
        removed = 0
        async with self._lock:
            for cache in [
                self._cik_cache,
                self._facts_cache,
                self._company_info_cache
            ]:
                expired_keys = [
                    k for k, v in cache.items() if v.is_expired()
                ]
                for key in expired_keys:
                    del cache[key]
                    removed += 1

        if removed > 0:
            logger.info(f"Cleared {removed} expired cache entries")
        return removed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_rate, 2),
            "cik_cache_size": len(self._cik_cache),
            "facts_cache_size": len(self._facts_cache),
            "company_info_cache_size": len(self._company_info_cache),
        }


# Global cache instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
