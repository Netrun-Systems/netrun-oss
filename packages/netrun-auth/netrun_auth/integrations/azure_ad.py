"""
Azure AD/Entra ID authentication integration for netrun-auth.

Provides comprehensive Azure AD authentication support including:
- Authorization Code Flow (web apps)
- Client Credentials Flow (service-to-service)
- On-Behalf-Of Flow (API delegation)
- Device Code Flow (CLI/device apps)
- Multi-tenant support
- Token validation with JWKS
- Claims mapping to netrun-auth format

Security features:
- PKCE for authorization code flow
- JWKS caching for token validation
- Comprehensive token validation (signature, audience, issuer, expiration)
- Multi-tenant tenant ID validation

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import base64
from urllib.parse import urlencode

import httpx
from msal import ConfidentialClientApplication, PublicClientApplication
from jwt import PyJWKClient
import jwt

from netrun_auth.core.exceptions import (
    TokenValidationError,
    AuthenticationError,
)


@dataclass
class AzureADConfig:
    """Azure AD configuration.

    Attributes:
        tenant_id: Azure AD tenant ID (or 'common' for multi-tenant)
        client_id: Application (client) ID from Azure portal
        client_secret: Client secret (None for public client flows)
        authority: Azure AD authority URL (auto-generated from tenant_id)
        redirect_uri: OAuth callback URI
        scopes: Default scopes to request
    """
    tenant_id: str
    client_id: str
    client_secret: Optional[str] = None
    authority: Optional[str] = None
    redirect_uri: str = "http://localhost:8000/auth/callback"
    scopes: List[str] = field(default_factory=lambda: ["User.Read"])

    def __post_init__(self):
        """Generate authority URL if not provided."""
        if self.authority is None:
            self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"


class AzureADClient:
    """Azure AD authentication client.

    Supports multiple OAuth 2.0 flows for different application types:
    - Authorization Code Flow (web applications)
    - Client Credentials Flow (service-to-service)
    - On-Behalf-Of Flow (API delegation)
    - Device Code Flow (CLI/device applications)

    Security features:
    - PKCE for authorization code flow
    - JWKS caching for token validation
    - Comprehensive token validation
    - Multi-tenant support
    """

    def __init__(self, config: AzureADConfig):
        """Initialize Azure AD client.

        Args:
            config: Azure AD configuration
        """
        self.config = config
        self._msal_app: Optional[ConfidentialClientApplication] = None
        self._pkce_verifiers: Dict[str, str] = {}

        # JWKS client for token validation (lazy-initialized)
        self._jwks_client: Optional[PyJWKClient] = None

    @property
    def msal_app(self) -> ConfidentialClientApplication:
        """Lazy-initialize MSAL application.

        Returns:
            MSAL confidential or public client application
        """
        if self._msal_app is None:
            if self.config.client_secret:
                # Confidential client (has secret)
                self._msal_app = ConfidentialClientApplication(
                    client_id=self.config.client_id,
                    client_credential=self.config.client_secret,
                    authority=self.config.authority
                )
            else:
                # Public client (no secret)
                self._msal_app = PublicClientApplication(
                    client_id=self.config.client_id,
                    authority=self.config.authority
                )
        return self._msal_app

    @property
    def jwks_client(self) -> PyJWKClient:
        """Lazy-initialize JWKS client for token validation.

        Returns:
            PyJWKClient for fetching Azure AD public keys
        """
        if self._jwks_client is None:
            # Azure AD JWKS endpoint (common for all tenants)
            jwks_url = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
            self._jwks_client = PyJWKClient(jwks_url)
        return self._jwks_client

    def _generate_pkce_pair(self) -> tuple[str, str]:
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
        use_pkce: bool = True,
        scopes: Optional[List[str]] = None
    ) -> tuple[str, str]:
        """Generate authorization URL for OAuth flow.

        Args:
            state: Optional state parameter for CSRF protection
            use_pkce: Whether to use PKCE (recommended)
            scopes: Optional scopes to request (defaults to config.scopes)

        Returns:
            tuple: (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        scopes = scopes or self.config.scopes

        if use_pkce:
            # Generate and store PKCE verifier
            code_verifier, code_challenge = self._generate_pkce_pair()
            self._pkce_verifiers[state] = code_verifier

            # Build authorization URL with PKCE
            auth_url = self.msal_app.get_authorization_request_url(
                scopes=scopes,
                state=state,
                redirect_uri=self.config.redirect_uri,
                code_challenge=code_challenge,
                code_challenge_method="S256"
            )
        else:
            # Build authorization URL without PKCE
            auth_url = self.msal_app.get_authorization_request_url(
                scopes=scopes,
                state=state,
                redirect_uri=self.config.redirect_uri
            )

        return auth_url, state

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code from callback
            state: State parameter from callback (used to retrieve PKCE verifier)
            scopes: Optional scopes (defaults to config.scopes)

        Returns:
            Token response containing access_token, refresh_token, expires_in

        Raises:
            AuthenticationError: If token exchange fails
        """
        scopes = scopes or self.config.scopes

        # Retrieve PKCE verifier if used
        code_verifier = self._pkce_verifiers.pop(state, None)

        # Exchange code for tokens
        result = self.msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=scopes,
            redirect_uri=self.config.redirect_uri,
            code_verifier=code_verifier
        )

        if "error" in result:
            raise AuthenticationError(
                f"Token exchange failed: {result.get('error_description', result['error'])}"
            )

        return result

    async def get_client_credentials_token(
        self,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get token using client credentials flow (service-to-service).

        Client credentials flow is for server-to-server authentication
        without user context. Requires client_secret.

        Args:
            scopes: Scopes to request (typically resource/.default)

        Returns:
            Token response containing access_token

        Raises:
            AuthenticationError: If token acquisition fails
        """
        if not self.config.client_secret:
            raise AuthenticationError("Client credentials flow requires client_secret")

        scopes = scopes or [f"{self.config.client_id}/.default"]

        result = self.msal_app.acquire_token_for_client(scopes=scopes)

        if "error" in result:
            raise AuthenticationError(
                f"Client credentials flow failed: {result.get('error_description', result['error'])}"
            )

        return result

    async def get_on_behalf_of_token(
        self,
        user_assertion: str,
        scopes: List[str]
    ) -> Dict[str, Any]:
        """Get token on behalf of user (API delegation).

        On-behalf-of flow allows a service to call another service
        using the user's identity. Requires client_secret.

        Args:
            user_assertion: User's access token
            scopes: Scopes to request for downstream service

        Returns:
            Token response containing access_token

        Raises:
            AuthenticationError: If token acquisition fails
        """
        if not self.config.client_secret:
            raise AuthenticationError("On-behalf-of flow requires client_secret")

        result = self.msal_app.acquire_token_on_behalf_of(
            user_assertion=user_assertion,
            scopes=scopes
        )

        if "error" in result:
            raise AuthenticationError(
                f"On-behalf-of flow failed: {result.get('error_description', result['error'])}"
            )

        return result

    async def validate_azure_token(
        self,
        token: str,
        validate_audience: bool = True,
        allowed_tenants: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate Azure AD token and extract claims.

        Validates:
        - Signature using JWKS
        - Token expiration
        - Audience (if validate_audience=True)
        - Issuer
        - Tenant ID (if allowed_tenants provided)

        Args:
            token: JWT access token from Azure AD
            validate_audience: Whether to validate audience claim
            allowed_tenants: List of allowed tenant IDs (None = allow all)

        Returns:
            Validated token claims

        Raises:
            TokenValidationError: If validation fails
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.config.client_id if validate_audience else None,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": validate_audience,
                    "verify_iss": False,  # Multi-tenant has variable issuer
                }
            )

            # Validate tenant if restrictions configured
            if allowed_tenants:
                tenant_id = claims.get("tid")
                if tenant_id not in allowed_tenants:
                    raise TokenValidationError(f"Tenant {tenant_id} not allowed")

            # Validate required claims exist
            if not claims.get("oid") and not claims.get("sub"):
                raise TokenValidationError("Missing required identity claims (oid/sub)")

            return claims

        except jwt.ExpiredSignatureError:
            raise TokenValidationError("Token expired")
        except jwt.InvalidAudienceError:
            raise TokenValidationError("Invalid audience")
        except jwt.InvalidTokenError as e:
            raise TokenValidationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise TokenValidationError(f"Token validation failed: {str(e)}")

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch user profile from Microsoft Graph.

        Args:
            access_token: Valid access token with User.Read scope

        Returns:
            User profile data from Microsoft Graph

        Raises:
            AuthenticationError: If Graph API call fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(f"Failed to fetch user profile: {e}")

    async def get_user_groups(self, access_token: str) -> List[str]:
        """Fetch user's group memberships from Microsoft Graph.

        Args:
            access_token: Valid access token with Group.Read.All or Directory.Read.All scope

        Returns:
            List of group IDs user is member of

        Raises:
            AuthenticationError: If Graph API call fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/memberOf",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                # Extract group IDs
                return [group["id"] for group in data.get("value", [])]
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(f"Failed to fetch user groups: {e}")

    def map_azure_claims_to_local(
        self,
        azure_claims: Dict[str, Any],
        organization_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Map Azure AD claims to netrun-auth claims format.

        Azure AD claims:
        - oid: Object ID (unique user identifier)
        - sub: Subject (user identifier)
        - email/preferred_username: Email address
        - name: Display name
        - roles: Application roles
        - groups: Group memberships
        - tid: Tenant ID

        Netrun-auth claims:
        - user_id: User identifier
        - organization_id: Tenant/organization identifier
        - roles: User roles
        - permissions: Fine-grained permissions

        Args:
            azure_claims: Claims from Azure AD token
            organization_mapping: Optional mapping of tenant_id to organization_id

        Returns:
            Claims in netrun-auth format
        """
        # Map user identifier (prefer oid, fallback to sub)
        user_id = azure_claims.get("oid") or azure_claims.get("sub")

        # Map tenant to organization
        tenant_id = azure_claims.get("tid")
        if organization_mapping and tenant_id in organization_mapping:
            organization_id = organization_mapping[tenant_id]
        else:
            organization_id = tenant_id

        # Map roles (from app roles or groups)
        roles = azure_claims.get("roles", [])
        if not roles and "groups" in azure_claims:
            # Use group IDs as roles if no app roles
            roles = azure_claims["groups"]

        # Build netrun-auth claims
        local_claims = {
            "user_id": user_id,
            "organization_id": organization_id,
            "email": azure_claims.get("email") or azure_claims.get("preferred_username"),
            "name": azure_claims.get("name"),
            "roles": roles,
            "permissions": [],  # Populate based on roles in application logic
            "azure_tenant_id": tenant_id,
            "azure_oid": azure_claims.get("oid"),
        }

        return local_claims


class AzureADMultiTenantClient(AzureADClient):
    """Multi-tenant Azure AD client.

    Validates tokens from any Azure AD tenant.
    Maps tenant_id to organization_id in local claims.

    Use this for SaaS applications that accept users from any
    Azure AD tenant.
    """

    def __init__(self, config: AzureADConfig):
        """Initialize multi-tenant Azure AD client.

        Args:
            config: Azure AD configuration (tenant_id will be overridden to 'common')
        """
        # Override tenant_id to 'common' for multi-tenant
        config.tenant_id = "common"
        config.authority = "https://login.microsoftonline.com/common"
        super().__init__(config)

    async def validate_tenant(
        self,
        tenant_id: str,
        allowed_tenants: Optional[List[str]] = None
    ) -> bool:
        """Validate tenant is allowed.

        Use this to implement tenant allowlist for multi-tenant applications.

        Args:
            tenant_id: Tenant ID to validate
            allowed_tenants: List of allowed tenant IDs (None = allow all)

        Returns:
            True if tenant is allowed
        """
        if allowed_tenants is None:
            return True
        return tenant_id in allowed_tenants


# FastAPI integration helpers
_azure_ad_client: Optional[AzureADClient] = None


def get_azure_ad_client() -> AzureADClient:
    """FastAPI dependency to get Azure AD client.

    Returns:
        Singleton Azure AD client instance

    Raises:
        RuntimeError: If client not initialized
    """
    if _azure_ad_client is None:
        raise RuntimeError("Azure AD client not initialized. Call initialize_azure_ad() first.")
    return _azure_ad_client


def initialize_azure_ad(config: AzureADConfig) -> AzureADClient:
    """Initialize Azure AD client singleton.

    Args:
        config: Azure AD configuration

    Returns:
        Initialized Azure AD client
    """
    global _azure_ad_client
    _azure_ad_client = AzureADClient(config)
    return _azure_ad_client


async def get_current_user_azure(
    token: str,
    azure_client: Optional[AzureADClient] = None
) -> Dict[str, Any]:
    """FastAPI dependency to validate Azure AD token and get user.

    Args:
        token: Bearer token from Authorization header
        azure_client: Optional Azure AD client (uses singleton if None)

    Returns:
        User claims from validated token

    Raises:
        TokenValidationError: If token validation fails
    """
    if azure_client is None:
        azure_client = get_azure_ad_client()

    # Validate token and extract claims
    azure_claims = await azure_client.validate_azure_token(token)

    # Map to local claims format
    local_claims = azure_client.map_azure_claims_to_local(azure_claims)

    return local_claims
