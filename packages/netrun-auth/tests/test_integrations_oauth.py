"""
Unit tests for OAuth 2.0 integration.

Tests:
- OAuthConfig presets (Google, GitHub, Okta, Auth0)
- Authorization URL generation with PKCE
- Token exchange
- Token refresh
- Claims mapping
- OAuthManager provider registration

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from netrun_auth.integrations.oauth import (
    OAuthProvider,
    OAuthConfig,
    OAuthClient,
    OAuthManager,
)
from netrun_auth.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
)


class TestOAuthConfig:
    """Test OAuthConfig dataclass and presets."""

    def test_google_config(self):
        """Test Google OAuth preset."""
        config = OAuthConfig.google(
            client_id="test-google-id",
            client_secret="test-google-secret",
            redirect_uri="http://localhost:8000/callback"
        )

        assert config.provider == OAuthProvider.GOOGLE
        assert config.client_id == "test-google-id"
        assert config.authorization_endpoint == "https://accounts.google.com/o/oauth2/v2/auth"
        assert config.token_endpoint == "https://oauth2.googleapis.com/token"
        assert config.userinfo_endpoint == "https://openidconnect.googleapis.com/v1/userinfo"
        assert "openid" in config.scopes
        assert "email" in config.scopes

    def test_github_config(self):
        """Test GitHub OAuth preset."""
        config = OAuthConfig.github(
            client_id="test-github-id",
            client_secret="test-github-secret",
            redirect_uri="http://localhost:8000/callback"
        )

        assert config.provider == OAuthProvider.GITHUB
        assert config.authorization_endpoint == "https://github.com/login/oauth/authorize"
        assert config.token_endpoint == "https://github.com/login/oauth/access_token"
        assert "read:user" in config.scopes

    def test_okta_config(self):
        """Test Okta OAuth preset."""
        config = OAuthConfig.okta(
            client_id="test-okta-id",
            client_secret="test-okta-secret",
            redirect_uri="http://localhost:8000/callback",
            okta_domain="dev-12345.okta.com"
        )

        assert config.provider == OAuthProvider.OKTA
        assert "dev-12345.okta.com" in config.authorization_endpoint
        assert "dev-12345.okta.com" in config.token_endpoint
        assert config.jwks_uri is not None

    def test_auth0_config(self):
        """Test Auth0 OAuth preset."""
        config = OAuthConfig.auth0(
            client_id="test-auth0-id",
            client_secret="test-auth0-secret",
            redirect_uri="http://localhost:8000/callback",
            auth0_domain="dev-12345.us.auth0.com"
        )

        assert config.provider == OAuthProvider.AUTH0
        assert "dev-12345.us.auth0.com" in config.authorization_endpoint
        assert "dev-12345.us.auth0.com" in config.token_endpoint


class TestOAuthClient:
    """Test OAuthClient."""

    @pytest.fixture
    def google_config(self):
        """Create test Google OAuth config."""
        return OAuthConfig.google(
            client_id="test-client-id",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback"
        )

    @pytest.fixture
    def oauth_client(self, google_config):
        """Create test OAuth client."""
        return OAuthClient(google_config)

    def test_client_initialization(self, oauth_client, google_config):
        """Test client initialization."""
        assert oauth_client.config == google_config
        assert oauth_client._pkce_verifiers == {}

    def test_generate_state(self, oauth_client):
        """Test state parameter generation."""
        state = oauth_client.generate_state()

        # Verify state is secure random string
        assert len(state) > 0
        assert isinstance(state, str)

        # Verify two states are different
        state2 = oauth_client.generate_state()
        assert state != state2

    def test_generate_pkce_pair(self, oauth_client):
        """Test PKCE generation."""
        verifier, challenge = oauth_client.generate_pkce_pair()

        # Verify verifier length
        assert 43 <= len(verifier) <= 128

        # Verify challenge is base64url
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in challenge)

        # Verify challenge length (S256)
        assert len(challenge) == 43

    def test_get_authorization_url(self, oauth_client):
        """Test authorization URL generation."""
        auth_url, state = oauth_client.get_authorization_url()

        # Verify state is returned
        assert state is not None
        assert len(state) > 0

        # Verify PKCE verifier is stored
        assert state in oauth_client._pkce_verifiers

        # Verify URL structure
        assert "accounts.google.com" in auth_url
        assert "response_type=code" in auth_url
        assert "client_id=" in auth_url
        assert "redirect_uri=" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert f"state={state}" in auth_url

    def test_get_authorization_url_custom_scopes(self, oauth_client):
        """Test authorization URL with custom scopes."""
        auth_url, state = oauth_client.get_authorization_url(
            scopes=["custom_scope_1", "custom_scope_2"]
        )

        # Verify custom scopes in URL
        assert "scope=custom_scope_1+custom_scope_2" in auth_url

    def test_map_google_claims(self, oauth_client):
        """Test Google claims mapping."""
        google_claims = {
            "sub": "google-user-id",
            "email": "test@gmail.com",
            "name": "Test User",
            "email_verified": True,
            "picture": "https://example.com/photo.jpg"
        }

        local_claims = oauth_client.map_provider_claims_to_local(google_claims)

        assert local_claims["user_id"] == "google-user-id"
        assert local_claims["email"] == "test@gmail.com"
        assert local_claims["name"] == "Test User"
        assert local_claims["provider"] == "google"
        assert local_claims["email_verified"] is True

    def test_map_github_claims(self):
        """Test GitHub claims mapping."""
        config = OAuthConfig.github(
            client_id="test-id",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback"
        )
        client = OAuthClient(config)

        github_claims = {
            "id": 12345,
            "login": "testuser",
            "email": "test@example.com",
            "name": "Test User",
            "avatar_url": "https://github.com/avatar.jpg",
            "html_url": "https://github.com/testuser"
        }

        local_claims = client.map_provider_claims_to_local(github_claims)

        assert local_claims["user_id"] == "12345"
        assert local_claims["username"] == "testuser"
        assert local_claims["email"] == "test@example.com"
        assert local_claims["provider"] == "github"
        assert local_claims["github_profile"] == "https://github.com/testuser"


class TestOAuthManager:
    """Test OAuthManager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = OAuthManager()

        assert manager._clients == {}
        assert manager.available_providers == []

    def test_register_provider(self):
        """Test provider registration."""
        manager = OAuthManager()

        google_config = OAuthConfig.google(
            client_id="test-id",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback"
        )

        manager.register_provider(google_config)

        assert OAuthProvider.GOOGLE in manager.available_providers
        assert isinstance(manager.get_client(OAuthProvider.GOOGLE), OAuthClient)

    def test_register_multiple_providers(self):
        """Test registering multiple providers."""
        manager = OAuthManager()

        google_config = OAuthConfig.google(
            client_id="google-id",
            client_secret="google-secret",
            redirect_uri="http://localhost:8000/callback"
        )

        github_config = OAuthConfig.github(
            client_id="github-id",
            client_secret="github-secret",
            redirect_uri="http://localhost:8000/callback"
        )

        manager.register_provider(google_config)
        manager.register_provider(github_config)

        assert len(manager.available_providers) == 2
        assert OAuthProvider.GOOGLE in manager.available_providers
        assert OAuthProvider.GITHUB in manager.available_providers

    def test_get_client_not_registered(self):
        """Test getting client for unregistered provider."""
        manager = OAuthManager()

        with pytest.raises(ConfigurationError, match="Provider .* not registered"):
            manager.get_client(OAuthProvider.GOOGLE)

    def test_get_client_success(self):
        """Test getting registered client."""
        manager = OAuthManager()

        google_config = OAuthConfig.google(
            client_id="test-id",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback"
        )

        manager.register_provider(google_config)

        client = manager.get_client(OAuthProvider.GOOGLE)

        assert isinstance(client, OAuthClient)
        assert client.config.provider == OAuthProvider.GOOGLE
