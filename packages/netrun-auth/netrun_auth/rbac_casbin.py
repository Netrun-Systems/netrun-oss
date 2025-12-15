"""
Netrun Authentication - Casbin RBAC Manager
============================================

Casbin-backed RBAC manager with netrun-auth API compatibility.

Provides enterprise-grade RBAC with pluggable storage backends:
- Memory (default for development/testing)
- PostgreSQL (via casbin-async-sqlalchemy-adapter)
- Redis (via casbin-redis-adapter)

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-03
"""

import logging
from typing import List, Optional, Tuple, Any
from pathlib import Path

try:
    import casbin
    from casbin import AsyncEnforcer
    _HAS_CASBIN = True
except ImportError:
    _HAS_CASBIN = False
    AsyncEnforcer = None  # type: ignore

from .types import User
from .exceptions import PermissionDeniedError, RoleNotFoundError
from .models import RBAC_MODEL_PATH, RBAC_MODEL_TENANT_PATH

logger = logging.getLogger(__name__)


class CasbinRBACManager:
    """
    Casbin-backed RBAC manager with netrun-auth API compatibility.

    Features:
    - Pluggable storage backends (memory, PostgreSQL, Redis)
    - Multi-tenant support with domain-based isolation
    - Role hierarchy with inheritance
    - Wildcard permissions (e.g., "users:*", "*:read")
    - Async-first API

    Examples:
        # Memory backend (development)
        manager = CasbinRBACManager()
        await manager.initialize()

        # PostgreSQL backend (production)
        from casbin_async_sqlalchemy_adapter import Adapter
        adapter = Adapter("postgresql://...")
        manager = CasbinRBACManager(adapter=adapter)
        await manager.initialize()

        # Redis backend (distributed)
        from casbin_redis_adapter import Adapter
        adapter = Adapter("redis://localhost:6379")
        manager = CasbinRBACManager(adapter=adapter)
        await manager.initialize()
    """

    def __init__(
        self,
        model_path: str | None = None,
        policy_path: str | None = None,
        adapter: Any = None,
        multi_tenant: bool = False,
    ):
        """
        Initialize Casbin RBAC manager.

        Args:
            model_path: Path to Casbin model file (uses default if None)
            policy_path: Path to Casbin policy file (for file-based adapter)
            adapter: Casbin adapter instance (uses memory adapter if None)
            multi_tenant: Enable multi-tenant mode with domain-based isolation

        Raises:
            ImportError: If casbin package is not installed
        """
        if not _HAS_CASBIN:
            raise ImportError(
                "casbin package is required for CasbinRBACManager. "
                "Install with: pip install 'netrun-auth[casbin]'"
            )

        self.multi_tenant = multi_tenant
        self._model_path = model_path or (
            RBAC_MODEL_TENANT_PATH if multi_tenant else RBAC_MODEL_PATH
        )
        self._policy_path = policy_path
        self._adapter = adapter
        self._enforcer: Optional[AsyncEnforcer] = None

        logger.info(
            f"Initialized CasbinRBACManager (multi_tenant={multi_tenant}, "
            f"model={self._model_path}, adapter={type(adapter).__name__ if adapter else 'Memory'})"
        )

    async def initialize(self) -> None:
        """
        Initialize Casbin enforcer.

        Must be called before using the manager (supports async adapters).
        """
        if self._adapter:
            # Use provided adapter
            self._enforcer = casbin.AsyncEnforcer(self._model_path, self._adapter)
        elif self._policy_path:
            # Use file-based adapter
            self._enforcer = casbin.AsyncEnforcer(self._model_path, self._policy_path)
        else:
            # Use memory adapter (no persistence)
            self._enforcer = casbin.AsyncEnforcer(self._model_path)

        # Load policy from adapter if available
        if self._adapter:
            await self._enforcer.load_policy()

        logger.info("Casbin enforcer initialized successfully")

    async def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Check if user has permission to perform action on resource.

        Args:
            user_id: User unique identifier
            resource: Resource name (e.g., "users", "/api/users")
            action: Action name (e.g., "read", "GET")
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            True if permission granted, False otherwise

        Raises:
            ValueError: If tenant_id is required but not provided
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            # Format: enforce(subject, domain, object, action)
            # Note: enforce() is synchronous even in AsyncEnforcer
            return self._enforcer.enforce(user_id, tenant_id, resource, action)
        else:
            # Format: enforce(subject, object, action)
            return self._enforcer.enforce(user_id, resource, action)

    async def add_role_for_user(
        self,
        user_id: str,
        role: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Assign role to user.

        Args:
            user_id: User unique identifier
            role: Role name to assign
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            True if role added successfully
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            # Use domain-specific method
            result = await self._enforcer.add_role_for_user_in_domain(user_id, role, tenant_id)
        else:
            # Use standard method
            result = await self._enforcer.add_role_for_user(user_id, role)

        if result:
            logger.info(f"Added role '{role}' to user '{user_id}' (tenant={tenant_id})")

        return result

    async def remove_role_for_user(
        self,
        user_id: str,
        role: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Remove role from user.

        Args:
            user_id: User unique identifier
            role: Role name to remove
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            True if role removed successfully
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            result = await self._enforcer.delete_role_for_user_in_domain(user_id, role, tenant_id)
        else:
            result = await self._enforcer.delete_role_for_user(user_id, role)

        if result:
            logger.info(f"Removed role '{role}' from user '{user_id}' (tenant={tenant_id})")

        return result

    async def get_roles_for_user(
        self,
        user_id: str,
        tenant_id: str | None = None,
    ) -> List[str]:
        """
        Get all roles assigned to user.

        Args:
            user_id: User unique identifier
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            List of role names
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            # Get roles for user in specific domain
            roles = await self._enforcer.get_roles_for_user_in_domain(user_id, tenant_id)
        else:
            roles = await self._enforcer.get_roles_for_user(user_id)

        return roles

    async def add_permission_for_role(
        self,
        role: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Add permission to role.

        Args:
            role: Role name
            resource: Resource name
            action: Action name
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            True if permission added successfully
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            # Format: add_policy(subject, domain, object, action)
            result = await self._enforcer.add_policy(role, tenant_id, resource, action)
        else:
            # Format: add_policy(subject, object, action)
            result = await self._enforcer.add_policy(role, resource, action)

        if result:
            logger.info(
                f"Added permission '{resource}:{action}' to role '{role}' (tenant={tenant_id})"
            )

        return result

    async def remove_permission_for_role(
        self,
        role: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Remove permission from role.

        Args:
            role: Role name
            resource: Resource name
            action: Action name
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            True if permission removed successfully
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            result = await self._enforcer.remove_policy(role, tenant_id, resource, action)
        else:
            result = await self._enforcer.remove_policy(role, resource, action)

        if result:
            logger.info(
                f"Removed permission '{resource}:{action}' from role '{role}' (tenant={tenant_id})"
            )

        return result

    async def get_permissions_for_role(
        self,
        role: str,
        tenant_id: str | None = None,
    ) -> List[Tuple[str, str]]:
        """
        Get all permissions for role.

        Args:
            role: Role name
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            List of (resource, action) tuples
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        # Get all permissions for role
        permissions = await self._enforcer.get_permissions_for_user(role)

        # Filter by tenant if multi-tenant mode
        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            # Format: [role, tenant, resource, action]
            filtered = [
                (perm[2], perm[3])
                for perm in permissions
                if len(perm) >= 4 and perm[1] == tenant_id
            ]
            return filtered
        else:
            # Format: [role, resource, action]
            return [(perm[1], perm[2]) for perm in permissions if len(perm) >= 3]

    async def get_users_for_role(
        self,
        role: str,
        tenant_id: str | None = None,
    ) -> List[str]:
        """
        Get all users assigned to role.

        Args:
            role: Role name
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            List of user IDs
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            users = await self._enforcer.get_users_for_role_in_domain(role, tenant_id)
        else:
            users = await self._enforcer.get_users_for_role(role)

        return users

    async def delete_role(
        self,
        role: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Delete role and all associated permissions.

        Args:
            role: Role name to delete
            tenant_id: Tenant/organization identifier (required if multi_tenant=True)

        Returns:
            True if role deleted successfully
        """
        if not self._enforcer:
            raise RuntimeError("CasbinRBACManager not initialized. Call initialize() first.")

        # Remove all permissions for role
        if self.multi_tenant:
            if not tenant_id:
                raise ValueError("tenant_id is required for multi-tenant mode")
            result = await self._enforcer.remove_filtered_policy(0, role, tenant_id)
        else:
            result = await self._enforcer.remove_filtered_policy(0, role)

        if result:
            logger.info(f"Deleted role '{role}' (tenant={tenant_id})")

        return result

    async def clear_cache(self) -> None:
        """Clear internal Casbin cache."""
        if self._enforcer:
            # Only reload policy if using an adapter
            if self._adapter:
                await self._enforcer.load_policy()
            logger.info("Cleared Casbin cache")

    # Compatibility methods for netrun-auth API

    async def check_permission_for_user(
        self,
        user: User,
        permission: str,
        raise_exception: bool = True,
    ) -> bool:
        """
        Check if user has permission (netrun-auth compatibility).

        Args:
            user: User object
            permission: Permission string in "resource:action" format
            raise_exception: Raise exception if permission denied

        Returns:
            True if user has permission

        Raises:
            PermissionDeniedError: If raise_exception=True and permission denied
        """
        # Parse permission string
        if ":" not in permission:
            raise ValueError(f"Invalid permission format: {permission}. Expected 'resource:action'")

        resource, action = permission.split(":", 1)
        tenant_id = user.organization_id if self.multi_tenant else None

        # Check permission
        has_permission = await self.check_permission(
            user.user_id,
            resource,
            action,
            tenant_id=tenant_id,
        )

        if not has_permission and raise_exception:
            raise PermissionDeniedError(
                message=f"Permission denied: {permission}",
                permission=permission,
                details={
                    "user_id": user.user_id,
                    "organization_id": user.organization_id,
                }
            )

        return has_permission

    def get_enforcer(self) -> Optional[AsyncEnforcer]:
        """
        Get underlying Casbin enforcer for advanced operations.

        Returns:
            Casbin AsyncEnforcer instance or None if not initialized
        """
        return self._enforcer
