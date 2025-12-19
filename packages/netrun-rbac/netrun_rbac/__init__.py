"""
DEPRECATED: netrun_rbac → netrun.rbac

This module provides backwards compatibility for code using the old import path.

Migration Guide:
    OLD: from netrun_rbac import require_role, Role
    NEW: from netrun.rbac import require_role, Role

This compatibility layer will be removed in version 3.0.0.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'netrun_rbac' package has been migrated to namespace package 'netrun.rbac'. "
    "Please update your imports: 'from netrun.rbac import ...' instead of 'from netrun_rbac import ...'. "
    "This compatibility shim will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from new location
from netrun.rbac import (
    # Dependencies
    require_role,
    require_roles,
    require_owner,
    require_admin,
    require_member,
    check_resource_ownership,
    # Models
    Role,
    Permission,
    RoleHierarchy,
    # Policies
    RLSPolicyGenerator,
    # Tenant Context
    TenantContext,
    set_tenant_context,
    clear_tenant_context,
    # Exceptions
    RBACException,
    InsufficientPermissionsError,
    TenantIsolationError,
    ResourceOwnershipError,
)

__version__ = "2.0.0"
__all__ = [
    # Dependencies
    "require_role",
    "require_roles",
    "require_owner",
    "require_admin",
    "require_member",
    "check_resource_ownership",
    # Models
    "Role",
    "Permission",
    "RoleHierarchy",
    # Policies
    "RLSPolicyGenerator",
    # Tenant Context
    "TenantContext",
    "set_tenant_context",
    "clear_tenant_context",
    # Exceptions
    "RBACException",
    "InsufficientPermissionsError",
    "TenantIsolationError",
    "ResourceOwnershipError",
]
