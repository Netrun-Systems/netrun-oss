"""
Azure AD Integration Tests
Service #59 Unified Authentication

Tests for Azure AD/Entra ID authentication integration covering:
- Configuration and initialization
- Authorization URL generation with PKCE
- Token exchange (authorization code flow)
- Token validation with JWKS
- User profile and group fetching
- Claims mapping to local format
- Multi-tenant support

Total: 35+ tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import jwt as pyjwt

from netrun_auth.integrations.azure_ad import (
    AzureADConfig,
    AzureADClient,
    AzureADMultiTenantClient,
    get_azure_ad_client,
    initialize_azure_ad,
    get_current_user_azure,
)
from netrun_auth.core.exceptions import AuthenticationError, TokenValidationError


@pytest.fixture
def azure_config():
    """Create test Azure AD configuration."""
    return AzureADConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )


@pytest.fixture
def azure_client(azure_config):
    """Create AzureADClient instance."""
    return AzureADClient(azure_config)


@pytest.fixture
def multi_tenant_client():
    """Create multi-tenant Azure AD client."""
    config = AzureADConfig(
        tenant_id="common",
        client_id="test-client-id",
        client_secret="test-client-secret"
    )
    return AzureADMultiTenantClient(config)


class TestAzureADConfig:
    """Test Azure AD configuration."""

    def test_config_auto_generates_authority(self):
        """Authority should be auto-generated from tenant_id."""
        config = AzureADConfig(
            tenant_id="test-tenant",
            client_id="test-client"
        )
        assert config.authority == "https://login.microsoftonline.com/test-tenant"

    def test_config_default_scopes(self):
        """Default scopes should include User.Read."""
        config = AzureADConfig(tenant_id="test", client_id="test")
        assert "User.Read" in config.scopes

    def test_config_custom_authority(self):
        """Custom authority should override auto-generation."""
        custom_authority = "https://custom.authority.com/tenant"
        config = AzureADConfig(
            tenant_id="test",
            client_id="test",
            authority=custom_authority
        )
        assert config.authority == custom_authority

    def test_config_custom_scopes(self):
        """Custom scopes should be configurable."""
        custom_scopes = ["User.Read", "Group.Read.All", "Directory.Read.All"]
        config = AzureADConfig(
            tenant_id="test",
            client_id="test",
            scopes=custom_scopes
        )
        assert config.scopes == custom_scopes

    def test_config_optional_client_secret(self):
        """Client secret should be optional for public clients."""
        config = AzureADConfig(
            tenant_id="test",
            client_id="test"
            # No client_secret
        )
        assert config.client_secret is None


class TestAzureADClient:
    """Test Azure AD client functionality."""

    def test_msal_app_lazy_initialization(self, azure_client):
        """MSAL app should be lazily initialized."""
        # Should not be initialized yet
        assert azure_client._msal_app is None

        # Mock MSAL to avoid network calls
        with patch('netrun_auth.integrations.azure_ad.ConfidentialClientApplication') as mock_msal:
            mock_app = MagicMock()
            mock_msal.return_value = mock_app

            # Access property should initialize
            msal_app = azure_client.msal_app
            assert msal_app is not None
            assert azure_client._msal_app is not None

    def test_msal_app_confidential_vs_public(self):
        """Should create confidential client with secret, public without."""
        from msal import ConfidentialClientApplication, PublicClientApplication

        # Mock both MSAL client types
        with patch('netrun_auth.integrations.azure_ad.ConfidentialClientApplication') as mock_conf:
            with patch('netrun_auth.integrations.azure_ad.PublicClientApplication') as mock_pub:
                mock_conf_app = MagicMock(spec=ConfidentialClientApplication)
                mock_pub_app = MagicMock(spec=PublicClientApplication)
                mock_conf.return_value = mock_conf_app
                mock_pub.return_value = mock_pub_app

                # With secret (confidential)
                config_confidential = AzureADConfig(
                    tenant_id="test",
                    client_id="test",
                    client_secret="secret"
                )
                client_confidential = AzureADClient(config_confidential)
                msal_app = client_confidential.msal_app
                assert mock_conf.called
                assert msal_app == mock_conf_app

                # Without secret (public)
                config_public = AzureADConfig(
                    tenant_id="test",
                    client_id="test"
                )
                client_public = AzureADClient(config_public)
                msal_app = client_public.msal_app
                assert mock_pub.called
                assert msal_app == mock_pub_app

    def test_jwks_client_lazy_initialization(self, azure_client):
        """JWKS client should be lazily initialized."""
        assert azure_client._jwks_client is None

        jwks_client = azure_client.jwks_client
        assert jwks_client is not None

    def test_generate_pkce_pair(self, azure_client):
        """PKCE pair should generate verifier and S256 challenge."""
        verifier, challenge = azure_client._generate_pkce_pair()

        # Verifier should be URL-safe string
        assert len(verifier) >= 43
        assert len(challenge) >= 43

        # Challenge should be different from verifier (S256 transformation)
        assert verifier != challenge

        # Generate again should be different
        verifier2, challenge2 = azure_client._generate_pkce_pair()
        assert verifier != verifier2
        assert challenge != challenge2

    def test_get_authorization_url_includes_pkce(self, azure_client):
        """Authorization URL should include PKCE challenge."""
        # Mock MSAL app to avoid network calls
        mock_msal = MagicMock()
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize?code_challenge=test&code_challenge_method=S256"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            url, state = azure_client.get_authorization_url(use_pkce=True)

            assert isinstance(url, str)
            assert isinstance(state, str)
            assert "code_challenge" in url
            assert "code_challenge_method=S256" in url
            assert state in azure_client._pkce_verifiers

    def test_get_authorization_url_without_pkce(self, azure_client):
        """Authorization URL without PKCE should not include challenge."""
        mock_msal = MagicMock()
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            url, state = azure_client.get_authorization_url(use_pkce=False)

            assert isinstance(url, str)
            assert "code_challenge" not in url

    def test_get_authorization_url_custom_state(self, azure_client):
        """Should accept custom state parameter."""
        mock_msal = MagicMock()
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            custom_state = "my-custom-state-123"
            url, state = azure_client.get_authorization_url(state=custom_state, use_pkce=False)

            assert state == custom_state

    def test_get_authorization_url_custom_scopes(self, azure_client):
        """Should accept custom scopes."""
        mock_msal = MagicMock()
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize?scope=User.Read+Mail.Read"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            custom_scopes = ["User.Read", "Mail.Read"]
            url, state = azure_client.get_authorization_url(scopes=custom_scopes, use_pkce=False)

            # MSAL formats scopes in the URL
            assert "User.Read" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, azure_client):
        """Code exchange should return access and refresh tokens."""
        # Mock MSAL app response
        mock_result = {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

        mock_msal = MagicMock()
        mock_msal.acquire_token_by_authorization_code.return_value = mock_result
        mock_msal.get_authorization_request_url.return_value = "https://login.microsoftonline.com/authorize?code_challenge=test&code_challenge_method=S256"

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            # Generate authorization URL to create PKCE verifier
            url, state = azure_client.get_authorization_url(use_pkce=True)

            result = await azure_client.exchange_code_for_tokens(
                code="test-auth-code",
                state=state
            )

            assert result["access_token"] == "mock-access-token"
            assert result["refresh_token"] == "mock-refresh-token"

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_error(self, azure_client):
        """Code exchange error should raise AuthenticationError."""
        mock_error = {
            "error": "invalid_grant",
            "error_description": "The authorization code is invalid"
        }

        mock_msal = MagicMock()
        mock_msal.acquire_token_by_authorization_code.return_value = mock_error

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            with pytest.raises(AuthenticationError, match="invalid"):
                await azure_client.exchange_code_for_tokens(
                    code="invalid-code",
                    state="state"
                )

    @pytest.mark.asyncio
    async def test_get_client_credentials_token(self, azure_client):
        """Client credentials flow should return access token."""
        mock_result = {
            "access_token": "mock-service-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

        mock_msal = MagicMock()
        mock_msal.acquire_token_for_client.return_value = mock_result

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            result = await azure_client.get_client_credentials_token()

            assert result["access_token"] == "mock-service-token"

    @pytest.mark.asyncio
    async def test_get_client_credentials_requires_secret(self):
        """Client credentials flow should require client_secret."""
        config = AzureADConfig(
            tenant_id="test",
            client_id="test"
            # No secret
        )
        client = AzureADClient(config)

        # Should raise immediately without trying to access msal_app
        with pytest.raises(AuthenticationError, match="client_secret"):
            await client.get_client_credentials_token()

    @pytest.mark.asyncio
    async def test_get_on_behalf_of_token(self, azure_client):
        """On-behalf-of flow should return delegated token."""
        mock_result = {
            "access_token": "mock-delegated-token",
            "expires_in": 3600
        }

        mock_msal = MagicMock()
        mock_msal.acquire_token_on_behalf_of.return_value = mock_result

        with patch.object(type(azure_client), 'msal_app', new_callable=lambda: property(lambda self: mock_msal)):
            result = await azure_client.get_on_behalf_of_token(
                user_assertion="user-access-token",
                scopes=["api://downstream/.default"]
            )

            assert result["access_token"] == "mock-delegated-token"

    @pytest.mark.asyncio
    async def test_get_on_behalf_of_requires_secret(self):
        """On-behalf-of flow should require client_secret."""
        config = AzureADConfig(tenant_id="test", client_id="test")
        client = AzureADClient(config)

        with pytest.raises(AuthenticationError, match="client_secret"):
            await client.get_on_behalf_of_token(
                user_assertion="token",
                scopes=["scope"]
            )


class TestAzureTokenValidation:
    """Test Azure AD token validation."""

    @pytest.mark.asyncio
    async def test_validate_azure_token_valid(self, azure_client):
        """Valid Azure token should be validated successfully."""
        # Create a mock token with required claims
        claims = {
            "oid": "azure-user-123",
            "sub": "azure-user-123",
            "email": "user@example.com",
            "tid": "tenant-123",
            "aud": azure_client.config.client_id,
            "iss": "https://login.microsoftonline.com/tenant-123/v2.0",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp())
        }

        # Mock JWKS client and JWT decode
        with patch.object(azure_client.jwks_client, 'get_signing_key_from_jwt') as mock_jwks:
            mock_key = MagicMock()
            mock_key.key = "mock-public-key"
            mock_jwks.return_value = mock_key

            with patch('netrun_auth.integrations.azure_ad.jwt.decode', return_value=claims):
                result = await azure_client.validate_azure_token("mock-token")

                assert result["oid"] == "azure-user-123"
                assert result["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_validate_azure_token_expired(self, azure_client):
        """Expired Azure token should raise error."""
        # Mock the _jwks_client attribute
        mock_jwks = MagicMock()
        mock_key = MagicMock()
        mock_key.key = "mock-public-key"
        mock_jwks.get_signing_key_from_jwt.return_value = mock_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode', side_effect=pyjwt.ExpiredSignatureError):
            with pytest.raises(TokenValidationError, match="expired"):
                await azure_client.validate_azure_token("expired-token")

    @pytest.mark.asyncio
    async def test_validate_azure_token_invalid_audience(self, azure_client):
        """Invalid audience should raise error."""
        # Mock the _jwks_client attribute
        mock_jwks = MagicMock()
        mock_key = MagicMock()
        mock_key.key = "mock-public-key"
        mock_jwks.get_signing_key_from_jwt.return_value = mock_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode', side_effect=pyjwt.InvalidAudienceError):
            with pytest.raises(TokenValidationError, match="audience"):
                await azure_client.validate_azure_token("token")

    @pytest.mark.asyncio
    async def test_validate_azure_token_tenant_restriction(self, azure_client):
        """Token from disallowed tenant should be rejected."""
        claims = {
            "oid": "user-123",
            "tid": "blocked-tenant",
            "aud": azure_client.config.client_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }

        # Mock the _jwks_client attribute
        mock_jwks = MagicMock()
        mock_key = MagicMock()
        mock_key.key = "mock-public-key"
        mock_jwks.get_signing_key_from_jwt.return_value = mock_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode', return_value=claims):
            with pytest.raises(TokenValidationError, match="not allowed"):
                await azure_client.validate_azure_token(
                    "token",
                    allowed_tenants=["allowed-tenant-1", "allowed-tenant-2"]
                )

    @pytest.mark.asyncio
    async def test_validate_azure_token_missing_identity_claims(self, azure_client):
        """Token missing oid/sub should be rejected."""
        claims = {
            "tid": "tenant-123",
            "aud": azure_client.config.client_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
            # Missing oid and sub
        }

        # Mock the _jwks_client attribute
        mock_jwks = MagicMock()
        mock_key = MagicMock()
        mock_key.key = "mock-public-key"
        mock_jwks.get_signing_key_from_jwt.return_value = mock_key
        azure_client._jwks_client = mock_jwks

        with patch('netrun_auth.integrations.azure_ad.jwt.decode', return_value=claims):
            with pytest.raises(TokenValidationError, match="identity claims"):
                await azure_client.validate_azure_token("token")


class TestAzureUserProfile:
    """Test Azure AD user profile and groups fetching."""

    @pytest.mark.asyncio
    async def test_get_user_profile(self, azure_client):
        """User profile should be fetched from Microsoft Graph."""
        mock_profile = {
            "id": "user-123",
            "displayName": "Test User",
            "mail": "user@example.com",
            "userPrincipalName": "user@example.com"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()  # Changed from AsyncMock to MagicMock
            mock_response.json = MagicMock(return_value=mock_profile)  # json() is sync, returns dict
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            profile = await azure_client.get_user_profile("access-token")

            assert profile["displayName"] == "Test User"
            assert profile["mail"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_user_profile_error(self, azure_client):
        """Graph API error should raise AuthenticationError."""
        with patch('httpx.AsyncClient') as mock_client_class:
            from httpx import HTTPStatusError, Request, Response

            mock_client = AsyncMock()
            mock_response = Response(status_code=401)
            mock_client.get = AsyncMock(return_value=mock_response)

            # Make raise_for_status raise exception
            def raise_error():
                raise HTTPStatusError(
                    "Unauthorized",
                    request=Request("GET", "https://example.com"),
                    response=mock_response
                )
            mock_response.raise_for_status = raise_error

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AuthenticationError):
                await azure_client.get_user_profile("invalid-token")

    @pytest.mark.asyncio
    async def test_get_user_groups(self, azure_client):
        """User groups should be fetched from Microsoft Graph."""
        mock_groups = {
            "value": [
                {"id": "group-1"},
                {"id": "group-2"},
                {"id": "group-3"}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()  # Changed from AsyncMock to MagicMock
            mock_response.json = MagicMock(return_value=mock_groups)  # json() is sync, returns dict
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            groups = await azure_client.get_user_groups("access-token")

            assert len(groups) == 3
            assert "group-1" in groups
            assert "group-2" in groups


class TestAzureClaimsMapping:
    """Test Azure AD to local claims mapping."""

    def test_map_azure_claims_to_local(self, azure_client):
        """Azure claims should map to local format."""
        azure_claims = {
            "oid": "azure-user-123",
            "email": "user@example.com",
            "name": "Test User",
            "roles": ["Admin", "User"],
            "groups": ["group-1", "group-2"],
            "tid": "tenant-123"
        }

        local = azure_client.map_azure_claims_to_local(azure_claims)

        assert local["user_id"] == "azure-user-123"
        assert local["email"] == "user@example.com"
        assert local["name"] == "Test User"
        assert "Admin" in local["roles"]
        assert local["azure_tenant_id"] == "tenant-123"

    def test_map_azure_claims_with_organization_mapping(self, azure_client):
        """Tenant ID should map to organization ID."""
        azure_claims = {
            "oid": "user-123",
            "tid": "azure-tenant-456"
        }

        org_mapping = {
            "azure-tenant-456": "netrun-org-789"
        }

        local = azure_client.map_azure_claims_to_local(azure_claims, org_mapping)

        assert local["organization_id"] == "netrun-org-789"

    def test_map_azure_claims_fallback_to_sub(self, azure_client):
        """Should use sub if oid is missing."""
        azure_claims = {
            "sub": "subject-123",
            "tid": "tenant"
        }

        local = azure_client.map_azure_claims_to_local(azure_claims)

        assert local["user_id"] == "subject-123"

    def test_map_azure_claims_groups_as_roles(self, azure_client):
        """Groups should be used as roles if no app roles."""
        azure_claims = {
            "oid": "user-123",
            "groups": ["group-1", "group-2"],
            "tid": "tenant"
            # No roles claim
        }

        local = azure_client.map_azure_claims_to_local(azure_claims)

        assert local["roles"] == ["group-1", "group-2"]


class TestAzureMultiTenant:
    """Test multi-tenant Azure AD client."""

    def test_multi_tenant_uses_common_authority(self, multi_tenant_client):
        """Multi-tenant client should use /common authority."""
        assert "common" in multi_tenant_client.config.authority.lower()

    @pytest.mark.asyncio
    async def test_validate_tenant_allowed(self, multi_tenant_client):
        """Allowed tenant should pass validation."""
        is_valid = await multi_tenant_client.validate_tenant(
            tenant_id="allowed-tenant",
            allowed_tenants=["allowed-tenant", "another-tenant"]
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_tenant_blocked(self, multi_tenant_client):
        """Blocked tenant should fail validation."""
        is_valid = await multi_tenant_client.validate_tenant(
            tenant_id="blocked-tenant",
            allowed_tenants=["allowed-tenant"]
        )

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_tenant_allow_all(self, multi_tenant_client):
        """None allowlist should allow all tenants."""
        is_valid = await multi_tenant_client.validate_tenant(
            tenant_id="any-tenant",
            allowed_tenants=None
        )

        assert is_valid is True


class TestAzureIntegrationHelpers:
    """Test FastAPI integration helpers."""

    def test_initialize_azure_ad(self, azure_config):
        """Should initialize global Azure AD client."""
        client = initialize_azure_ad(azure_config)

        assert client is not None
        assert isinstance(client, AzureADClient)

        # Should be retrievable
        retrieved = get_azure_ad_client()
        assert retrieved is client

    def test_get_azure_ad_client_not_initialized(self):
        """Should raise error if not initialized."""
        # Reset global client
        import netrun_auth.integrations.azure_ad as azure_module
        azure_module._azure_ad_client = None

        with pytest.raises(RuntimeError) as exc_info:
            get_azure_ad_client()

        assert "not initialized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_current_user_azure(self, azure_client):
        """Should validate token and return user claims."""
        mock_azure_claims = {
            "oid": "user-123",
            "email": "user@example.com",
            "tid": "tenant-123"
        }

        with patch.object(azure_client, 'validate_azure_token', return_value=mock_azure_claims):
            with patch.object(azure_client, 'map_azure_claims_to_local') as mock_map:
                mock_map.return_value = {"user_id": "user-123", "email": "user@example.com"}

                user = await get_current_user_azure("token", azure_client)

                assert user["user_id"] == "user-123"
                mock_map.assert_called_once_with(mock_azure_claims)
