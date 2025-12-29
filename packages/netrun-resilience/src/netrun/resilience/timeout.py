"""
Timeout decorator for function execution.

Provides timeout functionality for both synchronous and asynchronous functions.
"""

import asyncio
import functools
import signal
import threading
from typing import Callable, TypeVar

from .types import TimeoutConfig

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when function execution exceeds timeout."""
    pass


def timeout(seconds: float = 5.0, message: str = "Operation timed out") -> Callable:
    """
    Decorator to enforce timeout on function execution.

    For async functions, uses asyncio.wait_for.
    For sync functions, uses signal (Unix) or threading (Windows).

    Args:
        seconds: Timeout duration in seconds
        message: Custom error message when timeout occurs

    Returns:
        Decorated function with timeout enforcement

    Raises:
        TimeoutError: When execution exceeds timeout

    Example:
        @timeout(seconds=5.0)
        async def slow_operation():
            await asyncio.sleep(10)  # Will timeout after 5 seconds
    """
    config = TimeoutConfig(seconds=seconds, message=message)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=config.seconds
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(config.message)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return _timeout_sync(func, config, *args, **kwargs)
            return sync_wrapper

    return decorator


def _timeout_sync(
    func: Callable[..., T],
    config: TimeoutConfig,
    *args,
    **kwargs
) -> T:
    """
    Execute synchronous function with timeout.

    Uses threading to enforce timeout on sync functions.
    """
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=config.seconds)

    if thread.is_alive():
        # Timeout occurred
        raise TimeoutError(config.message)

    if exception[0]:
        raise exception[0]

    return result[0]
