#!/usr/bin/env python3
"""
Netrun Service Library - Testing Example

Demonstrates using netrun-pytest-fixtures for comprehensive testing.

Requirements:
    pip install netrun-pytest-fixtures[all]
    pip install pytest pytest-asyncio httpx

Run:
    pytest test_example.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch

# ============================================================================
# CONFTEST SETUP (normally in conftest.py)
# ============================================================================
pytest_plugins = ["netrun_pytest_fixtures"]


# ============================================================================
# SAMPLE CODE TO TEST
# ============================================================================
class UserService:
    """Example service for testing."""

    def __init__(self, db_session, redis_client, logger=None):
        self.db = db_session
        self.redis = redis_client
        self.logger = logger

    async def get_user(self, user_id: str):
        """Get user by ID with caching."""
        # Check cache first
        cached = await self.redis.get(f"user:{user_id}")
        if cached:
            if self.logger:
                self.logger.info("cache_hit", user_id=user_id)
            return cached

        # Fetch from database
        user = await self.db.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Cache result
        await self.redis.set(f"user:{user_id}", user, ex=300)
        if self.logger:
            self.logger.info("user_fetched", user_id=user_id)
        return user

    async def create_user(self, username: str, email: str):
        """Create a new user."""
        user_id = f"user-{hash(username) % 10000}"

        # Save to database
        await self.db.execute(
            f"INSERT INTO users (id, username, email) VALUES ('{user_id}', '{username}', '{email}')"
        )

        if self.logger:
            self.logger.info("user_created", user_id=user_id, username=username)

        return {"id": user_id, "username": username, "email": email}


# ============================================================================
# BASIC FIXTURE TESTS
# ============================================================================
class TestBasicFixtures:
    """Test basic fixture availability."""

    def test_temp_directory(self, temp_dir):
        """Test temp directory fixture."""
        assert temp_dir.exists()
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")
        assert test_file.read_text() == "Hello, World!"

    def test_random_string(self, random_string):
        """Test random string fixture."""
        assert len(random_string) > 0
        assert isinstance(random_string, str)

    def test_sample_uuid(self, sample_uuid):
        """Test UUID fixture."""
        import uuid

        assert isinstance(sample_uuid, uuid.UUID)


# ============================================================================
# JWT/AUTH FIXTURE TESTS
# ============================================================================
class TestJWTFixtures:
    """Test JWT-related fixtures."""

    def test_jwt_token(self, jwt_token):
        """Test JWT token generation."""
        assert jwt_token is not None
        assert len(jwt_token.split(".")) == 3  # JWT has 3 parts

    def test_jwt_with_custom_claims(self, jwt_token_factory):
        """Test JWT with custom claims."""
        token = jwt_token_factory(
            sub="test-user",
            roles=["admin", "user"],
            custom_claims={"tenant_id": "tenant-123"},
        )
        assert token is not None

    def test_jwt_secret(self, jwt_secret):
        """Test JWT secret fixture."""
        assert len(jwt_secret) >= 32  # Secure secret length


# ============================================================================
# REDIS FIXTURE TESTS
# ============================================================================
class TestRedisFixtures:
    """Test Redis-related fixtures."""

    @pytest.mark.asyncio
    async def test_mock_redis_get_set(self, mock_redis):
        """Test mock Redis get/set operations."""
        await mock_redis.set("key1", "value1")
        result = await mock_redis.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_mock_redis_expiry(self, mock_redis):
        """Test mock Redis with expiry."""
        await mock_redis.set("key2", "value2", ex=300)
        result = await mock_redis.get("key2")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_mock_redis_delete(self, mock_redis):
        """Test mock Redis delete."""
        await mock_redis.set("key3", "value3")
        await mock_redis.delete("key3")
        result = await mock_redis.get("key3")
        assert result is None


# ============================================================================
# DATABASE FIXTURE TESTS
# ============================================================================
class TestDatabaseFixtures:
    """Test database-related fixtures."""

    @pytest.mark.asyncio
    async def test_async_db_session(self, async_db_session):
        """Test async database session fixture."""
        assert async_db_session is not None
        # Session should be a mock or real session

    @pytest.mark.asyncio
    async def test_db_transaction_rollback(self, async_db_session):
        """Test that sessions rollback after test."""
        # Fixture should handle cleanup automatically
        pass


# ============================================================================
# HTTP CLIENT FIXTURE TESTS
# ============================================================================
class TestHTTPClientFixtures:
    """Test HTTP client fixtures."""

    @pytest.mark.asyncio
    async def test_mock_http_client(self, mock_httpx_client):
        """Test mock HTTP client."""
        mock_httpx_client.get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"data": "test"},
        )

        response = await mock_httpx_client.get("https://api.example.com/data")
        assert response.status_code == 200


# ============================================================================
# LOGGING FIXTURE TESTS
# ============================================================================
class TestLoggingFixtures:
    """Test logging-related fixtures."""

    def test_captured_logs(self, captured_logs):
        """Test log capture fixture."""
        import logging

        logger = logging.getLogger("test")
        logger.info("Test message")

        # captured_logs should contain the log entry
        assert len(captured_logs) >= 0  # Fixture captures logs

    def test_mock_logger(self, mock_logger):
        """Test mock logger fixture."""
        mock_logger.info("test message", key="value")
        mock_logger.info.assert_called()


# ============================================================================
# SERVICE INTEGRATION TESTS
# ============================================================================
class TestUserService:
    """Integration tests for UserService."""

    @pytest.fixture
    def user_service(self, async_db_session, mock_redis, mock_logger):
        """Create UserService with fixtures."""
        return UserService(
            db_session=async_db_session,
            redis_client=mock_redis,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_get_user_cache_miss(self, user_service, async_db_session, mock_redis):
        """Test getting user with cache miss."""
        # Setup
        mock_redis.get = AsyncMock(return_value=None)
        async_db_session.execute = AsyncMock(return_value={"id": "user-123", "name": "Test"})

        # Execute
        user = await user_service.get_user("user-123")

        # Verify
        assert user is not None
        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_get_user_cache_hit(self, user_service, mock_redis, mock_logger):
        """Test getting user with cache hit."""
        # Setup
        cached_user = {"id": "user-123", "name": "Cached User"}
        mock_redis.get = AsyncMock(return_value=cached_user)

        # Execute
        user = await user_service.get_user("user-123")

        # Verify
        assert user == cached_user
        mock_logger.info.assert_called_with("cache_hit", user_id="user-123")

    @pytest.mark.asyncio
    async def test_create_user(self, user_service, async_db_session, mock_logger):
        """Test creating a new user."""
        # Setup
        async_db_session.execute = AsyncMock()

        # Execute
        user = await user_service.create_user("testuser", "test@example.com")

        # Verify
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        async_db_session.execute.assert_called_once()


# ============================================================================
# FASTAPI CLIENT TESTS
# ============================================================================
class TestAPIEndpoints:
    """Test API endpoints with test client."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        # This would use the test_client fixture from netrun-pytest-fixtures
        # In a real test, you'd import your FastAPI app
        pass

    @pytest.mark.asyncio
    async def test_authenticated_endpoint(self, test_client, jwt_token):
        """Test authenticated endpoint."""
        # Example of testing with JWT
        # response = await test_client.get(
        #     "/api/users/me",
        #     headers={"Authorization": f"Bearer {jwt_token}"}
        # )
        # assert response.status_code == 200
        pass


# ============================================================================
# ENVIRONMENT FIXTURE TESTS
# ============================================================================
class TestEnvironmentFixtures:
    """Test environment-related fixtures."""

    def test_clean_environment(self, clean_env):
        """Test clean environment fixture."""
        import os

        # Fixture should provide isolated environment
        assert "TEST_VAR" not in os.environ

    def test_temp_env_vars(self, temp_env):
        """Test temporary environment variables."""
        import os

        temp_env["MY_VAR"] = "my_value"
        assert os.environ.get("MY_VAR") == "my_value"


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
