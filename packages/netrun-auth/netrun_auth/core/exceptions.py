"""
Core exceptions for netrun-auth.

Provides standardized exception classes for authentication,
authorization, and configuration errors.

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""


class NetrunAuthError(Exception):
    """Base exception for all netrun-auth errors."""
    pass


class AuthenticationError(NetrunAuthError):
    """Raised when authentication fails."""
    pass


class TokenValidationError(NetrunAuthError):
    """Raised when token validation fails."""
    pass


class ConfigurationError(NetrunAuthError):
    """Raised when configuration is invalid."""
    pass


class AuthorizationError(NetrunAuthError):
    """Raised when user lacks required permissions."""
    pass
