"""
RBAC Exceptions - Custom exception classes for RBAC operations

Extracted from: Intirkast error handling patterns
"""


class RBACException(Exception):
    """Base exception for all RBAC-related errors"""

    def __init__(self, message: str, status_code: int = 403):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InsufficientPermissionsError(RBACException):
    """
    Raised when user lacks required role or permission

    HTTP Status: 403 Forbidden
    """

    def __init__(self, required_role: str, user_role: str | None = None):
        message = f"Insufficient permissions. Required role: {required_role}"
        if user_role:
            message += f" (current: {user_role})"
        super().__init__(message, status_code=403)


class TenantIsolationError(RBACException):
    """
    Raised when attempting cross-tenant access

    HTTP Status: 403 Forbidden
    Security Level: CRITICAL
    """

    def __init__(self, message: str = "Cross-tenant access denied"):
        super().__init__(message, status_code=403)


class ResourceOwnershipError(RBACException):
    """
    Raised when attempting to access resource owned by another user

    HTTP Status: 403 Forbidden
    """

    def __init__(self, message: str = "You can only access your own resources"):
        super().__init__(message, status_code=403)


class InvalidRoleError(RBACException):
    """
    Raised when an invalid role is specified

    HTTP Status: 400 Bad Request
    """

    def __init__(self, role: str):
        message = f"Invalid role: {role}. Must be one of: viewer, member, admin, owner"
        super().__init__(message, status_code=400)


class MissingTenantContextError(RBACException):
    """
    Raised when tenant context is required but not set

    HTTP Status: 400 Bad Request
    """

    def __init__(self, message: str = "Tenant context not set. Check authentication middleware."):
        super().__init__(message, status_code=400)
