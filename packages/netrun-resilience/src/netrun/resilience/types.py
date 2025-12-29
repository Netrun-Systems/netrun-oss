"""
Type definitions for netrun-resilience package.

Provides configuration classes for retry policies, circuit breakers,
timeouts, and bulkhead isolation patterns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Type


class CircuitState(Enum):
    """Circuit breaker state machine states."""
    CLOSED = "closed"  # Normal operation - requests pass through
    OPEN = "open"  # Blocking requests due to failures
    HALF_OPEN = "half_open"  # Testing recovery with limited requests


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior with exponential backoff.

    Attributes:
        max_attempts: Maximum number of retry attempts (including initial)
        base_delay_ms: Initial delay in milliseconds before first retry
        max_delay_ms: Maximum delay cap in milliseconds
        backoff_multiplier: Exponential backoff multiplier (delay = base * multiplier^attempt)
        jitter: Whether to add random jitter to delays (reduces thundering herd)
        exceptions: Tuple of exception types to retry on
    """
    max_attempts: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter: bool = True
    exceptions: Tuple[Type[Exception], ...] = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker pattern.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit
        success_threshold: Number of successes in HALF_OPEN to close circuit
        timeout_seconds: Time to wait before transitioning from OPEN to HALF_OPEN
        half_open_max_calls: Maximum concurrent requests allowed in HALF_OPEN state
    """
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class TimeoutConfig:
    """
    Configuration for timeout behavior.

    Attributes:
        seconds: Timeout duration in seconds
        message: Custom error message when timeout occurs
    """
    seconds: float = 5.0
    message: str = "Operation timed out"


@dataclass
class BulkheadConfig:
    """
    Configuration for bulkhead isolation pattern.

    Attributes:
        max_concurrent: Maximum number of concurrent executions
        max_queue: Maximum queue size for waiting requests
    """
    max_concurrent: int = 10
    max_queue: int = 100


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""
    pass


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""
    pass


class BulkheadFullError(Exception):
    """Raised when bulkhead is at capacity and queue is full."""
    pass
