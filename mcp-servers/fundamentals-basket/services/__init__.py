"""
Services package for Financials-Basket MCP Server

Contains the microservices:
- CacheService: CIK and facts caching with TTL
- FetcherService: HTTP clients with retry, rate limiting, circuit breaker
- ParserService: XBRL parsing, ratio calculations, temporal metadata
- OrchestratorService: Request routing, fallback chain coordination
"""

from .cache import CacheService
from .fetcher import FetcherService
from .parser import ParserService
from .orchestrator import OrchestratorService

__all__ = [
    "CacheService",
    "FetcherService",
    "ParserService",
    "OrchestratorService",
]
