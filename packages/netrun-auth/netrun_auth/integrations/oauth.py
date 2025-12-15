"""
Generic OAuth 2.0 client for netrun-auth.

Provides OAuth 2.0 authentication support for multiple providers:
- Google
- GitHub
- Okta
- Auth0
- Custom OAuth providers

Security features:
- PKCE for all authorization code flows
- State parameter for CSRF protection
- Token refresh support
- Secure credential storage
- Claims mapping to netrun-auth format

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import secrets
import hashlib
import base64

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

from netrun_auth.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
)


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GOOGLE = "google"
    GITHUB = "github"
    OKTA = "okta"
    AUTH0 = "auth0"
    CUSTOM = "custom"


@dataclass
class OAuthConfig:
    """OAuth 2.0 configuration.

    Attributes:
        provider: OAuth provider type
        client_id: OAuth client ID
        client_secret: OAuth client secret
        authorization_endpoint: OAuth authorization URL
        token_endpoint: OAuth token URL
        userinfo_endpoint: Optional userinfo URL
        jwks_uri: Optional JWKS URL for token validation
        redirect_uri: OAuth callback URI
        scopes: Default scopes to request
    """
    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    redirect_uri: str = "http://localhost:8000/auth/callback"
    scopes: List[str] = field(default_factory=list)

    @classmethod
    def google(
        cls,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> "OAuthConfig":
        """Pre-configured Google OAuth.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth callback URI

        Returns:
            Google OAuth configuration
        """
        return cls(
            provider=OAuthProvider.GOOGLE,
            client_id=client_id,
            client_secret=client_secret,
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
            jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
            redirect_uri=redirect_uri,
            scopes=["openid", "email", "profile"]
        )

    @classmethod
    def github(
        cls,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> "OAuthConfig":
        """Pre-configured GitHub OAuth.

        Args:
            client_id: GitHub OAuth client ID
            client_secret: GitHub OAuth client secret
            redirect_uri: OAuth callback URI

        Returns:
            GitHub OAuth configuration
        """
        return cls(
            provider=OAuthProvider.GITHUB,
            client_id=client_id,
            client_secret=client_secret,
            authorization_endpoint="https://github.com/login/oauth/authorize",
            token_endpoint="https://github.com/login/oauth/access_token",
            userinfo_endpoint="https://api.github.com/user",
            redirect_uri=redirect_uri,
            scopes=["read:user", "user:email"]
        )

    @classmethod
    def okta(
        cls,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        okta_domain: str
    ) -> "OAuthConfig":
        """Pre-configured Okta OAuth.

        Args:
            client_id: Okta OAuth client ID
            client_secret: Okta OAuth client secret
            redirect_uri: OAuth callback URI
            okta_domain: Okta domain (e.g., 'dev-12345.okta.com')

        Returns:
            Okta OAuth configuration
        """
        return cls(
            provider=OAuthProvider.OKTA,
            client_id=client_id,
            client_secret=client_secret,
            authorization_endpoint=f"https://{okta_domain}/oauth2/v1/authorize",
            token_endpoint=f"https://{okta_domain}/oauth2/v1/token",
            userinfo_endpoint=f"https://{okta_domain}/oauth2/v1/userinfo",
            jwks_uri=f"https://{okta_domain}/oauth2/v1/keys",
            redirect_uri=redirect_uri,
            scopes=["openid", "email", "profile"]
        )

    @classmethod
    def auth0(
        cls,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        auth0_domain: str
    ) -> "OAuthConfig":
        """Pre-configured Auth0 OAuth.

        Args:
            client_id: Auth0 OAuth client ID
            client_secret: Auth0 OAuth client secret
            redirect_uri: OAuth callback URI
            auth0_domain: Auth0 domain (e.g., 'dev-12345.us.auth0.com')

        Returns:
            Auth0 OAuth configuration
        """
        return cls(
            provider=OAuthProvider.AUTH0,
            client_id=client_id,
            client_secret=client_secret,
            authorization_endpoint=f"https://{auth0_domain}/authorize",
            token_endpoint=f"https://{auth0_domain}/oauth/token",
            userinfo_endpoint=f"https://{auth0_domain}/userinfo",
            jwks_uri=f"https://{auth0_domain}/.well-known/jwks.json",
            redirect_uri=redirect_uri,
            scopes=["openid", "email", "profile"]
        )


class OAuthClient:
    """Generic OAuth 2.0 client using Authlib.

    Supports:
    - Authorization Code Flow with PKCE
    - Token refresh
    - User profile retrieval
    - Claims mapping to local format

    Security features:
    - PKCE for all flows
    - State parameter for CSRF protection
    - Secure PKCE verifier storage
    """

    def __init__(self, config: OAuthConfig):
        """Initialize OAuth client.

        Args:
            config: OAuth configuration
        """
        self.config = config
        self._pkce_verifiers: Dict[str, str] = {}

    def generate_state(self) -> str:
        """Generate cryptographically secure state parameter.

        State parameter prevents CSRF attacks by ensuring authorization
        response matches authorization request.

        Returns:
            Secure random state string
        """
        return secrets.token_urlsafe(32)

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge (S256).

        PKCE (Proof Key for Code Exchange) protects against authorization
        code interception attacks.

        Returns:
            tuple: (code_verifier, code_challenge)
        """
        # Generate cryptographically secure verifier (43-128 chars)
        code_verifier = secrets.token_urlsafe(64)

        # Generate S256 challenge
        challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip("=")

        return code_verifier, code_challenge

    def get_authorization_url(
        self,
        state: Optional[str] = None,
        scopes: Optional[List[str]] = None
    ) -> tuple[str, str]:
        """Generate authorization URL with PKCE.

        Args:
            state: Optional state parameter (generated if None)
            scopes: Optional scopes (defaults to config.scopes)

        Returns:
            tuple: (authorization_url, state)
        """
        if state is None:
            state = self.generate_state()

        scopes = scopes or self.config.scopes

        # Generate PKCE pair
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Store verifier for token exchange
        self._pkce_verifiers[state] = code_verifier

        # Build authorization URL
        client = AsyncOAuth2Client(
            client_id=self.config.client_id,
            redirect_uri=self.config.redirect_uri,
            scope=" ".join(scopes)
        )

        authorization_url, _ = client.create_authorization_url(
            self.config.authorization_endpoint,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256"
        )

        return authorization_url, state

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens.

        Uses stored PKCE verifier for the given state.

        Args:
            code: Authorization code from callback
            state: State parameter from callback

        Returns:
            Token response containing access_token, refresh_token (if available), expires_in

        Raises:
            AuthenticationError: If token exchange fails
        """
        # Retrieve and remove PKCE verifier
        code_verifier = self._pkce_verifiers.pop(state, None)
        if not code_verifier:
            raise AuthenticationError("Invalid state parameter (PKCE verifier not found)")

        # Create OAuth client
        client = AsyncOAuth2Client(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            redirect_uri=self.config.redirect_uri
        )

        try:
            # Exchange code for tokens with PKCE verifier
            token = await client.fetch_token(
                self.config.token_endpoint,
                code=code,
                code_verifier=code_verifier
            )
            return token
        except Exception as e:
            raise AuthenticationError(f"Token exchange failed: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            New token response containing access_token

        Raises:
            AuthenticationError: If token refresh fails
        """
        client = AsyncOAuth2Client(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret
        )

        try:
            token = await client.refresh_token(
                self.config.token_endpoint,
                refresh_token=refresh_token
            )
            return token
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Fetch user info from provider's userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            User info from provider

        Raises:
            AuthenticationError: If userinfo call fails
        """
        if not self.config.userinfo_endpoint:
            raise ConfigurationError("No userinfo endpoint configured")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.config.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(f"Failed to fetch user info: {e}")

    def map_provider_claims_to_local(
        self,
        provider_claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map provider-specific claims to netrun-auth format.

        Default mappings:
        - Google: sub -> user_id, email, name
        - GitHub: id -> user_id, login -> username, email
        - Okta: sub -> user_id, email, name
        - Auth0: sub -> user_id, email, name

        Args:
            provider_claims: Claims from OAuth provider

        Returns:
            Claims in netrun-auth format
        """
        # Base mapping (works for most OIDC providers)
        local_claims = {
            "user_id": None,
            "email": None,
            "name": None,
            "username": None,
            "roles": [],
            "permissions": [],
            "provider": self.config.provider.value,
        }

        # Provider-specific mappings
        if self.config.provider == OAuthProvider.GOOGLE:
            local_claims.update({
                "user_id": provider_claims.get("sub"),
                "email": provider_claims.get("email"),
                "name": provider_claims.get("name"),
                "username": provider_claims.get("email"),
                "email_verified": provider_claims.get("email_verified", False),
                "picture": provider_claims.get("picture"),
            })

        elif self.config.provider == OAuthProvider.GITHUB:
            local_claims.update({
                "user_id": str(provider_claims.get("id")),
                "email": provider_claims.get("email"),
                "name": provider_claims.get("name"),
                "username": provider_claims.get("login"),
                "avatar_url": provider_claims.get("avatar_url"),
                "github_profile": provider_claims.get("html_url"),
            })

        elif self.config.provider in (OAuthProvider.OKTA, OAuthProvider.AUTH0):
            local_claims.update({
                "user_id": provider_claims.get("sub"),
                "email": provider_claims.get("email"),
                "name": provider_claims.get("name"),
                "username": provider_claims.get("preferred_username") or provider_claims.get("email"),
                "email_verified": provider_claims.get("email_verified", False),
            })

        else:
            # Generic OIDC mapping
            local_claims.update({
                "user_id": provider_claims.get("sub"),
                "email": provider_claims.get("email"),
                "name": provider_claims.get("name"),
                "username": provider_claims.get("preferred_username") or provider_claims.get("email"),
            })

        # Remove None values
        return {k: v for k, v in local_claims.items() if v is not None}


class OAuthManager:
    """Manage multiple OAuth providers.

    Allows registering multiple OAuth providers and retrieving
    the appropriate client for each provider.
    """

    def __init__(self):
        """Initialize OAuth manager."""
        self._clients: Dict[OAuthProvider, OAuthClient] = {}

    def register_provider(self, config: OAuthConfig) -> None:
        """Register an OAuth provider.

        Args:
            config: OAuth configuration for provider
        """
        self._clients[config.provider] = OAuthClient(config)

    def get_client(self, provider: OAuthProvider) -> OAuthClient:
        """Get OAuth client for provider.

        Args:
            provider: OAuth provider type

        Returns:
            OAuth client for provider

        Raises:
            ConfigurationError: If provider not registered
        """
        if provider not in self._clients:
            raise ConfigurationError(f"Provider {provider.value} not registered")
        return self._clients[provider]

    @property
    def available_providers(self) -> List[OAuthProvider]:
        """List of registered providers.

        Returns:
            List of registered OAuth provider types
        """
        return list(self._clients.keys())


# Singleton instance
_oauth_manager: Optional[OAuthManager] = None


def get_oauth_manager() -> OAuthManager:
    """Get or create OAuth manager singleton.

    Returns:
        Singleton OAuth manager instance
    """
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager


# FastAPI integration
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse


def create_oauth_router(
    oauth_manager: Optional[OAuthManager] = None,
    on_login_success: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
) -> APIRouter:
    """Create FastAPI router for OAuth endpoints.

    Creates:
    - GET /oauth/{provider}/authorize - Start OAuth flow
    - GET /oauth/{provider}/callback - Handle OAuth callback

    Args:
        oauth_manager: Optional OAuth manager (uses singleton if None)
        on_login_success: Optional callback to process successful login

    Returns:
        FastAPI router with OAuth endpoints
    """
    router = APIRouter(prefix="/oauth", tags=["oauth"])

    if oauth_manager is None:
        oauth_manager = get_oauth_manager()

    @router.get("/{provider}/authorize")
    async def oauth_authorize(provider: str, request: Request):
        """Start OAuth authorization flow.

        Args:
            provider: OAuth provider name (google, github, okta, auth0)
            request: FastAPI request

        Returns:
            Redirect to provider's authorization URL
        """
        try:
            # Parse provider
            provider_enum = OAuthProvider(provider.lower())

            # Get OAuth client
            client = oauth_manager.get_client(provider_enum)

            # Generate authorization URL
            auth_url, state = client.get_authorization_url()

            # Store state in session for validation
            request.session["oauth_state"] = state
            request.session["oauth_provider"] = provider

            return RedirectResponse(url=auth_url)

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {provider}. Available: {[p.value for p in oauth_manager.available_providers]}"
            )
        except ConfigurationError as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{provider}/callback")
    async def oauth_callback(
        provider: str,
        code: str,
        state: str,
        request: Request
    ):
        """Handle OAuth callback.

        Args:
            provider: OAuth provider name
            code: Authorization code
            state: State parameter for CSRF validation
            request: FastAPI request

        Returns:
            Token response or redirect with user info
        """
        try:
            # Validate state parameter
            stored_state = request.session.get("oauth_state")
            stored_provider = request.session.get("oauth_provider")

            if not stored_state or stored_state != state:
                raise HTTPException(status_code=400, detail="Invalid state parameter")

            if stored_provider != provider:
                raise HTTPException(status_code=400, detail="Provider mismatch")

            # Clear session
            request.session.pop("oauth_state", None)
            request.session.pop("oauth_provider", None)

            # Parse provider
            provider_enum = OAuthProvider(provider.lower())

            # Get OAuth client
            client = oauth_manager.get_client(provider_enum)

            # Exchange code for tokens
            tokens = await client.exchange_code_for_tokens(code, state)

            # Get user info
            user_info = await client.get_user_info(tokens["access_token"])

            # Map to local claims
            local_claims = client.map_provider_claims_to_local(user_info)

            # Call success callback if provided
            if on_login_success:
                result = on_login_success(local_claims)
                return result

            # Default: Return user info and tokens
            return {
                "user": local_claims,
                "tokens": tokens
            }

        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

    return router
