"""
Netrun Authentication - FastAPI Dependencies
=============================================

Dependency injection functions for FastAPI routes.

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

from typing import Optional, List
from fastapi import Request, Depends, HTTPException, status

from .types import User, AuthContext
from .rbac import RBACManager, get_rbac_manager
from .exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    RoleNotFoundError
)


def get_auth_context(request: Request) -> AuthContext:
    """
    Get authentication context from request state.

    Dependency for FastAPI routes requiring authentication.

    Args:
        request: FastAPI request

    Returns:
        AuthContext with user information

    Raises:
        HTTPException: If user not authenticated

    Example:
        @app.get("/protected")
        def protected_route(auth: AuthContext = Depends(get_auth_context)):
            return {"user_id": auth.user_id}
    """
    if not hasattr(request.state, "auth"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return request.state.auth


def get_current_user(auth_context: AuthContext = Depends(get_auth_context)) -> User:
    """
    Get current authenticated user.

    Dependency for FastAPI routes requiring user information.

    Args:
        auth_context: Authentication context from middleware

    Returns:
        User object with roles and permissions

    Example:
        @app.get("/me")
        def get_me(user: User = Depends(get_current_user)):
            return {"user_id": user.user_id, "roles": user.roles}
    """
    return auth_context.to_user()


def get_current_user_optional(request: Request) -> Optional[User]:
    """
    Get current authenticated user (optional).

    Dependency for routes that work with or without authentication.

    Args:
        request: FastAPI request

    Returns:
        User object if authenticated, None otherwise

    Example:
        @app.get("/public")
        def public_route(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                return {"authenticated": True, "user_id": user.user_id}
            return {"authenticated": False}
    """
    if not hasattr(request.state, "auth"):
        return None

    return request.state.auth.to_user()


def require_roles(*roles: str):
    """
    Create dependency that requires user to have specific roles.

    Args:
        *roles: Role names required (OR logic - user needs at least one)

    Returns:
        Dependency function

    Raises:
        HTTPException: If user doesn't have required role

    Example:
        @app.get("/admin")
        def admin_route(user: User = Depends(require_roles("admin", "super_admin"))):
            return {"message": "Admin access granted"}
    """
    def check_roles(user: User = Depends(get_current_user)) -> User:
        if not user.has_any_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}"
            )
        return user

    return check_roles


def require_all_roles(*roles: str):
    """
    Create dependency that requires user to have all specified roles.

    Args:
        *roles: Role names required (AND logic - user needs all)

    Returns:
        Dependency function

    Raises:
        HTTPException: If user doesn't have all required roles

    Example:
        @app.get("/special")
        def special_route(user: User = Depends(require_all_roles("admin", "auditor"))):
            return {"message": "Special access granted"}
    """
    def check_roles(user: User = Depends(get_current_user)) -> User:
        if not user.has_all_roles(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires all roles: {', '.join(roles)}"
            )
        return user

    return check_roles


def require_permissions(*permissions: str):
    """
    Create dependency that requires user to have specific permissions.

    Args:
        *permissions: Permission strings required (OR logic - user needs at least one)

    Returns:
        Dependency function

    Raises:
        HTTPException: If user doesn't have required permission

    Example:
        @app.delete("/users/{user_id}")
        def delete_user(
            user_id: str,
            user: User = Depends(require_permissions("users:delete", "admin:delete"))
        ):
            return {"message": f"Deleted user {user_id}"}
    """
    def check_permissions(
        user: User = Depends(get_current_user),
        rbac: RBACManager = Depends(get_rbac_manager)
    ) -> User:
        try:
            rbac.check_any_permission(user, list(permissions))
        except PermissionDeniedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message
            )
        return user

    return check_permissions


def require_all_permissions(*permissions: str):
    """
    Create dependency that requires user to have all specified permissions.

    Args:
        *permissions: Permission strings required (AND logic - user needs all)

    Returns:
        Dependency function

    Raises:
        HTTPException: If user doesn't have all required permissions

    Example:
        @app.post("/admin/critical")
        def critical_operation(
            user: User = Depends(require_all_permissions("admin:write", "admin:execute"))
        ):
            return {"message": "Critical operation executed"}
    """
    def check_permissions(
        user: User = Depends(get_current_user),
        rbac: RBACManager = Depends(get_rbac_manager)
    ) -> User:
        try:
            rbac.check_all_permissions(user, list(permissions))
        except PermissionDeniedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message
            )
        return user

    return check_permissions


def require_organization(organization_id: str):
    """
    Create dependency that requires user to belong to specific organization.

    Args:
        organization_id: Organization ID required

    Returns:
        Dependency function

    Raises:
        HTTPException: If user doesn't belong to organization

    Example:
        @app.get("/org/{org_id}/data")
        def get_org_data(
            org_id: str,
            user: User = Depends(require_organization(org_id))
        ):
            return {"organization_id": org_id, "data": "..."}
    """
    def check_organization(user: User = Depends(get_current_user)) -> User:
        if user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Organization mismatch"
            )
        return user

    return check_organization


def require_self_or_permission(user_id_param: str, permission: str):
    """
    Create dependency that requires user to be acting on themselves OR have permission.

    Useful for endpoints like "update profile" where users can update their own
    profile, or admins can update any profile.

    Args:
        user_id_param: Name of path/query parameter containing target user ID
        permission: Permission required for non-self access

    Returns:
        Dependency function

    Raises:
        HTTPException: If user is not self and lacks permission

    Example:
        @app.put("/users/{user_id}")
        def update_user(
            user_id: str,
            user: User = Depends(require_self_or_permission("user_id", "users:update"))
        ):
            return {"message": f"Updated user {user_id}"}
    """
    def check_self_or_permission(
        request: Request,
        user: User = Depends(get_current_user),
        rbac: RBACManager = Depends(get_rbac_manager)
    ) -> User:
        # Extract target user ID from path parameters
        target_user_id = request.path_params.get(user_id_param)

        # Allow if user is acting on themselves
        if target_user_id == user.user_id:
            return user

        # Otherwise check permission
        try:
            rbac.check_permission(user, permission)
        except PermissionDeniedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message
            )

        return user

    return check_self_or_permission
