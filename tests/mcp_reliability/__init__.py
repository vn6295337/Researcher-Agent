"""
MCP Server Reliability Testing Framework

Provides high-frequency, randomized stress testing for MCP servers with:
- Company sampling strategies
- Rate limiting protection
- Circuit breaker patterns
- Result classification and aggregation
"""

from .company_sampler import CompanySampler, SamplingStrategy, create_test_batch
from .rate_limiter import get_rate_limiter_registry, RateLimiterRegistry
from .circuit_breaker import get_circuit_breaker_registry, CircuitBreakerRegistry
from .result_classifier import ResultClassifier, ResultAggregator, ResultCategory

__all__ = [
    "CompanySampler",
    "SamplingStrategy",
    "create_test_batch",
    "get_rate_limiter_registry",
    "RateLimiterRegistry",
    "get_circuit_breaker_registry",
    "CircuitBreakerRegistry",
    "ResultClassifier",
    "ResultAggregator",
    "ResultCategory",
]
