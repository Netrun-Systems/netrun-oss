"""
Retry decorator with exponential backoff and jitter.

Provides retry functionality for both synchronous and asynchronous functions
with configurable backoff strategies and exception filtering.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Callable, Optional, Tuple, Type, TypeVar, Union

from .types import RetryConfig, RetryExhausted

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    base_delay_ms: int = 1000,
    max_delay_ms: int = 30000,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator to retry function execution with exponential backoff.

    Supports both synchronous and asynchronous functions. Uses exponential
    backoff with optional jitter to prevent thundering herd problem.

    Args:
        max_attempts: Maximum number of attempts (including initial call)
        base_delay_ms: Initial delay in milliseconds
        max_delay_ms: Maximum delay cap in milliseconds
        backoff_multiplier: Exponential backoff multiplier
        jitter: Whether to add random jitter (0.5-1.0x) to delays
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called before each retry: callback(exception, attempt)

    Returns:
        Decorated function with retry behavior

    Raises:
        RetryExhausted: When all retry attempts fail

    Example:
        @retry(max_attempts=3, base_delay_ms=1000, exceptions=(ConnectionError,))
        async def call_api():
            response = await httpx.get("https://api.example.com")
            return response.json()
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay_ms=base_delay_ms,
        max_delay_ms=max_delay_ms,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        exceptions=exceptions
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await _retry_async(func, config, on_retry, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return _retry_sync(func, config, on_retry, *args, **kwargs)
            return sync_wrapper

    return decorator


def _retry_sync(
    func: Callable[..., T],
    config: RetryConfig,
    on_retry: Optional[Callable[[Exception, int], None]],
    *args,
    **kwargs
) -> T:
    """Execute synchronous function with retry logic."""
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)

        except config.exceptions as e:
            last_exception = e

            if attempt + 1 >= config.max_attempts:
                # All attempts exhausted
                logger.error(
                    f"Retry exhausted for {func.__name__} after {config.max_attempts} attempts: {e}"
                )
                raise RetryExhausted(
                    f"Failed after {config.max_attempts} attempts. Last error: {e}"
                ) from e

            # Calculate delay with exponential backoff
            delay_ms = min(
                config.base_delay_ms * (config.backoff_multiplier ** attempt),
                config.max_delay_ms
            )

            # Apply jitter if enabled
            if config.jitter:
                delay_ms = delay_ms * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                f"after {delay_ms:.0f}ms delay: {e}"
            )

            # Call retry callback if provided
            if on_retry:
                on_retry(e, attempt + 1)

            # Sleep before retry
            time.sleep(delay_ms / 1000.0)

    # This should never be reached, but satisfies type checker
    raise RetryExhausted(f"Failed after {config.max_attempts} attempts") from last_exception


async def _retry_async(
    func: Callable[..., T],
    config: RetryConfig,
    on_retry: Optional[Callable[[Exception, int], None]],
    *args,
    **kwargs
) -> T:
    """Execute asynchronous function with retry logic."""
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)

        except config.exceptions as e:
            last_exception = e

            if attempt + 1 >= config.max_attempts:
                # All attempts exhausted
                logger.error(
                    f"Retry exhausted for {func.__name__} after {config.max_attempts} attempts: {e}"
                )
                raise RetryExhausted(
                    f"Failed after {config.max_attempts} attempts. Last error: {e}"
                ) from e

            # Calculate delay with exponential backoff
            delay_ms = min(
                config.base_delay_ms * (config.backoff_multiplier ** attempt),
                config.max_delay_ms
            )

            # Apply jitter if enabled
            if config.jitter:
                delay_ms = delay_ms * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                f"after {delay_ms:.0f}ms delay: {e}"
            )

            # Call retry callback if provided
            if on_retry:
                on_retry(e, attempt + 1)

            # Sleep before retry (async)
            await asyncio.sleep(delay_ms / 1000.0)

    # This should never be reached, but satisfies type checker
    raise RetryExhausted(f"Failed after {config.max_attempts} attempts") from last_exception
