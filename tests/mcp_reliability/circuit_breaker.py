"""
Circuit Breaker - Prevents cascading failures during MCP stress testing.

Implements the circuit breaker pattern:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing if service recovered
"""

import time
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes in half-open before closing
    half_open_timeout: float = 30.0  # Seconds before transitioning to half-open
    reset_timeout: float = 60.0  # Full reset timeout


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single service/endpoint.

    Thread-safe implementation with state transitions:
    CLOSED -> OPEN (on failure_threshold failures)
    OPEN -> HALF_OPEN (after half_open_timeout)
    HALF_OPEN -> CLOSED (on success_threshold successes)
    HALF_OPEN -> OPEN (on any failure)
    """
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.monotonic)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _transition(self, new_state: CircuitState):
        """Transition to a new state."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.last_state_change = time.monotonic()
            # Reset counters on state change
            if new_state == CircuitState.CLOSED:
                self.failure_count = 0
                self.success_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self.success_count = 0

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns True if request can proceed, False if circuit is open.
        """
        with self._lock:
            now = time.monotonic()

            if self.state == CircuitState.CLOSED:
                return True

            elif self.state == CircuitState.OPEN:
                # Check if we should transition to half-open
                if self.last_failure_time:
                    elapsed = now - self.last_failure_time
                    if elapsed >= self.config.half_open_timeout:
                        self._transition(CircuitState.HALF_OPEN)
                        return True  # Allow test request
                return False

            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests in half-open state
                return True

        return False

    def record_success(self):
        """Record a successful request."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._transition(CircuitState.CLOSED)
            elif self.state == CircuitState.CLOSED:
                # Optionally reset failure count on success
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self, error: Optional[str] = None):
        """Record a failed request."""
        with self._lock:
            self.last_failure_time = time.monotonic()

            if self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    self._transition(CircuitState.OPEN)

            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                self._transition(CircuitState.OPEN)

    def force_open(self):
        """Force the circuit open (for testing/manual intervention)."""
        with self._lock:
            self._transition(CircuitState.OPEN)
            self.last_failure_time = time.monotonic()

    def force_close(self):
        """Force the circuit closed (for testing/manual intervention)."""
        with self._lock:
            self._transition(CircuitState.CLOSED)

    def status(self) -> Dict:
        """Get current circuit breaker status."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "time_in_state": time.monotonic() - self.last_state_change,
                "last_failure": self.last_failure_time
            }


class CircuitBreakerRegistry:
    """Registry of circuit breakers for all MCP servers.

    Provides centralized management and monitoring of circuit breakers.
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize registry with optional shared config."""
        self.config = config or CircuitBreakerConfig()
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
        self._setup_defaults()

    def _setup_defaults(self):
        """Create circuit breakers for known MCP servers."""
        servers = [
            "fundamentals-basket",
            "valuation-basket",
            "volatility-basket",
            "macro-basket",
            "news-basket",
            "sentiment-basket"
        ]
        for server in servers:
            self.breakers[server] = CircuitBreaker(name=server, config=self.config)

    def get(self, server: str) -> CircuitBreaker:
        """Get or create circuit breaker for a server."""
        with self._lock:
            if server not in self.breakers:
                self.breakers[server] = CircuitBreaker(name=server, config=self.config)
            return self.breakers[server]

    def allow_request(self, server: str) -> bool:
        """Check if request to server should be allowed."""
        return self.get(server).allow_request()

    def record_success(self, server: str):
        """Record successful request to server."""
        self.get(server).record_success()

    def record_failure(self, server: str, error: Optional[str] = None):
        """Record failed request to server."""
        self.get(server).record_failure(error)

    def status(self) -> Dict:
        """Get status of all circuit breakers."""
        return {
            name: breaker.status()
            for name, breaker in self.breakers.items()
        }

    def all_closed(self) -> bool:
        """Check if all circuit breakers are closed (healthy)."""
        return all(
            b.state == CircuitState.CLOSED
            for b in self.breakers.values()
        )

    def open_breakers(self) -> list:
        """Get list of servers with open circuit breakers."""
        return [
            name for name, b in self.breakers.items()
            if b.state == CircuitState.OPEN
        ]

    def reset_all(self):
        """Reset all circuit breakers to closed state."""
        for breaker in self.breakers.values():
            breaker.force_close()


# Global registry instance
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


async def with_circuit_breaker(
    server: str,
    func: Callable,
    *args,
    **kwargs
) -> Any:
    """Execute function with circuit breaker protection.

    Args:
        server: MCP server name
        func: Async function to execute
        *args, **kwargs: Arguments for func

    Returns:
        Result from func

    Raises:
        CircuitOpenError: If circuit is open
        Original exception: If func fails
    """
    registry = get_circuit_breaker_registry()

    if not registry.allow_request(server):
        raise CircuitOpenError(f"Circuit breaker open for {server}")

    try:
        result = await func(*args, **kwargs)
        registry.record_success(server)
        return result
    except Exception as e:
        registry.record_failure(server, str(e))
        raise


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass


if __name__ == "__main__":
    # Demo usage
    registry = get_circuit_breaker_registry()
    print("Initial status:")
    for name, status in registry.status().items():
        print(f"  {name}: {status['state']}")

    # Simulate failures
    print("\nSimulating failures for fundamentals-basket...")
    for i in range(6):
        registry.record_failure("fundamentals-basket", f"Error {i}")
        print(f"  Failure {i+1}: state = {registry.get('fundamentals-basket').state.value}")

    print("\nFinal status:")
    for name, status in registry.status().items():
        print(f"  {name}: {status['state']}")

    print(f"\nOpen breakers: {registry.open_breakers()}")
