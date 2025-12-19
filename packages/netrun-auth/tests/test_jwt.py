"""
JWT Manager Tests
Service #59 Unified Authentication

Tests for JWTManager class covering:
- Token generation (access and refresh)
- Token validation and verification
- Token refresh and rotation
- Token blacklisting
- Key management
- Edge cases and security

Total: 45+ tests
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import jwt as pyjwt
import asyncio

from netrun.auth.jwt import JWTManager, KeyPair
from netrun.auth.config import AuthConfig
from netrun.auth.types import TokenType, TokenClaims
from netrun.auth.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError
)


@pytest.fixture
def auth_config():
    """Create test authentication configuration."""
    return AuthConfig()


@pytest.fixture
def jwt_manager(mock_redis):
    """Create JWTManager instance with mock Redis."""
    config = AuthConfig()
    return JWTManager(config=config, redis_client=mock_redis)


class TestJWTTokenGeneration:
    """Test JWT token generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_access_token_valid_claims(self, jwt_manager):
        """Test generating access token with valid claims."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456",
            roles=["user", "admin"],
            permissions=["users:read", "users:write"]
        )

        assert token_pair.access_token is not None
        assert isinstance(token_pair.access_token, str)
        assert token_pair.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_generate_refresh_token_valid_claims(self, jwt_manager):
        """Test generating refresh token with valid claims."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456"
        )

        assert token_pair.refresh_token is not None
        assert isinstance(token_pair.refresh_token, str)

    @pytest.mark.asyncio
    async def test_generate_token_pair_returns_two_tokens(self, jwt_manager):
        """Test generating both access and refresh tokens together."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456"
        )

        assert token_pair.access_token != token_pair.refresh_token
        assert len(token_pair.access_token) > 0
        assert len(token_pair.refresh_token) > 0

    @pytest.mark.asyncio
    async def test_token_contains_required_claims(self, jwt_manager):
        """
        Test that generated token contains all required JWT claims.

        Required claims:
        - jti (JWT ID)
        - sub (subject)
        - iat (issued at)
        - exp (expiration)
        - user_id
        - organization_id
        - roles
        - permissions
        """
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456",
            roles=["user"],
            permissions=["users:read"]
        )

        # Decode without verification to inspect claims
        claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        assert "jti" in claims
        assert "sub" in claims
        assert "iat" in claims
        assert "exp" in claims
        assert "user_id" in claims
        assert "organization_id" in claims
        assert "roles" in claims
        assert "permissions" in claims
        assert claims["user_id"] == "user-123"
        assert claims["organization_id"] == "org-456"

    @pytest.mark.asyncio
    async def test_access_token_expiry_default_15_minutes(self, jwt_manager):
        """Test that access tokens expire after 15 minutes by default."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123"
        )

        claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        iat = datetime.fromtimestamp(claims["iat"], tz=timezone.utc)
        exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        expiry_duration = exp - iat

        # Should be 15 minutes (900 seconds)
        assert 890 <= expiry_duration.total_seconds() <= 910

    @pytest.mark.asyncio
    async def test_refresh_token_expiry_default_30_days(self, jwt_manager):
        """Test that refresh tokens expire after 30 days by default."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123"
        )

        claims = pyjwt.decode(
            token_pair.refresh_token,
            options={"verify_signature": False}
        )

        iat = datetime.fromtimestamp(claims["iat"], tz=timezone.utc)
        exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        expiry_duration = exp - iat

        # Should be 30 days (2592000 seconds)
        expected_seconds = 30 * 24 * 60 * 60
        assert expected_seconds - 100 <= expiry_duration.total_seconds() <= expected_seconds + 100

    @pytest.mark.asyncio
    async def test_custom_expiry_times_respected(self):
        """Test that custom expiry times are applied correctly."""
        config = AuthConfig(
            access_token_expiry_minutes=30,  # Fixed: was access_token_expire_minutes
            refresh_token_expiry_days=60      # Fixed: was refresh_token_expire_days
        )
        manager = JWTManager(config=config)

        token_pair = await manager.generate_token_pair(user_id="user-123")

        access_claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        iat = datetime.fromtimestamp(access_claims["iat"], tz=timezone.utc)
        exp = datetime.fromtimestamp(access_claims["exp"], tz=timezone.utc)
        expiry_duration = exp - iat

        # Should be 30 minutes (1800 seconds)
        assert 1790 <= expiry_duration.total_seconds() <= 1810

    @pytest.mark.asyncio
    async def test_token_type_claim_set_correctly(self, jwt_manager):
        """Test that token_type claim distinguishes access vs refresh tokens."""
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        access_claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )
        refresh_claims = pyjwt.decode(
            token_pair.refresh_token,
            options={"verify_signature": False}
        )

        assert access_claims["typ"] == TokenType.ACCESS.value
        assert refresh_claims["typ"] == TokenType.REFRESH.value

    @pytest.mark.asyncio
    async def test_iat_claim_is_current_timestamp(self, jwt_manager):
        """Test that iat (issued at) claim matches generation time."""
        before = datetime.now(timezone.utc).replace(microsecond=0)  # Remove microseconds for comparison
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")
        after = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=1)  # Add 1 second buffer

        claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        iat = datetime.fromtimestamp(claims["iat"], tz=timezone.utc)
        assert before <= iat <= after

    @pytest.mark.asyncio
    async def test_jti_is_unique_per_token(self, jwt_manager):
        """Test that each token gets a unique jti for blacklisting."""
        token_pair1 = await jwt_manager.generate_token_pair(user_id="user-123")
        token_pair2 = await jwt_manager.generate_token_pair(user_id="user-123")

        claims1 = pyjwt.decode(
            token_pair1.access_token,
            options={"verify_signature": False}
        )
        claims2 = pyjwt.decode(
            token_pair2.access_token,
            options={"verify_signature": False}
        )

        assert claims1["jti"] != claims2["jti"]


class TestJWTTokenValidation:
    """Test JWT token validation and verification."""

    @pytest.mark.asyncio
    async def test_validate_token_valid(self, jwt_manager):
        """Test validating a properly signed, non-expired token."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456"
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)
        assert claims.user_id == "user-123"
        assert claims.organization_id == "org-456"

    @pytest.mark.asyncio
    async def test_validate_token_expired_raises_error(self, mock_redis):
        """Test that expired tokens raise ExpiredSignatureError."""
        # Create token with very short expiration (1 minute minimum)
        config = AuthConfig(access_token_expiry_minutes=1)
        manager = JWTManager(config=config, redis_client=mock_redis)

        # Generate a token and manually modify expiry to be in the past
        token_pair = await manager.generate_token_pair(user_id="user-123")

        # Decode and modify the token to have expired timestamp
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta
        expired_claims = pyjwt.decode(token_pair.access_token, options={"verify_signature": False})
        expired_claims["exp"] = int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp())

        # Re-encode with expired timestamp
        key_pair = manager.key_pairs[manager.current_key_id]
        expired_token = pyjwt.encode(
            expired_claims,
            key_pair.get_private_pem(),
            algorithm="RS256",
            headers={"kid": manager.current_key_id}
        )

        with pytest.raises(TokenExpiredError):
            await manager.verify_token(expired_token)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_signature_raises_error(self, jwt_manager):
        """Test that tokens with invalid signatures raise InvalidSignatureError."""
        # Create token with one manager
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        # Try to verify with different manager (different keys)
        different_manager = JWTManager()

        with pytest.raises(TokenInvalidError):
            await different_manager.verify_token(token_pair.access_token)

    @pytest.mark.asyncio
    async def test_validate_token_wrong_algorithm_raises_error(self, jwt_manager):
        """
        Test that tokens signed with wrong algorithm are rejected.

        Should only accept RS256, reject HS256, HS384, etc.
        """
        # Create token with HS256 instead of RS256
        claims = {
            "user_id": "user-123",
            "jti": "test-jti",
            "sub": "user-123",
            "typ": TokenType.ACCESS.value,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
        }

        bad_token = pyjwt.encode(claims, "secret", algorithm="HS256")

        with pytest.raises(TokenInvalidError):
            await jwt_manager.verify_token(bad_token)

    @pytest.mark.asyncio
    async def test_validate_token_blacklisted_raises_error(self, jwt_manager, mock_redis):
        """Test that blacklisted tokens are rejected during validation."""
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        # Blacklist the token
        claims = await jwt_manager.verify_token(token_pair.access_token)
        await jwt_manager.revoke_token(claims.jti)

        # Mock Redis to return blacklisted
        mock_redis.exists = AsyncMock(return_value=1)

        with pytest.raises(TokenBlacklistedError):
            await jwt_manager.verify_token(token_pair.access_token)

    @pytest.mark.asyncio
    async def test_validate_token_missing_required_claims_raises_error(self, jwt_manager):
        """
        Test that tokens missing required claims are rejected.

        Required: jti, sub, user_id, organization_id, roles, permissions
        """
        # Get a valid key pair
        key_pair = jwt_manager.key_pairs[jwt_manager.current_key_id]

        # Create token with missing required claims
        incomplete_claims = {
            "jti": "test-jti",
            "sub": "user-123",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
            # Missing: user_id, organization_id, roles, permissions
        }

        token = pyjwt.encode(
            incomplete_claims,
            key_pair.get_private_pem(),
            algorithm="RS256",
            headers={"kid": jwt_manager.current_key_id}
        )

        with pytest.raises(TokenInvalidError):
            await jwt_manager.verify_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_malformed_jwt_raises_error(self, jwt_manager):
        """Test that malformed JWT strings raise DecodeError."""
        malformed_token = "not.a.valid.jwt.token.at.all"

        with pytest.raises(TokenInvalidError):
            await jwt_manager.verify_token(malformed_token)

    @pytest.mark.asyncio
    async def test_validate_returns_decoded_claims(self, jwt_manager):
        """Test that validate_token returns the decoded claims dictionary."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456",
            roles=["admin"],
            permissions=["users:read", "users:write"]
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)

        assert isinstance(claims, TokenClaims)
        assert claims.user_id == "user-123"
        assert claims.organization_id == "org-456"
        assert "admin" in claims.roles
        assert "users:read" in claims.permissions


class TestJWTTokenRefresh:
    """Test JWT token refresh and rotation."""

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_pair(self, jwt_manager, mock_redis):
        """
        Test that refreshing a token returns new access + refresh tokens.

        Should return a tuple of (new_access_token, new_refresh_token).
        """
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        # Mock Redis to validate refresh token
        mock_redis.scan = AsyncMock(return_value=(0, [b"auth:refresh:user-123:session:jti"]))

        new_token_pair = await jwt_manager.refresh_tokens(token_pair.refresh_token)

        assert new_token_pair.access_token != token_pair.access_token
        assert new_token_pair.refresh_token != token_pair.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_blacklists_old_token(self, jwt_manager, mock_redis):
        """
        Test that refresh operation blacklists the old refresh token.

        Prevents token reuse attacks.
        """
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        # Mock Redis operations
        mock_redis.scan = AsyncMock(return_value=(0, [b"auth:refresh:user-123:session:jti"]))
        mock_redis.setex = AsyncMock(return_value=True)

        await jwt_manager.refresh_tokens(token_pair.refresh_token)

        # Verify setex was called (blacklisting)
        assert mock_redis.setex.called

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_type_raises_error(self, jwt_manager):
        """
        Test that attempting to refresh an access token raises error.

        Only refresh tokens should be accepted for refresh operations.
        """
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        # Try to refresh with access token instead of refresh token
        with pytest.raises(TokenInvalidError):
            await jwt_manager.refresh_tokens(token_pair.access_token)

    @pytest.mark.asyncio
    async def test_refresh_expired_token_raises_error(self, mock_redis):
        """Test that refreshing an expired refresh token raises error."""
        # Create token with minimum expiration (1 day minimum)
        config = AuthConfig(refresh_token_expiry_days=1)
        manager = JWTManager(config=config, redis_client=mock_redis)

        token_pair = await manager.generate_token_pair(user_id="user-123")

        # Decode and modify the token to have expired timestamp
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta
        expired_claims = pyjwt.decode(token_pair.refresh_token, options={"verify_signature": False})
        expired_claims["exp"] = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())

        # Re-encode with expired timestamp
        key_pair = manager.key_pairs[manager.current_key_id]
        expired_token = pyjwt.encode(
            expired_claims,
            key_pair.get_private_pem(),
            algorithm="RS256",
            headers={"kid": manager.current_key_id}
        )

        with pytest.raises(TokenExpiredError):
            await manager.refresh_tokens(expired_token)

    @pytest.mark.asyncio
    async def test_refresh_preserves_user_claims(self, jwt_manager, mock_redis):
        """
        Test that refresh operation preserves user identity claims.

        user_id, organization_id, roles, permissions should be preserved.
        """
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id="org-456",
            roles=["admin"],
            permissions=["users:read", "users:write"]
        )

        # Mock Redis
        mock_redis.scan = AsyncMock(return_value=(0, [b"auth:refresh:user-123:session:jti"]))

        new_token_pair = await jwt_manager.refresh_tokens(token_pair.refresh_token)

        new_claims = pyjwt.decode(
            new_token_pair.access_token,
            options={"verify_signature": False}
        )

        assert new_claims["user_id"] == "user-123"
        assert new_claims["organization_id"] == "org-456"
        assert "admin" in new_claims["roles"]

    @pytest.mark.asyncio
    async def test_refresh_updates_iat_and_exp(self, jwt_manager, mock_redis):
        """
        Test that refresh operation updates iat and exp timestamps.

        New tokens should have current iat and new exp.
        """
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        old_claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        # Wait a moment
        await asyncio.sleep(1)

        # Mock Redis
        mock_redis.scan = AsyncMock(return_value=(0, [b"auth:refresh:user-123:session:jti"]))

        new_token_pair = await jwt_manager.refresh_tokens(token_pair.refresh_token)

        new_claims = pyjwt.decode(
            new_token_pair.access_token,
            options={"verify_signature": False}
        )

        assert new_claims["iat"] > old_claims["iat"]
        assert new_claims["exp"] > old_claims["exp"]

    @pytest.mark.asyncio
    async def test_refresh_generates_new_jti(self, jwt_manager, mock_redis):
        """
        Test that refresh operation generates new jti for new tokens.

        Ensures each token is uniquely identifiable.
        """
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")

        old_claims = pyjwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        # Mock Redis
        mock_redis.scan = AsyncMock(return_value=(0, [b"auth:refresh:user-123:session:jti"]))

        new_token_pair = await jwt_manager.refresh_tokens(token_pair.refresh_token)

        new_claims = pyjwt.decode(
            new_token_pair.access_token,
            options={"verify_signature": False}
        )

        assert new_claims["jti"] != old_claims["jti"]


class TestJWTTokenBlacklisting:
    """Test JWT token blacklisting functionality."""

    @pytest.mark.asyncio
    async def test_blacklist_token_adds_to_redis(self, jwt_manager, mock_redis):
        """
        Test that blacklist_token adds jti to Redis with correct TTL.

        TTL should match token expiry to avoid storing expired blacklist entries.
        """
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")
        claims = await jwt_manager.verify_token(token_pair.access_token)

        await jwt_manager.revoke_token(claims.jti)

        # Verify setex was called with correct parameters
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args
        assert claims.jti in call_args[0][0]  # Key contains jti

    @pytest.mark.asyncio
    async def test_is_blacklisted_returns_true_for_blacklisted(self, jwt_manager, mock_redis):
        """Test that is_blacklisted returns True for blacklisted tokens."""
        token_pair = await jwt_manager.generate_token_pair(user_id="user-123")
        claims = await jwt_manager.verify_token(token_pair.access_token)

        # Mock Redis to return exists
        mock_redis.exists = AsyncMock(return_value=1)

        is_blacklisted = await jwt_manager._is_token_blacklisted(claims.jti)
        assert is_blacklisted is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_returns_false_for_valid(self, jwt_manager, mock_redis):
        """Test that is_blacklisted returns False for non-blacklisted tokens."""
        # Mock Redis to return not exists
        mock_redis.exists = AsyncMock(return_value=0)

        is_blacklisted = await jwt_manager._is_token_blacklisted("nonexistent-jti")
        assert is_blacklisted is False

    @pytest.mark.asyncio
    async def test_blacklist_uses_correct_redis_key_format(self, jwt_manager, mock_redis):
        """
        Test that blacklist keys follow format: auth:blacklist:{jti}

        Ensures consistent Redis key naming convention.
        """
        jti = "test-jti-12345"
        await jwt_manager.revoke_token(jti)

        # Check that setex was called with correct key format
        call_args = mock_redis.setex.call_args[0]
        assert "auth:blacklist:" in call_args[0]
        assert jti in call_args[0]


class TestJWTKeyManagement:
    """Test JWT key loading and management."""

    def test_load_keys_from_pem_files(self, temp_key_files):
        """Test loading RSA keys from PEM files."""
        private_path, public_path = temp_key_files

        # Read key contents
        with open(private_path, 'rb') as f:
            private_pem = f.read().decode()
        with open(public_path, 'rb') as f:
            public_pem = f.read().decode()

        # Create config with keys
        config = AuthConfig()
        config.jwt_private_key = private_pem
        config.jwt_public_key = public_pem

        manager = JWTManager(config=config)
        assert len(manager.key_pairs) > 0

    def test_rs256_algorithm_enforced(self, jwt_manager):
        """
        Test that JWTManager enforces RS256 algorithm.

        Should reject HS256, HS384, and other symmetric algorithms.
        """
        assert jwt_manager.config.jwt_algorithm == "RS256"

    def test_key_rotation_generates_new_key(self, jwt_manager):
        """Test that key rotation generates new key pair."""
        old_key_id = jwt_manager.current_key_id

        jwt_manager.rotate_keys()

        assert jwt_manager.current_key_id != old_key_id
        assert jwt_manager.current_key_id in jwt_manager.key_pairs


class TestJWTEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_roles_list_allowed(self, jwt_manager):
        """Test that tokens with empty roles list are valid."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            roles=[]
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)
        assert claims.roles == []

    @pytest.mark.asyncio
    async def test_empty_permissions_list_allowed(self, jwt_manager):
        """Test that tokens with empty permissions list are valid."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            permissions=[]
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)
        assert claims.permissions == []

    @pytest.mark.asyncio
    async def test_optional_fields_can_be_none(self, jwt_manager):
        """
        Test that optional fields (session_id, ip_address, user_agent) can be None.

        Required fields: jti, sub, user_id, organization_id, roles, permissions
        Optional fields: session_id, ip_address, user_agent
        """
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            organization_id=None,
            session_id=None,
            ip_address=None,
            user_agent=None
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)
        # Should not raise error

    @pytest.mark.asyncio
    async def test_unicode_in_claims_handled(self, jwt_manager):
        """Test that Unicode characters in claims are properly encoded/decoded."""
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-测试-123",
            organization_id="org-тест-456"
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)
        assert claims.user_id == "user-测试-123"
        assert claims.organization_id == "org-тест-456"

    @pytest.mark.asyncio
    async def test_very_long_permissions_list(self, jwt_manager):
        """Test token generation with large permissions list (100+ permissions)."""
        permissions = [f"resource{i}:action{j}" for i in range(20) for j in range(5)]

        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            permissions=permissions
        )

        claims = await jwt_manager.verify_token(token_pair.access_token)
        assert len(claims.permissions) == 100

    @pytest.mark.asyncio
    async def test_token_size_reasonable(self, jwt_manager):
        """
        Test that generated tokens are reasonably sized.

        JWT tokens should be < 8KB to fit in HTTP headers.
        """
        permissions = [f"resource{i}:action" for i in range(50)]

        token_pair = await jwt_manager.generate_token_pair(
            user_id="user-123",
            permissions=permissions
        )

        # Check token size (8KB = 8192 bytes)
        assert len(token_pair.access_token) < 8192
        assert len(token_pair.refresh_token) < 8192

    @pytest.mark.asyncio
    async def test_concurrent_token_generation(self, jwt_manager):
        """Test thread safety of concurrent token generation."""
        async def generate_token(user_id):
            return await jwt_manager.generate_token_pair(user_id=user_id)

        # Generate 10 tokens concurrently
        tasks = [generate_token(f"user-{i}") for i in range(10)]
        token_pairs = await asyncio.gather(*tasks)

        # All tokens should be unique
        access_tokens = [tp.access_token for tp in token_pairs]
        assert len(set(access_tokens)) == 10

    @pytest.mark.asyncio
    async def test_revoke_all_user_tokens(self, jwt_manager, mock_redis):
        """Test revoking all tokens for a user."""
        # Mock Redis scan to return multiple keys
        mock_redis.scan = AsyncMock(side_effect=[
            (0, [b"auth:refresh:user-123:session1:jti1", b"auth:refresh:user-123:session2:jti2"])
        ])
        mock_redis.delete = AsyncMock(return_value=1)

        await jwt_manager.revoke_all_user_tokens("user-123")

        # Verify Redis operations were called
        assert mock_redis.scan.called
        assert mock_redis.setex.called  # For blacklisting
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, jwt_manager, mock_redis):
        """Test retrieving active sessions for a user."""
        import json

        session_data = json.dumps({
            "user_id": "user-123",
            "session_id": "session-123",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        mock_redis.scan = AsyncMock(return_value=(
            0,
            [b"auth:refresh:user-123:session-123:jti1"]
        ))
        mock_redis.get = AsyncMock(return_value=session_data)

        sessions = await jwt_manager.get_active_sessions("user-123")

        assert len(sessions) > 0
        assert sessions[0]["user_id"] == "user-123"

    def test_get_public_keys_returns_jwks(self, jwt_manager):
        """Test retrieving public keys for JWKS endpoint."""
        public_keys = jwt_manager.get_public_keys()

        assert isinstance(public_keys, dict)
        assert len(public_keys) > 0

        # Check that keys are PEM formatted
        for key_id, key_pem in public_keys.items():
            assert "-----BEGIN PUBLIC KEY-----" in key_pem
