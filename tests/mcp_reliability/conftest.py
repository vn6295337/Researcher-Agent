"""
Pytest configuration and fixtures for MCP reliability tests.
"""

import pytest
import asyncio
from pathlib import Path


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "smoke: quick smoke tests for basic functionality")
    config.addinivalue_line("markers", "standard: standard reliability tests")
    config.addinivalue_line("markers", "stress: high-load stress tests")
    config.addinivalue_line("markers", "soak: long-running soak tests")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset global singletons before each test."""
    from tests.mcp_reliability.rate_limiter import get_rate_limiter_registry
    from tests.mcp_reliability.circuit_breaker import get_circuit_breaker_registry

    # Reset circuit breakers
    cb_registry = get_circuit_breaker_registry()
    cb_registry.reset_all()

    yield

    # Cleanup after test if needed
