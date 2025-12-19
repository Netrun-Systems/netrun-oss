"""
FastAPI Dependencies for RBAC Enforcement

Extracted from: Intirkast middleware/rbac.py + middleware/auth.py
Generalized for multi-project reuse with placeholder patterns

Usage:
    from netrun_rbac import require_role, require_admin

    @router.get("/admin/dashboard")
    async def admin_dashboard(user: dict = Depends(require_admin)):
        return {"message": "Admin access granted"}
"""

import logging
from typing import Callable, List

from fastapi import Depends, HTTPException

from .exceptions import InsufficientPermissionsError, ResourceOwnershipError
from .models import RoleHierarchy

logger = logging.getLogger(__name__)


# PLACEHOLDER: Replace with your authentication dependency
# This should return user context dict with: user_id, tenant_id, roles
def get_current_user() -> dict:
    """
    PLACEHOLDER: Replace with your authentication dependency

    Expected return format:
    {
        "user_id": "uuid-string",
        "tenant_id": "uuid-string",
        "email": "user@example.com",
        "roles": ["admin"],  # or single role as string
        "auth_source": "jwt|session|azure_ad"
    }

    Example replacement:
        from your_app.auth import get_current_user_token

        def get_current_user(token: dict = Depends(get_current_user_token)):
            return {
                "user_id": token["sub"],
                "tenant_id": token["tenant_id"],
                "roles": token.get("roles", ["member"])
            }
    """
    raise HTTPException(
        status_code=500,
        detail="RBAC not configured: Replace get_current_user placeholder with your auth dependency",
    )


def require_role(required_role: str) -> Callable:
    """
    Dependency factory to enforce role requirements (hierarchical)

    Extracted from: Intirkast middleware/rbac.py (require_role pattern)

    Args:
        required_role: Minimum required role (viewer|member|admin|owner)

    Returns:
        FastAPI dependency function

    Usage:
        @router.get("/api/admin/settings")
        async def get_settings(user: dict = Depends(require_role("admin"))):
            # Only admin and owner can access
            return {"settings": "..."}

        @router.delete("/api/tenant")
        async def delete_tenant(user: dict = Depends(require_role("owner"))):
            # Only owner can delete tenant
            return {"status": "deleted"}
    """

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        """
        Validate user has required role level

        Args:
            user: User context from authentication

        Returns:
            User context if authorized

        Raises:
            InsufficientPermissionsError: If user lacks required role
        """
        user_roles = user.get("roles", [])

        # Ensure roles is a list
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        # Get highest role level from user's roles
        user_role_level = max(
            [RoleHierarchy.get_role_level(role) for role in user_roles], default=-1
        )

        required_level = RoleHierarchy.get_role_level(required_role)

        if user_role_level < required_level:
            logger.warning(
                f"Access denied: User {user.get('user_id')} has roles {user_roles}, "
                f"but {required_role} required"
            )
            raise InsufficientPermissionsError(
                required_role=required_role, user_role=user_roles[0] if user_roles else None
            )

        return user

    return role_checker


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory to enforce multiple allowed roles (non-hierarchical)

    Extracted from: Intirkast middleware/rbac.py (require_any_role pattern)

    Args:
        allowed_roles: List of allowed roles

    Returns:
        FastAPI dependency function

    Usage:
        @router.patch("/api/posts/{post_id}")
        async def update_post(
            post_id: str,
            user: dict = Depends(require_roles(["member", "admin", "owner"]))
        ):
            # Members, admins, or owners can update posts
            return {"status": "updated"}
    """

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        """
        Validate user has one of the allowed roles

        Args:
            user: User context from authentication

        Returns:
            User context if authorized

        Raises:
            InsufficientPermissionsError: If user lacks any allowed role
        """
        user_roles = user.get("roles", [])

        # Ensure roles is a list
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        # Check if user has any of the required roles
        has_required_role = any(role in user_roles for role in allowed_roles)

        if not has_required_role:
            logger.warning(
                f"Access denied: User {user.get('user_id')} has roles {user_roles}, "
                f"but one of {allowed_roles} required"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )

        return user

    return role_checker


def require_owner() -> Callable:
    """
    Dependency to enforce owner-only access

    Convenience wrapper for require_role("owner")

    Usage:
        @router.delete("/api/tenant/{tenant_id}")
        async def delete_tenant(
            tenant_id: str,
            user: dict = Depends(require_owner())
        ):
            # Only tenant owner can delete
            return {"status": "deleted"}
    """
    return require_role("owner")


def require_admin() -> Callable:
    """
    Dependency to enforce admin or owner access

    Convenience wrapper for require_role("admin")

    Usage:
        @router.post("/api/users/invite")
        async def invite_user(
            invite_data: InviteRequest,
            user: dict = Depends(require_admin())
        ):
            # Admins and owners can invite users
            return {"status": "invited"}
    """
    return require_role("admin")


def require_member() -> Callable:
    """
    Dependency to enforce member, admin, or owner access

    Convenience wrapper for require_role("member")

    Usage:
        @router.post("/api/content/schedule")
        async def schedule_content(
            content_data: ContentRequest,
            user: dict = Depends(require_member())
        ):
            # Members, admins, and owners can schedule content
            return {"status": "scheduled"}
    """
    return require_role("member")


def check_resource_ownership(user: dict, resource_user_id: str) -> bool:
    """
    Helper function to check if user owns a resource or is owner/admin

    Extracted from: Intirkast middleware/rbac.py (check_resource_ownership)

    Args:
        user: User context from authentication
        resource_user_id: User ID who owns the resource

    Returns:
        True if user can access the resource

    Usage in endpoint logic:
        @router.patch("/api/posts/{post_id}")
        async def update_post(
            post_id: str,
            post_data: UpdatePostRequest,
            user: dict = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            # Get post from database
            post = await db.get(Post, post_id)

            # Check ownership
            if not check_resource_ownership(user, post.user_id):
                raise HTTPException(status_code=403, detail="Not authorized")

            # Update post...
    """
    user_roles = user.get("roles", [])
    current_user_id = user.get("user_id")

    # Ensure roles is a list
    if isinstance(user_roles, str):
        user_roles = [user_roles]

    # Owners and admins can access all resources
    if "owner" in user_roles or "admin" in user_roles:
        return True

    # Otherwise, must be resource owner
    return current_user_id == resource_user_id


def require_owner_or_self(resource_user_id_getter: Callable) -> Callable:
    """
    Dependency factory to enforce owner role OR self-access

    Extracted from: Intirkast middleware/rbac.py (require_owner_or_self pattern)

    Args:
        resource_user_id_getter: Async function to get resource's user_id

    Returns:
        FastAPI dependency function

    Usage:
        async def get_user_id_from_path(user_id: str) -> str:
            return user_id

        @router.patch("/api/users/{user_id}")
        async def update_user(
            user_id: str,
            user_data: UpdateUserRequest,
            current_user: dict = Depends(require_owner_or_self(get_user_id_from_path))
        ):
            # Users can update their own profile, or owners can update anyone
            return {"status": "updated"}
    """

    async def access_checker(
        current_user: dict = Depends(get_current_user),
        resource_user_id: str = Depends(resource_user_id_getter),
    ) -> dict:
        """
        Validate user is owner OR accessing their own resource

        Args:
            current_user: User context from authentication
            resource_user_id: User ID who owns the resource

        Returns:
            User context if authorized

        Raises:
            ResourceOwnershipError: If user lacks access
        """
        user_roles = current_user.get("roles", [])
        current_user_id = current_user.get("user_id")

        # Ensure roles is a list
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        # Check if user is owner OR accessing their own resource
        is_owner = "owner" in user_roles
        is_self = current_user_id == resource_user_id

        if not (is_owner or is_self):
            logger.warning(
                f"Access denied: User {current_user_id} attempting to access "
                f"resource owned by {resource_user_id}"
            )
            raise ResourceOwnershipError()

        return current_user

    return access_checker
