"""
Netrun RBAC Tenant Dependencies - FastAPI dependencies for tenant context.

Following Netrun Systems SDLC v2.3 standards.
"""

from typing import Optional, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from ..tenancy.context import TenantContext, TenantContextData
from ..tenancy.exceptions import TenantContextError, TenantAccessDeniedError
from ..models.enums import TenantRole
from ..isolation.base import IsolationStrategy
from ..isolation.hybrid import HybridIsolationStrategy


async def get_current_tenant(
    request: Request,
) -> Optional[TenantContextData]:
    """
    Get the current tenant context if available.

    This dependency returns None if no tenant context is set,
    allowing routes to handle both authenticated and public access.

    Usage:
        @app.get("/resource")
        async def get_resource(
            tenant = Depends(get_current_tenant)
        ):
            if tenant:
                # Tenant-scoped logic
            else:
                # Public access logic
    """
    return TenantContext.get_current()


async def require_tenant(
    request: Request,
) -> TenantContextData:
    """
    Require a valid tenant context.

    Raises HTTP 401 if no tenant context is set.
    Use this for routes that must have tenant identification.

    Usage:
        @app.get("/contacts")
        async def list_contacts(
            tenant = Depends(require_tenant)
        ):
            # tenant is guaranteed to be TenantContextData
            return await service.get_all()
    """
    ctx = TenantContext.get_current()

    if ctx is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TENANT_REQUIRED",
                "message": "Tenant identification required"
            }
        )

    return ctx


async def require_user(
    request: Request,
) -> TenantContextData:
    """
    Require a valid tenant context with authenticated user.

    Raises HTTP 401 if no tenant context or user is set.
    Use this for routes that require user authentication.

    Usage:
        @app.post("/contacts")
        async def create_contact(
            tenant = Depends(require_user)
        ):
            # tenant.user_id is guaranteed to be set
            return await service.create(data)
    """
    ctx = TenantContext.get_current()

    if ctx is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TENANT_REQUIRED",
                "message": "Tenant identification required"
            }
        )

    if ctx.user_id is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": "USER_REQUIRED",
                "message": "User authentication required"
            }
        )

    return ctx


def require_tenant_role(*roles: TenantRole) -> Callable:
    """
    Dependency factory that requires specific tenant roles.

    Args:
        *roles: TenantRole values that are allowed

    Returns:
        Dependency function that validates role

    Usage:
        @app.delete("/admin/settings")
        async def admin_action(
            tenant = Depends(require_tenant_role(TenantRole.ADMIN, TenantRole.OWNER))
        ):
            # Only admins and owners can access
            pass
    """
    allowed_roles = set(r.value for r in roles)

    async def dependency(
        request: Request,
    ) -> TenantContextData:
        ctx = TenantContext.get_current()

        if ctx is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TENANT_REQUIRED",
                    "message": "Tenant identification required"
                }
            )

        # Check if user has any of the required roles
        user_roles = set(ctx.user_roles)
        if not (user_roles & allowed_roles):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_ROLE",
                    "message": f"Required role: {', '.join(allowed_roles)}",
                    "user_roles": list(ctx.user_roles),
                }
            )

        return ctx

    return dependency


def require_permission(permission: str) -> Callable:
    """
    Dependency factory that requires a specific custom permission.

    Args:
        permission: Permission string to require

    Returns:
        Dependency function that validates permission

    Usage:
        @app.post("/reports/export")
        async def export_reports(
            tenant = Depends(require_permission("export_reports"))
        ):
            # Only users with export_reports permission can access
            pass
    """
    async def dependency(
        request: Request,
    ) -> TenantContextData:
        ctx = TenantContext.get_current()

        if ctx is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TENANT_REQUIRED",
                    "message": "Tenant identification required"
                }
            )

        # Check custom permissions
        if not ctx.has_permission(permission):
            # Also check if user is admin (admins have all permissions)
            if not ctx.is_admin:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail={
                        "error": "PERMISSION_DENIED",
                        "message": f"Required permission: {permission}",
                    }
                )

        return ctx

    return dependency


async def get_isolation_strategy(
    request: Request,
) -> IsolationStrategy:
    """
    Get the isolation strategy from request state.

    Returns HybridIsolationStrategy if not set by middleware.

    Usage:
        @app.get("/contacts")
        async def list_contacts(
            isolation = Depends(get_isolation_strategy),
            session = Depends(get_session),
        ):
            await isolation.setup_session(session)
            # Use session with isolation configured
    """
    if hasattr(request.state, "isolation_strategy"):
        return request.state.isolation_strategy

    # Default to hybrid if not set
    return HybridIsolationStrategy()


async def get_tenant_id(
    tenant: TenantContextData = Depends(require_tenant),
) -> UUID:
    """
    Get just the tenant ID from context.

    Convenience dependency for routes that only need the tenant ID.

    Usage:
        @app.get("/contacts")
        async def list_contacts(
            tenant_id: UUID = Depends(get_tenant_id)
        ):
            return await service.get_by_tenant(tenant_id)
    """
    return tenant.tenant_id


async def get_user_id(
    tenant: TenantContextData = Depends(require_user),
) -> UUID:
    """
    Get just the user ID from context.

    Convenience dependency for routes that only need the user ID.

    Usage:
        @app.get("/my-contacts")
        async def my_contacts(
            user_id: UUID = Depends(get_user_id)
        ):
            return await service.get_by_user(user_id)
    """
    return tenant.user_id


async def get_tenant_config(
    request: Request,
) -> Optional[dict]:
    """
    Get tenant configuration/settings from context.

    Returns None if no tenant context is set.

    Usage:
        @app.get("/settings")
        async def get_settings(
            config = Depends(get_tenant_config)
        ):
            return config or {}
    """
    ctx = TenantContext.get_current()

    if ctx is None:
        return None

    # In actual implementation, this would fetch from tenant.settings
    # Here we return a placeholder
    return {}


async def require_active_tenant(
    request: Request,
) -> TenantContextData:
    """
    Require an active (non-suspended) tenant.

    Raises HTTP 403 if tenant is suspended or inactive.

    Usage:
        @app.post("/contacts")
        async def create_contact(
            tenant = Depends(require_active_tenant)
        ):
            # Tenant is guaranteed to be active
            pass
    """
    ctx = TenantContext.get_current()

    if ctx is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TENANT_REQUIRED",
                "message": "Tenant identification required"
            }
        )

    # Check tenant status via request state (set by middleware)
    if hasattr(request.state, "tenant_status"):
        if request.state.tenant_status not in ("active", "trial"):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "TENANT_INACTIVE",
                    "message": "Tenant is suspended or inactive",
                    "status": request.state.tenant_status
                }
            )

    return ctx
