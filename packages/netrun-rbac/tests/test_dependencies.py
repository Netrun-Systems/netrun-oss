"""
Tests for FastAPI RBAC Dependencies

Tests role enforcement and resource ownership validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from netrun.rbac.dependencies import (
    require_role,
    require_roles,
    require_owner,
    require_admin,
    require_member,
    check_resource_ownership,
)
from netrun.rbac.exceptions import InsufficientPermissionsError


class TestRequireRole:
    """Test require_role dependency factory"""

    @pytest.mark.asyncio
    async def test_require_role_sufficient_permissions(self):
        """Test successful authorization with sufficient role"""
        # Mock user with admin role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["admin"],
        }

        # Create dependency
        dependency = require_role("member")

        # Mock get_current_user
        async def mock_get_current_user():
            return mock_user

        # Execute dependency
        result = await dependency(user=mock_user)

        # Should return user context
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_role_insufficient_permissions(self):
        """Test authorization failure with insufficient role"""
        # Mock user with viewer role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["viewer"],
        }

        # Create dependency requiring admin
        dependency = require_role("admin")

        # Execute dependency
        with pytest.raises(InsufficientPermissionsError) as exc_info:
            await dependency(user=mock_user)

        # Verify error message
        assert "admin" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_require_role_owner_can_access_admin(self):
        """Test owner can access admin-required resources"""
        # Mock user with owner role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["owner"],
        }

        # Create dependency requiring admin
        dependency = require_role("admin")

        # Execute dependency
        result = await dependency(user=mock_user)

        # Should succeed (owner > admin)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_role_single_role_string(self):
        """Test handling of single role as string (not list)"""
        # Mock user with role as string
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": "admin",  # String, not list
        }

        # Create dependency
        dependency = require_role("member")

        # Execute dependency
        result = await dependency(user=mock_user)

        # Should convert to list and succeed
        assert result == mock_user


class TestRequireRoles:
    """Test require_roles dependency factory"""

    @pytest.mark.asyncio
    async def test_require_roles_has_allowed_role(self):
        """Test successful authorization with allowed role"""
        # Mock user with member role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["member"],
        }

        # Create dependency allowing member or admin
        dependency = require_roles(["member", "admin"])

        # Execute dependency
        result = await dependency(user=mock_user)

        # Should succeed
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_roles_missing_allowed_role(self):
        """Test authorization failure without allowed role"""
        # Mock user with viewer role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["viewer"],
        }

        # Create dependency allowing only member or admin
        dependency = require_roles(["member", "admin"])

        # Execute dependency
        with pytest.raises(HTTPException) as exc_info:
            await dependency(user=mock_user)

        # Verify error
        assert exc_info.value.status_code == 403


class TestConvenienceDependencies:
    """Test convenience dependency wrappers"""

    @pytest.mark.asyncio
    async def test_require_owner(self):
        """Test require_owner convenience function"""
        # Mock user with owner role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["owner"],
        }

        # Create dependency
        dependency = require_owner()

        # Execute
        result = await dependency(user=mock_user)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_admin(self):
        """Test require_admin convenience function"""
        # Mock user with admin role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["admin"],
        }

        # Create dependency
        dependency = require_admin()

        # Execute
        result = await dependency(user=mock_user)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_member(self):
        """Test require_member convenience function"""
        # Mock user with member role
        mock_user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "roles": ["member"],
        }

        # Create dependency
        dependency = require_member()

        # Execute
        result = await dependency(user=mock_user)
        assert result == mock_user


class TestCheckResourceOwnership:
    """Test resource ownership validation"""

    def test_check_resource_ownership_owner_role(self):
        """Test owner can access all resources"""
        user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "roles": ["owner"],
        }

        # Different resource owner
        resource_user_id = "660e8400-e29b-41d4-a716-446655440001"

        # Owner should have access
        assert check_resource_ownership(user, resource_user_id) is True

    def test_check_resource_ownership_admin_role(self):
        """Test admin can access all resources"""
        user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "roles": ["admin"],
        }

        # Different resource owner
        resource_user_id = "660e8400-e29b-41d4-a716-446655440001"

        # Admin should have access
        assert check_resource_ownership(user, resource_user_id) is True

    def test_check_resource_ownership_self_access(self):
        """Test user can access their own resources"""
        user_id = "550e8400-e29b-41d4-a716-446655440000"

        user = {"user_id": user_id, "roles": ["member"]}

        # Same user
        assert check_resource_ownership(user, user_id) is True

    def test_check_resource_ownership_denied(self):
        """Test user cannot access other user's resources"""
        user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "roles": ["member"],
        }

        # Different resource owner
        resource_user_id = "660e8400-e29b-41d4-a716-446655440001"

        # Member should NOT have access
        assert check_resource_ownership(user, resource_user_id) is False

    def test_check_resource_ownership_role_as_string(self):
        """Test role handling when role is string (not list)"""
        user = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "roles": "owner",  # String, not list
        }

        resource_user_id = "660e8400-e29b-41d4-a716-446655440001"

        # Should convert to list and work
        assert check_resource_ownership(user, resource_user_id) is True
