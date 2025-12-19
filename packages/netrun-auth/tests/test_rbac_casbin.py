"""
Tests for Casbin RBAC Manager

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-03
"""

import pytest
from netrun.auth.types import User

# Skip all tests if casbin not installed
pytest.importorskip("casbin")

from netrun.auth.rbac_casbin import CasbinRBACManager
from netrun.auth.exceptions import PermissionDeniedError


@pytest.fixture
async def casbin_manager():
    """Create Casbin RBAC manager with memory adapter."""
    manager = CasbinRBACManager(multi_tenant=False)
    await manager.initialize()
    return manager


@pytest.fixture
async def casbin_manager_tenant():
    """Create Casbin RBAC manager with multi-tenant support."""
    manager = CasbinRBACManager(multi_tenant=True)
    await manager.initialize()
    return manager


@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    return User(
        user_id="user123",
        organization_id="org456",
        roles=["user"],
        permissions=[],
    )


class TestCasbinRBACManager:
    """Test CasbinRBACManager basic functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test manager initialization."""
        manager = CasbinRBACManager()
        await manager.initialize()
        assert manager._enforcer is not None

    @pytest.mark.asyncio
    async def test_add_role_for_user(self, casbin_manager):
        """Test adding role to user."""
        result = await casbin_manager.add_role_for_user("user123", "admin")
        assert result is True

        roles = await casbin_manager.get_roles_for_user("user123")
        assert "admin" in roles

    @pytest.mark.asyncio
    async def test_remove_role_for_user(self, casbin_manager):
        """Test removing role from user."""
        # Add role first
        await casbin_manager.add_role_for_user("user123", "admin")

        # Remove role
        result = await casbin_manager.remove_role_for_user("user123", "admin")
        assert result is True

        roles = await casbin_manager.get_roles_for_user("user123")
        assert "admin" not in roles

    @pytest.mark.asyncio
    async def test_get_roles_for_user_empty(self, casbin_manager):
        """Test getting roles for user with no roles."""
        roles = await casbin_manager.get_roles_for_user("user123")
        assert roles == []

    @pytest.mark.asyncio
    async def test_add_permission_for_role(self, casbin_manager):
        """Test adding permission to role."""
        result = await casbin_manager.add_permission_for_role(
            "admin", "users", "read"
        )
        assert result is True

        permissions = await casbin_manager.get_permissions_for_role("admin")
        assert ("users", "read") in permissions

    @pytest.mark.asyncio
    async def test_remove_permission_for_role(self, casbin_manager):
        """Test removing permission from role."""
        # Add permission first
        await casbin_manager.add_permission_for_role("admin", "users", "read")

        # Remove permission
        result = await casbin_manager.remove_permission_for_role(
            "admin", "users", "read"
        )
        assert result is True

        permissions = await casbin_manager.get_permissions_for_role("admin")
        assert ("users", "read") not in permissions

    @pytest.mark.asyncio
    async def test_check_permission_granted(self, casbin_manager):
        """Test permission check when permission is granted."""
        # Setup: admin role can read users
        await casbin_manager.add_permission_for_role("admin", "users", "read")
        await casbin_manager.add_role_for_user("user123", "admin")

        # Check permission
        has_permission = await casbin_manager.check_permission(
            "user123", "users", "read"
        )
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, casbin_manager):
        """Test permission check when permission is denied."""
        # No permissions granted
        has_permission = await casbin_manager.check_permission(
            "user123", "users", "delete"
        )
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_get_users_for_role(self, casbin_manager):
        """Test getting all users assigned to role."""
        await casbin_manager.add_role_for_user("user1", "admin")
        await casbin_manager.add_role_for_user("user2", "admin")
        await casbin_manager.add_role_for_user("user3", "viewer")

        users = await casbin_manager.get_users_for_role("admin")
        assert "user1" in users
        assert "user2" in users
        assert "user3" not in users

    @pytest.mark.asyncio
    async def test_delete_role(self, casbin_manager):
        """Test deleting role and all associated permissions."""
        # Setup
        await casbin_manager.add_permission_for_role("admin", "users", "read")
        await casbin_manager.add_permission_for_role("admin", "users", "write")

        # Delete role
        result = await casbin_manager.delete_role("admin")
        assert result is True

        # Verify permissions removed
        permissions = await casbin_manager.get_permissions_for_role("admin")
        assert len(permissions) == 0


class TestCasbinMultiTenant:
    """Test Casbin RBAC manager with multi-tenant support."""

    @pytest.mark.asyncio
    async def test_add_role_for_user_with_tenant(self, casbin_manager_tenant):
        """Test adding role to user in specific tenant."""
        result = await casbin_manager_tenant.add_role_for_user(
            "user123", "admin", tenant_id="org1"
        )
        assert result is True

        roles = await casbin_manager_tenant.get_roles_for_user(
            "user123", tenant_id="org1"
        )
        assert "admin" in roles

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, casbin_manager_tenant):
        """Test that permissions are isolated between tenants."""
        # Add role in org1
        await casbin_manager_tenant.add_role_for_user(
            "user123", "admin", tenant_id="org1"
        )

        # Check roles in org1 and org2
        roles_org1 = await casbin_manager_tenant.get_roles_for_user(
            "user123", tenant_id="org1"
        )
        roles_org2 = await casbin_manager_tenant.get_roles_for_user(
            "user123", tenant_id="org2"
        )

        assert "admin" in roles_org1
        assert "admin" not in roles_org2

    @pytest.mark.asyncio
    async def test_check_permission_with_tenant(self, casbin_manager_tenant):
        """Test permission check in multi-tenant mode."""
        # Setup: admin role can read users in org1
        await casbin_manager_tenant.add_permission_for_role(
            "admin", "users", "read", tenant_id="org1"
        )
        await casbin_manager_tenant.add_role_for_user(
            "user123", "admin", tenant_id="org1"
        )

        # Check permission in org1
        has_permission_org1 = await casbin_manager_tenant.check_permission(
            "user123", "users", "read", tenant_id="org1"
        )
        assert has_permission_org1 is True

        # Check permission in org2 (should be denied)
        has_permission_org2 = await casbin_manager_tenant.check_permission(
            "user123", "users", "read", tenant_id="org2"
        )
        assert has_permission_org2 is False

    @pytest.mark.asyncio
    async def test_missing_tenant_id_raises_error(self, casbin_manager_tenant):
        """Test that missing tenant_id raises ValueError in multi-tenant mode."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await casbin_manager_tenant.check_permission(
                "user123", "users", "read"
            )


class TestCasbinCompatibility:
    """Test netrun-auth API compatibility methods."""

    @pytest.mark.asyncio
    async def test_check_permission_for_user(self, casbin_manager, sample_user):
        """Test check_permission_for_user compatibility method."""
        # Setup
        await casbin_manager.add_permission_for_role("user", "projects", "read")
        await casbin_manager.add_role_for_user("user123", "user")

        # Check permission
        has_permission = await casbin_manager.check_permission_for_user(
            sample_user, "projects:read", raise_exception=False
        )
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_permission_for_user_raises_exception(
        self, casbin_manager, sample_user
    ):
        """Test check_permission_for_user raises PermissionDeniedError."""
        # No permissions granted
        with pytest.raises(PermissionDeniedError, match="Permission denied"):
            await casbin_manager.check_permission_for_user(
                sample_user, "users:delete", raise_exception=True
            )

    @pytest.mark.asyncio
    async def test_invalid_permission_format(self, casbin_manager, sample_user):
        """Test invalid permission format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid permission format"):
            await casbin_manager.check_permission_for_user(
                sample_user, "invalid_permission", raise_exception=False
            )

    @pytest.mark.asyncio
    async def test_get_enforcer(self, casbin_manager):
        """Test get_enforcer returns underlying Casbin enforcer."""
        enforcer = casbin_manager.get_enforcer()
        assert enforcer is not None
        assert hasattr(enforcer, "enforce")


class TestCasbinUserIntegration:
    """Test User model integration with Casbin."""

    @pytest.mark.asyncio
    async def test_user_has_permission_casbin(self, casbin_manager, sample_user):
        """Test User.has_permission_casbin method."""
        # Setup
        await casbin_manager.add_permission_for_role("user", "projects", "read")
        await casbin_manager.add_role_for_user("user123", "user")

        # Check permission using User method
        enforcer = casbin_manager.get_enforcer()
        has_permission = await sample_user.has_permission_casbin(
            enforcer, "projects", "read"
        )
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_user_has_permission_casbin_with_tenant(
        self, casbin_manager_tenant
    ):
        """Test User.has_permission_casbin with tenant_id."""
        user = User(
            user_id="user123",
            organization_id="org1",
            roles=["admin"],
            permissions=[],
        )

        # Setup
        await casbin_manager_tenant.add_permission_for_role(
            "admin", "users", "write", tenant_id="org1"
        )
        await casbin_manager_tenant.add_role_for_user(
            "user123", "admin", tenant_id="org1"
        )

        # Check permission using User method (should use user's organization_id)
        enforcer = casbin_manager_tenant.get_enforcer()
        has_permission = await user.has_permission_casbin(
            enforcer, "users", "write"
        )
        assert has_permission is True


class TestCasbinEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_uninitialized_manager_raises_error(self):
        """Test that using uninitialized manager raises RuntimeError."""
        manager = CasbinRBACManager()
        # Don't call initialize()

        with pytest.raises(RuntimeError, match="not initialized"):
            await manager.check_permission("user123", "users", "read")

    @pytest.mark.asyncio
    async def test_clear_cache(self, casbin_manager):
        """Test clearing Casbin cache."""
        # Add some data
        await casbin_manager.add_role_for_user("user123", "admin")

        # Clear cache (should reload policy)
        await casbin_manager.clear_cache()

        # Verify data still exists after reload
        roles = await casbin_manager.get_roles_for_user("user123")
        assert "admin" in roles

    @pytest.mark.asyncio
    async def test_multiple_roles_per_user(self, casbin_manager):
        """Test user with multiple roles."""
        await casbin_manager.add_role_for_user("user123", "admin")
        await casbin_manager.add_role_for_user("user123", "viewer")

        roles = await casbin_manager.get_roles_for_user("user123")
        assert "admin" in roles
        assert "viewer" in roles
        assert len(roles) == 2

    @pytest.mark.asyncio
    async def test_multiple_permissions_per_role(self, casbin_manager):
        """Test role with multiple permissions."""
        await casbin_manager.add_permission_for_role("admin", "users", "read")
        await casbin_manager.add_permission_for_role("admin", "users", "write")
        await casbin_manager.add_permission_for_role("admin", "projects", "delete")

        permissions = await casbin_manager.get_permissions_for_role("admin")
        assert len(permissions) == 3
        assert ("users", "read") in permissions
        assert ("users", "write") in permissions
        assert ("projects", "delete") in permissions
