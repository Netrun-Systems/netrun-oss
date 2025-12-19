"""
Authentication-related exceptions for Netrun Systems.

All authentication exceptions return HTTP 401 Unauthorized status codes
with specific error codes for different authentication failure scenarios.
"""

from typing import Any, Dict, Optional

from fastapi import status

from .base import NetrunException


class InvalidCredentialsError(NetrunException):
    """
    Raised when user provides invalid email/password combination.

    Status Code: 401 Unauthorized
    Error Code: AUTH_INVALID_CREDENTIALS
    """

    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_INVALID_CREDENTIALS",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class TokenExpiredError(NetrunException):
    """
    Raised when authentication token has expired.

    Status Code: 401 Unauthorized
    Error Code: AUTH_TOKEN_EXPIRED
    """

    def __init__(
        self,
        message: str = "Authentication token has expired",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_TOKEN_EXPIRED",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class TokenInvalidError(NetrunException):
    """
    Raised when authentication token is malformed or invalid.

    Status Code: 401 Unauthorized
    Error Code: AUTH_TOKEN_INVALID
    """

    def __init__(
        self,
        message: str = "Authentication token is invalid",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_TOKEN_INVALID",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class TokenRevokedError(NetrunException):
    """
    Raised when authentication token has been explicitly revoked.

    Status Code: 401 Unauthorized
    Error Code: AUTH_TOKEN_REVOKED
    """

    def __init__(
        self,
        message: str = "Authentication token has been revoked",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_TOKEN_REVOKED",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class AuthenticationRequiredError(NetrunException):
    """
    Raised when endpoint requires authentication but none provided.

    Status Code: 401 Unauthorized
    Error Code: AUTH_REQUIRED
    """

    def __init__(
        self,
        message: str = "Authentication is required to access this resource",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_REQUIRED",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )
