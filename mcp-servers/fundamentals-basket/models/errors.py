"""
Error definitions for Financials-Basket MCP Server

Defines error codes and custom exceptions for inter-service communication.
"""

from dataclasses import dataclass
from typing import Optional


class ErrorCodes:
    """Standardized error codes for service communication."""

    # Fetcher errors
    CIK_NOT_FOUND = "CIK_NOT_FOUND"
    SEC_TIMEOUT = "SEC_TIMEOUT"
    SEC_RATE_LIMIT = "SEC_RATE_LIMIT"
    SEC_API_ERROR = "SEC_API_ERROR"

    YAHOO_TIMEOUT = "YAHOO_TIMEOUT"
    YAHOO_NO_DATA = "YAHOO_NO_DATA"
    YAHOO_API_ERROR = "YAHOO_API_ERROR"

    # Circuit breaker errors
    CIRCUIT_OPEN = "CIRCUIT_OPEN"

    # Parser errors
    INVALID_FACTS = "INVALID_FACTS"
    CONCEPT_NOT_FOUND = "CONCEPT_NOT_FOUND"
    PARSE_ERROR = "PARSE_ERROR"

    # General errors
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ServiceError:
    """
    Structured error for service communication.

    Includes metadata for error handling and retry decisions.
    """
    code: str
    message: str
    source: str
    recoverable: bool = True
    retry_after: Optional[float] = None  # seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "error": self.code,
            "message": self.message,
            "source": self.source,
            "recoverable": self.recoverable,
        }
        if self.retry_after:
            result["retry_after"] = self.retry_after
        return result


class FinancialsServiceError(Exception):
    """Base exception for financials service errors."""

    def __init__(self, code: str, message: str, source: str = "Unknown"):
        self.code = code
        self.message = message
        self.source = source
        super().__init__(f"[{code}] {message}")

    def to_service_error(self, recoverable: bool = True) -> ServiceError:
        """Convert to ServiceError for API response."""
        return ServiceError(
            code=self.code,
            message=self.message,
            source=self.source,
            recoverable=recoverable,
        )


class CIKNotFoundError(FinancialsServiceError):
    """Raised when CIK cannot be found for a ticker."""

    def __init__(self, ticker: str):
        super().__init__(
            code=ErrorCodes.CIK_NOT_FOUND,
            message=f"Could not find CIK for ticker {ticker}",
            source="SEC EDGAR",
        )
        self.ticker = ticker


class APITimeoutError(FinancialsServiceError):
    """Raised when an API call times out."""

    def __init__(self, source: str, timeout: float):
        super().__init__(
            code=ErrorCodes.TIMEOUT,
            message=f"API call timed out after {timeout}s",
            source=source,
        )
        self.timeout = timeout


class CircuitOpenError(FinancialsServiceError):
    """Raised when circuit breaker is open."""

    def __init__(self, source: str, retry_after: float):
        super().__init__(
            code=ErrorCodes.CIRCUIT_OPEN,
            message=f"Circuit breaker open for {source}",
            source=source,
        )
        self.retry_after = retry_after

    def to_service_error(self, recoverable: bool = True) -> ServiceError:
        """Convert to ServiceError with retry_after."""
        error = super().to_service_error(recoverable)
        error.retry_after = self.retry_after
        return error


class RateLimitError(FinancialsServiceError):
    """Raised when rate limit is exceeded."""

    def __init__(self, source: str, retry_after: float):
        super().__init__(
            code=ErrorCodes.SEC_RATE_LIMIT if "SEC" in source else ErrorCodes.TIMEOUT,
            message=f"Rate limit exceeded for {source}",
            source=source,
        )
        self.retry_after = retry_after

    def to_service_error(self, recoverable: bool = True) -> ServiceError:
        """Convert to ServiceError with retry_after."""
        error = super().to_service_error(recoverable)
        error.retry_after = self.retry_after
        return error


class ParseError(FinancialsServiceError):
    """Raised when parsing fails."""

    def __init__(self, message: str, source: str = "Parser"):
        super().__init__(
            code=ErrorCodes.PARSE_ERROR,
            message=message,
            source=source,
        )
