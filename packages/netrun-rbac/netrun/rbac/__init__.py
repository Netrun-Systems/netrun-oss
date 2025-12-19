"""
Netrun RBAC - Multi-tenant Role-Based Access Control with PostgreSQL RLS

Extracted from Intirkast SaaS platform (85% code reuse, 12h time savings)

Features:
- Role hierarchy enforcement (owner > admin > member > viewer)
- FastAPI dependency injection for route protection
- PostgreSQL Row-Level Security (RLS) policy generators
- Tenant context management
- Resource ownership validation
- Project-agnostic with placeholder configuration
- Tenant isolation contract testing utilities (NEW in v2.1)
- Escape path detection for CI/CD pipelines (NEW in v2.1)

Usage:
    from netrun.rbac import require_role, require_roles, TenantContext, RLSPolicyGenerator

    @app.get("/api/admin/dashboard")
    async def admin_dashboard(user: dict = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}

Testing Tenant Isolation:
    from netrun.rbac import (
        assert_tenant_isolation,
        TenantTestContext,
        TenantEscapePathScanner,
    )

    # Assert query has tenant filter
    query = select(Item).where(Item.tenant_id == tenant_id)
    await assert_tenant_isolation(query)

    # Test cross-tenant isolation
    async with TenantTestContext(session) as ctx:
        # Create data in tenant A, switch to B, verify isolation
        await ctx.switch_to_tenant_b()
        items = await session.execute(select(Item))
        assert len(items.scalars().all()) == 0  # Must not see tenant A's data!

    # Scan codebase for escape paths (CI/CD)
    scanner = TenantEscapePathScanner()
    findings = scanner.scan_directory("./src")
    sys.exit(ci_fail_on_findings(findings))
"""

from .dependencies import (
    require_role,
    require_roles,
    require_owner,
    require_admin,
    require_member,
    check_resource_ownership,
)
from .models import Role, Permission, RoleHierarchy
from .policies import RLSPolicyGenerator
from .tenant import TenantContext, set_tenant_context, clear_tenant_context
from .exceptions import (
    RBACException,
    InsufficientPermissionsError,
    TenantIsolationError,
    ResourceOwnershipError,
)

# Tenant Isolation Testing Utilities (v2.1)
from .testing import (
    # Core assertions
    assert_tenant_isolation,
    assert_tenant_isolation_sync,
    # Test context management
    TenantTestContext,
    tenant_test_context,
    # Background task handling
    BackgroundTaskTenantContext,
    preserve_tenant_context,
    # Escape path detection
    TenantEscapePathScanner,
    EscapePathSeverity,
    EscapePathFinding,
    # CI/CD utilities
    ci_fail_on_findings,
    # Pytest integration
    tenant_isolation_test,
    # Compliance
    get_compliance_documentation,
    COMPLIANCE_MAPPING,
)

__version__ = "2.1.0"
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
    # Testing - Core Assertions
    "assert_tenant_isolation",
    "assert_tenant_isolation_sync",
    # Testing - Context Management
    "TenantTestContext",
    "tenant_test_context",
    # Testing - Background Tasks
    "BackgroundTaskTenantContext",
    "preserve_tenant_context",
    # Testing - Escape Path Detection
    "TenantEscapePathScanner",
    "EscapePathSeverity",
    "EscapePathFinding",
    # Testing - CI/CD Integration
    "ci_fail_on_findings",
    "tenant_isolation_test",
    # Testing - Compliance
    "get_compliance_documentation",
    "COMPLIANCE_MAPPING",
]
