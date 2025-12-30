"""
Netrun RBAC Tenancy Exceptions - Custom exceptions for multi-tenant operations.

Following Netrun Systems SDLC v2.3 standards.

Exception hierarchy:
    TenancyError (base)
    ├── TenantContextError      - Context not set or invalid
    ├── TenantNotFoundError     - Tenant doesn't exist
    ├── TenantAccessDeniedError - User can't access tenant
    ├── TenantSuspendedError    - Tenant account is suspended
    ├── CrossTenantViolationError - Attempted cross-tenant access
    └── IsolationViolationError - Isolation check failed
"""

from typing import Optional, Any
from uuid import UUID


class TenancyError(Exception):
    """
    Base exception for all tenancy-related errors.

    All tenancy exceptions inherit from this class, allowing for
    broad exception handling when needed.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        code: str = "TENANCY_ERROR",
        details: Optional[dict] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class TenantContextError(TenancyError):
    """
    Raised when tenant context is not set or is invalid.

    Common causes:
    - Request made without going through TenantResolutionMiddleware
    - TenantContext context manager not used
    - Context cleared unexpectedly
    """

    def __init__(
        self,
        message: str = "Tenant context is not set",
        details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            code="TENANT_CONTEXT_ERROR",
            details=details
        )


class TenantNotFoundError(TenancyError):
    """
    Raised when a tenant cannot be found.

    This can occur when:
    - Tenant ID/slug doesn't exist in database
    - Tenant has been deleted
    - Tenant lookup fails
    """

    def __init__(
        self,
        tenant_identifier: Any,
        identifier_type: str = "id",
        details: Optional[dict] = None
    ):
        message = f"Tenant not found: {identifier_type}={tenant_identifier}"
        super().__init__(
            message=message,
            code="TENANT_NOT_FOUND",
            details={
                "tenant_identifier": str(tenant_identifier),
                "identifier_type": identifier_type,
                **(details or {})
            }
        )


class TenantAccessDeniedError(TenancyError):
    """
    Raised when a user doesn't have access to a tenant.

    This occurs when:
    - User is not a member of the tenant
    - User's membership is inactive
    - User doesn't have required role
    """

    def __init__(
        self,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        reason: str = "Access denied",
        details: Optional[dict] = None
    ):
        message = f"Access to tenant denied: {reason}"
        super().__init__(
            message=message,
            code="TENANT_ACCESS_DENIED",
            details={
                "user_id": str(user_id) if user_id else None,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "reason": reason,
                **(details or {})
            }
        )


class TenantSuspendedError(TenancyError):
    """
    Raised when trying to access a suspended tenant.

    Tenant suspension can occur due to:
    - Non-payment
    - Policy violation
    - Administrative action
    - Security concerns
    """

    def __init__(
        self,
        tenant_id: Optional[UUID] = None,
        tenant_slug: Optional[str] = None,
        suspension_reason: Optional[str] = None,
        details: Optional[dict] = None
    ):
        identifier = tenant_slug or str(tenant_id) if tenant_id else "unknown"
        message = f"Tenant '{identifier}' is suspended"
        if suspension_reason:
            message += f": {suspension_reason}"

        super().__init__(
            message=message,
            code="TENANT_SUSPENDED",
            details={
                "tenant_id": str(tenant_id) if tenant_id else None,
                "tenant_slug": tenant_slug,
                "suspension_reason": suspension_reason,
                **(details or {})
            }
        )


class CrossTenantViolationError(TenancyError):
    """
    Raised when attempting to access resources from another tenant.

    This is a serious security violation and should be logged
    and monitored for potential attacks.
    """

    def __init__(
        self,
        current_tenant_id: Optional[UUID] = None,
        target_tenant_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[dict] = None
    ):
        message = "Cross-tenant access violation detected"
        if resource_type:
            message += f" for {resource_type}"

        super().__init__(
            message=message,
            code="CROSS_TENANT_VIOLATION",
            details={
                "current_tenant_id": str(current_tenant_id) if current_tenant_id else None,
                "target_tenant_id": str(target_tenant_id) if target_tenant_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                **(details or {})
            }
        )


class IsolationViolationError(TenancyError):
    """
    Raised when data isolation check fails.

    This can occur in hybrid mode when:
    - RLS policy would have blocked the query
    - Application-level filter was missing
    - Query attempted to access cross-tenant data
    """

    def __init__(
        self,
        operation: str = "query",
        model: Optional[str] = None,
        expected_tenant: Optional[UUID] = None,
        actual_tenant: Optional[UUID] = None,
        details: Optional[dict] = None
    ):
        message = f"Isolation violation in {operation}"
        if model:
            message += f" on {model}"

        super().__init__(
            message=message,
            code="ISOLATION_VIOLATION",
            details={
                "operation": operation,
                "model": model,
                "expected_tenant_id": str(expected_tenant) if expected_tenant else None,
                "actual_tenant_id": str(actual_tenant) if actual_tenant else None,
                **(details or {})
            }
        )


class TeamAccessDeniedError(TenancyError):
    """
    Raised when a user doesn't have access to a team.

    This occurs when:
    - User is not a member of the team
    - User doesn't have required team role
    - Team is private and user doesn't have explicit access
    """

    def __init__(
        self,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        reason: str = "Access denied",
        details: Optional[dict] = None
    ):
        message = f"Access to team denied: {reason}"
        super().__init__(
            message=message,
            code="TEAM_ACCESS_DENIED",
            details={
                "user_id": str(user_id) if user_id else None,
                "team_id": str(team_id) if team_id else None,
                "reason": reason,
                **(details or {})
            }
        )


class ShareAccessDeniedError(TenancyError):
    """
    Raised when a user doesn't have access to a shared resource.

    This occurs when:
    - Share has expired
    - Share has been revoked
    - User doesn't have required permission level
    """

    def __init__(
        self,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        required_permission: Optional[str] = None,
        reason: str = "Access denied",
        details: Optional[dict] = None
    ):
        message = f"Access to shared resource denied: {reason}"
        super().__init__(
            message=message,
            code="SHARE_ACCESS_DENIED",
            details={
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "required_permission": required_permission,
                "reason": reason,
                **(details or {})
            }
        )


class TenantInactiveError(TenancyError):
    """Raised when tenant is inactive."""

    def __init__(
        self,
        tenant_id: Optional[UUID] = None,
        message: str = "Tenant is inactive",
        details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            code="TENANT_INACTIVE",
            details={"tenant_id": str(tenant_id) if tenant_id else None, **(details or {})}
        )


class TenantLimitExceededError(TenancyError):
    """Raised when tenant exceeds a limit (users, storage, etc.)."""

    def __init__(
        self,
        limit_type: str = "unknown",
        current_value: Optional[int] = None,
        max_value: Optional[int] = None,
        details: Optional[dict] = None
    ):
        message = f"Tenant limit exceeded: {limit_type}"
        super().__init__(
            message=message,
            code="TENANT_LIMIT_EXCEEDED",
            details={
                "limit_type": limit_type,
                "current_value": current_value,
                "max_value": max_value,
                **(details or {})
            }
        )


class TeamNotFoundError(TenancyError):
    """Raised when a team cannot be found."""

    def __init__(
        self,
        team_identifier: Any,
        identifier_type: str = "id",
        details: Optional[dict] = None
    ):
        message = f"Team not found: {identifier_type}={team_identifier}"
        super().__init__(
            message=message,
            code="TEAM_NOT_FOUND",
            details={
                "team_identifier": str(team_identifier),
                "identifier_type": identifier_type,
                **(details or {})
            }
        )


class TeamHierarchyError(TenancyError):
    """Raised when team hierarchy operation fails."""

    def __init__(
        self,
        message: str = "Team hierarchy error",
        team_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            code="TEAM_HIERARCHY_ERROR",
            details={
                "team_id": str(team_id) if team_id else None,
                "parent_id": str(parent_id) if parent_id else None,
                **(details or {})
            }
        )


class SharePermissionError(TenancyError):
    """Raised when share permission check fails."""

    def __init__(
        self,
        required_permission: str = "unknown",
        actual_permission: Optional[str] = None,
        details: Optional[dict] = None
    ):
        message = f"Insufficient share permission: requires {required_permission}"
        super().__init__(
            message=message,
            code="SHARE_PERMISSION_ERROR",
            details={
                "required_permission": required_permission,
                "actual_permission": actual_permission,
                **(details or {})
            }
        )


class ShareExpiredError(TenancyError):
    """Raised when accessing an expired share."""

    def __init__(
        self,
        share_id: Optional[UUID] = None,
        expired_at: Optional[str] = None,
        details: Optional[dict] = None
    ):
        message = "Share has expired"
        super().__init__(
            message=message,
            code="SHARE_EXPIRED",
            details={
                "share_id": str(share_id) if share_id else None,
                "expired_at": expired_at,
                **(details or {})
            }
        )


class InvalidShareTargetError(TenancyError):
    """Raised when share target is invalid."""

    def __init__(
        self,
        target_type: str = "unknown",
        target_id: Optional[UUID] = None,
        reason: str = "Invalid target",
        details: Optional[dict] = None
    ):
        message = f"Invalid share target: {reason}"
        super().__init__(
            message=message,
            code="INVALID_SHARE_TARGET",
            details={
                "target_type": target_type,
                "target_id": str(target_id) if target_id else None,
                "reason": reason,
                **(details or {})
            }
        )
