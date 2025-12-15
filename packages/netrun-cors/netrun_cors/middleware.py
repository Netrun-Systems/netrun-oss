"""
CORSMiddleware wrapper with Netrun Systems standardization.

Extends FastAPI/Starlette CORSMiddleware with validation and logging.

v1.1.0: Added netrun-logging and netrun-errors integration for structured
logging and standardized error handling.
"""

from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

# Optional netrun-logging integration
_use_netrun_logging = False
_logger = None

try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


def _log(level: str, message: str, **kwargs) -> None:
    """Log using netrun-logging if available, otherwise standard logging."""
    if _use_netrun_logging:
        log_method = getattr(_logger, level, _logger.info)
        log_method(message, **kwargs)
    else:
        log_method = getattr(_logger, level, _logger.info)
        log_method(f"{message} {kwargs}")


class CORSMiddleware(FastAPICORSMiddleware):
    """
    Enhanced CORSMiddleware with OWASP compliance validation.

    Validates that wildcard origins are not combined with credentials
    (a security vulnerability per OWASP guidelines).

    Raises:
        ValueError: If allow_origins=["*"] and allow_credentials=True

    Example:
        >>> # Valid configuration
        >>> CORSMiddleware(
        ...     app=app,
        ...     allow_origins=["https://app.example.com"],
        ...     allow_credentials=True
        ... )

        >>> # Invalid configuration (raises ValueError)
        >>> CORSMiddleware(
        ...     app=app,
        ...     allow_origins=["*"],
        ...     allow_credentials=True
        ... )
        Traceback (most recent call last):
        ValueError: OWASP Violation: Cannot use wildcard origins with credentials...
    """

    def __init__(
        self,
        app,
        allow_origins: List[str] = None,
        allow_credentials: bool = False,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
        **kwargs
    ):
        """
        Initialize CORS middleware with OWASP compliance validation.

        Args:
            app: FastAPI application instance
            allow_origins: List of allowed origins (or ["*"] for all)
            allow_credentials: Allow credentials in CORS requests
            allow_methods: List of allowed HTTP methods
            allow_headers: List of allowed HTTP headers
            expose_headers: List of headers exposed to browser
            max_age: Preflight cache duration in seconds
            **kwargs: Additional arguments passed to FastAPICORSMiddleware

        Raises:
            ValueError: If wildcard origins combined with credentials
        """
        # OWASP Compliance Check
        if allow_origins and "*" in allow_origins and allow_credentials:
            _log(
                "error",
                "cors_owasp_violation",
                issue="wildcard_with_credentials",
                allow_origins=allow_origins,
                allow_credentials=allow_credentials,
            )
            raise ValueError(
                "OWASP Violation: Cannot use wildcard origins ['*'] with "
                "allow_credentials=True. This creates a security vulnerability. "
                "Either specify explicit origins or disable credentials."
            )

        # Set defaults if not provided
        if allow_origins is None:
            allow_origins = []
        if allow_methods is None:
            allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        if allow_headers is None:
            allow_headers = ["*"]
        if expose_headers is None:
            expose_headers = ["X-Request-ID", "X-Process-Time"]

        super().__init__(
            app=app,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            expose_headers=expose_headers,
            max_age=max_age,
            **kwargs
        )

        # Log CORS configuration (structured logging)
        _log(
            "info",
            "cors_middleware_configured",
            origin_count=len(allow_origins),
            allow_credentials=allow_credentials,
            methods=allow_methods,
            max_age=max_age,
            using_netrun_logging=_use_netrun_logging,
        )
