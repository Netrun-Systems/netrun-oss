"""Tests for auth module - JWT authentication validation."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketException, status

# Test if jose is available
try:
    from jose import jwt, JWTError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from netrun.websocket.auth import (
    JWTAuthService,
    TokenAuthMiddleware,
    authenticate_websocket,
)


class TestJWTAuthService:
    """Test JWTAuthService class."""

    def test_initialization_without_jose(self):
        """Test initialization fails without jose library."""
        if JWT_AVAILABLE:
            pytest.skip("jose is available, skipping this test")

        with pytest.raises(ImportError, match="JWT support not available"):
            JWTAuthService(secret_key="test-secret")

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_initialization_with_defaults(self):
        """Test JWT service initialization with default values."""
        service = JWTAuthService(secret_key="test-secret")
        assert service.secret_key == "test-secret"
        assert service.algorithm == "HS256"
        assert service.token_expiry_seconds == 7200

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_initialization_with_custom_config(self):
        """Test JWT service initialization with custom configuration."""
        service = JWTAuthService(
            secret_key="custom-secret",
            algorithm="HS512",
            token_expiry_seconds=3600
        )
        assert service.secret_key == "custom-secret"
        assert service.algorithm == "HS512"
        assert service.token_expiry_seconds == 3600

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_generate_token_basic(self):
        """Test generating basic JWT token."""
        service = JWTAuthService(secret_key="test-secret")
        token = service.generate_token(user_id="user123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_generate_token_with_additional_claims(self):
        """Test generating token with additional claims."""
        service = JWTAuthService(secret_key="test-secret")
        additional_claims = {
            "role": "admin",
            "permissions": ["read", "write"]
        }
        token = service.generate_token(
            user_id="user123",
            additional_claims=additional_claims
        )

        # Decode and verify claims
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["user_id"] == "user123"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_generate_token_with_custom_expiry(self):
        """Test generating token with custom expiry duration."""
        service = JWTAuthService(secret_key="test-secret", token_expiry_seconds=7200)
        token = service.generate_token(user_id="user123", expiry_seconds=1800)

        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])

        # Check expiry is approximately 30 minutes from now
        exp = payload["exp"]
        now = datetime.now(timezone.utc).timestamp()
        expiry_diff = exp - now

        # Allow 5 second tolerance for test execution time
        assert 1795 < expiry_diff < 1805

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_validate_token_valid(self):
        """Test validating a valid JWT token."""
        service = JWTAuthService(secret_key="test-secret")
        token = service.generate_token(user_id="user123")

        payload = service.validate_token(token)

        assert payload is not None
        assert payload["user_id"] == "user123"
        assert "exp" in payload
        assert "iat" in payload

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_validate_token_invalid_signature(self):
        """Test validating token with invalid signature."""
        service = JWTAuthService(secret_key="test-secret")
        token = service.generate_token(user_id="user123")

        # Try to validate with different secret
        service_wrong = JWTAuthService(secret_key="wrong-secret")
        payload = service_wrong.validate_token(token)

        assert payload is None

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_validate_token_malformed(self):
        """Test validating malformed token."""
        service = JWTAuthService(secret_key="test-secret")

        payload = service.validate_token("not.a.valid.jwt.token")

        assert payload is None

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_validate_token_expired(self):
        """Test validating expired token."""
        service = JWTAuthService(secret_key="test-secret")

        # Create token that expires immediately
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "user_id": "user123",
            "iat": now,
            "exp": now - timedelta(seconds=10)  # Already expired
        }
        expired_token = jwt.encode(claims, "test-secret", algorithm="HS256")

        payload = service.validate_token(expired_token)

        assert payload is None

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_validate_token_exception_handling(self):
        """Test validate_token handles unexpected exceptions."""
        service = JWTAuthService(secret_key="test-secret")

        # Test with empty string
        payload = service.validate_token("")
        assert payload is None

        # Test with None-like value
        payload = service.validate_token("null")
        assert payload is None

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_get_user_id_valid_token(self):
        """Test extracting user ID from valid token."""
        service = JWTAuthService(secret_key="test-secret")
        token = service.generate_token(user_id="user123")

        user_id = service.get_user_id(token)

        assert user_id == "user123"

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_get_user_id_invalid_token(self):
        """Test extracting user ID from invalid token."""
        service = JWTAuthService(secret_key="test-secret")

        user_id = service.get_user_id("invalid.token")

        assert user_id is None

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_get_user_id_from_sub_claim(self):
        """Test extracting user ID from sub claim when user_id not present."""
        service = JWTAuthService(secret_key="test-secret")

        # Create token with only sub claim
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user456",
            "iat": now,
            "exp": now + timedelta(hours=2)
        }
        token = jwt.encode(claims, "test-secret", algorithm="HS256")

        user_id = service.get_user_id(token)

        assert user_id == "user456"

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_is_token_expired_valid(self):
        """Test checking if valid token is not expired."""
        service = JWTAuthService(secret_key="test-secret")
        token = service.generate_token(user_id="user123")

        is_expired = service.is_token_expired(token)

        assert is_expired is False

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_is_token_expired_actually_expired(self):
        """Test checking if expired token is detected."""
        service = JWTAuthService(secret_key="test-secret")

        # Create already expired token
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "user_id": "user123",
            "iat": now - timedelta(hours=3),
            "exp": now - timedelta(hours=1)
        }
        expired_token = jwt.encode(claims, "test-secret", algorithm="HS256")

        is_expired = service.is_token_expired(expired_token)

        assert is_expired is True

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_is_token_expired_invalid_token(self):
        """Test checking expiration of invalid token."""
        service = JWTAuthService(secret_key="test-secret")

        is_expired = service.is_token_expired("invalid.token")

        assert is_expired is True

    @pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
    def test_is_token_expired_no_exp_claim(self):
        """Test checking expiration of token without exp claim."""
        service = JWTAuthService(secret_key="test-secret")

        # Create token without exp claim
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "user_id": "user123",
            "iat": now
        }
        token = jwt.encode(claims, "test-secret", algorithm="HS256")

        is_expired = service.is_token_expired(token)

        assert is_expired is True


@pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
class TestAuthenticateWebSocket:
    """Test authenticate_websocket function."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful WebSocket authentication."""
        service = JWTAuthService(secret_key="test-secret")
        token = service.generate_token(user_id="user123")
        websocket = MagicMock(spec=WebSocket)

        payload = await authenticate_websocket(websocket, token, service)

        assert payload is not None
        assert payload["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_authenticate_no_token(self):
        """Test authentication fails without token."""
        service = JWTAuthService(secret_key="test-secret")
        websocket = MagicMock(spec=WebSocket)

        with pytest.raises(WebSocketException) as exc_info:
            await authenticate_websocket(websocket, "", service)

        assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
        assert "Authentication required" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self):
        """Test authentication fails with invalid token."""
        service = JWTAuthService(secret_key="test-secret")
        websocket = MagicMock(spec=WebSocket)

        with pytest.raises(WebSocketException) as exc_info:
            await authenticate_websocket(websocket, "invalid.token", service)

        assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
        assert "Invalid authentication token" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_authenticate_expired_token(self):
        """Test authentication fails with expired token."""
        service = JWTAuthService(secret_key="test-secret")
        websocket = MagicMock(spec=WebSocket)

        # Create expired token (timestamp-based, not validated until checked)
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "user_id": "user123",
            "iat": now - timedelta(hours=3),
            "exp": (now - timedelta(hours=1)).timestamp()  # Use timestamp
        }
        expired_token = jwt.encode(claims, "test-secret", algorithm="HS256")

        with pytest.raises(WebSocketException) as exc_info:
            await authenticate_websocket(websocket, expired_token, service)

        assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
        # Token might be invalid before expiry check due to JWT validation
        assert "Invalid" in exc_info.value.reason or "expired" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_authenticate_with_sub_claim_only(self):
        """Test authentication with only sub claim (no user_id)."""
        service = JWTAuthService(secret_key="test-secret")
        websocket = MagicMock(spec=WebSocket)

        # Create token with only sub claim
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user456",
            "iat": now,
            "exp": now + timedelta(hours=2)
        }
        token = jwt.encode(claims, "test-secret", algorithm="HS256")

        payload = await authenticate_websocket(websocket, token, service)

        assert payload is not None
        assert payload["sub"] == "user456"


@pytest.mark.skipif(not JWT_AVAILABLE, reason="jose not installed")
class TestTokenAuthMiddleware:
    """Test TokenAuthMiddleware class."""

    def test_initialization(self):
        """Test middleware initialization."""
        service = JWTAuthService(secret_key="test-secret")
        middleware = TokenAuthMiddleware(auth_service=service)

        assert middleware.auth_service is service

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication through middleware."""
        service = JWTAuthService(secret_key="test-secret")
        middleware = TokenAuthMiddleware(auth_service=service)
        token = service.generate_token(user_id="user123")
        websocket = MagicMock(spec=WebSocket)

        payload = await middleware.authenticate(websocket, token)

        assert payload is not None
        assert payload["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """Test authentication failure through middleware."""
        service = JWTAuthService(secret_key="test-secret")
        middleware = TokenAuthMiddleware(auth_service=service)
        websocket = MagicMock(spec=WebSocket)

        with pytest.raises(WebSocketException):
            await middleware.authenticate(websocket, "invalid.token")
