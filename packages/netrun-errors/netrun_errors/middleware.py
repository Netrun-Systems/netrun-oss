"""
Error logging middleware for FastAPI applications.

Provides request/response logging with correlation ID injection,
performance tracking, and structured logging integration.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .base import NetrunException

logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging with correlation IDs.

    Features:
    - Automatic correlation ID generation and injection
    - Request/response logging with timing
    - Structured logging with request context
    - Performance tracking
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with correlation ID and logging.

        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain

        Returns:
            Response from downstream handlers
        """
        # Generate correlation ID
        correlation_id = NetrunException._generate_correlation_id()

        # Add correlation ID to request state for downstream access
        request.state.correlation_id = correlation_id

        # Start timing
        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # Inject correlation ID into response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as exc:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log exception
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "exception_type": type(exc).__name__,
                },
                exc_info=True,
            )

            # Re-raise for exception handlers
            raise


def install_error_logging_middleware(app) -> None:
    """
    Install error logging middleware on a FastAPI application.

    Usage:
        from fastapi import FastAPI
        from netrun_errors import install_error_logging_middleware

        app = FastAPI()
        install_error_logging_middleware(app)

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(ErrorLoggingMiddleware)
    logger.info("Error logging middleware installed successfully")
