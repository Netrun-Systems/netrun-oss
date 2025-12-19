"""
Authorization-related exceptions for Netrun Systems.

All authorization exceptions return HTTP 403 Forbidden status codes
for authenticated users lacking sufficient permissions.
"""

from typing import Any, Dict, Optional

from fastapi import status

from .base import NetrunException


class InsufficientPermissionsError(NetrunException):
    """
    Raised when authenticated user lacks required permissions.

    Status Code: 403 Forbidden
    Error Code: AUTHZ_INSUFFICIENT_PERMISSIONS
    """

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHZ_INSUFFICIENT_PERMISSIONS",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class TenantAccessDeniedError(NetrunException):
    """
    Raised when user attempts to access resources outside their tenant scope.

    Status Code: 403 Forbidden
    Error Code: AUTHZ_TENANT_ACCESS_DENIED
    """

    def __init__(
        self,
        message: str = "Access denied: resource belongs to a different tenant",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHZ_TENANT_ACCESS_DENIED",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )
