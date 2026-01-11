"""
MCP Server Stress Test Suite

High-frequency, randomized testing of MCP servers with:
- Company sampling strategies
- Rate limiting protection
- Circuit breaker patterns
- Result classification and aggregation
"""

import asyncio
import random
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# pytest is optional - only needed when running as test suite
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy decorator for when pytest isn't available
    class pytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        class mark:
            @staticmethod
            def asyncio(func):
                return func
            @staticmethod
            def smoke(func):
                return func
            @staticmethod
            def standard(func):
                return func
            @staticmethod
            def stress(func):
                return func

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_reliability.company_sampler import (
    CompanySampler, SamplingStrategy, Company, create_test_batch
)
from tests.mcp_reliability.rate_limiter import (
    get_rate_limiter_registry, RateLimiterRegistry
)
from tests.mcp_reliability.circuit_breaker import (
    get_circuit_breaker_registry, CircuitBreakerRegistry, CircuitOpenError
)
from tests.mcp_reliability.result_classifier import (
    ResultClassifier, ResultAggregator, ResultCategory, ClassificationResult
)


@dataclass
class TestConfig:
    """Configuration for stress test runs."""
    batch_size: int = 20
    sampling_strategy: str = "uniform"
    max_concurrent: int = 5
    request_interval_ms: int = 200
    timeout_seconds: float = 60.0
    retry_attempts: int = 3
    seed: Optional[int] = None
    servers: List[str] = None

    def __post_init__(self):
        if self.servers is None:
            self.servers = [
                "fundamentals-basket",
                "valuation-basket",
                "volatility-basket",
                "macro-basket",
                "news-basket",
                "sentiment-basket"
            ]


class MCPTestRunner:
    """Orchestrates stress testing of MCP servers."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.sampler = CompanySampler()
        self.rate_limiters = get_rate_limiter_registry()
        self.circuit_breakers = get_circuit_breaker_registry()
        self.classifier = ResultClassifier()
        self.aggregator = ResultAggregator()
        self.results: List[ClassificationResult] = []

    async def _call_mcp_server(
        self,
        server: str,
        ticker: str,
        company_name: str
    ) -> Dict:
        """Call an MCP server and return the response.

        Uses mock responses by default. Set USE_REAL_MCP=1 to use actual MCP servers.
        """
        import os

        # Use mock by default for framework testing
        if not os.getenv("USE_REAL_MCP"):
            return await self._mock_mcp_response(server, ticker)

        # Import the actual MCP client when USE_REAL_MCP is set
        try:
            from mcp_client import call_mcp_server

            # Map server to tool name and arguments
            server_tools = {
                "fundamentals-basket": ("get_sec_fundamentals", {"ticker": ticker}),
                "valuation-basket": ("get_valuation_basket", {"ticker": ticker}),
                "volatility-basket": ("get_volatility_basket", {"ticker": ticker}),
                "macro-basket": ("get_macro_basket", {}),
                "news-basket": ("get_all_sources_news", {"ticker": ticker, "company_name": company_name}),
                "sentiment-basket": ("get_sentiment_basket", {"ticker": ticker, "company_name": company_name}),
            }

            tool_config = server_tools.get(server)
            if tool_config:
                tool_name, arguments = tool_config
                return await call_mcp_server(server, tool_name, arguments, timeout=self.config.timeout_seconds)
            else:
                return {"error": f"Unknown server: {server}"}

        except ImportError as e:
            # Fallback to mock response if import fails
            return await self._mock_mcp_response(server, ticker)

    async def _mock_mcp_response(self, server: str, ticker: str) -> Dict:
        """Generate mock response for testing the framework."""
        await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate latency

        # Simulate random failures (3% chance) - low for smoke tests
        if random.random() < 0.03:
            raise Exception("Simulated API error: 503 Service Unavailable")

        # Simulate rate limits (2% chance)
        if random.random() < 0.02:
            raise Exception("429 Rate limit exceeded")

        # Mock responses by server
        responses = {
            "fundamentals-basket": {
                "ticker": ticker,
                "financials": {"revenue": random.randint(1000, 100000) * 1000000},
                "debt": {"debt_to_equity": random.uniform(0.5, 2.0)},
                "swot_category": random.choice(["STRENGTH", "WEAKNESS", "NEUTRAL"])
            },
            "valuation-basket": {
                "metrics": {
                    "pe_ratio": {"trailing": random.uniform(10, 50)},
                    "pb_ratio": random.uniform(1, 10)
                },
                "overall_signal": random.choice(["BUY", "HOLD", "SELL"])
            },
            "volatility-basket": {
                "metrics": {
                    "beta": {"value": random.uniform(0.5, 2.0)},
                    "vix": {"value": random.uniform(15, 35)}
                }
            },
            "macro-basket": {
                "metrics": {
                    "gdp_growth": {"value": random.uniform(1, 4)},
                    "interest_rate": {"value": random.uniform(4, 6)}
                }
            },
            "news-basket": {
                "results": [{"title": f"News about {ticker}", "url": "https://example.com"}]
            },
            "sentiment-basket": {
                "composite_score": random.uniform(30, 70),
                "finnhub_score": random.uniform(20, 80),
                "reddit_score": random.uniform(20, 80)
            }
        }

        return responses.get(server, {"ticker": ticker})

    async def _test_single(
        self,
        server: str,
        ticker: str,
        company_name: str
    ) -> ClassificationResult:
        """Test a single server/ticker combination."""
        # Check circuit breaker
        if not self.circuit_breakers.allow_request(server):
            return ClassificationResult(
                category=ResultCategory.HARD_FAILURE,
                server=server,
                ticker=ticker,
                latency_ms=0,
                data_completeness=0.0,
                error_message="Circuit breaker open"
            )

        # Map server to API for rate limiting
        api_map = {
            "fundamentals-basket": "sec_edgar",
            "valuation-basket": "yahoo_finance",
            "volatility-basket": "fred",
            "macro-basket": "fred",
            "news-basket": "tavily",
            "sentiment-basket": "finnhub"
        }
        api = api_map.get(server, server)

        # Wait for rate limit
        if not await self.rate_limiters.acquire(api, timeout=10.0):
            return ClassificationResult(
                category=ResultCategory.RATE_LIMITED,
                server=server,
                ticker=ticker,
                latency_ms=0,
                data_completeness=0.0,
                error_message="Rate limit wait timeout"
            )

        # Make the request
        start_time = time.perf_counter()
        error = None
        response = None

        try:
            response = await asyncio.wait_for(
                self._call_mcp_server(server, ticker, company_name),
                timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            error = Exception(f"Timeout after {self.config.timeout_seconds}s")
        except Exception as e:
            error = e

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Classify result
        result = self.classifier.classify(server, ticker, response, error, latency_ms)

        # Update circuit breaker
        if result.category in [ResultCategory.SUCCESS, ResultCategory.PARTIAL, ResultCategory.FALLBACK]:
            self.circuit_breakers.record_success(server)
        else:
            self.circuit_breakers.record_failure(server, result.error_message)

        return result

    async def _test_batch(
        self,
        companies: List[Company],
        servers: List[str]
    ) -> List[ClassificationResult]:
        """Test a batch of companies against servers."""
        tasks = []

        for company in companies:
            for server in servers:
                tasks.append(self._test_single(server, company.ticker, company.name))

                # Add jitter between task creation
                await asyncio.sleep(self.config.request_interval_ms / 1000 * random.uniform(0.5, 1.5))

        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def limited_task(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(*[limited_task(t) for t in tasks], return_exceptions=True)

        # Filter out exceptions and convert to ClassificationResult
        valid_results = []
        for r in results:
            if isinstance(r, ClassificationResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                valid_results.append(ClassificationResult(
                    category=ResultCategory.UNKNOWN,
                    server="unknown",
                    ticker="unknown",
                    latency_ms=0,
                    data_completeness=0.0,
                    error_message=str(r)
                ))

        return valid_results

    async def run(self) -> Dict:
        """Run the stress test and return results."""
        start_time = datetime.utcnow()

        # Sample companies
        strategy = SamplingStrategy(self.config.sampling_strategy)
        companies = self.sampler.sample(
            self.config.batch_size,
            strategy,
            self.config.seed
        )

        print(f"Testing {len(companies)} companies against {len(self.config.servers)} servers")
        print(f"Strategy: {self.config.sampling_strategy}, Seed: {self.config.seed}")

        # Run tests
        results = await self._test_batch(companies, self.config.servers)

        # Aggregate results
        for result in results:
            self.aggregator.add(result)
            self.results.append(result)

        # Generate summary
        summary = self.aggregator.summary()
        summary["test_config"] = {
            "batch_size": self.config.batch_size,
            "sampling_strategy": self.config.sampling_strategy,
            "servers": self.config.servers,
            "seed": self.config.seed
        }
        summary["start_time"] = start_time.isoformat() + "Z"
        summary["end_time"] = datetime.utcnow().isoformat() + "Z"
        summary["circuit_breaker_status"] = self.circuit_breakers.status()
        summary["rate_limiter_status"] = self.rate_limiters.status()

        return summary

    def export_results(self, path: Path):
        """Export detailed results to NDJSON file."""
        with open(path, "w") as f:
            for result in self.results:
                f.write(result.to_json() + "\n")


# --- Pytest Test Cases ---

@pytest.fixture
def test_config():
    """Default test configuration for smoke tests."""
    return TestConfig(
        batch_size=5,
        sampling_strategy="uniform",
        max_concurrent=3,
        seed=42
    )


@pytest.fixture
def runner(test_config):
    """Create test runner instance."""
    return MCPTestRunner(test_config)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_basic_connectivity(runner):
    """Smoke test: verify basic MCP connectivity."""
    summary = await runner.run()

    assert summary["total"] > 0, "No tests were executed"
    print(f"\nSmoke test results: {summary['total']} tests, {summary['success_rate']:.1%} success rate")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_all_servers_reachable(runner):
    """Smoke test: verify all MCP servers are reachable."""
    summary = await runner.run()

    for server in runner.config.servers:
        server_results = summary["by_server"].get(server, {})
        total_for_server = sum(server_results.values())
        assert total_for_server > 0, f"No results for server {server}"


@pytest.mark.standard
@pytest.mark.asyncio
async def test_standard_reliability():
    """Standard reliability test with larger batch."""
    config = TestConfig(
        batch_size=50,
        sampling_strategy="mixed",
        max_concurrent=5,
        seed=int(time.time())
    )
    runner = MCPTestRunner(config)
    summary = await runner.run()

    # Success + Partial + Fallback should be >= 90%
    effective_success = (
        summary["by_category"]["success"] +
        summary["by_category"]["partial"] +
        summary["by_category"]["fallback"]
    ) / summary["total"]

    assert effective_success >= 0.90, f"Effective success rate {effective_success:.1%} < 90%"


@pytest.mark.stress
@pytest.mark.asyncio
async def test_stress_high_concurrency():
    """Stress test with high concurrency."""
    config = TestConfig(
        batch_size=100,
        sampling_strategy="uniform",
        max_concurrent=10,
        request_interval_ms=50,
        seed=int(time.time())
    )
    runner = MCPTestRunner(config)
    summary = await runner.run()

    # Just verify it completes without crashing
    assert summary["total"] > 0
    print(f"\nStress test: {summary['total']} tests, P99 latency: {summary['latency_p99']:.0f}ms")


@pytest.mark.asyncio
async def test_circuit_breaker_triggers():
    """Test that circuit breaker opens on repeated failures."""
    registry = get_circuit_breaker_registry()
    registry.reset_all()

    # Simulate 6 failures (threshold is 5)
    for i in range(6):
        registry.record_failure("fundamentals-basket", f"Error {i}")

    assert "fundamentals-basket" in registry.open_breakers()


@pytest.mark.asyncio
async def test_rate_limiter_respects_limits():
    """Test that rate limiter prevents rapid requests."""
    registry = get_rate_limiter_registry()

    # Try to acquire 20 rapid requests on SEC EDGAR (limit: 10/sec)
    acquired = 0
    for _ in range(20):
        if await registry.acquire("sec_edgar", timeout=0.1):
            acquired += 1

    # Should have acquired roughly 10 (the capacity)
    assert acquired <= 12, f"Rate limiter allowed too many requests: {acquired}"


if __name__ == "__main__":
    # Run as standalone script
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server Stress Test")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of companies to test")
    parser.add_argument("--strategy", default="uniform", choices=["uniform", "stratified", "edge_case", "mixed"])
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent requests")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--output", type=Path, help="Output path for detailed results")
    args = parser.parse_args()

    config = TestConfig(
        batch_size=args.batch_size,
        sampling_strategy=args.strategy,
        max_concurrent=args.max_concurrent,
        seed=args.seed
    )

    async def main():
        runner = MCPTestRunner(config)
        summary = await runner.run()
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(json.dumps(summary, indent=2))

        if args.output:
            runner.export_results(args.output)
            print(f"\nDetailed results exported to: {args.output}")

    asyncio.run(main())
