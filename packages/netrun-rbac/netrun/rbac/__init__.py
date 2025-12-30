"""
Netrun RBAC v3.0.0 - Multi-tenant Role-Based Access Control with PostgreSQL RLS

Following Netrun Systems SDLC v2.3 standards.

Features (v3.0.0):
- Unified tenant isolation (PostgreSQL RLS + Application-level filtering)
- Hierarchical teams with sub-team support
- Resource-level sharing (user/team/tenant/external)
- Generic TenantQueryService for auto-filtered CRUD
- FastAPI middleware stack for automatic tenant context
- Migration helpers and RLS policy generators
- Comprehensive testing utilities for isolation verification

Features (v2.x - Backward Compatible):
- Role hierarchy enforcement (owner > admin > member > viewer)
- FastAPI dependency injection for route protection
- Tenant context management
- Resource ownership validation
- Tenant isolation contract testing utilities
- Escape path detection for CI/CD pipelines

Quick Start (v3.0.0):
    from netrun.rbac import (
        # Middleware setup
        setup_tenancy_middleware, TenancyConfig, IsolationMode,
        # Context management
        TenantContextV3, TenantContextData,
        # Generic query service
        TenantQueryService,
        # Model mixins
        TenantMixin, TeamMixin, ShareableMixin,
        # FastAPI dependencies
        require_tenant, get_current_tenant, require_team_member,
    )

    app = FastAPI()

    # Setup middleware (one line!)
    setup_tenancy_middleware(
        app,
        config=TenancyConfig(isolation_mode=IsolationMode.HYBRID),
        get_session=get_db_session
    )

    # Define tenant-aware model
    class Contact(Base, TenantMixin, TeamMixin, ShareableMixin):
        __tablename__ = "contacts"
        id = Column(UUID, primary_key=True)
        name = Column(String(200))

    # Use auto-filtered service
    @app.get("/contacts")
    async def list_contacts(
        tenant = Depends(require_tenant),
        session = Depends(get_session)
    ):
        service = TenantQueryService(session, Contact)
        return await service.get_all(include_shared=True)

Legacy Usage (v2.x - Still Supported):
    from netrun.rbac import require_role, require_roles, TenantContext

    @app.get("/api/admin/dashboard")
    async def admin_dashboard(user: dict = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}
"""

# =============================================================================
# v3.0.0 - New Unified Tenancy System
# =============================================================================

# Models - Core data models and mixins
from .models import (
    # Enums
    TenantRole,
    TeamRole,
    SharePermission,
    TenantStatus,
    IsolationMode,
    InvitationStatus,
    # Mixins
    TenantMixin,
    TeamMixin,
    ShareableMixin,
    AuditMixin,
    SoftDeleteMixin,
    # Models
    Tenant,
    Team,
    TenantMembership,
    TeamMembership,
    TenantInvitation,
    ResourceShare,
)

# Tenancy - Context management and configuration
from .tenancy import (
    # Context
    TenantContext as TenantContextV3,  # Aliased to avoid conflict with v2
    TenantContextData,
    get_current_tenant_context,
    require_tenant_context,
    # Config
    TenancyConfig,
    TenantResolutionStrategy,
    # Exceptions
    TenancyError,
    TenantContextError,
    TenantNotFoundError,
    TenantInactiveError,
    TenantLimitExceededError,
    CrossTenantViolationError,
    TeamNotFoundError,
    TeamHierarchyError,
    SharePermissionError,
    ShareExpiredError,
    InvalidShareTargetError,
)

# Isolation - Isolation strategies
from .isolation import (
    IsolationStrategy,
    RLSIsolationStrategy,
    ApplicationIsolationStrategy,
    HybridIsolationStrategy,
    get_isolation_strategy,
)

# Middleware - FastAPI middleware components
from .middleware import (
    TenantResolutionMiddleware,
    IsolationEnforcementMiddleware,
    TenantSecurityMiddleware,
    setup_tenancy_middleware,
)

# Services - Business logic and query services
from .services import (
    TenantQueryService,
    TenantService,
    TeamService,
    MembershipService,
    ShareService,
)

# Dependencies - FastAPI dependency injection (v3.0.0)
from .dependencies import (
    # Tenant dependencies
    get_current_tenant,
    require_tenant,
    get_tenant_config,
    require_active_tenant,
    # Team dependencies
    get_user_teams,
    require_team_member,
    require_team_admin,
    require_team_owner,
    # Share dependencies
    can_access_resource,
    require_share_permission,
    require_edit_permission,
    require_view_permission,
)

# Dependencies - v2.x backward compatibility
from .dependencies_legacy import (
    require_role,
    require_roles,
    require_owner,
    require_admin,
    require_member,
    check_resource_ownership,
)

# Migrations - Database migration helpers
from .migrations import (
    add_tenancy_to_table,
    add_tenant_column_to_existing,
    add_team_column_to_existing,
    add_share_columns_to_existing,
    backfill_tenant_data,
    create_rls_helper_functions,
    create_tenancy_audit_triggers,
    generate_rls_policy,
    generate_rls_policies,
    enable_rls_on_table,
    disable_rls_on_table,
    generate_full_tenancy_setup,
)

# Testing - Test utilities and fixtures (v3.0.0)
from .testing import (
    # Factories
    TenantFactory,
    TeamFactory,
    UserFactory,
    # Fixtures
    tenant_context as tenant_context_fixture,
    create_test_tenant,
    create_test_team,
    create_test_user,
    # Isolation testing
    assert_tenant_isolation as assert_tenant_isolation_v3,
    assert_no_cross_tenant_access,
    IsolationTestCase,
    run_isolation_tests,
    multi_tenant_test,
)

# =============================================================================
# v2.x - Backward Compatibility (Legacy API)
# =============================================================================

from .models_legacy import Role, Permission, RoleHierarchy
from .policies import RLSPolicyGenerator
from .tenant import (
    TenantContext,  # v2 TenantContext
    set_tenant_context,
    clear_tenant_context,
)
from .exceptions import (
    RBACException,
    InsufficientPermissionsError,
    TenantIsolationError,
    ResourceOwnershipError,
)

# v2.1 Testing Utilities (Legacy)
from .testing_legacy import (
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

# =============================================================================
# Version and Exports
# =============================================================================

__version__ = "3.0.0"

__all__ = [
    # ==========================================================================
    # v3.0.0 Exports - New Unified Tenancy System
    # ==========================================================================

    # Models - Enums
    "TenantRole",
    "TeamRole",
    "SharePermission",
    "TenantStatus",
    "IsolationMode",
    "InvitationStatus",

    # Models - Mixins
    "TenantMixin",
    "TeamMixin",
    "ShareableMixin",
    "AuditMixin",
    "SoftDeleteMixin",

    # Models - Classes
    "Tenant",
    "Team",
    "TenantMembership",
    "TeamMembership",
    "TenantInvitation",
    "ResourceShare",

    # Tenancy - Context
    "TenantContextV3",
    "TenantContextData",
    "get_current_tenant_context",
    "require_tenant_context",

    # Tenancy - Config
    "TenancyConfig",
    "TenantResolutionStrategy",

    # Tenancy - Exceptions
    "TenancyError",
    "TenantContextError",
    "TenantNotFoundError",
    "TenantInactiveError",
    "TenantLimitExceededError",
    "CrossTenantViolationError",
    "TeamNotFoundError",
    "TeamHierarchyError",
    "SharePermissionError",
    "ShareExpiredError",
    "InvalidShareTargetError",

    # Isolation - Strategies
    "IsolationStrategy",
    "RLSIsolationStrategy",
    "ApplicationIsolationStrategy",
    "HybridIsolationStrategy",
    "get_isolation_strategy",

    # Middleware
    "TenantResolutionMiddleware",
    "IsolationEnforcementMiddleware",
    "TenantSecurityMiddleware",
    "setup_tenancy_middleware",

    # Services
    "TenantQueryService",
    "TenantService",
    "TeamService",
    "MembershipService",
    "ShareService",

    # Dependencies - v3.0.0 Tenant
    "get_current_tenant",
    "require_tenant",
    "get_tenant_config",
    "require_active_tenant",

    # Dependencies - v3.0.0 Team
    "get_user_teams",
    "require_team_member",
    "require_team_admin",
    "require_team_owner",

    # Dependencies - v3.0.0 Share
    "can_access_resource",
    "require_share_permission",
    "require_edit_permission",
    "require_view_permission",

    # Migrations - Table modification
    "add_tenancy_to_table",
    "add_tenant_column_to_existing",
    "add_team_column_to_existing",
    "add_share_columns_to_existing",
    "backfill_tenant_data",
    "create_rls_helper_functions",
    "create_tenancy_audit_triggers",

    # Migrations - RLS generation
    "generate_rls_policy",
    "generate_rls_policies",
    "enable_rls_on_table",
    "disable_rls_on_table",
    "generate_full_tenancy_setup",

    # Testing - Factories
    "TenantFactory",
    "TeamFactory",
    "UserFactory",

    # Testing - Fixtures
    "tenant_context_fixture",
    "create_test_tenant",
    "create_test_team",
    "create_test_user",

    # Testing - Isolation
    "assert_tenant_isolation_v3",
    "assert_no_cross_tenant_access",
    "IsolationTestCase",
    "run_isolation_tests",
    "multi_tenant_test",

    # ==========================================================================
    # v2.x Exports - Backward Compatibility
    # ==========================================================================

    # Dependencies (v2.x)
    "require_role",
    "require_roles",
    "require_owner",
    "require_admin",
    "require_member",
    "check_resource_ownership",

    # Models (v2.x)
    "Role",
    "Permission",
    "RoleHierarchy",

    # Policies (v2.x)
    "RLSPolicyGenerator",

    # Tenant Context (v2.x)
    "TenantContext",
    "set_tenant_context",
    "clear_tenant_context",

    # Exceptions (v2.x)
    "RBACException",
    "InsufficientPermissionsError",
    "TenantIsolationError",
    "ResourceOwnershipError",

    # Testing - Core Assertions (v2.1)
    "assert_tenant_isolation",
    "assert_tenant_isolation_sync",

    # Testing - Context Management (v2.1)
    "TenantTestContext",
    "tenant_test_context",

    # Testing - Background Tasks (v2.1)
    "BackgroundTaskTenantContext",
    "preserve_tenant_context",

    # Testing - Escape Path Detection (v2.1)
    "TenantEscapePathScanner",
    "EscapePathSeverity",
    "EscapePathFinding",

    # Testing - CI/CD Integration (v2.1)
    "ci_fail_on_findings",
    "tenant_isolation_test",

    # Testing - Compliance (v2.1)
    "get_compliance_documentation",
    "COMPLIANCE_MAPPING",
]
