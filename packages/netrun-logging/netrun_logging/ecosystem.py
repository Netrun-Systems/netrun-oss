"""
Netrun Ecosystem Integration Helpers
Context management and logging utilities for Netrun package ecosystem

v1.2.0: Added ecosystem integration for netrun-errors, netrun-auth, netrun-config
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar

from netrun_logging.correlation import (
    bind_context,
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
)
from netrun_logging.logger import get_logger

# Type variable for function return type
T = TypeVar("T")


def bind_error_context(
    error_code: str,
    status_code: int,
    correlation_id: Optional[str] = None,
    **additional_context
) -> None:
    """
    Bind error context for subsequent log entries.

    Use this when catching exceptions to add error context to logs
    before logging the error.

    Args:
        error_code: Machine-readable error code (e.g., "AUTH_INVALID_CREDENTIALS")
        status_code: HTTP status code
        correlation_id: Optional correlation ID (uses current context if not provided)
        **additional_context: Additional context fields to bind

    Example:
        >>> try:
        ...     validate_token(token)
        ... except TokenExpiredError as e:
        ...     bind_error_context("AUTH_TOKEN_EXPIRED", 401, user_id=user_id)
        ...     logger.error("token_validation_failed", reason=str(e))
    """
    context = {
        "error_code": error_code,
        "status_code": status_code,
        **additional_context,
    }

    if correlation_id:
        context["correlation_id"] = correlation_id
    elif not get_correlation_id():
        # Ensure we have a correlation ID for error tracking
        context["correlation_id"] = generate_correlation_id()

    bind_context(**context)


def bind_request_context(
    method: str,
    path: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    **additional_context
) -> None:
    """
    Bind HTTP request context for subsequent log entries.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        correlation_id: Optional correlation ID (generates new one if not provided)
        user_id: Optional user ID for authenticated requests
        tenant_id: Optional tenant ID for multi-tenant requests
        **additional_context: Additional context fields to bind

    Example:
        >>> bind_request_context(
        ...     method="POST",
        ...     path="/api/users",
        ...     user_id="12345",
        ...     tenant_id="acme-corp"
        ... )
        >>> logger.info("request_started")  # Includes method, path, user_id, tenant_id
    """
    cid = correlation_id or get_correlation_id() or generate_correlation_id()

    context = {
        "correlation_id": cid,
        "http_method": method,
        "http_path": path,
        **additional_context,
    }

    if user_id:
        context["user_id"] = user_id
    if tenant_id:
        context["tenant_id"] = tenant_id

    set_correlation_id(cid)
    bind_context(**context)


def bind_operation_context(
    operation: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    **additional_context
) -> None:
    """
    Bind operation context for business logic tracking.

    Args:
        operation: Operation name (e.g., "create_user", "process_payment")
        resource_type: Optional resource type being operated on
        resource_id: Optional resource ID being operated on
        **additional_context: Additional context fields to bind

    Example:
        >>> bind_operation_context(
        ...     operation="create_order",
        ...     resource_type="Order",
        ...     customer_id="cust_123"
        ... )
        >>> logger.info("operation_started")
    """
    context = {
        "operation": operation,
        **additional_context,
    }

    if resource_type:
        context["resource_type"] = resource_type
    if resource_id:
        context["resource_id"] = resource_id

    bind_context(**context)


@contextmanager
def log_operation_timing(
    operation: str,
    logger_name: Optional[str] = None,
    level: str = "info",
    **context
):
    """
    Context manager for timing operations and logging duration.

    Args:
        operation: Operation name for logging
        logger_name: Optional logger name (uses __name__ if not provided)
        level: Log level for completion message (default: "info")
        **context: Additional context to include in log messages

    Yields:
        None

    Example:
        >>> with log_operation_timing("database_query", table="users"):
        ...     results = db.query("SELECT * FROM users")
        # Logs: operation_completed operation=database_query duration_ms=42.5 table=users
    """
    logger = get_logger(logger_name or __name__)
    start_time = time.perf_counter()

    # Bind operation context
    bind_operation_context(operation, **context)

    try:
        yield
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_method = getattr(logger, level, logger.info)
        log_method(
            "operation_completed",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            success=True,
            **context,
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "operation_failed",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            success=False,
            error_type=type(e).__name__,
            error_message=str(e),
            **context,
        )
        raise


def log_timing(
    operation: Optional[str] = None,
    level: str = "info",
    include_args: bool = False,
):
    """
    Decorator for timing function execution and logging duration.

    Args:
        operation: Optional operation name (uses function name if not provided)
        level: Log level for completion message (default: "info")
        include_args: Include function arguments in log context (default: False)

    Returns:
        Decorated function

    Example:
        >>> @log_timing(operation="fetch_user_data")
        ... async def get_user(user_id: str) -> User:
        ...     return await db.get_user(user_id)
        # Logs: operation_completed operation=fetch_user_data duration_ms=15.3
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation or func.__name__
        logger = get_logger(func.__module__)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            context: Dict[str, Any] = {"function": func.__name__}
            if include_args:
                context["args_count"] = len(args)
                context["kwargs_keys"] = list(kwargs.keys())

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_method = getattr(logger, level, logger.info)
                log_method(
                    "operation_completed",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    success=True,
                    **context,
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "operation_failed",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    success=False,
                    error_type=type(e).__name__,
                    **context,
                )
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            context: Dict[str, Any] = {"function": func.__name__}
            if include_args:
                context["args_count"] = len(args)
                context["kwargs_keys"] = list(kwargs.keys())

            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_method = getattr(logger, level, logger.info)
                log_method(
                    "operation_completed",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    success=True,
                    **context,
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "operation_failed",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    success=False,
                    error_type=type(e).__name__,
                    **context,
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def create_audit_logger(
    service_name: str,
    actor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Any:
    """
    Create a logger pre-configured for audit logging.

    Args:
        service_name: Name of the service generating audit logs
        actor_id: Optional ID of the actor performing actions
        tenant_id: Optional tenant ID for multi-tenant contexts

    Returns:
        Configured logger instance

    Example:
        >>> audit = create_audit_logger("user-service", actor_id=admin_id)
        >>> audit.info("user_deleted", target_user_id=deleted_user_id)
    """
    logger = get_logger(f"audit.{service_name}")

    # Bind default audit context
    context = {"audit": True, "service": service_name}
    if actor_id:
        context["actor_id"] = actor_id
    if tenant_id:
        context["tenant_id"] = tenant_id

    return logger.bind(**context)
