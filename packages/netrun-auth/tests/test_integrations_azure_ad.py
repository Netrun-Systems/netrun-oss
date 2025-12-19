"""
Unit tests for Azure AD integration.

Tests:
- AzureADConfig initialization
- Authorization URL generation with PKCE
- Token exchange
- Token validation
- Claims mapping
- Multi-tenant support

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from netrun.auth.integrations.azure_ad import (
    AzureADConfig,
    AzureADClient,
    AzureADMultiTenantClient,
)
from netrun.auth.core.exceptions import (
    TokenValidationError,
    AuthenticationError,
)


class TestAzureADConfig:
    """Test AzureADConfig dataclass."""

    def test_config_initialization(self):
        """Test basic config initialization."""
        config = AzureADConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret"
        )

        assert config.tenant_id == "test-tenant-id"
        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-secret"
        assert config.authority == "https://login.microsoftonline.com/test-tenant-id"
        assert config.scopes == ["User.Read"]

    def test_config_custom_authority(self):
        """Test config with custom authority."""
        config = AzureADConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            authority="https://custom.authority.com"
        )

        assert config.authority == "https://custom.authority.com"

    def test_config_custom_scopes(self):
        """Test config with custom scopes."""
        config = AzureADConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            scopes=["openid", "profile", "email"]
        )

        assert config.scopes == ["openid", "profile", "email"]


class TestAzureADClient:
    """Test AzureADClient."""

    @pytest.fixture
    def azure_config(self):
        """Create test Azure AD config."""
        return AzureADConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback"
        )

    @pytest.fixture
    def azure_client(self, azure_config):
        """Create test Azure AD client."""
        return AzureADClient(azure_config)

    def test_client_initialization(self, azure_client, azure_config):
        """Test client initialization."""
        assert azure_client.config == azure_config
        assert azure_client._msal_app is None
        assert azure_client._jwks_client is None
        assert azure_client._pkce_verifiers == {}

    def test_generate_pkce_pair(self, azure_client):
        """Test PKCE code_verifier and code_challenge generation."""
        verifier, challenge = azure_client._generate_pkce_pair()

        # Verify verifier length (43-128 chars for base64url)
        assert 43 <= len(verifier) <= 128

        # Verify challenge is base64url encoded
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in challenge)

        # Verify challenge length (43 chars for S256)
        assert len(challenge) == 43

    def test_get_authorization_url_with_pkce(self, azure_client):
        """Test authorization URL generation with PKCE."""
        mock_msal = MagicMock()
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize?code_challenge=test&code_challenge_method=S256&state=test-state"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            auth_url, state = azure_client.get_authorization_url(use_pkce=True)

            # Verify state is generated
            assert state is not None
            assert len(state) > 0

            # Verify PKCE verifier is stored
            assert state in azure_client._pkce_verifiers

            # Verify URL contains expected parameters
            assert "code_challenge=" in auth_url
            assert "code_challenge_method=S256" in auth_url
            assert "state=" in auth_url

    def test_get_authorization_url_without_pkce(self, azure_client):
        """Test authorization URL generation without PKCE."""
        mock_msal = MagicMock()
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize?state=test-state"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            auth_url, state = azure_client.get_authorization_url(use_pkce=False)

            # Verify state is generated
            assert state is not None

            # Verify no PKCE verifier stored
            assert state not in azure_client._pkce_verifiers

            # Verify URL does not contain PKCE parameters
            assert "code_challenge=" not in auth_url

    @pytest.mark.asyncio
    async def test_validate_azure_token_success(self, azure_client):
        """Test successful token validation."""
        # Mock JWKS client and JWT decode
        mock_signing_key = Mock()
        mock_signing_key.key = "test-public-key"

        # Mock the _jwks_client attribute directly
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "oid": "test-user-id",
                "sub": "test-subject",
                "email": "test@example.com",
                "tid": "test-tenant-id"
            }

            claims = await azure_client.validate_azure_token("test-token")

            assert claims["oid"] == "test-user-id"
            assert claims["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_validate_azure_token_missing_identity_claims(self, azure_client):
        """Test token validation with missing identity claims."""
        mock_signing_key = Mock()
        mock_signing_key.key = "test-public-key"

        # Mock the _jwks_client attribute directly
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "email": "test@example.com",
                "tid": "test-tenant-id"
                # Missing oid and sub
            }

            with pytest.raises(TokenValidationError, match="identity claims"):
                await azure_client.validate_azure_token("test-token")

    @pytest.mark.asyncio
    async def test_validate_azure_token_tenant_not_allowed(self, azure_client):
        """Test token validation with disallowed tenant."""
        mock_signing_key = Mock()
        mock_signing_key.key = "test-public-key"

        # Mock the _jwks_client attribute directly
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "oid": "test-user-id",
                "sub": "test-subject",
                "tid": "unauthorized-tenant"
            }

            with pytest.raises(TokenValidationError, match="not allowed"):
                await azure_client.validate_azure_token(
                    "test-token",
                    allowed_tenants=["allowed-tenant-1", "allowed-tenant-2"]
                )

    def test_map_azure_claims_to_local(self, azure_client):
        """Test mapping Azure claims to local format."""
        azure_claims = {
            "oid": "azure-user-id",
            "sub": "azure-subject",
            "email": "test@example.com",
            "name": "Test User",
            "tid": "azure-tenant-id",
            "roles": ["role1", "role2"]
        }

        local_claims = azure_client.map_azure_claims_to_local(azure_claims)

        assert local_claims["user_id"] == "azure-user-id"
        assert local_claims["organization_id"] == "azure-tenant-id"
        assert local_claims["email"] == "test@example.com"
        assert local_claims["name"] == "Test User"
        assert local_claims["roles"] == ["role1", "role2"]
        assert local_claims["azure_oid"] == "azure-user-id"

    def test_map_azure_claims_with_organization_mapping(self, azure_client):
        """Test mapping Azure claims with custom organization mapping."""
        azure_claims = {
            "oid": "azure-user-id",
            "tid": "azure-tenant-id"
        }

        organization_mapping = {
            "azure-tenant-id": "local-org-123"
        }

        local_claims = azure_client.map_azure_claims_to_local(
            azure_claims,
            organization_mapping=organization_mapping
        )

        assert local_claims["organization_id"] == "local-org-123"
        assert local_claims["azure_tenant_id"] == "azure-tenant-id"


class TestAzureADMultiTenantClient:
    """Test AzureADMultiTenantClient."""

    def test_multi_tenant_config_override(self):
        """Test multi-tenant client overrides tenant_id."""
        config = AzureADConfig(
            tenant_id="specific-tenant",
            client_id="test-client-id",
            client_secret="test-secret"
        )

        client = AzureADMultiTenantClient(config)

        # Verify tenant_id is overridden to 'common'
        assert client.config.tenant_id == "common"
        assert client.config.authority == "https://login.microsoftonline.com/common"

    @pytest.mark.asyncio
    async def test_validate_tenant_with_allowlist(self):
        """Test tenant validation with allowlist."""
        config = AzureADConfig(
            tenant_id="common",
            client_id="test-client-id"
        )

        client = AzureADMultiTenantClient(config)

        # Test allowed tenant
        is_allowed = await client.validate_tenant(
            "allowed-tenant-1",
            allowed_tenants=["allowed-tenant-1", "allowed-tenant-2"]
        )
        assert is_allowed is True

        # Test disallowed tenant
        is_allowed = await client.validate_tenant(
            "unauthorized-tenant",
            allowed_tenants=["allowed-tenant-1", "allowed-tenant-2"]
        )
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_validate_tenant_no_restrictions(self):
        """Test tenant validation with no restrictions."""
        config = AzureADConfig(
            tenant_id="common",
            client_id="test-client-id"
        )

        client = AzureADMultiTenantClient(config)

        # Any tenant should be allowed when no restrictions
        is_allowed = await client.validate_tenant("any-tenant")
        assert is_allowed is True
