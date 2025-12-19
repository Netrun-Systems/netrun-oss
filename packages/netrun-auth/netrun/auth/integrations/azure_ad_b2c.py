"""
Azure AD B2C authentication integration for netrun-auth.

Provides comprehensive Azure AD B2C authentication support including:
- Authorization Code Flow with PKCE (web/SPA applications)
- User Flows (sign-up/sign-in, password reset, profile edit)
- Social identity provider support (Google, Facebook, etc.)
- Token validation with B2C-specific JWKS endpoints
- B2C-specific claims mapping (emails array, tfp, idp)
- Multi-tenant support for SaaS applications

Key differences from standard Azure AD:
- Uses b2clogin.com instead of login.microsoftonline.com
- JWKS endpoint includes user flow/policy name
- Claims include B2C-specific fields (emails[], tfp, idp)
- Supports social identity providers with idp_access_token

Security features:
- PKCE for all authorization flows (required for SPAs)
- JWKS caching for token validation performance
- Comprehensive token validation (signature, audience, issuer, expiration)
- Multi-tenant tenant ID validation
- State parameter for CSRF protection

Author: Netrun Systems
Version: 1.0.0
Date: 2025-12-07
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
import secrets
import hashlib
import base64
import logging

import httpx
from jwt import PyJWKClient
import jwt

from netrun.auth.exceptions import (
    TokenInvalidError,
    TokenExpiredError,
    AuthenticationError,
)

# Configure logging
logger = logging.getLogger(__name__)


class B2CUserFlow(str, Enum):
    """Azure AD B2C user flow types."""

    SIGNUP_SIGNIN = "signup_signin"
    PASSWORD_RESET = "password_reset"
    PROFILE_EDIT = "profile_edit"


@dataclass
class B2CUserFlowConfig:
    """Configuration for B2C user flows (policies).

    User flows define the authentication experience in Azure AD B2C.
    Each flow has a unique name that appears in the authority URL.

    Attributes:
        signup_signin: Combined sign-up and sign-in flow (e.g., "B2C_1_signup_signin")
        password_reset: Self-service password reset flow (e.g., "B2C_1_password_reset")
        profile_edit: Profile editing flow (e.g., "B2C_1_profile_edit")
    """
    signup_signin: str = "B2C_1_signup_signin"
    password_reset: str = "B2C_1_password_reset"
    profile_edit: str = "B2C_1_profile_edit"

    def get_policy(self, flow: B2CUserFlow) -> str:
        """Get policy name for a user flow type."""
        mapping = {
            B2CUserFlow.SIGNUP_SIGNIN: self.signup_signin,
            B2CUserFlow.PASSWORD_RESET: self.password_reset,
            B2CUserFlow.PROFILE_EDIT: self.profile_edit,
        }
        return mapping[flow]


@dataclass
class AzureADB2CConfig:
    """Azure AD B2C configuration.

    B2C uses a different URL structure than standard Azure AD:
    - Authority: https://{tenant_name}.b2clogin.com/{tenant_name}.onmicrosoft.com/{policy}
    - JWKS: https://{tenant_name}.b2clogin.com/{tenant_name}.onmicrosoft.com/{policy}/discovery/v2.0/keys

    Attributes:
        tenant_name: B2C tenant name (e.g., "netrunsystems" for netrunsystems.onmicrosoft.com)
        tenant_id: Azure AD tenant ID (GUID) - used for issuer validation
        client_id: Application (client) ID from Azure portal
        client_secret: Client secret (optional - not used for SPA/public clients)
        redirect_uri: OAuth callback URI
        scopes: Default scopes to request
        user_flows: User flow configuration
    """
    tenant_name: str
    client_id: str
    tenant_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: str = "http://localhost:3000"
    scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    user_flows: B2CUserFlowConfig = field(default_factory=B2CUserFlowConfig)

    # Cache settings
    jwks_cache_ttl: int = 600  # 10 minutes
    jwks_rate_limit: int = 10  # requests per minute

    def get_authority(self, flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN) -> str:
        """Get the authority URL for a specific user flow.

        Args:
            flow: User flow type

        Returns:
            B2C authority URL
        """
        policy = self.user_flows.get_policy(flow)
        return f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com/{policy}"

    def get_jwks_uri(self, flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN) -> str:
        """Get the JWKS endpoint URI for a specific user flow.

        Args:
            flow: User flow type

        Returns:
            B2C JWKS endpoint URL
        """
        policy = self.user_flows.get_policy(flow)
        return f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com/{policy}/discovery/v2.0/keys"

    def get_issuer(self) -> str:
        """Get the expected token issuer.

        Returns:
            B2C issuer URL (uses tenant_id if available, otherwise tenant_name)
        """
        if self.tenant_id:
            return f"https://{self.tenant_name}.b2clogin.com/{self.tenant_id}/v2.0/"
        return f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com/v2.0/"


@dataclass
class B2CTokenClaims:
    """Azure AD B2C token claims.

    B2C tokens have specific claims that differ from standard Azure AD:
    - emails: Array of email addresses (B2C-specific)
    - tfp: Trust framework policy (user flow name)
    - idp: Identity provider (local, google, facebook, etc.)
    - idp_access_token: Access token from social provider (if configured)

    Standard OIDC claims:
    - oid: Object ID (unique user identifier in B2C)
    - sub: Subject (alternative user identifier)
    - name: Display name
    - given_name: First name
    - family_name: Last name
    """
    # Required identifiers
    oid: Optional[str] = None  # Object ID (primary identifier)
    sub: Optional[str] = None  # Subject (fallback identifier)

    # User profile
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None

    # Email - B2C uses array, standard uses string
    emails: Optional[List[str]] = None
    email: Optional[str] = None

    # B2C-specific claims
    tfp: Optional[str] = None  # Trust framework policy
    acr: Optional[str] = None  # Auth context class reference
    idp: Optional[str] = None  # Identity provider
    idp_access_token: Optional[str] = None  # Social provider token

    # Token metadata
    aud: Optional[str] = None  # Audience
    iss: Optional[str] = None  # Issuer
    iat: Optional[int] = None  # Issued at
    exp: Optional[int] = None  # Expiration
    nbf: Optional[int] = None  # Not before
    nonce: Optional[str] = None  # Replay prevention
    auth_time: Optional[int] = None  # Time of authentication

    # Custom B2C attributes (extension_*)
    extension_Role: Optional[str] = None
    extension_Department: Optional[str] = None
    extension_OrganizationId: Optional[str] = None

    # Raw claims for custom attributes
    _raw_claims: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, claims: Dict[str, Any]) -> "B2CTokenClaims":
        """Create B2CTokenClaims from a dictionary of claims.

        Args:
            claims: Dictionary of JWT claims

        Returns:
            B2CTokenClaims instance
        """
        return cls(
            oid=claims.get("oid"),
            sub=claims.get("sub"),
            name=claims.get("name"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            emails=claims.get("emails"),
            email=claims.get("email"),
            tfp=claims.get("tfp"),
            acr=claims.get("acr"),
            idp=claims.get("idp"),
            idp_access_token=claims.get("idp_access_token"),
            aud=claims.get("aud"),
            iss=claims.get("iss"),
            iat=claims.get("iat"),
            exp=claims.get("exp"),
            nbf=claims.get("nbf"),
            nonce=claims.get("nonce"),
            auth_time=claims.get("auth_time"),
            extension_Role=claims.get("extension_Role"),
            extension_Department=claims.get("extension_Department"),
            extension_OrganizationId=claims.get("extension_OrganizationId"),
            _raw_claims=claims,
        )

    @property
    def user_id(self) -> Optional[str]:
        """Get the primary user identifier (oid preferred, sub fallback)."""
        return self.oid or self.sub

    @property
    def primary_email(self) -> Optional[str]:
        """Get the primary email (from emails array or email claim)."""
        if self.emails and len(self.emails) > 0:
            return self.emails[0]
        return self.email

    @property
    def display_name(self) -> str:
        """Get display name with fallbacks."""
        return self.name or self.given_name or "User"

    @property
    def identity_provider(self) -> str:
        """Get the identity provider name."""
        return self.idp or "local"

    @property
    def is_social_login(self) -> bool:
        """Check if user authenticated via social provider."""
        return self.idp is not None and self.idp != "local"

    def get_extension(self, name: str) -> Optional[Any]:
        """Get a custom B2C extension attribute.

        Args:
            name: Extension name (with or without "extension_" prefix)

        Returns:
            Extension value or None
        """
        # Normalize name
        if not name.startswith("extension_"):
            name = f"extension_{name}"
        return self._raw_claims.get(name)


class AzureADB2CClient:
    """Azure AD B2C authentication client.

    Supports B2C-specific OAuth 2.0 flows:
    - Authorization Code Flow with PKCE (web/SPA applications)
    - User flow switching (sign-up, password reset, profile edit)

    Key features:
    - B2C-specific JWKS endpoint handling
    - Social identity provider support
    - Claims mapping with B2C-specific fields
    - Multi-tenant support

    Example:
        ```python
        config = AzureADB2CConfig(
            tenant_name="netrunsystems",
            client_id="your-client-id",
            tenant_id="your-tenant-id",
        )
        client = AzureADB2CClient(config)

        # Validate a token
        claims = await client.validate_token(token)
        print(f"User: {claims.display_name} ({claims.primary_email})")
        ```
    """

    def __init__(self, config: AzureADB2CConfig):
        """Initialize Azure AD B2C client.

        Args:
            config: B2C configuration
        """
        self.config = config
        self._jwks_clients: Dict[str, PyJWKClient] = {}
        self._pkce_verifiers: Dict[str, str] = {}

    def _get_jwks_client(self, flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN) -> PyJWKClient:
        """Get or create JWKS client for a user flow.

        Each user flow has its own JWKS endpoint, so we cache clients per flow.

        Args:
            flow: User flow type

        Returns:
            PyJWKClient for the specified flow
        """
        flow_key = flow.value
        if flow_key not in self._jwks_clients:
            jwks_uri = self.config.get_jwks_uri(flow)
            self._jwks_clients[flow_key] = PyJWKClient(
                jwks_uri,
                cache_keys=True,
                lifespan=self.config.jwks_cache_ttl,
            )
        return self._jwks_clients[flow_key]

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge (S256).

        PKCE is required for B2C SPA applications and recommended for all.

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
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        redirect_uri: Optional[str] = None,
        prompt: Optional[str] = None,
        ui_locales: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """Generate authorization URL for B2C user flow.

        Args:
            flow: User flow type (signup_signin, password_reset, profile_edit)
            state: Optional state parameter for CSRF protection (auto-generated if None)
            nonce: Optional nonce for replay prevention (auto-generated if None)
            scopes: Optional scopes to request (defaults to config.scopes)
            redirect_uri: Optional redirect URI (defaults to config.redirect_uri)
            prompt: Optional prompt behavior (login, none, consent)
            ui_locales: Optional UI locale (e.g., "en-US", "es-ES")

        Returns:
            tuple: (authorization_url, state, nonce)
        """
        # Generate state and nonce if not provided
        if state is None:
            state = secrets.token_urlsafe(32)
        if nonce is None:
            nonce = secrets.token_urlsafe(32)

        scopes = scopes or self.config.scopes
        redirect_uri = redirect_uri or self.config.redirect_uri

        # Generate PKCE pair
        code_verifier, code_challenge = self._generate_pkce_pair()
        self._pkce_verifiers[state] = code_verifier

        # Build authorization URL
        authority = self.config.get_authority(flow)

        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "nonce": nonce,
            "response_mode": "query",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if prompt:
            params["prompt"] = prompt
        if ui_locales:
            params["ui_locales"] = ui_locales

        # Build URL
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{authority}/oauth2/v2.0/authorize?{query_string}"

        return auth_url, state, nonce

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
        redirect_uri: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            state: State parameter from callback (used to retrieve PKCE verifier)
            flow: User flow type
            redirect_uri: Redirect URI (must match authorization request)
            scopes: Scopes to request

        Returns:
            Token response containing access_token, id_token, refresh_token

        Raises:
            AuthenticationError: If token exchange fails
        """
        # Retrieve PKCE verifier
        code_verifier = self._pkce_verifiers.pop(state, None)
        if not code_verifier:
            raise AuthenticationError(
                "Invalid state parameter - PKCE verifier not found",
                error_code="B2C_INVALID_STATE",
            )

        redirect_uri = redirect_uri or self.config.redirect_uri
        scopes = scopes or self.config.scopes

        # Build token request
        authority = self.config.get_authority(flow)
        token_url = f"{authority}/oauth2/v2.0/token"

        data = {
            "client_id": self.config.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "code_verifier": code_verifier,
        }

        # Add client secret if configured (confidential client)
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                result = response.json()

                if "error" in result:
                    error_desc = result.get("error_description", result["error"])
                    logger.error(f"B2C token exchange failed: {error_desc}")
                    raise AuthenticationError(
                        f"Token exchange failed: {error_desc}",
                        error_code="B2C_TOKEN_EXCHANGE_FAILED",
                    )

                return result

            except httpx.HTTPError as e:
                logger.error(f"B2C token request failed: {e}")
                raise AuthenticationError(
                    f"Token request failed: {e}",
                    error_code="B2C_TOKEN_REQUEST_FAILED",
                )

    async def validate_token(
        self,
        token: str,
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
        validate_audience: bool = True,
        validate_issuer: bool = True,
        clock_tolerance: int = 60,
    ) -> B2CTokenClaims:
        """Validate B2C token and extract claims.

        Validates:
        - Signature using JWKS (B2C-specific endpoint)
        - Token expiration
        - Audience (client_id)
        - Issuer (B2C issuer URL)

        Args:
            token: JWT access token or ID token from B2C
            flow: User flow that issued the token
            validate_audience: Whether to validate audience claim
            validate_issuer: Whether to validate issuer claim
            clock_tolerance: Allowed clock skew in seconds

        Returns:
            Validated B2C token claims

        Raises:
            TokenExpiredError: If token is expired
            TokenInvalidError: If token validation fails
        """
        try:
            # Get signing key from B2C JWKS endpoint
            jwks_client = self._get_jwks_client(flow)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Build verification options
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_aud": validate_audience,
                "verify_iss": validate_issuer,
            }

            # Expected audience and issuer
            audience = self.config.client_id if validate_audience else None
            issuer = self.config.get_issuer() if validate_issuer else None

            # Decode and validate token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
                options=options,
                leeway=clock_tolerance,
            )

            # Create typed claims object
            b2c_claims = B2CTokenClaims.from_dict(claims)

            # Validate required claims
            if not b2c_claims.user_id:
                raise TokenInvalidError(
                    "Missing required identity claims (oid/sub)",
                    error_code="B2C_MISSING_IDENTITY",
                )

            logger.debug(f"B2C token validated for user: {b2c_claims.user_id}")
            return b2c_claims

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError(
                "B2C token has expired",
                error_code="B2C_TOKEN_EXPIRED",
            )
        except jwt.InvalidAudienceError:
            raise TokenInvalidError(
                "Invalid token audience",
                error_code="B2C_INVALID_AUDIENCE",
            )
        except jwt.InvalidIssuerError:
            raise TokenInvalidError(
                "Invalid token issuer",
                error_code="B2C_INVALID_ISSUER",
            )
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(
                f"Invalid B2C token: {e}",
                error_code="B2C_INVALID_TOKEN",
            )
        except Exception as e:
            logger.error(f"B2C token validation failed: {e}")
            raise TokenInvalidError(
                f"Token validation failed: {e}",
                error_code="B2C_VALIDATION_FAILED",
            )

    async def refresh_token(
        self,
        refresh_token: str,
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
        scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous token response
            flow: User flow type
            scopes: Scopes to request (defaults to config.scopes)

        Returns:
            New token response

        Raises:
            AuthenticationError: If refresh fails
        """
        scopes = scopes or self.config.scopes
        authority = self.config.get_authority(flow)
        token_url = f"{authority}/oauth2/v2.0/token"

        data = {
            "client_id": self.config.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(scopes),
        }

        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                result = response.json()

                if "error" in result:
                    error_desc = result.get("error_description", result["error"])
                    raise AuthenticationError(
                        f"Token refresh failed: {error_desc}",
                        error_code="B2C_REFRESH_FAILED",
                    )

                return result

            except httpx.HTTPError as e:
                raise AuthenticationError(
                    f"Token refresh request failed: {e}",
                    error_code="B2C_REFRESH_REQUEST_FAILED",
                )

    def map_claims_to_local(
        self,
        claims: B2CTokenClaims,
        role_mapping: Optional[Dict[str, str]] = None,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Map B2C claims to netrun-auth claims format.

        B2C claims → netrun-auth format:
        - oid/sub → user_id
        - emails[0]/email → email
        - name → name
        - idp → identity_provider
        - extension_Role → roles (mapped)
        - extension_OrganizationId → organization_id

        Args:
            claims: B2C token claims
            role_mapping: Optional mapping of B2C roles to local roles
            organization_id: Optional organization ID override

        Returns:
            Claims in netrun-auth format
        """
        # Map roles
        roles = []
        if claims.extension_Role:
            if role_mapping and claims.extension_Role in role_mapping:
                roles.append(role_mapping[claims.extension_Role])
            else:
                roles.append(claims.extension_Role)

        # Determine organization
        org_id = organization_id or claims.extension_OrganizationId

        return {
            "user_id": claims.user_id,
            "email": claims.primary_email,
            "name": claims.display_name,
            "given_name": claims.given_name,
            "family_name": claims.family_name,
            "roles": roles,
            "permissions": [],  # Populate based on roles in application
            "organization_id": org_id,
            "identity_provider": claims.identity_provider,
            "is_social_login": claims.is_social_login,
            "b2c_object_id": claims.oid,
            "b2c_policy": claims.tfp,
            "auth_time": claims.auth_time,
        }

    def get_password_reset_url(
        self,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """Get URL for password reset flow.

        Args:
            state: Optional state parameter
            redirect_uri: Optional redirect URI

        Returns:
            tuple: (url, state, nonce)
        """
        return self.get_authorization_url(
            flow=B2CUserFlow.PASSWORD_RESET,
            state=state,
            redirect_uri=redirect_uri,
        )

    def get_profile_edit_url(
        self,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """Get URL for profile edit flow.

        Args:
            state: Optional state parameter
            redirect_uri: Optional redirect URI

        Returns:
            tuple: (url, state, nonce)
        """
        return self.get_authorization_url(
            flow=B2CUserFlow.PROFILE_EDIT,
            state=state,
            redirect_uri=redirect_uri,
        )

    def is_password_reset_error(self, error_description: str) -> bool:
        """Check if error indicates user clicked 'Forgot password'.

        B2C returns AADB2C90118 when user clicks forgot password link
        in the sign-in UI. Application should redirect to password reset flow.

        Args:
            error_description: Error description from B2C

        Returns:
            True if this is a password reset request
        """
        return "AADB2C90118" in error_description

    def is_cancelled_error(self, error_description: str) -> bool:
        """Check if user cancelled the authentication.

        B2C returns AADB2C90091 when user clicks cancel button.

        Args:
            error_description: Error description from B2C

        Returns:
            True if user cancelled
        """
        return "AADB2C90091" in error_description


# FastAPI integration helpers
_b2c_client: Optional[AzureADB2CClient] = None


def initialize_b2c(config: AzureADB2CConfig) -> AzureADB2CClient:
    """Initialize Azure AD B2C client singleton.

    Args:
        config: B2C configuration

    Returns:
        Initialized B2C client
    """
    global _b2c_client
    _b2c_client = AzureADB2CClient(config)
    logger.info(f"Azure AD B2C client initialized for tenant: {config.tenant_name}")
    return _b2c_client


def get_b2c_client() -> AzureADB2CClient:
    """FastAPI dependency to get B2C client.

    Returns:
        Singleton B2C client instance

    Raises:
        RuntimeError: If client not initialized
    """
    if _b2c_client is None:
        raise RuntimeError("B2C client not initialized. Call initialize_b2c() first.")
    return _b2c_client


async def get_current_user_b2c(
    token: str,
    b2c_client: Optional[AzureADB2CClient] = None,
    flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
) -> Dict[str, Any]:
    """FastAPI dependency to validate B2C token and get user.

    Args:
        token: Bearer token from Authorization header
        b2c_client: Optional B2C client (uses singleton if None)
        flow: User flow that issued the token

    Returns:
        User claims in netrun-auth format

    Raises:
        TokenInvalidError: If token validation fails
        TokenExpiredError: If token is expired
    """
    if b2c_client is None:
        b2c_client = get_b2c_client()

    # Validate token and get claims
    claims = await b2c_client.validate_token(token, flow=flow)

    # Map to local format
    return b2c_client.map_claims_to_local(claims)


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract Bearer token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Token string or None
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


def is_b2c_configured() -> bool:
    """Check if B2C client is configured and initialized.

    Returns:
        True if B2C is ready to use
    """
    return _b2c_client is not None
