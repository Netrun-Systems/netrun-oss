"""
Global exception handlers for FastAPI applications.

Provides centralized exception handling with structured JSON responses,
correlation ID injection, and logging integration.

v1.1.0: Enhanced logging with optional netrun-logging integration for
structured key=value logging and correlation ID consistency.
"""

import logging
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .base import NetrunException

# Try to use netrun-logging for structured logging
_use_structlog = False
_structlog_logger = None

try:
    from netrun_logging import get_logger as _get_structlog_logger
    _structlog_logger = _get_structlog_logger(__name__)
    _use_structlog = True
except ImportError:
    pass

# Fallback to standard logging
logger = logging.getLogger(__name__)


def _log_error(
    message: str,
    level: str = "error",
    exc_info: bool = False,
    **kwargs
) -> None:
    """Log error using netrun-logging if available, otherwise standard logging."""
    if _use_structlog and _structlog_logger is not None:
        log_method = getattr(_structlog_logger, level, _structlog_logger.error)
        log_method(message, **kwargs)
    else:
        log_method = getattr(logger, level, logger.error)
        log_method(message, extra=kwargs, exc_info=exc_info)


async def netrun_exception_handler(
    request: Request, exc: NetrunException
) -> JSONResponse:
    """
    Handle NetrunException instances with structured JSON responses.

    Args:
        request: FastAPI request object
        exc: NetrunException instance

    Returns:
        JSONResponse with structured error format
    """
    # Add request path to error details
    error_dict = exc.to_dict()
    error_dict["error"]["path"] = str(request.url.path)

    # Log error with correlation ID (structured logging if netrun-logging available)
    _log_error(
        "netrun_exception",
        level="error",
        correlation_id=exc.correlation_id,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=str(request.url.path),
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_dict,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI request validation errors with structured format.

    Args:
        request: FastAPI request object
        exc: RequestValidationError instance

    Returns:
        JSONResponse with validation error details
    """
    from datetime import datetime, timezone

    correlation_id = NetrunException._generate_correlation_id()

    error_response = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "validation_errors": exc.errors(),
            },
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        }
    }

    _log_error(
        "validation_error",
        level="warning",
        correlation_id=correlation_id,
        path=str(request.url.path),
        method=request.method,
        error_count=len(exc.errors()),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
    )


async def http_exception_handler(
    request: Request, exc: Union[StarletteHTTPException, Exception]
) -> JSONResponse:
    """
    Handle generic HTTP exceptions with structured format.

    Args:
        request: FastAPI request object
        exc: HTTPException or generic Exception

    Returns:
        JSONResponse with structured error format
    """
    from datetime import datetime, timezone

    correlation_id = NetrunException._generate_correlation_id()

    # Determine status code
    if isinstance(exc, StarletteHTTPException):
        status_code = exc.status_code
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "An unexpected error occurred"

    error_response = {
        "error": {
            "code": "HTTP_ERROR",
            "message": message,
            "details": {},
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        }
    }

    _log_error(
        "http_exception",
        level="error",
        exc_info=(status_code >= 500),
        correlation_id=correlation_id,
        status_code=status_code,
        message=message,
        path=str(request.url.path),
        method=request.method,
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled exceptions with structured format.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSONResponse with generic error format
    """
    from datetime import datetime, timezone

    correlation_id = NetrunException._generate_correlation_id()

    error_response = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "details": {},
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        }
    }

    _log_error(
        "unhandled_exception",
        level="error",
        exc_info=True,
        correlation_id=correlation_id,
        path=str(request.url.path),
        method=request.method,
        exception_type=type(exc).__name__,
        exception_message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


def install_exception_handlers(app: FastAPI) -> None:
    """
    Install all Netrun exception handlers on a FastAPI application.

    Usage:
        from fastapi import FastAPI
        from netrun_errors import install_exception_handlers

        app = FastAPI()
        install_exception_handlers(app)

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(NetrunException, netrun_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    _log_error(
        "exception_handlers_installed",
        level="info",
        handler_count=4,
        using_structlog=_use_structlog,
    )
