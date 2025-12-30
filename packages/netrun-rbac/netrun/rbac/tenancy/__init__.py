"""
Netrun RBAC Tenancy Module - Context management for multi-tenant applications.

Following Netrun Systems SDLC v2.3 standards.

Usage:
    from netrun.rbac.tenancy import TenantContext, TenancyConfig

    # Set context for a request
    with TenantContext(tenant_id=uuid, tenant_slug="acme", user_id=user_uuid):
        # All operations within this block are tenant-scoped
        contacts = await contact_service.get_all()

    # Get current context
    ctx = TenantContext.get_current()
    if ctx:
        print(f"Current tenant: {ctx.tenant_slug}")

    # Require context (raises if not set)
    ctx = TenantContext.require()
"""

from .context import (
    TenantContext,
    TenantContextData,
    get_tenant_context as get_current_tenant_context,
    require_tenant_context,
)
from .config import TenancyConfig, TenantResolutionStrategy
from .exceptions import (
    TenancyError,
    TenantContextError,
    TenantNotFoundError,
    TenantAccessDeniedError,
    TenantSuspendedError,
    CrossTenantViolationError,
    IsolationViolationError,
    TenantInactiveError,
    TenantLimitExceededError,
    TeamNotFoundError,
    TeamHierarchyError,
    SharePermissionError,
    ShareExpiredError,
    InvalidShareTargetError,
)

__all__ = [
    # Context
    "TenantContext",
    "TenantContextData",
    "get_current_tenant_context",
    "require_tenant_context",
    # Configuration
    "TenancyConfig",
    "TenantResolutionStrategy",
    # Exceptions
    "TenancyError",
    "TenantContextError",
    "TenantNotFoundError",
    "TenantAccessDeniedError",
    "TenantSuspendedError",
    "CrossTenantViolationError",
    "IsolationViolationError",
    "TenantInactiveError",
    "TenantLimitExceededError",
    "TeamNotFoundError",
    "TeamHierarchyError",
    "SharePermissionError",
    "ShareExpiredError",
    "InvalidShareTargetError",
]
