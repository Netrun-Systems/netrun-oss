"""
netrun-resilience: Resilience patterns for distributed systems.

Provides decorators and utilities for retry, circuit breaker, timeout,
and bulkhead isolation patterns.
"""

from .bulkhead import bulkhead, Bulkhead
from .circuit_breaker import circuit_breaker, CircuitBreaker
from .retry import retry
from .timeout import timeout
from .types import (
    BulkheadConfig,
    BulkheadFullError,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    RetryConfig,
    RetryExhausted,
    TimeoutConfig,
)

__version__ = "1.0.0"

__all__ = [
    # Decorators
    "retry",
    "circuit_breaker",
    "timeout",
    "bulkhead",
    # Classes
    "CircuitBreaker",
    "Bulkhead",
    # Config classes
    "RetryConfig",
    "CircuitBreakerConfig",
    "TimeoutConfig",
    "BulkheadConfig",
    # Enums
    "CircuitState",
    # Exceptions
    "RetryExhausted",
    "CircuitOpenError",
    "BulkheadFullError",
]
