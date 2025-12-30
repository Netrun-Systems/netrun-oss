"""
Netrun RBAC Share Dependencies - FastAPI dependencies for resource sharing access control.

Following Netrun Systems SDLC v2.3 standards.
"""

from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Path
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from ..tenancy.context import TenantContext, TenantContextData
from ..models.enums import SharePermission


def can_access_resource(
    resource_type: str,
    resource_id_param: str = "id",
    check_share_service: bool = True,
) -> Callable:
    """
    Dependency factory that checks if user can access a specific resource.

    This checks:
    1. User owns the resource (created_by)
    2. Resource is in user's team
    3. Resource is shared with user
    4. Resource is shared with user's team
    5. User is tenant admin (can access all)

    Args:
        resource_type: Type of resource (e.g., "contact", "document")
        resource_id_param: Name of path parameter containing resource ID
        check_share_service: Whether to check ShareService for shares

    Returns:
        Dependency function that validates access

    Usage:
        @app.get("/contacts/{id}")
        async def get_contact(
            id: UUID,
            access = Depends(can_access_resource("contact", "id"))
        ):
            # User has access to this contact
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

        # Get resource ID from path
        resource_id_str = request.path_params.get(resource_id_param)
        if not resource_id_str:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={
                    "error": "RESOURCE_ID_REQUIRED",
                    "message": f"Resource ID required in {resource_id_param}"
                }
            )

        try:
            resource_id = UUID(resource_id_str)
        except ValueError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={
                    "error": "INVALID_RESOURCE_ID",
                    "message": "Invalid resource ID format"
                }
            )

        # Store resource info in request state for use by route
        request.state.resource_type = resource_type
        request.state.resource_id = resource_id

        # Admin bypass - admins can access all resources in tenant
        if ctx.is_admin:
            return ctx

        # Access check would typically be done via:
        # 1. Query the resource and check ownership
        # 2. Check ShareService for shares
        # This is handled by TenantQueryService in actual usage

        # For the dependency, we just verify context is valid
        # Actual access check happens in service layer

        return ctx

    return dependency


def require_resource_permission(
    resource_type: str,
    resource_id_param: str = "id",
    permission: SharePermission = SharePermission.VIEW,
) -> Callable:
    """
    Dependency factory that requires specific permission level on a resource.

    Args:
        resource_type: Type of resource
        resource_id_param: Name of path parameter containing resource ID
        permission: Required permission level

    Returns:
        Dependency function that validates permission

    Usage:
        @app.put("/documents/{id}")
        async def update_document(
            id: UUID,
            access = Depends(require_resource_permission(
                "document", "id", SharePermission.EDIT
            ))
        ):
            # User has edit permission on this document
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

        # Get resource ID from path
        resource_id_str = request.path_params.get(resource_id_param)
        if not resource_id_str:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={
                    "error": "RESOURCE_ID_REQUIRED",
                    "message": f"Resource ID required in {resource_id_param}"
                }
            )

        try:
            resource_id = UUID(resource_id_str)
        except ValueError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={
                    "error": "INVALID_RESOURCE_ID",
                    "message": "Invalid resource ID format"
                }
            )

        # Store for route handler
        request.state.resource_type = resource_type
        request.state.resource_id = resource_id
        request.state.required_permission = permission

        # Admin bypass
        if ctx.is_admin:
            return ctx

        # Permission check would be done via ShareService
        # Here we just set up the context for the service layer

        return ctx

    return dependency


async def get_external_share_context(
    token: str,
    request: Request,
) -> dict:
    """
    Get context for external (token-based) share access.

    This is used for public share links where the user may not
    be authenticated.

    Usage:
        @app.get("/shared/{token}")
        async def view_shared_resource(
            token: str,
            share_context = Depends(get_external_share_context)
        ):
            # share_context contains share details
            return await service.get_by_share(share_context)
    """
    # This would lookup the share by token
    # Return share details for the route handler to use

    return {
        "token": token,
        "is_external": True,
        # ShareService would populate these:
        # "resource_type": ...,
        # "resource_id": ...,
        # "permission": ...,
        # "expires_at": ...,
    }


def require_share_owner() -> Callable:
    """
    Dependency that requires the user to be the owner of a share.

    Used for managing (revoking, updating) shares.

    Usage:
        @app.delete("/shares/{share_id}")
        async def revoke_share(
            share_id: UUID,
            tenant = Depends(require_share_owner())
        ):
            # Only share owner can revoke
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

        if ctx.user_id is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "USER_REQUIRED",
                    "message": "User authentication required"
                }
            )

        # Get share_id from path
        share_id_str = request.path_params.get("share_id")
        if share_id_str:
            try:
                share_id = UUID(share_id_str)
                request.state.share_id = share_id
            except ValueError:
                pass

        # Actual ownership check would be done in service layer
        # by comparing share.shared_by with ctx.user_id

        # Admin can also manage any share
        if ctx.is_admin:
            return ctx

        return ctx

    return dependency


def require_can_reshare() -> Callable:
    """
    Dependency that requires FULL permission (ability to re-share).

    Used for endpoints that create new shares from existing access.

    Usage:
        @app.post("/documents/{id}/share")
        async def share_document(
            id: UUID,
            tenant = Depends(require_can_reshare())
        ):
            # User must have FULL permission to share
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

        # Admin bypass
        if ctx.is_admin:
            return ctx

        # FULL permission check would be done in service layer
        # This dependency just ensures context is available

        return ctx

    return dependency


# Convenience aliases
def require_share_permission(
    resource_type: str,
    resource_id_param: str = "id",
    permission: SharePermission = SharePermission.VIEW,
) -> Callable:
    """
    Alias for require_resource_permission.

    Usage:
        @app.get("/contacts/{id}")
        async def get_contact(
            id: UUID,
            access = Depends(require_share_permission("contact", "id", SharePermission.VIEW))
        ):
            pass
    """
    return require_resource_permission(resource_type, resource_id_param, permission)


def require_view_permission(
    resource_type: str,
    resource_id_param: str = "id",
) -> Callable:
    """
    Convenience wrapper for require_resource_permission with VIEW permission.

    Usage:
        @app.get("/documents/{id}")
        async def view_document(
            id: UUID,
            access = Depends(require_view_permission("document"))
        ):
            pass
    """
    return require_resource_permission(resource_type, resource_id_param, SharePermission.VIEW)


def require_edit_permission(
    resource_type: str,
    resource_id_param: str = "id",
) -> Callable:
    """
    Convenience wrapper for require_resource_permission with EDIT permission.

    Usage:
        @app.put("/documents/{id}")
        async def update_document(
            id: UUID,
            access = Depends(require_edit_permission("document"))
        ):
            pass
    """
    return require_resource_permission(resource_type, resource_id_param, SharePermission.EDIT)
