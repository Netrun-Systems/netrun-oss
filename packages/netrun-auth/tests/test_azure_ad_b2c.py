"""
Tests for Azure AD B2C integration.

These tests cover:
- B2C configuration
- Token claims parsing
- Authorization URL generation
- Token validation (mocked)
- Claims mapping
- FastAPI integration helpers

Author: Netrun Systems
Version: 1.0.0
Date: 2025-12-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import time

from netrun.auth.integrations.azure_ad_b2c import (
    AzureADB2CConfig,
    AzureADB2CClient,
    B2CUserFlow,
    B2CUserFlowConfig,
    B2CTokenClaims,
    initialize_b2c,
    get_b2c_client,
    get_current_user_b2c,
    extract_bearer_token,
    is_b2c_configured,
)
from netrun.auth.exceptions import (
    TokenInvalidError,
    TokenExpiredError,
    AuthenticationError,
)


# Test fixtures
@pytest.fixture
def b2c_config() -> AzureADB2CConfig:
    """Create a test B2C configuration."""
    return AzureADB2CConfig(
        tenant_name="testtenant",
        client_id="test-client-id-12345",
        tenant_id="test-tenant-id-67890",
        redirect_uri="http://localhost:3000/auth/callback",
        scopes=["openid", "profile", "email"],
        user_flows=B2CUserFlowConfig(
            signup_signin="B2C_1_test_susi",
            password_reset="B2C_1_test_reset",
            profile_edit="B2C_1_test_edit",
        ),
    )


@pytest.fixture
def b2c_client(b2c_config: AzureADB2CConfig) -> AzureADB2CClient:
    """Create a test B2C client."""
    return AzureADB2CClient(b2c_config)


@pytest.fixture
def sample_claims() -> dict:
    """Create sample B2C token claims."""
    now = int(time.time())
    return {
        "oid": "user-object-id-12345",
        "sub": "user-subject-id-67890",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "emails": ["testuser@example.com", "testuser2@example.com"],
        "tfp": "B2C_1_test_susi",
        "idp": "google.com",
        "idp_access_token": "google-access-token-abc123",
        "aud": "test-client-id-12345",
        "iss": "https://testtenant.b2clogin.com/test-tenant-id-67890/v2.0/",
        "iat": now - 300,
        "exp": now + 3600,
        "nbf": now - 300,
        "nonce": "test-nonce-12345",
        "auth_time": now - 300,
        "extension_Role": "admin",
        "extension_Department": "Engineering",
        "extension_OrganizationId": "org-12345",
    }


class TestAzureADB2CConfig:
    """Tests for B2C configuration."""

    def test_config_defaults(self):
        """Test configuration with minimal required fields."""
        config = AzureADB2CConfig(
            tenant_name="mytenant",
            client_id="my-client-id",
        )

        assert config.tenant_name == "mytenant"
        assert config.client_id == "my-client-id"
        assert config.tenant_id is None
        assert config.client_secret is None
        assert config.redirect_uri == "http://localhost:3000"
        assert config.scopes == ["openid", "profile", "email"]

    def test_get_authority(self, b2c_config: AzureADB2CConfig):
        """Test authority URL generation."""
        authority = b2c_config.get_authority(B2CUserFlow.SIGNUP_SIGNIN)
        assert authority == "https://testtenant.b2clogin.com/testtenant.onmicrosoft.com/B2C_1_test_susi"

        authority_reset = b2c_config.get_authority(B2CUserFlow.PASSWORD_RESET)
        assert authority_reset == "https://testtenant.b2clogin.com/testtenant.onmicrosoft.com/B2C_1_test_reset"

    def test_get_jwks_uri(self, b2c_config: AzureADB2CConfig):
        """Test JWKS URI generation."""
        jwks_uri = b2c_config.get_jwks_uri(B2CUserFlow.SIGNUP_SIGNIN)
        assert "testtenant.b2clogin.com" in jwks_uri
        assert "B2C_1_test_susi" in jwks_uri
        assert "discovery/v2.0/keys" in jwks_uri

    def test_get_issuer_with_tenant_id(self, b2c_config: AzureADB2CConfig):
        """Test issuer URL with tenant ID."""
        issuer = b2c_config.get_issuer()
        assert issuer == "https://testtenant.b2clogin.com/test-tenant-id-67890/v2.0/"

    def test_get_issuer_without_tenant_id(self):
        """Test issuer URL without tenant ID."""
        config = AzureADB2CConfig(
            tenant_name="mytenant",
            client_id="my-client-id",
        )
        issuer = config.get_issuer()
        assert issuer == "https://mytenant.b2clogin.com/mytenant.onmicrosoft.com/v2.0/"


class TestB2CUserFlowConfig:
    """Tests for B2C user flow configuration."""

    def test_default_policies(self):
        """Test default policy names."""
        config = B2CUserFlowConfig()
        assert config.signup_signin == "B2C_1_signup_signin"
        assert config.password_reset == "B2C_1_password_reset"
        assert config.profile_edit == "B2C_1_profile_edit"

    def test_get_policy(self):
        """Test get_policy method."""
        config = B2CUserFlowConfig(
            signup_signin="B2C_1_custom_susi",
            password_reset="B2C_1_custom_reset",
            profile_edit="B2C_1_custom_edit",
        )
        assert config.get_policy(B2CUserFlow.SIGNUP_SIGNIN) == "B2C_1_custom_susi"
        assert config.get_policy(B2CUserFlow.PASSWORD_RESET) == "B2C_1_custom_reset"
        assert config.get_policy(B2CUserFlow.PROFILE_EDIT) == "B2C_1_custom_edit"


class TestB2CTokenClaims:
    """Tests for B2C token claims dataclass."""

    def test_from_dict(self, sample_claims: dict):
        """Test creating claims from dictionary."""
        claims = B2CTokenClaims.from_dict(sample_claims)

        assert claims.oid == "user-object-id-12345"
        assert claims.sub == "user-subject-id-67890"
        assert claims.name == "Test User"
        assert claims.given_name == "Test"
        assert claims.family_name == "User"
        assert claims.emails == ["testuser@example.com", "testuser2@example.com"]
        assert claims.tfp == "B2C_1_test_susi"
        assert claims.idp == "google.com"
        assert claims.extension_Role == "admin"

    def test_user_id_property(self, sample_claims: dict):
        """Test user_id property (oid preferred)."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        assert claims.user_id == "user-object-id-12345"

        # Test fallback to sub
        claims_no_oid = B2CTokenClaims.from_dict({"sub": "sub-only"})
        assert claims_no_oid.user_id == "sub-only"

    def test_primary_email_property(self, sample_claims: dict):
        """Test primary_email property (emails[0] preferred)."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        assert claims.primary_email == "testuser@example.com"

        # Test fallback to email claim
        claims_email = B2CTokenClaims.from_dict({"email": "single@example.com"})
        assert claims_email.primary_email == "single@example.com"

    def test_display_name_property(self, sample_claims: dict):
        """Test display_name property with fallbacks."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        assert claims.display_name == "Test User"

        claims_given = B2CTokenClaims.from_dict({"given_name": "First"})
        assert claims_given.display_name == "First"

        claims_empty = B2CTokenClaims.from_dict({})
        assert claims_empty.display_name == "User"

    def test_identity_provider_property(self, sample_claims: dict):
        """Test identity_provider property."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        assert claims.identity_provider == "google.com"

        claims_local = B2CTokenClaims.from_dict({})
        assert claims_local.identity_provider == "local"

    def test_is_social_login_property(self, sample_claims: dict):
        """Test is_social_login property."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        assert claims.is_social_login is True

        claims_local = B2CTokenClaims.from_dict({})
        assert claims_local.is_social_login is False

    def test_get_extension(self, sample_claims: dict):
        """Test get_extension method."""
        claims = B2CTokenClaims.from_dict(sample_claims)

        # With prefix
        assert claims.get_extension("extension_Role") == "admin"

        # Without prefix
        assert claims.get_extension("Role") == "admin"

        # Non-existent
        assert claims.get_extension("NonExistent") is None


class TestAzureADB2CClient:
    """Tests for B2C client."""

    def test_get_authorization_url(self, b2c_client: AzureADB2CClient):
        """Test authorization URL generation."""
        url, state, nonce = b2c_client.get_authorization_url()

        assert "testtenant.b2clogin.com" in url
        assert "B2C_1_test_susi" in url
        assert "client_id=test-client-id-12345" in url
        assert "response_type=code" in url
        assert "code_challenge=" in url  # PKCE
        assert "code_challenge_method=S256" in url
        assert state is not None
        assert nonce is not None
        assert len(state) > 20  # Secure random state

    def test_get_authorization_url_with_custom_params(self, b2c_client: AzureADB2CClient):
        """Test authorization URL with custom parameters."""
        url, state, nonce = b2c_client.get_authorization_url(
            flow=B2CUserFlow.PROFILE_EDIT,
            prompt="login",
            ui_locales="es-ES",
        )

        assert "B2C_1_test_edit" in url
        assert "prompt=login" in url
        assert "ui_locales=es-ES" in url

    def test_pkce_verifier_storage(self, b2c_client: AzureADB2CClient):
        """Test PKCE verifier is stored for state."""
        url, state, nonce = b2c_client.get_authorization_url()

        # Verifier should be stored
        assert state in b2c_client._pkce_verifiers
        verifier = b2c_client._pkce_verifiers[state]
        assert len(verifier) > 40  # URL-safe base64 encoded

    def test_get_password_reset_url(self, b2c_client: AzureADB2CClient):
        """Test password reset URL generation."""
        url, state, nonce = b2c_client.get_password_reset_url()
        assert "B2C_1_test_reset" in url

    def test_get_profile_edit_url(self, b2c_client: AzureADB2CClient):
        """Test profile edit URL generation."""
        url, state, nonce = b2c_client.get_profile_edit_url()
        assert "B2C_1_test_edit" in url

    def test_is_password_reset_error(self, b2c_client: AzureADB2CClient):
        """Test password reset error detection."""
        assert b2c_client.is_password_reset_error(
            "Error AADB2C90118: User clicked forgot password"
        ) is True
        assert b2c_client.is_password_reset_error("Some other error") is False

    def test_is_cancelled_error(self, b2c_client: AzureADB2CClient):
        """Test user cancelled detection."""
        assert b2c_client.is_cancelled_error(
            "Error AADB2C90091: User cancelled the operation"
        ) is True
        assert b2c_client.is_cancelled_error("Some other error") is False

    def test_map_claims_to_local(self, b2c_client: AzureADB2CClient, sample_claims: dict):
        """Test claims mapping to local format."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        local = b2c_client.map_claims_to_local(claims)

        assert local["user_id"] == "user-object-id-12345"
        assert local["email"] == "testuser@example.com"
        assert local["name"] == "Test User"
        assert local["identity_provider"] == "google.com"
        assert local["is_social_login"] is True
        assert local["b2c_object_id"] == "user-object-id-12345"
        assert local["b2c_policy"] == "B2C_1_test_susi"
        assert "admin" in local["roles"]
        assert local["organization_id"] == "org-12345"

    def test_map_claims_with_role_mapping(self, b2c_client: AzureADB2CClient, sample_claims: dict):
        """Test claims mapping with custom role mapping."""
        claims = B2CTokenClaims.from_dict(sample_claims)
        role_mapping = {"admin": "super_admin", "user": "basic_user"}
        local = b2c_client.map_claims_to_local(claims, role_mapping=role_mapping)

        assert "super_admin" in local["roles"]

    @pytest.mark.asyncio
    async def test_exchange_code_without_state(self, b2c_client: AzureADB2CClient):
        """Test code exchange fails without valid state."""
        with pytest.raises(AuthenticationError) as exc_info:
            await b2c_client.exchange_code_for_tokens(
                code="test-code",
                state="invalid-state",
            )
        assert "B2C_INVALID_STATE" in str(exc_info.value.error_code)

    @pytest.mark.asyncio
    async def test_validate_token_expired(self, b2c_client: AzureADB2CClient):
        """Test token validation with expired token."""
        # Create a mock that raises expired error
        with patch.object(b2c_client, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_jwks.return_value = mock_client

            # Create expired token simulation
            import jwt as pyjwt
            with patch("jwt.decode") as mock_decode:
                mock_decode.side_effect = pyjwt.ExpiredSignatureError("Token expired")

                with pytest.raises(TokenExpiredError):
                    await b2c_client.validate_token("expired.token.here")

    @pytest.mark.asyncio
    async def test_validate_token_invalid_audience(self, b2c_client: AzureADB2CClient):
        """Test token validation with wrong audience."""
        with patch.object(b2c_client, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_jwks.return_value = mock_client

            import jwt as pyjwt
            with patch("jwt.decode") as mock_decode:
                mock_decode.side_effect = pyjwt.InvalidAudienceError("Invalid audience")

                with pytest.raises(TokenInvalidError) as exc_info:
                    await b2c_client.validate_token("wrong.audience.token")
                assert "B2C_INVALID_AUDIENCE" in str(exc_info.value.error_code)


class TestFastAPIHelpers:
    """Tests for FastAPI integration helpers."""

    def test_extract_bearer_token(self):
        """Test bearer token extraction."""
        assert extract_bearer_token("Bearer abc123") == "abc123"
        assert extract_bearer_token("Bearer ") == ""
        assert extract_bearer_token("Basic abc123") is None
        assert extract_bearer_token("") is None
        assert extract_bearer_token(None) is None

    def test_initialize_and_get_client(self, b2c_config: AzureADB2CConfig):
        """Test client initialization and retrieval."""
        # Clear any existing client
        import netrun.auth.integrations.azure_ad_b2c as b2c_module
        b2c_module._b2c_client = None

        # Should raise before initialization
        with pytest.raises(RuntimeError):
            get_b2c_client()

        # Initialize
        client = initialize_b2c(b2c_config)
        assert client is not None
        assert isinstance(client, AzureADB2CClient)

        # Should return same instance
        assert get_b2c_client() is client
        assert is_b2c_configured() is True

        # Cleanup
        b2c_module._b2c_client = None
        assert is_b2c_configured() is False

    @pytest.mark.asyncio
    async def test_get_current_user_b2c(self, b2c_config: AzureADB2CConfig, sample_claims: dict):
        """Test FastAPI dependency for getting current user."""
        import netrun.auth.integrations.azure_ad_b2c as b2c_module
        b2c_module._b2c_client = None

        # Initialize client
        client = initialize_b2c(b2c_config)

        # Mock token validation
        with patch.object(client, "validate_token") as mock_validate:
            mock_validate.return_value = B2CTokenClaims.from_dict(sample_claims)

            user = await get_current_user_b2c("test.token.here")

            assert user["user_id"] == "user-object-id-12345"
            assert user["email"] == "testuser@example.com"
            mock_validate.assert_called_once()

        # Cleanup
        b2c_module._b2c_client = None


class TestB2CUserFlow:
    """Tests for B2CUserFlow enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert B2CUserFlow.SIGNUP_SIGNIN.value == "signup_signin"
        assert B2CUserFlow.PASSWORD_RESET.value == "password_reset"
        assert B2CUserFlow.PROFILE_EDIT.value == "profile_edit"

    def test_enum_string_behavior(self):
        """Test enum value access for string usage."""
        # Use .value for string operations
        assert B2CUserFlow.SIGNUP_SIGNIN.value == "signup_signin"
        assert B2CUserFlow.PASSWORD_RESET.value == "password_reset"
        # Can be used in f-strings with .value
        assert f"{B2CUserFlow.PROFILE_EDIT.value}" == "profile_edit"


# Integration test marker for tests requiring real B2C tenant
@pytest.mark.integration
class TestB2CIntegration:
    """Integration tests requiring real Azure AD B2C tenant.

    These tests are skipped by default. Run with:
    pytest -m integration --b2c-tenant=<name> --b2c-client-id=<id>
    """

    @pytest.mark.skip(reason="Requires real B2C tenant configuration")
    @pytest.mark.asyncio
    async def test_real_token_validation(self):
        """Test token validation against real B2C tenant."""
        pass  # Implement with real credentials

    @pytest.mark.skip(reason="Requires real B2C tenant configuration")
    @pytest.mark.asyncio
    async def test_real_token_refresh(self):
        """Test token refresh against real B2C tenant."""
        pass  # Implement with real credentials
