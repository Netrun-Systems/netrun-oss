"""
Tests for RBAC Models

Tests role hierarchy, permission mappings, and role validation
"""

import pytest

from netrun.rbac.models import Role, Permission, RoleHierarchy, RoleAssignment


class TestRole:
    """Test Role enum"""

    def test_role_values(self):
        """Test role enum values"""
        assert Role.VIEWER.value == "viewer"
        assert Role.MEMBER.value == "member"
        assert Role.ADMIN.value == "admin"
        assert Role.OWNER.value == "owner"

    def test_role_comparison(self):
        """Test role enum equality"""
        assert Role.VIEWER == Role.VIEWER
        assert Role.ADMIN != Role.MEMBER


class TestRoleHierarchy:
    """Test RoleHierarchy utilities"""

    def test_hierarchy_levels(self):
        """Test role hierarchy numeric levels"""
        assert RoleHierarchy.HIERARCHY[Role.VIEWER] == 0
        assert RoleHierarchy.HIERARCHY[Role.MEMBER] == 1
        assert RoleHierarchy.HIERARCHY[Role.ADMIN] == 2
        assert RoleHierarchy.HIERARCHY[Role.OWNER] == 3

    def test_check_role_permission_valid(self):
        """Test hierarchical role permission checks (valid)"""
        # Owner can access admin-required resources
        assert RoleHierarchy.check_role_permission("owner", "admin") is True

        # Admin can access member-required resources
        assert RoleHierarchy.check_role_permission("admin", "member") is True

        # Member can access viewer-required resources
        assert RoleHierarchy.check_role_permission("member", "viewer") is True

        # Same role should work
        assert RoleHierarchy.check_role_permission("admin", "admin") is True

    def test_check_role_permission_invalid(self):
        """Test hierarchical role permission checks (invalid)"""
        # Viewer cannot access member-required resources
        assert RoleHierarchy.check_role_permission("viewer", "member") is False

        # Member cannot access admin-required resources
        assert RoleHierarchy.check_role_permission("member", "admin") is False

        # Admin cannot access owner-required resources
        assert RoleHierarchy.check_role_permission("admin", "owner") is False

    def test_check_role_permission_invalid_role(self):
        """Test hierarchical check with invalid role"""
        # Invalid user role
        assert RoleHierarchy.check_role_permission("invalid", "admin") is False

        # Invalid required role
        assert RoleHierarchy.check_role_permission("admin", "invalid") is False

    def test_get_role_level(self):
        """Test get_role_level method"""
        assert RoleHierarchy.get_role_level("viewer") == 0
        assert RoleHierarchy.get_role_level("member") == 1
        assert RoleHierarchy.get_role_level("admin") == 2
        assert RoleHierarchy.get_role_level("owner") == 3

        # Invalid role
        assert RoleHierarchy.get_role_level("invalid") == -1

    def test_has_permission(self):
        """Test permission checking"""
        # Viewer has read permissions
        assert RoleHierarchy.has_permission("viewer", Permission.USERS_READ) is True
        assert RoleHierarchy.has_permission("viewer", Permission.TENANT_READ) is True

        # Viewer cannot create content
        assert RoleHierarchy.has_permission("viewer", Permission.CONTENT_CREATE) is False

        # Member can create content
        assert RoleHierarchy.has_permission("member", Permission.CONTENT_CREATE) is True

        # Admin can invite users
        assert RoleHierarchy.has_permission("admin", Permission.INVITATIONS_CREATE) is True

        # Owner can delete tenant
        assert RoleHierarchy.has_permission("owner", Permission.TENANT_DELETE) is True

        # Invalid role
        assert RoleHierarchy.has_permission("invalid", Permission.USERS_READ) is False


class TestRoleAssignment:
    """Test RoleAssignment Pydantic model"""

    def test_role_assignment_creation(self):
        """Test creating role assignment"""
        assignment = RoleAssignment(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            tenant_id="660e8400-e29b-41d4-a716-446655440001",
            role=Role.ADMIN,
        )

        assert assignment.user_id == "550e8400-e29b-41d4-a716-446655440000"
        assert assignment.tenant_id == "660e8400-e29b-41d4-a716-446655440001"
        assert assignment.role == Role.ADMIN
        assert assignment.assigned_by is None

    def test_role_assignment_with_assigned_by(self):
        """Test role assignment with assigned_by field"""
        assignment = RoleAssignment(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            tenant_id="660e8400-e29b-41d4-a716-446655440001",
            role=Role.MEMBER,
            assigned_by="770e8400-e29b-41d4-a716-446655440002",
        )

        assert assignment.assigned_by == "770e8400-e29b-41d4-a716-446655440002"

    def test_role_assignment_validation(self):
        """Test Pydantic validation"""
        # Missing required fields
        with pytest.raises(Exception):  # Pydantic ValidationError
            RoleAssignment(user_id="550e8400-e29b-41d4-a716-446655440000")
