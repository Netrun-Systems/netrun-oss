"""
Netrun Authentication - Role-Based Access Control (RBAC)
=========================================================

Permission model with role aggregation and hierarchy support.

Permission Format: resource:action (e.g., "users:read", "admin:delete")

Changelog:
- v1.2.0: Integrated netrun-logging with structured permission check logging
- v1.0.0: Initial release with role hierarchy and permission model

Author: Netrun Systems
Version: 1.2.0
Date: 2025-12-05
"""

from typing import List, Set, Dict, Optional, Any
from functools import wraps

from .types import Role, Permission, User
from .exceptions import PermissionDeniedError, RoleNotFoundError

# Graceful netrun-logging integration
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger, bind_context
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)

logger = _logger


class RBACManager:
    """
    Role-Based Access Control manager.

    Manages roles, permissions, and role hierarchy with caching.
    """

    def __init__(self):
        """Initialize RBAC manager with default roles."""
        self.roles: Dict[str, Role] = {}
        self.role_hierarchy: Dict[str, List[str]] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self) -> None:
        """Initialize default role definitions."""
        # Define standard roles
        self.add_role(Role(
            name="viewer",
            permissions=[
                "users:read",
                "organizations:read",
                "projects:read",
                "services:read"
            ],
            description="Read-only access to all resources"
        ))

        self.add_role(Role(
            name="user",
            permissions=[
                "users:read",
                "users:update_self",
                "organizations:read",
                "projects:read",
                "projects:create",
                "projects:update",
                "services:read",
                "services:execute"
            ],
            inherits_from=["viewer"],
            description="Standard user with read/write access"
        ))

        self.add_role(Role(
            name="admin",
            permissions=[
                "users:read",
                "users:create",
                "users:update",
                "users:delete",
                "organizations:read",
                "organizations:update",
                "projects:read",
                "projects:create",
                "projects:update",
                "projects:delete",
                "services:read",
                "services:create",
                "services:update",
                "services:delete",
                "services:execute",
                "admin:access"
            ],
            inherits_from=["user"],
            description="Full administrative access"
        ))

        self.add_role(Role(
            name="super_admin",
            permissions=[
                "users:*",
                "organizations:*",
                "projects:*",
                "services:*",
                "admin:*",
                "system:*"
            ],
            inherits_from=["admin"],
            description="System-level administrative access"
        ))

        logger.info("Initialized default RBAC roles")

    def add_role(self, role: Role) -> None:
        """
        Add or update role definition.

        Args:
            role: Role to add
        """
        self.roles[role.name] = role
        if role.inherits_from:
            self.role_hierarchy[role.name] = role.inherits_from
        logger.debug(f"Added role: {role.name}")

    def get_role(self, role_name: str) -> Optional[Role]:
        """
        Get role definition by name.

        Args:
            role_name: Name of role to retrieve

        Returns:
            Role definition or None if not found
        """
        return self.roles.get(role_name)

    def get_role_permissions(self, role_name: str) -> Set[str]:
        """
        Get all permissions for a role including inherited permissions.

        Args:
            role_name: Name of role

        Returns:
            Set of permission strings

        Raises:
            RoleNotFoundError: If role does not exist
        """
        role = self.get_role(role_name)
        if not role:
            raise RoleNotFoundError(
                message=f"Role '{role_name}' not found",
                role=role_name
            )

        permissions = set(role.permissions)

        # Add inherited permissions
        if role.inherits_from:
            for parent_role_name in role.inherits_from:
                parent_permissions = self.get_role_permissions(parent_role_name)
                permissions.update(parent_permissions)

        return permissions

    def get_user_permissions(self, user: User) -> Set[str]:
        """
        Get all permissions for a user based on their roles.

        Args:
            user: User object with roles

        Returns:
            Set of permission strings
        """
        all_permissions = set(user.permissions)  # Direct permissions

        # Add role-based permissions
        for role_name in user.roles:
            try:
                role_permissions = self.get_role_permissions(role_name)
                all_permissions.update(role_permissions)
            except RoleNotFoundError:
                logger.warning(f"User {user.user_id} has unknown role: {role_name}")
                continue

        return all_permissions

    def check_permission(
        self,
        user: User,
        permission: str,
        raise_exception: bool = True
    ) -> bool:
        """
        Check if user has specific permission.

        Args:
            user: User to check
            permission: Permission string (e.g., "users:read")
            raise_exception: Raise exception if permission denied

        Returns:
            True if user has permission

        Raises:
            PermissionDeniedError: If raise_exception=True and permission denied
        """
        user_permissions = self.get_user_permissions(user)

        # Check exact match
        if permission in user_permissions:
            return True

        # Check wildcard permissions (e.g., "users:*" grants "users:read")
        perm = Permission.from_string(permission)
        for user_perm in user_permissions:
            if ":" in user_perm:
                resource, action = user_perm.split(":", 1)
                if resource == perm.resource and action == "*":
                    return True
                if resource == "*":
                    return True

        # Permission denied
        if raise_exception:
            if _use_netrun_logging:
                logger.warning(
                    "permission_denied",
                    user_id=user.user_id,
                    permission=permission,
                    user_roles=user.roles,
                    operation="permission_check"
                )
            raise PermissionDeniedError(
                message=f"Permission denied: {permission}",
                permission=permission,
                details={
                    "user_id": user.user_id,
                    "user_permissions": list(user_permissions)
                }
            )

        return False

    def check_any_permission(
        self,
        user: User,
        permissions: List[str],
        raise_exception: bool = True
    ) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            user: User to check
            permissions: List of permission strings
            raise_exception: Raise exception if no permissions match

        Returns:
            True if user has at least one permission

        Raises:
            PermissionDeniedError: If raise_exception=True and no permissions match
        """
        for permission in permissions:
            if self.check_permission(user, permission, raise_exception=False):
                return True

        if raise_exception:
            raise PermissionDeniedError(
                message=f"Requires one of: {', '.join(permissions)}",
                details={
                    "user_id": user.user_id,
                    "required_permissions": permissions
                }
            )

        return False

    def check_all_permissions(
        self,
        user: User,
        permissions: List[str],
        raise_exception: bool = True
    ) -> bool:
        """
        Check if user has all specified permissions.

        Args:
            user: User to check
            permissions: List of permission strings
            raise_exception: Raise exception if any permission missing

        Returns:
            True if user has all permissions

        Raises:
            PermissionDeniedError: If raise_exception=True and any permission missing
        """
        for permission in permissions:
            if not self.check_permission(user, permission, raise_exception=False):
                if raise_exception:
                    raise PermissionDeniedError(
                        message=f"Missing required permission: {permission}",
                        permission=permission,
                        details={
                            "user_id": user.user_id,
                            "required_permissions": permissions
                        }
                    )
                return False

        return True

    def has_role(self, user: User, role: str) -> bool:
        """
        Check if user has specific role.

        Args:
            user: User to check
            role: Role name

        Returns:
            True if user has role
        """
        return role in user.roles

    def has_any_role(self, user: User, roles: List[str]) -> bool:
        """
        Check if user has any of the specified roles.

        Args:
            user: User to check
            roles: List of role names

        Returns:
            True if user has at least one role
        """
        return any(role in user.roles for role in roles)

    def has_all_roles(self, user: User, roles: List[str]) -> bool:
        """
        Check if user has all specified roles.

        Args:
            user: User to check
            roles: List of role names

        Returns:
            True if user has all roles
        """
        return all(role in user.roles for role in roles)


# Singleton instances
_rbac_manager: Optional[RBACManager] = None
_casbin_manager = None  # type: ignore


def get_rbac_manager(
    backend: str = "memory",
    **kwargs
) -> RBACManager | Any:
    """
    Get RBAC manager instance with specified backend.

    Factory function to create RBAC managers with different storage backends:
    - "memory": In-memory RBAC (default, good for development/testing)
    - "casbin": Casbin-backed RBAC with memory adapter
    - "casbin-postgres": Casbin with PostgreSQL adapter
    - "casbin-redis": Casbin with Redis adapter

    Args:
        backend: Backend type ("memory", "casbin", "casbin-postgres", "casbin-redis")
        **kwargs: Additional arguments passed to backend constructor

    Returns:
        RBACManager or CasbinRBACManager instance

    Examples:
        # In-memory RBAC (default)
        rbac = get_rbac_manager()

        # Casbin with memory backend
        rbac = get_rbac_manager(backend="casbin")
        await rbac.initialize()

        # Casbin with PostgreSQL
        from casbin_async_sqlalchemy_adapter import Adapter
        adapter = Adapter("postgresql://...")
        rbac = get_rbac_manager(backend="casbin-postgres", adapter=adapter, multi_tenant=True)
        await rbac.initialize()

        # Casbin with Redis
        from casbin_redis_adapter import Adapter
        adapter = Adapter("redis://localhost:6379")
        rbac = get_rbac_manager(backend="casbin-redis", adapter=adapter)
        await rbac.initialize()
    """
    global _rbac_manager, _casbin_manager

    if backend == "memory":
        # Use traditional in-memory RBACManager
        if _rbac_manager is None:
            _rbac_manager = RBACManager()
        return _rbac_manager

    elif backend.startswith("casbin"):
        # Use Casbin-backed manager
        try:
            from .rbac_casbin import CasbinRBACManager
        except ImportError:
            raise ImportError(
                "Casbin backend requires casbin package. "
                "Install with: pip install 'netrun-auth[casbin]'"
            )

        # For casbin backends, always create new instance (or use provided singleton)
        # because different configurations may be needed
        if _casbin_manager is None or kwargs:
            _casbin_manager = CasbinRBACManager(**kwargs)

        return _casbin_manager

    else:
        raise ValueError(
            f"Unknown backend: {backend}. "
            f"Valid options: 'memory', 'casbin', 'casbin-postgres', 'casbin-redis'"
        )


# Legacy singleton function for backwards compatibility
def get_rbac_manager_legacy() -> RBACManager:
    """
    Get singleton RBAC manager instance (legacy, backwards compatibility).

    Returns:
        RBACManager instance

    Deprecated:
        Use get_rbac_manager() instead
    """
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def require_permission(permission: str):
    """
    Decorator to require specific permission for function/method.

    Args:
        permission: Required permission string

    Example:
        @require_permission("users:delete")
        def delete_user(user: User, user_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user from kwargs or first arg
            user = kwargs.get("user") or kwargs.get("current_user")
            if not user and args:
                user = args[0] if isinstance(args[0], User) else None

            if not user:
                raise PermissionDeniedError(
                    message="No user context available for permission check"
                )

            rbac = get_rbac_manager()
            rbac.check_permission(user, permission)
            return func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(role: str):
    """
    Decorator to require specific role for function/method.

    Args:
        role: Required role name

    Example:
        @require_role("admin")
        def admin_function(user: User):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = kwargs.get("user") or kwargs.get("current_user")
            if not user and args:
                user = args[0] if isinstance(args[0], User) else None

            if not user:
                raise PermissionDeniedError(
                    message="No user context available for role check"
                )

            if not user.has_role(role):
                raise RoleNotFoundError(
                    message=f"User does not have required role: {role}",
                    role=role
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator
