"""
Models package for Financials-Basket MCP Server

Contains data schemas and error definitions.
"""

from .schemas import (
    TemporalMetric,
    ParsedFinancials,
    DebtMetrics,
    CashFlowMetrics,
    SwotSummary,
    FinancialsBasket,
    FetchResult,
)
from .errors import (
    ServiceError,
    ErrorCodes,
    CIKNotFoundError,
    APITimeoutError,
    CircuitOpenError,
    RateLimitError,
)

__all__ = [
    # Schemas
    "TemporalMetric",
    "ParsedFinancials",
    "DebtMetrics",
    "CashFlowMetrics",
    "SwotSummary",
    "FinancialsBasket",
    "FetchResult",
    # Errors
    "ServiceError",
    "ErrorCodes",
    "CIKNotFoundError",
    "APITimeoutError",
    "CircuitOpenError",
    "RateLimitError",
]
