"""
Netrun Authentication - Exception Classes
==========================================

Custom exception hierarchy for authentication and authorization errors.

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

from typing import Optional, Dict, Any


class AuthenticationError(Exception):
    """Base exception for authentication failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERROR",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class AuthorizationError(AuthenticationError):
    """Exception for authorization/permission failures."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str = "AUTHORIZATION_ERROR",
        status_code: int = 403,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class TokenExpiredError(AuthenticationError):
    """Exception for expired tokens."""

    def __init__(
        self,
        message: str = "Token has expired",
        error_code: str = "TOKEN_EXPIRED",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class TokenInvalidError(AuthenticationError):
    """Exception for invalid tokens."""

    def __init__(
        self,
        message: str = "Invalid token",
        error_code: str = "TOKEN_INVALID",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class TokenBlacklistedError(AuthenticationError):
    """Exception for blacklisted tokens."""

    def __init__(
        self,
        message: str = "Token has been revoked",
        error_code: str = "TOKEN_BLACKLISTED",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class APIKeyInvalidError(AuthenticationError):
    """Exception for invalid API keys."""

    def __init__(
        self,
        message: str = "Invalid API key",
        error_code: str = "API_KEY_INVALID",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class RoleNotFoundError(AuthorizationError):
    """Exception when required role is not found."""

    def __init__(
        self,
        message: str = "Required role not found",
        role: Optional[str] = None,
        error_code: str = "ROLE_NOT_FOUND",
        status_code: int = 403,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if role:
            details["required_role"] = role
        super().__init__(message, error_code, status_code, details)


class PermissionDeniedError(AuthorizationError):
    """Exception when required permission is denied."""

    def __init__(
        self,
        message: str = "Permission denied",
        permission: Optional[str] = None,
        error_code: str = "PERMISSION_DENIED",
        status_code: int = 403,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if permission:
            details["required_permission"] = permission
        super().__init__(message, error_code, status_code, details)


class SessionExpiredError(AuthenticationError):
    """Exception for expired sessions."""

    def __init__(
        self,
        message: str = "Session has expired",
        error_code: str = "SESSION_EXPIRED",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class RateLimitExceededError(AuthenticationError):
    """Exception for rate limit violations."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        status_code: int = 429,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, error_code, status_code, details)


# Alias for Azure AD integration
TokenValidationError = TokenInvalidError
