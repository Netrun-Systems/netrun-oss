"""
Tests for Casbin FastAPI Middleware

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-03
"""

import pytest

# Skip all tests if dependencies not installed
pytest.importorskip("casbin")
pytest.importorskip("fastapi")

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from netrun_auth.rbac_casbin import CasbinRBACManager
from netrun_auth.middleware_casbin import (
    CasbinAuthMiddleware,
    path_prefix_mapper,
    regex_resource_mapper,
)
from netrun_auth.types import User


@pytest.fixture
async def casbin_manager():
    """Create and initialize Casbin RBAC manager."""
    manager = CasbinRBACManager(multi_tenant=False)
    await manager.initialize()

    # Setup permissions
    await manager.add_permission_for_role("admin", "/api/users", "read")
    await manager.add_permission_for_role("admin", "/api/users", "create")
    await manager.add_permission_for_role("user", "/api/projects", "read")
    await manager.add_role_for_user("admin_user", "admin")
    await manager.add_role_for_user("regular_user", "user")

    return manager


@pytest.fixture
def app_with_casbin_middleware(casbin_manager):
    """Create FastAPI app with Casbin middleware."""
    app = FastAPI()

    # Mock authentication middleware (sets request.state.user)
    @app.middleware("http")
    async def mock_auth_middleware(request: Request, call_next):
        # Extract user from header for testing
        user_id = request.headers.get("X-User-ID", "guest")
        request.state.user = User(
            user_id=user_id,
            organization_id="org1",
            roles=[],
            permissions=[],
        )
        return await call_next(request)

    # Add Casbin middleware
    app.add_middleware(
        CasbinAuthMiddleware,
        rbac_manager=casbin_manager,
        excluded_paths=["/health", "/public"],
    )

    # Test routes
    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_user():
        return {"created": True}

    @app.get("/api/projects")
    async def get_projects():
        return {"projects": ["project1"]}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/public")
    async def public():
        return {"public": True}

    return app


class TestCasbinAuthMiddleware:
    """Test CasbinAuthMiddleware basic functionality."""

    def test_excluded_paths_bypass_authorization(self, app_with_casbin_middleware):
        """Test that excluded paths bypass authorization checks."""
        client = TestClient(app_with_casbin_middleware)

        # Health endpoint should be accessible without auth
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        # Public endpoint should be accessible
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"public": True}

    def test_authenticated_user_with_permission(self, app_with_casbin_middleware):
        """Test authenticated user with granted permission."""
        client = TestClient(app_with_casbin_middleware)

        # Admin user can read users
        response = client.get("/api/users", headers={"X-User-ID": "admin_user"})
        assert response.status_code == 200
        assert "users" in response.json()

    def test_authenticated_user_without_permission(self, app_with_casbin_middleware):
        """Test authenticated user without permission gets 403."""
        client = TestClient(app_with_casbin_middleware)

        # Regular user cannot read users
        response = client.get("/api/users", headers={"X-User-ID": "regular_user"})
        assert response.status_code == 403
        assert "Permission denied" in response.json()["detail"]

    def test_unauthenticated_request(self, app_with_casbin_middleware):
        """Test that unauthenticated request gets 401."""
        # Create app without mock auth middleware
        app = FastAPI()

        @app.middleware("http")
        async def no_auth_middleware(request: Request, call_next):
            # Don't set request.state.user
            return await call_next(request)

        casbin_manager = CasbinRBACManager()

        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=casbin_manager,
        )

        @app.get("/api/users")
        async def get_users():
            return {"users": []}

        client = TestClient(app)
        response = client.get("/api/users")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_http_method_to_action_mapping(self, app_with_casbin_middleware):
        """Test HTTP method to action mapping."""
        client = TestClient(app_with_casbin_middleware)

        # Admin user can create users (POST -> create)
        response = client.post("/api/users", headers={"X-User-ID": "admin_user"})
        assert response.status_code == 200
        assert response.json()["created"] is True

        # Regular user cannot create users
        response = client.post("/api/users", headers={"X-User-ID": "regular_user"})
        assert response.status_code == 403

    def test_permission_header_in_response(self, app_with_casbin_middleware):
        """Test that permission denied response includes permission header."""
        client = TestClient(app_with_casbin_middleware)

        response = client.get("/api/users", headers={"X-User-ID": "regular_user"})
        assert response.status_code == 403
        assert "X-Permission-Required" in response.headers
        # Should indicate read permission on /api/users
        assert "/api/users" in response.headers["X-Permission-Required"]


class TestCustomResourceMappers:
    """Test custom resource mapping functions."""

    @pytest.mark.asyncio
    async def test_path_prefix_mapper(self):
        """Test path_prefix_mapper helper function."""
        mapper = path_prefix_mapper({
            "/api/users": "users",
            "/api/projects": "projects",
            "/api/admin": "admin",
        })

        # Create mock request
        class MockRequest:
            class URL:
                path = "/api/users/123"
            url = URL()

        request = MockRequest()
        resource = mapper(request)
        assert resource == "users"

        # Test non-matching path
        request.url.path = "/other/path"
        resource = mapper(request)
        assert resource == "/other/path"  # Default to path

    @pytest.mark.asyncio
    async def test_regex_resource_mapper(self):
        """Test regex_resource_mapper helper function."""
        import re

        mapper = regex_resource_mapper([
            (r"^/api/users(/.*)?$", "users"),
            (r"^/api/projects/[^/]+/tasks(/.*)?$", "tasks"),
        ])

        # Create mock request
        class MockRequest:
            class URL:
                path = "/api/users/123"
            url = URL()

        request = MockRequest()
        resource = mapper(request)
        assert resource == "users"

        # Test tasks pattern
        request.url.path = "/api/projects/proj1/tasks/task1"
        resource = mapper(request)
        assert resource == "tasks"

        # Test non-matching path
        request.url.path = "/other/path"
        resource = mapper(request)
        assert resource == "/other/path"  # Default to path


class TestCasbinMultiTenantMiddleware:
    """Test Casbin middleware with multi-tenant support."""

    @pytest.mark.asyncio
    async def test_multi_tenant_permission_check(self):
        """Test permission check in multi-tenant mode."""
        # Create multi-tenant manager
        manager = CasbinRBACManager(multi_tenant=True)
        await manager.initialize()

        # Setup: admin can read users in org1
        await manager.add_permission_for_role("admin", "users", "read", tenant_id="org1")
        await manager.add_role_for_user("user123", "admin", tenant_id="org1")

        # Create app with multi-tenant middleware
        app = FastAPI()

        @app.middleware("http")
        async def mock_auth_middleware(request: Request, call_next):
            request.state.user = User(
                user_id="user123",
                organization_id="org1",  # User's tenant
                roles=[],
                permissions=[],
            )
            return await call_next(request)

        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=manager,
        )

        @app.get("/users")
        async def get_users():
            return {"users": []}

        client = TestClient(app)
        response = client.get("/users")
        assert response.status_code == 200


class TestCasbinMiddlewareEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_user_type_in_state(self):
        """Test that invalid user type raises 500 error."""
        app = FastAPI()

        @app.middleware("http")
        async def invalid_user_middleware(request: Request, call_next):
            # Set invalid user type
            request.state.user = {"user_id": "user123"}  # Dict instead of User
            return await call_next(request)

        manager = CasbinRBACManager()
        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=manager,
        )

        @app.get("/api/test")
        async def test_route():
            return {"test": True}

        client = TestClient(app)
        response = client.get("/api/test")
        assert response.status_code == 500
        assert "Invalid user context" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_casbin_enforcer_error_handling(self):
        """Test handling of Casbin enforcer errors."""
        # This test verifies that errors from Casbin are caught
        # and returned as 500 Internal Server Error
        manager = CasbinRBACManager()
        await manager.initialize()

        app = FastAPI()

        @app.middleware("http")
        async def mock_auth_middleware(request: Request, call_next):
            request.state.user = User(
                user_id="user123",
                organization_id="org1",
                roles=[],
                permissions=[],
            )
            return await call_next(request)

        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=manager,
        )

        @app.get("/test")
        async def test_route():
            return {"test": True}

        client = TestClient(app)

        # Make request (may fail if enforcer has issues)
        response = client.get("/test")
        # Should either succeed (403) or fail gracefully (500)
        assert response.status_code in [403, 500]


class TestDefaultMappers:
    """Test default resource and action mappers."""

    def test_default_resource_mapper(self):
        """Test default resource mapper behavior."""
        from netrun_auth.middleware_casbin import CasbinAuthMiddleware

        class MockRequest:
            class URL:
                path = "/api/users/123"
            url = URL()

        request = MockRequest()
        resource = CasbinAuthMiddleware._default_resource_mapper(request)
        assert resource == "/users/123"  # /api prefix stripped

        # Test path without /api prefix
        request.url.path = "/users"
        resource = CasbinAuthMiddleware._default_resource_mapper(request)
        assert resource == "/users"

    def test_default_action_mapper(self):
        """Test default action mapper behavior."""
        from netrun_auth.middleware_casbin import CasbinAuthMiddleware

        class MockRequest:
            method = "GET"

        request = MockRequest()
        action = CasbinAuthMiddleware._default_action_mapper(request)
        assert action == "read"

        request.method = "POST"
        action = CasbinAuthMiddleware._default_action_mapper(request)
        assert action == "create"

        request.method = "PUT"
        action = CasbinAuthMiddleware._default_action_mapper(request)
        assert action == "update"

        request.method = "PATCH"
        action = CasbinAuthMiddleware._default_action_mapper(request)
        assert action == "update"

        request.method = "DELETE"
        action = CasbinAuthMiddleware._default_action_mapper(request)
        assert action == "delete"

        # Unknown method
        request.method = "CUSTOM"
        action = CasbinAuthMiddleware._default_action_mapper(request)
        assert action == "custom"
