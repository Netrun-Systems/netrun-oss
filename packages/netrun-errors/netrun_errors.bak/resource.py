"""
Resource-related exceptions for Netrun Systems.

Exceptions for resource lifecycle operations (CRUD) including
not found and conflict scenarios.
"""

from typing import Any, Dict, Optional

from fastapi import status

from .base import NetrunException


class ResourceNotFoundError(NetrunException):
    """
    Raised when requested resource does not exist.

    Status Code: 404 Not Found
    Error Code: RESOURCE_NOT_FOUND
    """

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        if message is None:
            if resource_id:
                message = f"{resource_type} with ID '{resource_id}' not found"
            else:
                message = f"{resource_type} not found"

        if details is None:
            details = {}
        if resource_id:
            details["resource_id"] = resource_id
        details["resource_type"] = resource_type

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class ResourceConflictError(NetrunException):
    """
    Raised when resource operation conflicts with existing state.

    Common scenarios:
    - Duplicate resource creation (unique constraint violation)
    - Concurrent modification conflicts
    - State transition violations

    Status Code: 409 Conflict
    Error Code: RESOURCE_CONFLICT
    """

    def __init__(
        self,
        message: str = "Resource operation conflicts with existing state",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )
