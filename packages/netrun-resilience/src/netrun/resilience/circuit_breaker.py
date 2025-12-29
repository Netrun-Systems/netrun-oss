"""
Circuit breaker pattern implementation.

Protects against cascading failures by tracking failures and temporarily
blocking requests when failure threshold is exceeded.

State Machine:
    CLOSED → OPEN → HALF_OPEN → CLOSED

    CLOSED: Normal operation, requests pass through
    OPEN: Circuit is open, rejecting all requests
    HALF_OPEN: Testing recovery, allowing limited requests
"""

import asyncio
import functools
import logging
import threading
import time
from typing import Callable, Optional, TypeVar

from .types import CircuitBreakerConfig, CircuitOpenError, CircuitState

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """
    Circuit breaker state manager.

    Thread-safe implementation that tracks failures and manages state transitions.
    """

    def __init__(self, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.

        Args:
            config: CircuitBreakerConfig with thresholds and timeouts
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock = threading.Lock()

        # State change callbacks
        self.on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None

    def _transition_state(self, new_state: CircuitState) -> None:
        """
        Transition to new state and invoke callback.

        Args:
            new_state: New circuit state
        """
        old_state = self.state
        self.state = new_state

        logger.info(f"Circuit breaker: {old_state.value} → {new_state.value}")

        if self.on_state_change:
            self.on_state_change(old_state, new_state)

    def _should_attempt(self) -> bool:
        """
        Check if request should be attempted based on current state.

        Returns:
            True if request should proceed, False if blocked

        Raises:
            CircuitOpenError: If circuit is open and blocking requests
        """
        with self._lock:
            current_time = time.time()

            if self.state == CircuitState.CLOSED:
                return True

            elif self.state == CircuitState.OPEN:
                # Check if we should transition to HALF_OPEN
                if self.last_failure_time is None:
                    # Inconsistent state - reset to CLOSED
                    self._transition_state(CircuitState.CLOSED)
                    self.failure_count = 0
                    return True

                time_since_failure = current_time - self.last_failure_time
                if time_since_failure >= self.config.timeout_seconds:
                    # Timeout elapsed, try HALF_OPEN
                    self._transition_state(CircuitState.HALF_OPEN)
                    self.success_count = 0
                    self.half_open_calls = 0
                    return True
                else:
                    # Still in timeout period
                    raise CircuitOpenError(
                        f"Circuit breaker open. Retry in {self.config.timeout_seconds - time_since_failure:.1f}s"
                    )

            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests in HALF_OPEN
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenError("Circuit breaker half-open. Max concurrent calls reached.")
                self.half_open_calls += 1
                return True

    def _record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.half_open_calls -= 1

                # Check if we should close circuit
                if self.success_count >= self.config.success_threshold:
                    self._transition_state(CircuitState.CLOSED)
                    self.failure_count = 0
                    self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    self.failure_count = max(0, self.failure_count - 1)

    def _record_failure(self) -> None:
        """Record failed execution."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # Failed in HALF_OPEN - reopen circuit
                self._transition_state(CircuitState.OPEN)
                self.half_open_calls -= 1

            elif self.state == CircuitState.CLOSED:
                # Check if we should open circuit
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_state(CircuitState.OPEN)

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            logger.info("Circuit breaker manually reset")
            self._transition_state(CircuitState.CLOSED)
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.half_open_calls = 0

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_metrics(self) -> dict:
        """Get current circuit breaker metrics."""
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "half_open_calls": self.half_open_calls,
                "last_failure_time": self.last_failure_time,
            }


def circuit_breaker(
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout_seconds: float = 60.0,
    half_open_max_calls: int = 3,
    on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
) -> Callable:
    """
    Decorator to protect function with circuit breaker pattern.

    Creates a shared circuit breaker instance per decorated function.

    Args:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in HALF_OPEN to close
        timeout_seconds: Time to wait before HALF_OPEN transition
        half_open_max_calls: Max concurrent calls in HALF_OPEN
        on_state_change: Callback for state transitions

    Returns:
        Decorated function with circuit breaker protection

    Raises:
        CircuitOpenError: When circuit is open and blocking requests

    Example:
        @circuit_breaker(failure_threshold=5, timeout_seconds=60)
        async def unreliable_service():
            return await external_api.call()
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout_seconds=timeout_seconds,
        half_open_max_calls=half_open_max_calls
    )

    # Create circuit breaker instance (shared across all calls)
    breaker = CircuitBreaker(config)
    if on_state_change:
        breaker.on_state_change = on_state_change

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                # Check if request should proceed
                breaker._should_attempt()

                try:
                    result = await func(*args, **kwargs)
                    breaker._record_success()
                    return result
                except Exception as e:
                    breaker._record_failure()
                    raise

            # Attach breaker instance for testing/inspection
            async_wrapper.circuit_breaker = breaker
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                # Check if request should proceed
                breaker._should_attempt()

                try:
                    result = func(*args, **kwargs)
                    breaker._record_success()
                    return result
                except Exception as e:
                    breaker._record_failure()
                    raise

            # Attach breaker instance for testing/inspection
            sync_wrapper.circuit_breaker = breaker
            return sync_wrapper

    return decorator
