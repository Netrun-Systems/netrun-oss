"""
Correlation ID Management
Thread-safe correlation ID tracking for distributed request tracing using structlog
"""

import uuid
from contextlib import contextmanager
from typing import Optional
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    bound_contextvars,
    unbind_contextvars,
)


def generate_correlation_id() -> str:
    """
    Generate a new UUID4 correlation ID.

    Returns:
        New correlation ID string

    Example:
        >>> cid = generate_correlation_id()
        >>> # Example: "550e8400-e29b-41d4-a716-446655440000"
    """
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set

    Example:
        >>> set_correlation_id("my-correlation-id")
        >>> cid = get_correlation_id()
        >>> print(cid)
        my-correlation-id
    """
    # Import here to avoid circular dependency
    from structlog.contextvars import get_contextvars
    ctx = get_contextvars()
    return ctx.get("correlation_id")


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID in the current context using structlog.

    Args:
        correlation_id: Correlation ID to set

    Example:
        >>> set_correlation_id("550e8400-e29b-41d4-a716-446655440000")
        >>> logger.info("request_started")  # Will include correlation_id
    """
    bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """
    Clear the current correlation ID.

    Example:
        >>> set_correlation_id("my-id")
        >>> clear_correlation_id()
        >>> cid = get_correlation_id()
        >>> print(cid)
        None
    """
    unbind_contextvars("correlation_id")


def bind_context(**kwargs) -> None:
    """
    Bind context variables for all subsequent logs.

    Args:
        **kwargs: Key-value pairs to bind to logging context

    Example:
        >>> bind_context(user_id="12345", tenant_id="acme-corp")
        >>> logger.info("user_action")  # Will include user_id and tenant_id
    """
    bind_contextvars(**kwargs)


def clear_context() -> None:
    """
    Clear all context variables.

    Example:
        >>> bind_context(user_id="12345", tenant_id="acme-corp")
        >>> clear_context()
        >>> logger.info("logged_out")  # No user_id or tenant_id
    """
    clear_contextvars()


@contextmanager
def correlation_id_context(correlation_id: Optional[str] = None):
    """
    Context manager for correlation ID scoping using structlog.

    Args:
        correlation_id: Optional correlation ID (generates new one if not provided)

    Yields:
        Correlation ID string

    Example:
        >>> with correlation_id_context() as cid:
        ...     logger.info("request_processing")
        ...     # All logs within this block will have correlation_id
    """
    cid = correlation_id or generate_correlation_id()
    with bound_contextvars(correlation_id=cid):
        yield cid
