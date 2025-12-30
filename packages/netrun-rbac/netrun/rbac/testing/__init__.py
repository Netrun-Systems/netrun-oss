"""
Netrun RBAC Testing Module - Test utilities and fixtures for multi-tenant testing.

Following Netrun Systems SDLC v2.3 standards.

Provides:
- Pytest fixtures for tenant context
- Cross-tenant isolation test helpers
- Mock tenant/team/user factories
- Isolation violation detection

Usage:
    import pytest
    from netrun.rbac.testing import (
        tenant_context,
        multi_tenant_test,
        TenantFactory,
        assert_tenant_isolation,
    )

    @pytest.fixture
    def tenant(tenant_factory):
        return tenant_factory.create()

    def test_contacts_isolated(tenant_context, contact_service):
        with tenant_context(tenant_id=tenant1.id):
            contacts = await contact_service.get_all()
            # Only tenant1's contacts returned
"""

from .fixtures import (
    TenantFactory,
    TeamFactory,
    UserFactory,
    tenant_context,
    create_test_tenant,
    create_test_team,
    create_test_user,
)
from .isolation_tests import (
    assert_tenant_isolation,
    assert_no_cross_tenant_access,
    IsolationTestCase,
    run_isolation_tests,
    multi_tenant_test,
)

__all__ = [
    # Factories
    "TenantFactory",
    "TeamFactory",
    "UserFactory",
    # Fixtures
    "tenant_context",
    "create_test_tenant",
    "create_test_team",
    "create_test_user",
    # Isolation testing
    "assert_tenant_isolation",
    "assert_no_cross_tenant_access",
    "IsolationTestCase",
    "run_isolation_tests",
    "multi_tenant_test",
]
