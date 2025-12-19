"""
Netrun Unified Error Handling Package.

A comprehensive error handling library for FastAPI applications with:
- Structured JSON error responses
- Automatic correlation ID generation (integrates with netrun-logging if available)
- Machine-readable error codes
- Global exception handlers
- Request/response logging middleware

Version: 1.1.0
Author: Netrun Systems
License: MIT

v1.1.0 Changes:
- Added netrun-logging integration for correlation ID consistency
- Added RateLimitExceededError (HTTP 429)
- Added BadGatewayError (HTTP 502)
- Added GatewayTimeoutError (HTTP 504)
- Added ExternalServiceError for generic external API failures
- Updated handlers to use netrun-logging when available
"""

__version__ = "1.1.0"

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
    # Handlers
    "install_exception_handlers",
    # Middleware
    "install_error_logging_middleware",
]
