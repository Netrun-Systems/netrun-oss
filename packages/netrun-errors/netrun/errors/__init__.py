"""
Netrun Unified Error Handling Package.

A comprehensive error handling library for FastAPI applications with:
- Structured JSON error responses
- Automatic correlation ID generation (integrates with netrun-logging if available)
- Machine-readable error codes
- Global exception handlers
- Request/response logging middleware

Version: 2.1.0
Author: Netrun Systems
License: MIT

v2.1.0 Changes:
- Added safe_http_error() helper (B1 back-port): build an HTTPException that
  never echoes raw exception text, closing the API-key-leak class where
  upstream exception messages embed provider secrets.

v1.1.0 Changes:
- Added netrun-logging integration for correlation ID consistency
- Added RateLimitExceededError (HTTP 429)
- Added BadGatewayError (HTTP 502)
- Added GatewayTimeoutError (HTTP 504)
- Added ExternalServiceError for generic external API failures
- Updated handlers to use netrun-logging when available
"""

__version__ = "2.1.0"

# Base exception
from .base import NetrunException

# Authentication exceptions
from .auth import (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
)

# Authorization exceptions
from .authorization import InsufficientPermissionsError, TenantAccessDeniedError

# Resource exceptions
from .resource import ResourceConflictError, ResourceNotFoundError

# Service exceptions
from .service import (
    ServiceUnavailableError,
    TemporalUnavailableError,
    RateLimitExceededError,
    BadGatewayError,
    GatewayTimeoutError,
    ExternalServiceError,
)

# Safe HTTP error helper (never leaks raw exception text)
from .safe import safe_http_error

# Exception handlers
from .handlers import install_exception_handlers

# Middleware
from .middleware import install_error_logging_middleware

__all__ = [
    # Base
    "NetrunException",
    # Authentication
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenRevokedError",
    "AuthenticationRequiredError",
    # Authorization
    "InsufficientPermissionsError",
    "TenantAccessDeniedError",
    # Resource
    "ResourceNotFoundError",
    "ResourceConflictError",
    # Service
    "ServiceUnavailableError",
    "TemporalUnavailableError",
    "RateLimitExceededError",
    "BadGatewayError",
    "GatewayTimeoutError",
    "ExternalServiceError",
    # Safe HTTP error helper
    "safe_http_error",
    # Handlers
    "install_exception_handlers",
    # Middleware
    "install_error_logging_middleware",
]
