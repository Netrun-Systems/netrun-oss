"""
FastAPI Middleware for Logging
Injects correlation ID and request logging for FastAPI applications
"""

import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from netrun.logging.correlation import set_correlation_id, clear_correlation_id

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects correlation ID into each request.

    Reads X-Correlation-ID header if present, otherwise generates a new UUID.
    Stores correlation ID in request state and response headers.
    """

    CORRELATION_ID_HEADER = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state
        request.state.correlation_id = correlation_id

        # Set in context for logging
        set_correlation_id(correlation_id)

        try:
            response = await call_next(request)

            # Add to response headers
            response.headers[self.CORRELATION_ID_HEADER] = correlation_id

            return response
        finally:
            # Clean up context
            clear_correlation_id()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request/response details.

    Logs:
    - Request: method, path, correlation ID
    - Response: status code, duration
    """

    def __init__(self, app: FastAPI, log_level: str = "INFO"):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Get correlation ID from request state (set by CorrelationIdMiddleware)
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log request
        logger.log(
            self.log_level,
            f"Request: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response
            logger.log(
                self.log_level,
                f"Response: {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )

            return response

        except Exception as e:
            # Log exception
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                f"Request failed: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }
            )
            raise


def add_logging_middleware(app: FastAPI, log_level: str = "INFO") -> None:
    """
    Add correlation ID and logging middleware to FastAPI app.

    Args:
        app: FastAPI application instance
        log_level: Logging level for request/response logs

    Usage:
        from fastapi import FastAPI
        from netrun.logging.middleware import add_logging_middleware

        app = FastAPI()
        add_logging_middleware(app)
    """
    # Order matters: CorrelationId first, then Logging
    app.add_middleware(LoggingMiddleware, log_level=log_level)
    app.add_middleware(CorrelationIdMiddleware)

    logger.info("Logging middleware added to FastAPI application")
