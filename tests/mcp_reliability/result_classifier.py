"""
Result Classifier - Classifies MCP server responses for reliability analysis.

Classification categories:
- SUCCESS: Valid response with expected data
- PARTIAL: Response OK but missing some fields
- FALLBACK: Primary source failed, secondary succeeded
- TRANSIENT: Temporary error (rate limit, timeout)
- PERSISTENT: Repeated failures
- HARD_FAILURE: Unrecoverable error
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ResultCategory(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FALLBACK = "fallback"
    TRANSIENT = "transient"
    PERSISTENT = "persistent"
    HARD_FAILURE = "hard_failure"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    HF_DEPENDENCY = "hf_dependency"
    COLD_START = "cold_start"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of classifying an MCP response."""
    category: ResultCategory
    server: str
    ticker: str
    latency_ms: float
    data_completeness: float  # 0.0 to 1.0
    fallback_used: bool = False
    primary_source: Optional[str] = None
    fallback_source: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "category": self.category.value,
            "server": self.server,
            "ticker": self.ticker,
            "latency_ms": self.latency_ms,
            "data_completeness": self.data_completeness,
            "fallback_used": self.fallback_used,
            "primary_source": self.primary_source,
            "fallback_source": self.fallback_source,
            "error_message": self.error_message
        }

    def to_json(self) -> str:
        """Convert to JSON string for logging."""
        return json.dumps(self.to_dict())


class ResultClassifier:
    """Classifies MCP server responses based on content and error patterns."""

    # Expected fields per server for completeness calculation
    EXPECTED_FIELDS = {
        "fundamentals-basket": {
            "required": ["ticker", "financials"],
            "optional": ["debt", "cash_flow", "swot_category"]
        },
        "valuation-basket": {
            "required": ["metrics"],
            "optional": ["overall_signal", "swot_category"]
        },
        "volatility-basket": {
            "required": ["metrics"],
            "optional": ["swot_category", "interpretation"]
        },
        "macro-basket": {
            "required": ["metrics"],
            "optional": ["swot_category", "interpretation"]
        },
        "news-basket": {
            "required": ["results"],
            "optional": ["query", "source"]
        },
        "sentiment-basket": {
            "required": ["composite_score"],
            "optional": ["finnhub_score", "reddit_score", "overall_swot_category"]
        }
    }

    # Fallback detection patterns
    FALLBACK_INDICATORS = {
        "fundamentals-basket": {
            "field": "source",
            "fallback_values": ["yahoo_fallback", "yfinance"]
        },
        "volatility-basket": {
            "field": "vix_source",
            "fallback_values": ["yahoo", "yfinance"]
        },
        "news-basket": {
            "primary_field": "tavily_results",
            "fallback_field": "nyt_results"
        },
        "sentiment-basket": {
            "field": "finnhub_score",
            "fallback_indicator": None  # null means fallback to reddit
        }
    }

    def __init__(self):
        self.attempt_counts: Dict[str, int] = {}  # Track consecutive failures

    def classify(
        self,
        server: str,
        ticker: str,
        response: Optional[Dict],
        error: Optional[Exception],
        latency_ms: float
    ) -> ClassificationResult:
        """Classify an MCP server response.

        Args:
            server: MCP server name
            ticker: Stock ticker tested
            response: Response dict (if successful)
            error: Exception (if failed)
            latency_ms: Request latency

        Returns:
            ClassificationResult with category and metadata
        """
        key = f"{server}:{ticker}"

        # Handle errors first
        if error:
            return self._classify_error(server, ticker, error, latency_ms)

        # Handle missing response
        if response is None:
            return ClassificationResult(
                category=ResultCategory.HARD_FAILURE,
                server=server,
                ticker=ticker,
                latency_ms=latency_ms,
                data_completeness=0.0,
                error_message="No response received"
            )

        # Check for error in response
        if isinstance(response, dict) and "error" in response:
            return self._classify_response_error(server, ticker, response, latency_ms)

        # Successful response - check completeness and fallback
        completeness = self._calculate_completeness(server, response)
        fallback_info = self._detect_fallback(server, response)

        # Reset failure counter on success
        self.attempt_counts[key] = 0

        if fallback_info["used"]:
            return ClassificationResult(
                category=ResultCategory.FALLBACK,
                server=server,
                ticker=ticker,
                latency_ms=latency_ms,
                data_completeness=completeness,
                fallback_used=True,
                primary_source=fallback_info.get("primary"),
                fallback_source=fallback_info.get("fallback"),
                raw_response=response
            )
        elif completeness < 0.5:
            return ClassificationResult(
                category=ResultCategory.PARTIAL,
                server=server,
                ticker=ticker,
                latency_ms=latency_ms,
                data_completeness=completeness,
                raw_response=response
            )
        else:
            return ClassificationResult(
                category=ResultCategory.SUCCESS,
                server=server,
                ticker=ticker,
                latency_ms=latency_ms,
                data_completeness=completeness,
                raw_response=response
            )

    def _classify_error(
        self,
        server: str,
        ticker: str,
        error: Exception,
        latency_ms: float
    ) -> ClassificationResult:
        """Classify an error response."""
        key = f"{server}:{ticker}"
        error_str = str(error).lower()

        # Increment attempt counter
        self.attempt_counts[key] = self.attempt_counts.get(key, 0) + 1
        attempts = self.attempt_counts[key]

        # Classify error type
        if "429" in error_str or "rate limit" in error_str:
            category = ResultCategory.RATE_LIMITED
        elif "timeout" in error_str or "timed out" in error_str:
            category = ResultCategory.TIMEOUT
        elif "huggingface" in error_str or "hf.space" in error_str:
            category = ResultCategory.HF_DEPENDENCY
        elif "cold start" in error_str:
            category = ResultCategory.COLD_START
        elif "503" in error_str or "502" in error_str or "500" in error_str:
            category = ResultCategory.TRANSIENT if attempts < 3 else ResultCategory.PERSISTENT
        elif "400" in error_str or "401" in error_str or "403" in error_str or "404" in error_str:
            category = ResultCategory.HARD_FAILURE
        else:
            category = ResultCategory.TRANSIENT if attempts < 3 else ResultCategory.PERSISTENT

        return ClassificationResult(
            category=category,
            server=server,
            ticker=ticker,
            latency_ms=latency_ms,
            data_completeness=0.0,
            error_message=str(error)
        )

    def _classify_response_error(
        self,
        server: str,
        ticker: str,
        response: Dict,
        latency_ms: float
    ) -> ClassificationResult:
        """Classify an error embedded in a response."""
        error_msg = response.get("error", "Unknown error")

        return ClassificationResult(
            category=ResultCategory.HARD_FAILURE,
            server=server,
            ticker=ticker,
            latency_ms=latency_ms,
            data_completeness=0.0,
            error_message=error_msg,
            raw_response=response
        )

    def _calculate_completeness(self, server: str, response: Dict) -> float:
        """Calculate data completeness for a response."""
        schema = self.EXPECTED_FIELDS.get(server, {"required": [], "optional": []})

        required = schema["required"]
        optional = schema["optional"]

        if not required and not optional:
            return 1.0  # Unknown server, assume complete

        required_present = sum(1 for f in required if f in response and response[f])
        optional_present = sum(1 for f in optional if f in response and response[f])

        total_required = len(required)
        total_optional = len(optional)

        if total_required == 0:
            return 1.0 if total_optional == 0 else optional_present / total_optional

        # Weight: required fields = 70%, optional = 30%
        required_score = required_present / total_required if total_required else 1.0
        optional_score = optional_present / total_optional if total_optional else 1.0

        return 0.7 * required_score + 0.3 * optional_score

    def _detect_fallback(self, server: str, response: Dict) -> Dict:
        """Detect if fallback was used in response."""
        indicators = self.FALLBACK_INDICATORS.get(server)
        if not indicators:
            return {"used": False}

        # Simple field-based detection
        if "field" in indicators:
            field = indicators["field"]
            value = response.get(field)

            if "fallback_values" in indicators:
                if value in indicators["fallback_values"]:
                    return {
                        "used": True,
                        "primary": f"primary_{server}",
                        "fallback": value
                    }

            if "fallback_indicator" in indicators:
                if value is indicators["fallback_indicator"]:
                    return {
                        "used": True,
                        "primary": field,
                        "fallback": "alternative"
                    }

        # News-basket: check if primary is empty but fallback has data
        if "primary_field" in indicators and "fallback_field" in indicators:
            primary = response.get(indicators["primary_field"], [])
            fallback = response.get(indicators["fallback_field"], [])
            if not primary and fallback:
                return {
                    "used": True,
                    "primary": indicators["primary_field"],
                    "fallback": indicators["fallback_field"]
                }

        return {"used": False}

    def reset_counters(self):
        """Reset all attempt counters."""
        self.attempt_counts.clear()


class ResultAggregator:
    """Aggregates classification results for analysis."""

    def __init__(self):
        self.results: List[ClassificationResult] = []
        self.counts: Dict[ResultCategory, int] = {cat: 0 for cat in ResultCategory}
        self.by_server: Dict[str, Dict[ResultCategory, int]] = {}
        self.latencies: List[float] = []

    def add(self, result: ClassificationResult):
        """Add a classification result."""
        self.results.append(result)
        self.counts[result.category] += 1
        self.latencies.append(result.latency_ms)

        if result.server not in self.by_server:
            self.by_server[result.server] = {cat: 0 for cat in ResultCategory}
        self.by_server[result.server][result.category] += 1

    def summary(self) -> Dict:
        """Generate summary statistics."""
        total = len(self.results)
        if total == 0:
            return {"total": 0, "success_rate": 0.0}

        success_count = self.counts[ResultCategory.SUCCESS] + self.counts[ResultCategory.PARTIAL]
        fallback_count = self.counts[ResultCategory.FALLBACK]

        return {
            "total": total,
            "success_rate": (success_count + fallback_count) / total,
            "fallback_rate": fallback_count / total,
            "failure_rate": sum(
                self.counts[c] for c in [
                    ResultCategory.HARD_FAILURE,
                    ResultCategory.PERSISTENT
                ]
            ) / total,
            "by_category": {cat.value: count for cat, count in self.counts.items()},
            "by_server": {
                server: {cat.value: count for cat, count in cats.items()}
                for server, cats in self.by_server.items()
            },
            "latency_p50": sorted(self.latencies)[len(self.latencies)//2] if self.latencies else 0,
            "latency_p95": sorted(self.latencies)[int(len(self.latencies)*0.95)] if self.latencies else 0,
            "latency_p99": sorted(self.latencies)[int(len(self.latencies)*0.99)] if self.latencies else 0
        }


if __name__ == "__main__":
    # Demo usage
    classifier = ResultClassifier()
    aggregator = ResultAggregator()

    # Simulate some results
    test_cases = [
        ("fundamentals-basket", "AAPL", {"ticker": "AAPL", "financials": {"revenue": 1000}}, None, 250),
        ("fundamentals-basket", "MSFT", {"ticker": "MSFT", "financials": {"revenue": 2000}, "source": "yahoo_fallback"}, None, 500),
        ("valuation-basket", "GOOGL", {"metrics": {"pe_ratio": 25}}, None, 150),
        ("news-basket", "TSLA", None, Exception("429 Rate limit exceeded"), 0),
        ("sentiment-basket", "NVDA", {"error": "Finnhub API key invalid"}, None, 100),
    ]

    for server, ticker, response, error, latency in test_cases:
        result = classifier.classify(server, ticker, response, error, latency)
        aggregator.add(result)
        print(f"{ticker} via {server}: {result.category.value}")

    print("\nSummary:")
    print(json.dumps(aggregator.summary(), indent=2))
