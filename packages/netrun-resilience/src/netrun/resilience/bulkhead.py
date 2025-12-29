"""
Bulkhead isolation pattern implementation.

Limits concurrent executions to prevent resource exhaustion and isolate failures.
"""

import asyncio
import functools
import logging
import threading
from typing import Callable, TypeVar

from .types import BulkheadConfig, BulkheadFullError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Bulkhead:
    """
    Bulkhead state manager for concurrency limiting.

    Maintains semaphores and queues for both sync and async execution.
    """

    def __init__(self, config: BulkheadConfig):
        """
        Initialize bulkhead.

        Args:
            config: BulkheadConfig with concurrency and queue limits
        """
        self.config = config

        # Async resources
        self.async_semaphore = asyncio.Semaphore(config.max_concurrent)
        self.async_queue_size = 0

        # Sync resources
        self.sync_semaphore = threading.Semaphore(config.max_concurrent)
        self.sync_queue_size = 0
        self._sync_lock = threading.Lock()

        # Metrics
        self.total_accepted = 0
        self.total_rejected = 0

    def get_metrics(self) -> dict:
        """Get current bulkhead metrics."""
        return {
            "max_concurrent": self.config.max_concurrent,
            "max_queue": self.config.max_queue,
            "async_active": self.config.max_concurrent - self.async_semaphore._value,
            "async_queued": self.async_queue_size,
            "sync_active": self.config.max_concurrent - self.sync_semaphore._value,
            "sync_queued": self.sync_queue_size,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
        }


def bulkhead(
    max_concurrent: int = 10,
    max_queue: int = 100
) -> Callable:
    """
    Decorator to limit concurrent executions with bulkhead pattern.

    Prevents resource exhaustion by limiting concurrent executions
    and queueing excess requests up to a maximum queue size.

    Args:
        max_concurrent: Maximum number of concurrent executions
        max_queue: Maximum queue size for waiting requests

    Returns:
        Decorated function with bulkhead isolation

    Raises:
        BulkheadFullError: When max concurrent + queue is exceeded

    Example:
        @bulkhead(max_concurrent=10, max_queue=100)
        async def resource_intensive():
            return await heavy_computation()
    """
    config = BulkheadConfig(
        max_concurrent=max_concurrent,
        max_queue=max_queue
    )

    # Create bulkhead instance (shared across all calls)
    bulkhead_instance = Bulkhead(config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                # Check if we can accept request
                active = config.max_concurrent - bulkhead_instance.async_semaphore._value
                queued = bulkhead_instance.async_queue_size

                if active >= config.max_concurrent and queued >= config.max_queue:
                    bulkhead_instance.total_rejected += 1
                    raise BulkheadFullError(
                        f"Bulkhead full: {active} active, {queued} queued (max: {config.max_queue})"
                    )

                # Increment queue size
                bulkhead_instance.async_queue_size += 1

                try:
                    async with bulkhead_instance.async_semaphore:
                        # Moved from queue to active
                        bulkhead_instance.async_queue_size -= 1
                        bulkhead_instance.total_accepted += 1

                        return await func(*args, **kwargs)
                except Exception as e:
                    # Ensure queue size is decremented on error
                    if bulkhead_instance.async_queue_size > 0:
                        bulkhead_instance.async_queue_size -= 1
                    raise

            # Attach bulkhead instance for testing/inspection
            async_wrapper.bulkhead = bulkhead_instance
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                # Check if we can accept request
                with bulkhead_instance._sync_lock:
                    active = config.max_concurrent - bulkhead_instance.sync_semaphore._value
                    queued = bulkhead_instance.sync_queue_size

                    if active >= config.max_concurrent and queued >= config.max_queue:
                        bulkhead_instance.total_rejected += 1
                        raise BulkheadFullError(
                            f"Bulkhead full: {active} active, {queued} queued (max: {config.max_queue})"
                        )

                    # Increment queue size
                    bulkhead_instance.sync_queue_size += 1

                try:
                    with bulkhead_instance.sync_semaphore:
                        # Moved from queue to active
                        with bulkhead_instance._sync_lock:
                            bulkhead_instance.sync_queue_size -= 1
                            bulkhead_instance.total_accepted += 1

                        return func(*args, **kwargs)
                except Exception as e:
                    # Ensure queue size is decremented on error
                    with bulkhead_instance._sync_lock:
                        if bulkhead_instance.sync_queue_size > 0:
                            bulkhead_instance.sync_queue_size -= 1
                    raise

            # Attach bulkhead instance for testing/inspection
            sync_wrapper.bulkhead = bulkhead_instance
            return sync_wrapper

    return decorator
