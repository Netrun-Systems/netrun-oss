"""
Netrun RBAC Dependencies Module - FastAPI dependency injection for tenancy.

Following Netrun Systems SDLC v2.3 standards.

Provides injectable dependencies for route handlers:
- get_current_tenant: Get current tenant context
- require_tenant: Require tenant context (raises if missing)
- require_tenant_role: Require specific role in tenant
- require_team_member: Require team membership
- can_access_resource: Check resource access via shares

v3.0.0 Features:
- Full tenant context injection
- Team hierarchy support
- Resource share permissions

v2.x Backward Compatibility:
- require_role, require_roles (role hierarchy enforcement)
- require_owner, require_admin, require_member (convenience functions)
- check_resource_ownership (resource access validation)

Usage:
    from fastapi import Depends
    from netrun.rbac.dependencies import require_tenant, require_tenant_role

    @app.get("/contacts")
    async def list_contacts(
        tenant = Depends(require_tenant),
    ):
        # tenant is TenantContextData
        return await service.get_all()

    @app.delete("/admin/settings")
    async def delete_settings(
        tenant = Depends(require_tenant_role(TenantRole.ADMIN)),
    ):
        # Only admins can access
        pass
"""

# v3.0.0 Dependencies
from .tenant import (
    get_current_tenant,
    require_tenant,
    require_tenant_role,
    require_user,
    get_isolation_strategy,
    get_tenant_config,
    require_active_tenant,
)
from .team import (
    require_team_member,
    require_team_role,
    get_user_teams,
    require_team_admin,
    require_team_owner,
)
from .share import (
    can_access_resource,
    require_resource_permission,
    require_share_permission,
    require_edit_permission,
    require_view_permission,
)

# v2.x Backward Compatibility
from ..dependencies_legacy import (
    require_role,
    require_roles,
    require_owner,
    require_admin,
    require_member,
    check_resource_ownership,
    require_owner_or_self,
)

__all__ = [
    # v3.0.0 - Tenant dependencies
    "get_current_tenant",
    "require_tenant",
    "require_tenant_role",
    "require_user",
    "get_isolation_strategy",
    "get_tenant_config",
    "require_active_tenant",
    # v3.0.0 - Team dependencies
    "require_team_member",
    "require_team_role",
    "get_user_teams",
    "require_team_admin",
    "require_team_owner",
    # v3.0.0 - Share dependencies
    "can_access_resource",
    "require_resource_permission",
    "require_share_permission",
    "require_edit_permission",
    "require_view_permission",
    # v2.x - Backward Compatibility
    "require_role",
    "require_roles",
    "require_owner",
    "require_admin",
    "require_member",
    "check_resource_ownership",
    "require_owner_or_self",
]
