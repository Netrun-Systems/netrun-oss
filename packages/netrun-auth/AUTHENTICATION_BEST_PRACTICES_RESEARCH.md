# Authentication Best Practices Research Report

**Service**: #59 Unified Authentication
**Version**: 1.0
**Research Date**: November 25, 2025
**Researcher**: Research Agent (Technical Research Specialist)
**SDLC Compliance**: v2.1

---

## Executive Summary

This research report provides comprehensive findings on Python authentication best practices for designing Service #59 Unified Authentication. The research covers FastAPI security patterns, Azure AD/Entra ID integration, JWT token handling, OAuth 2.0/OIDC implementations, and session management strategies.

**Key Recommendations:**
1. Use **PyJWT** (not python-jose) with **RS256** asymmetric signing
2. Implement **Authlib** for OAuth 2.0/OIDC server-side capabilities
3. Use **MSAL** + **Azure Identity** for Azure AD integration with managed identities
4. Adopt **Double Submit Cookie** pattern for CSRF protection
5. Use **Redis-backed sessions** for stateful authentication when needed

---

## Table of Contents

1. [Library Comparison Matrix](#1-library-comparison-matrix)
2. [Recommended Technology Stack](#2-recommended-technology-stack)
3. [FastAPI Security Patterns](#3-fastapi-security-patterns)
4. [Azure AD / Entra ID Integration](#4-azure-ad--entra-id-integration)
5. [JWT Best Practices](#5-jwt-best-practices)
6. [OAuth 2.0 / OIDC Patterns](#6-oauth-20--oidc-patterns)
7. [Session Management](#7-session-management)
8. [OWASP API Security Top 10](#8-owasp-api-security-top-10)
9. [API Design Recommendations](#9-api-design-recommendations)
10. [Security Considerations](#10-security-considerations)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Sources](#12-sources)

---

## 1. Library Comparison Matrix

### Authentication Library Comparison

| Feature | FastAPI-Users | Authlib | Custom Implementation |
|---------|--------------|---------|----------------------|
| **Maintenance Status** | Maintenance Mode (security updates only) | Active Development | N/A |
| **OAuth 2.0 Server** | No | Yes (full RFC compliance) | Build from scratch |
| **OIDC Support** | Limited | Full (20+ RFCs) | Build from scratch |
| **JWT Handling** | Via dependency | Built-in JWS/JWE/JWK | PyJWT/python-jose |
| **Database Adapters** | SQLAlchemy, MongoDB | Agnostic | Custom |
| **Azure AD Integration** | Via OAuth | Via OAuth | MSAL direct |
| **PKCE Support** | Limited | Full S256 support | Manual |
| **Session Management** | Redis, DB, JWT | Cookie-based | Redis/custom |
| **Multi-tenant** | Limited | Flexible | Full control |
| **Learning Curve** | Low | Medium | High |
| **Customization** | Medium | High | Full |
| **Production Readiness** | Good | Excellent | Depends on team |

### JWT Library Comparison

| Feature | PyJWT | python-jose | Authlib JWT |
|---------|-------|-------------|-------------|
| **Maintenance Status** | Active (Recommended) | Barely Maintained | Active |
| **Security** | High | Lower (less maintained) | High |
| **Algorithm Support** | HS256, RS256, ES256, EdDSA | Full JOSE | Full JOSE |
| **JWE (Encryption)** | No | Yes | Yes |
| **JWK Support** | Via cryptography | Yes | Yes |
| **Drop-in Replacement** | N/A | PyJWT compatible | Different API |
| **Performance** | Good | Good | Good |
| **Documentation** | Excellent | Good | Excellent |

**Recommendation**: Use **PyJWT** for JWT operations. python-jose is barely maintained and less secure. If JWE (encryption) is needed, use Authlib's JWT module or jwcrypto.

### Azure Authentication Library Comparison

| Feature | MSAL Python | Azure Identity | Direct HTTP |
|---------|------------|----------------|-------------|
| **Token Caching** | Built-in | Built-in | Manual |
| **Managed Identity** | Yes | Yes (DefaultAzureCredential) | Manual |
| **Multi-tenant** | Excellent | Good | Full control |
| **PKCE Support** | Yes | N/A (credential flows) | Manual |
| **Token Refresh** | Automatic | Automatic | Manual |
| **B2C Support** | Yes | Limited | Full control |
| **Service Principal** | Yes | Yes | Manual |
| **Workload Identity (AKS)** | Yes | Yes | Manual |

**Recommendation**: Use **MSAL** for user authentication flows and **Azure Identity (DefaultAzureCredential)** for service-to-service authentication with managed identities.

---

## 2. Recommended Technology Stack

### Core Authentication Stack

```
+------------------------------------------------------------------+
|                    Service #59 Unified Auth                       |
+------------------------------------------------------------------+
|  Framework     |  FastAPI + Starlette                            |
|  JWT Library   |  PyJWT (with cryptography for RS256)            |
|  OAuth/OIDC    |  Authlib (server + client)                      |
|  Azure Auth    |  MSAL Python + Azure Identity                   |
|  Session Store |  Redis (production) / Memory (development)      |
|  Password Hash |  Argon2 (via pwdlib or argon2-cffi)             |
|  CSRF          |  fastapi-csrf-protect                           |
|  Rate Limit    |  fastapi-limiter (Redis-backed)                 |
+------------------------------------------------------------------+
```

### Package Requirements

```toml
# pyproject.toml - Authentication dependencies
[project.dependencies]
fastapi = ">=0.109.0"
pyjwt = {version = ">=2.8.0", extras = ["crypto"]}
authlib = ">=1.3.0"
msal = ">=1.26.0"
azure-identity = ">=1.15.0"
redis = ">=5.0.0"
pwdlib = {version = ">=0.2.0", extras = ["argon2"]}
httpx = ">=0.26.0"

[project.optional-dependencies]
csrf = ["fastapi-csrf-protect>=0.3.0"]
ratelimit = ["fastapi-limiter>=0.1.6"]
```

### Why This Stack?

1. **PyJWT over python-jose**: python-jose is barely maintained and has security concerns. PyJWT is actively maintained and works as a drop-in replacement.

2. **Authlib over FastAPI-Users**: FastAPI-Users is in maintenance mode with no new features. Authlib provides full OAuth 2.0/OIDC server capabilities with 20+ RFC compliance.

3. **MSAL + Azure Identity**: MSAL handles user-facing OAuth flows with Azure AD, while Azure Identity's DefaultAzureCredential handles managed identity for service-to-service auth.

4. **Argon2 over bcrypt**: Argon2 is the winner of the Password Hashing Competition and is recommended by OWASP for new applications.

5. **Redis for sessions**: Provides TTL-based expiration, scalability across instances, and atomic operations for session management.

---

## 3. FastAPI Security Patterns

### OAuth2PasswordBearer Pattern

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Dependency to extract and validate JWT token.
    Raises 401 if token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user
```

### HTTPBearer Pattern (Alternative)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> User:
    """
    Alternative pattern using HTTPBearer.
    Useful when you need more control over the scheme validation.
    """
    token = credentials.credentials
    # Validate token and return user...
```

### Dependency Injection for Authorization

```python
from fastapi import Security
from typing import List

def require_permissions(required_permissions: List[str]):
    """
    Factory function to create permission-checking dependencies.
    Implements RBAC (Role-Based Access Control).
    """
    async def permission_checker(
        user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if not all(perm in user.permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return permission_checker

# Usage in routes
@router.get("/admin/users")
async def list_users(
    user: Annotated[User, Security(require_permissions(["admin:read"]))]
):
    return await get_all_users()
```

### Scopes-Based Authorization

```python
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "users:read": "Read user information",
        "users:write": "Create and update users",
        "admin": "Full administrative access",
    }
)

async def get_current_user_with_scopes(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Validates both token AND required scopes.
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    # Decode token and check scopes
    payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
    token_scopes = payload.get("scopes", [])

    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user
```

---

## 4. Azure AD / Entra ID Integration

### Multi-Tenant Configuration

```python
from msal import ConfidentialClientApplication
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import os

# Multi-tenant app configuration
AZURE_AD_CONFIG = {
    "client_id": "[AZURE_CLIENT_ID]",
    "client_secret": "[AZURE_CLIENT_SECRET]",  # Not needed with managed identity
    "authority": "https://login.microsoftonline.com/organizations",  # Multi-tenant
    "scopes": ["https://graph.microsoft.com/.default"],
}

class AzureADAuthenticator:
    """
    Azure AD authentication handler supporting multi-tenant scenarios.
    """

    def __init__(self, tenant_id: str = None):
        """
        Initialize authenticator.

        Args:
            tenant_id: Specific tenant ID for single-tenant,
                      None or "organizations" for multi-tenant
        """
        if tenant_id:
            authority = f"https://login.microsoftonline.com/{tenant_id}"
        else:
            authority = "https://login.microsoftonline.com/organizations"

        self.app = ConfidentialClientApplication(
            client_id=AZURE_AD_CONFIG["client_id"],
            client_credential=AZURE_AD_CONFIG["client_secret"],
            authority=authority,
        )

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate authorization URL for user login."""
        return self.app.get_authorization_request_url(
            scopes=["openid", "profile", "email"],
            redirect_uri=redirect_uri,
            state=state,
        )

    async def acquire_token_by_code(
        self,
        code: str,
        redirect_uri: str
    ) -> dict:
        """Exchange authorization code for tokens."""
        result = self.app.acquire_token_by_authorization_code(
            code=code,
            scopes=["openid", "profile", "email"],
            redirect_uri=redirect_uri,
        )
        if "error" in result:
            raise AuthenticationError(result.get("error_description"))
        return result
```

### Managed Identity Pattern (Recommended for Azure Services)

```python
from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    AzureCliCredential,
)
import os

def get_azure_credential():
    """
    Get appropriate Azure credential based on environment.

    Production: Uses ManagedIdentityCredential for security
    Development: Falls back to AzureCliCredential
    """
    # Check if running in Azure (App Service, Functions, AKS, etc.)
    if os.getenv("WEBSITE_HOSTNAME") or os.getenv("IDENTITY_ENDPOINT"):
        # Use user-assigned managed identity if configured
        client_id = os.getenv("AZURE_CLIENT_ID")
        if client_id:
            return ManagedIdentityCredential(client_id=client_id)
        return ManagedIdentityCredential()

    # Local development - use Azure CLI credentials
    return AzureCliCredential()

# For general use, DefaultAzureCredential tries multiple methods
credential = DefaultAzureCredential(
    managed_identity_client_id=os.getenv("AZURE_CLIENT_ID"),
    exclude_interactive_browser_credential=True,  # Non-interactive for services
)
```

### Token Validation for Multi-Tenant

```python
import jwt
from jwt import PyJWKClient
from typing import Optional

class AzureADTokenValidator:
    """
    Validates Azure AD tokens for multi-tenant applications.
    """

    def __init__(
        self,
        client_id: str,
        allowed_tenants: Optional[list] = None
    ):
        self.client_id = client_id
        self.allowed_tenants = allowed_tenants
        self.jwks_client = PyJWKClient(
            "https://login.microsoftonline.com/common/discovery/v2.0/keys"
        )

    def validate_token(self, token: str) -> dict:
        """
        Validate Azure AD token.

        Validates:
        - Signature using JWKS
        - Audience matches client_id
        - Token not expired
        - Tenant is allowed (if restrictions configured)
        """
        # Get signing key from JWKS endpoint
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.client_id,
            options={"verify_iss": False}  # Multi-tenant has variable issuer
        )

        # Validate tenant if restrictions configured
        if self.allowed_tenants:
            tenant_id = claims.get("tid")
            if tenant_id not in self.allowed_tenants:
                raise jwt.InvalidTokenError("Tenant not allowed")

        return claims
```

### Best Practices for Azure AD Integration

1. **Use Managed Identity in Production**: Eliminates secrets management entirely
2. **Token Caching**: MSAL handles caching automatically; avoid duplicate token requests
3. **Silent Token Acquisition First**: Always try `acquire_token_silent()` before interactive flows
4. **Multi-Tenant Consent**: Implement admin consent flow for organizational apps
5. **Tenant Restrictions**: For B2B apps, validate `tid` claim against allowed tenants

---

## 5. JWT Best Practices

### Algorithm Selection: RS256 vs HS256

| Aspect | RS256 (Asymmetric) | HS256 (Symmetric) |
|--------|-------------------|-------------------|
| **Key Management** | Private key signs, public key verifies | Single shared secret |
| **Distribution** | Public key can be shared safely | Secret must be protected |
| **Best For** | Distributed systems, microservices | Single service, internal APIs |
| **Performance** | Slower signing/verification | Faster |
| **Security** | Higher (key separation) | Requires secure secret distribution |
| **JWKS Endpoint** | Can publish public keys | Not applicable |

**Recommendation**: Use **RS256** for production systems, especially when:
- Multiple services need to verify tokens
- You want to publish a JWKS endpoint
- Token verification happens in untrusted environments

### JWT Implementation with PyJWT

```python
import jwt
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from pathlib import Path

class JWTHandler:
    """
    Production-ready JWT handler using RS256.
    """

    def __init__(
        self,
        private_key_path: str = None,
        public_key_path: str = None,
        issuer: str = "netrun-auth",
        audience: str = "netrun-api",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        self.issuer = issuer
        self.audience = audience
        self.access_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_expire = timedelta(days=refresh_token_expire_days)

        # Load keys
        if private_key_path:
            self.private_key = Path(private_key_path).read_bytes()
        if public_key_path:
            self.public_key = Path(public_key_path).read_bytes()

    def create_access_token(
        self,
        subject: str,
        scopes: list = None,
        additional_claims: dict = None
    ) -> str:
        """
        Create a signed access token.

        Claims included:
        - sub: Subject (user ID)
        - iss: Issuer
        - aud: Audience
        - exp: Expiration time
        - iat: Issued at
        - jti: Unique token ID
        - scopes: Permission scopes
        """
        now = datetime.now(timezone.utc)
        claims = {
            "sub": subject,
            "iss": self.issuer,
            "aud": self.audience,
            "exp": now + self.access_expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "access",
        }
        if scopes:
            claims["scopes"] = scopes
        if additional_claims:
            claims.update(additional_claims)

        return jwt.encode(claims, self.private_key, algorithm="RS256")

    def create_refresh_token(self, subject: str) -> str:
        """Create a refresh token with longer expiration."""
        now = datetime.now(timezone.utc)
        claims = {
            "sub": subject,
            "iss": self.issuer,
            "aud": self.audience,
            "exp": now + self.refresh_expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        return jwt.encode(claims, self.private_key, algorithm="RS256")

    def decode_token(self, token: str, expected_type: str = "access") -> dict:
        """
        Decode and validate a token.

        Validates:
        - Signature
        - Expiration
        - Issuer
        - Audience
        - Token type
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],  # CRITICAL: Hard-code algorithm
                audience=self.audience,
                issuer=self.issuer,
            )
            if payload.get("type") != expected_type:
                raise jwt.InvalidTokenError("Invalid token type")
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
```

### Token Refresh Pattern

```python
from redis import Redis
from typing import Tuple

class TokenRefreshService:
    """
    Handles token refresh with revocation support.
    """

    def __init__(self, jwt_handler: JWTHandler, redis: Redis):
        self.jwt = jwt_handler
        self.redis = redis
        self.revoked_prefix = "revoked:"

    async def refresh_tokens(
        self,
        refresh_token: str
    ) -> Tuple[str, str]:
        """
        Exchange refresh token for new access + refresh tokens.

        Implements refresh token rotation:
        - Old refresh token is revoked
        - New refresh token is issued
        """
        # Validate refresh token
        payload = self.jwt.decode_token(refresh_token, expected_type="refresh")

        # Check if token is revoked
        jti = payload["jti"]
        if await self.is_revoked(jti):
            raise TokenRevokedError("Refresh token has been revoked")

        # Revoke old refresh token (rotation)
        await self.revoke_token(jti, payload["exp"])

        # Issue new tokens
        subject = payload["sub"]
        new_access = self.jwt.create_access_token(subject)
        new_refresh = self.jwt.create_refresh_token(subject)

        return new_access, new_refresh

    async def revoke_token(self, jti: str, exp: datetime):
        """Add token to revocation list with TTL."""
        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await self.redis.setex(
                f"{self.revoked_prefix}{jti}",
                ttl,
                "1"
            )

    async def is_revoked(self, jti: str) -> bool:
        """Check if token is in revocation list."""
        return await self.redis.exists(f"{self.revoked_prefix}{jti}")
```

### Security Best Practices for JWT

1. **Hard-code algorithms**: Never compute from token header to prevent algorithm confusion attacks
2. **Validate all critical claims**: Always validate `exp`, `iss`, `aud`, and custom claims
3. **Use short expiration for access tokens**: 15-30 minutes recommended
4. **Implement refresh token rotation**: Issue new refresh token on each refresh
5. **Store refresh tokens securely**: Database or Redis with proper encryption
6. **Never store sensitive data in tokens**: JWTs are base64-encoded, not encrypted
7. **Use JWKS for public key distribution**: Enables key rotation without code changes

---

## 6. OAuth 2.0 / OIDC Patterns

### Authorization Code Flow with PKCE (Authlib)

```python
from authlib.integrations.starlette_client import OAuth
from authlib.common.security import generate_token
from starlette.config import Config

# OAuth client configuration
oauth = OAuth()
oauth.register(
    name='azure',
    client_id='[AZURE_CLIENT_ID]',
    client_secret='[AZURE_CLIENT_SECRET]',
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'code_challenge_method': 'S256',  # PKCE
    },
)

# Authorization endpoint
@router.get("/auth/login")
async def login(request: Request):
    """Initiate OAuth flow with PKCE."""
    redirect_uri = request.url_for('auth_callback')
    return await oauth.azure.authorize_redirect(request, redirect_uri)

# Callback endpoint
@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback and exchange code for tokens."""
    token = await oauth.azure.authorize_access_token(request)

    # Validate ID token
    user_info = token.get('userinfo')
    if not user_info:
        user_info = await oauth.azure.userinfo(token=token)

    # Create session or JWT
    return create_user_session(user_info)
```

### Client Credentials Flow (Service-to-Service)

```python
from authlib.integrations.httpx_client import AsyncOAuth2Client

class ServiceAuthClient:
    """
    OAuth 2.0 client credentials flow for service-to-service auth.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
        scope: str = None,
    ):
        self.client = AsyncOAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=token_endpoint,
        )
        self.scope = scope
        self._token = None

    async def get_token(self) -> str:
        """
        Get access token, refreshing if expired.
        Uses client_credentials grant.
        """
        if self._token and not self._token.is_expired():
            return self._token['access_token']

        self._token = await self.client.fetch_token(
            url=self.client.token_endpoint,
            grant_type='client_credentials',
            scope=self.scope,
        )
        return self._token['access_token']

    async def request_with_auth(
        self,
        method: str,
        url: str,
        **kwargs
    ):
        """Make authenticated request to protected resource."""
        token = await self.get_token()
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {token}'

        async with httpx.AsyncClient() as client:
            return await client.request(method, url, headers=headers, **kwargs)
```

### OIDC ID Token Validation

```python
from authlib.jose import jwt
from authlib.oidc.core import CodeIDToken

class OIDCValidator:
    """
    Validates OIDC ID tokens according to spec.
    """

    def __init__(self, issuer: str, client_id: str, jwks_uri: str):
        self.issuer = issuer
        self.client_id = client_id
        self.jwks_uri = jwks_uri
        self._jwks = None

    async def get_jwks(self):
        """Fetch and cache JWKS from provider."""
        if not self._jwks:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri)
                self._jwks = response.json()
        return self._jwks

    async def validate_id_token(
        self,
        id_token: str,
        nonce: str = None
    ) -> dict:
        """
        Validate OIDC ID token.

        Validates:
        - Signature against JWKS
        - Issuer claim
        - Audience claim
        - Expiration
        - Nonce (if provided)
        """
        jwks = await self.get_jwks()

        claims = jwt.decode(
            id_token,
            jwks,
            claims_cls=CodeIDToken,
            claims_options={
                'iss': {'essential': True, 'value': self.issuer},
                'aud': {'essential': True, 'value': self.client_id},
            }
        )
        claims.validate()

        # Validate nonce if provided (prevents replay attacks)
        if nonce and claims.get('nonce') != nonce:
            raise ValueError("Nonce mismatch")

        return claims
```

### OAuth Flows Decision Matrix

| Flow | Use Case | Client Type | PKCE Required |
|------|----------|-------------|---------------|
| **Authorization Code** | Web apps with backend | Confidential | Recommended |
| **Authorization Code + PKCE** | SPAs, Mobile apps | Public | Required |
| **Client Credentials** | Service-to-service | Confidential | No |
| **Device Code** | IoT, CLI tools | Public | No |
| **Refresh Token** | Token renewal | Both | No |

---

## 7. Session Management

### Redis-Backed Session Store

```python
from redis.asyncio import Redis
from typing import Optional, Any
import json
import secrets
from datetime import timedelta

class RedisSessionStore:
    """
    Redis-backed session management with security features.
    """

    def __init__(
        self,
        redis: Redis,
        prefix: str = "session:",
        default_ttl: int = 3600,  # 1 hour
        max_ttl: int = 86400,     # 24 hours
    ):
        self.redis = redis
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.max_ttl = max_ttl

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}{session_id}"

    async def create(
        self,
        data: dict,
        ttl: int = None
    ) -> str:
        """
        Create new session with secure random ID.

        Returns session ID (use as cookie value).
        """
        session_id = secrets.token_urlsafe(32)  # 256-bit random
        ttl = min(ttl or self.default_ttl, self.max_ttl)

        await self.redis.setex(
            self._key(session_id),
            ttl,
            json.dumps(data),
        )
        return session_id

    async def get(self, session_id: str) -> Optional[dict]:
        """Retrieve session data."""
        data = await self.redis.get(self._key(session_id))
        if data:
            return json.loads(data)
        return None

    async def update(
        self,
        session_id: str,
        data: dict,
        extend_ttl: bool = True
    ) -> bool:
        """Update session data, optionally extending TTL."""
        key = self._key(session_id)

        if extend_ttl:
            ttl = await self.redis.ttl(key)
            if ttl > 0:
                await self.redis.setex(key, ttl, json.dumps(data))
                return True
        else:
            # Preserve existing TTL
            await self.redis.set(key, json.dumps(data), xx=True)
            return True
        return False

    async def delete(self, session_id: str) -> bool:
        """Delete session (logout)."""
        return await self.redis.delete(self._key(session_id)) > 0

    async def extend(self, session_id: str, ttl: int = None) -> bool:
        """Extend session TTL (sliding expiration)."""
        ttl = min(ttl or self.default_ttl, self.max_ttl)
        return await self.redis.expire(self._key(session_id), ttl)
```

### Secure Cookie Configuration

```python
from fastapi import Response
from datetime import datetime, timedelta

def set_session_cookie(
    response: Response,
    session_id: str,
    max_age: int = 3600,
    secure: bool = True,
    httponly: bool = True,
    samesite: str = "lax",
) -> Response:
    """
    Set session cookie with security attributes.

    Security attributes:
    - secure: Only send over HTTPS
    - httponly: Not accessible via JavaScript (XSS protection)
    - samesite: CSRF protection (lax or strict)
    """
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=max_age,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
        path="/",
    )
    return response

def clear_session_cookie(response: Response) -> Response:
    """Clear session cookie on logout."""
    response.delete_cookie(
        key="session_id",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return response
```

### CSRF Protection with Double Submit Cookie

```python
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = "[CSRF_SECRET_KEY]"
    cookie_samesite: str = "lax"
    cookie_secure: bool = True

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

# Usage in routes
@router.post("/api/protected")
async def protected_route(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    """
    Protected route requiring CSRF token.

    Client must:
    1. Get CSRF token from cookie
    2. Send token in X-CSRF-Token header
    """
    await csrf_protect.validate_csrf(request)
    # Process request...
```

### Session vs JWT: When to Use Each

| Scenario | Recommended | Reasoning |
|----------|-------------|-----------|
| Browser-based web app | Session + Cookie | Better security (HttpOnly), easy revocation |
| SPA (React, Vue) | JWT in memory + Refresh in HttpOnly cookie | Balance between usability and security |
| Mobile app | JWT with secure storage | No cookies in native apps |
| API-to-API | JWT or OAuth client credentials | Stateless, scalable |
| High-security app | Session with Redis | Immediate revocation, audit trail |
| Microservices | JWT with short expiry | Stateless, no shared session store needed |

---

## 8. OWASP API Security Top 10

### Top 10 API Security Risks (2023)

| Rank | Risk | Description | Mitigation |
|------|------|-------------|------------|
| **API1** | Broken Object Level Authorization (BOLA) | Access to other users' data via ID manipulation | Validate user owns requested resource |
| **API2** | Broken Authentication | Weak auth mechanisms | Use OAuth 2.0/OIDC, MFA, rate limiting |
| **API3** | Broken Object Property Level Authorization | Excessive data exposure | Filter response data by permission |
| **API4** | Unrestricted Resource Consumption | DoS via resource exhaustion | Rate limiting, pagination, query limits |
| **API5** | Broken Function Level Authorization | Access to admin functions | RBAC/ABAC, verify permissions per endpoint |
| **API6** | Unrestricted Access to Sensitive Flows | Abuse of business logic | Rate limiting, CAPTCHA, flow validation |
| **API7** | Server-Side Request Forgery (SSRF) | Server makes malicious requests | Validate/sanitize URLs, allowlists |
| **API8** | Security Misconfiguration | Default configs, verbose errors | Security hardening, hide stack traces |
| **API9** | Improper Inventory Management | Shadow APIs, deprecated endpoints | API documentation, version management |
| **API10** | Unsafe Consumption of APIs | Trusting third-party API data | Validate all external data |

### Implementation Patterns for Top Risks

#### BOLA Prevention (API1)

```python
async def get_resource(
    resource_id: str,
    user: User = Depends(get_current_user)
):
    """
    Always verify resource ownership.
    """
    resource = await db.get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404)

    # CRITICAL: Verify ownership
    if resource.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    return resource
```

#### Rate Limiting (API4)

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Initialize with Redis
@app.on_event("startup")
async def startup():
    await FastAPILimiter.init(redis)

# Apply rate limits
@router.post("/auth/login")
@limiter.limit("5/minute")  # 5 attempts per minute
async def login(request: Request, ...):
    ...

@router.get("/api/resources")
@limiter.limit("100/minute")  # 100 requests per minute
async def list_resources(...):
    ...
```

#### RBAC Implementation (API5)

```python
from enum import Enum
from typing import Set

class Permission(str, Enum):
    READ_USERS = "users:read"
    WRITE_USERS = "users:write"
    DELETE_USERS = "users:delete"
    ADMIN = "admin:*"

class Role(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.USER: {Permission.READ_USERS},
    Role.MODERATOR: {Permission.READ_USERS, Permission.WRITE_USERS},
    Role.ADMIN: {Permission.READ_USERS, Permission.WRITE_USERS,
                 Permission.DELETE_USERS, Permission.ADMIN},
}

def require_permission(permission: Permission):
    """Decorator/dependency for permission checks."""
    async def checker(user: User = Depends(get_current_user)):
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        if permission not in user_permissions and Permission.ADMIN not in user_permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
```

---

## 9. API Design Recommendations

### Authentication Endpoint Structure

```
POST /auth/register          # User registration
POST /auth/login             # Login (returns tokens)
POST /auth/logout            # Logout (revoke tokens)
POST /auth/refresh           # Refresh access token
POST /auth/forgot-password   # Request password reset
POST /auth/reset-password    # Complete password reset
POST /auth/verify-email      # Email verification
GET  /auth/me                # Current user info
PUT  /auth/me                # Update current user

# OAuth/SSO
GET  /auth/oauth/{provider}          # Initiate OAuth flow
GET  /auth/oauth/{provider}/callback # OAuth callback
POST /auth/oauth/{provider}/token    # Exchange OAuth token

# Multi-tenant
GET  /auth/tenants           # List user's tenants
POST /auth/tenants/{id}/switch # Switch active tenant
```

### Request/Response Patterns

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# Registration
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)

class RegisterResponse(BaseModel):
    id: str
    email: str
    full_name: str
    email_verified: bool = False
    created_at: datetime

# Login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds

# Error responses (RFC 7807 Problem Details)
class ErrorResponse(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: Optional[str] = None

# User info
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    permissions: List[str]
    tenant_id: Optional[str]
    email_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
```

### Multi-Tenant Authentication Pattern

```python
from fastapi import Header
from typing import Optional

async def get_current_tenant(
    x_tenant_id: Optional[str] = Header(None),
    user: User = Depends(get_current_user),
) -> Tenant:
    """
    Resolve current tenant from header or user default.

    Multi-tenant authentication flow:
    1. User authenticates (gets JWT with user_id)
    2. Request includes X-Tenant-Id header
    3. Verify user has access to requested tenant
    4. Set tenant context for request
    """
    if x_tenant_id:
        # Verify user has access to this tenant
        tenant = await db.get_tenant(x_tenant_id)
        if not tenant or user.id not in tenant.member_ids:
            raise HTTPException(
                status_code=403,
                detail="Access to tenant denied"
            )
        return tenant

    # Use user's default tenant
    return await db.get_tenant(user.default_tenant_id)
```

---

## 10. Security Considerations

### Password Security

```python
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Use Argon2 (winner of Password Hashing Competition)
password_hash = PasswordHash((
    Argon2Hasher(
        time_cost=3,        # iterations
        memory_cost=65536,  # 64 MB
        parallelism=4,      # threads
    ),
))

def hash_password(password: str) -> str:
    """Hash password using Argon2."""
    return password_hash.hash(password)

def verify_password(password: str, hash: str) -> bool:
    """Verify password against hash."""
    return password_hash.verify(password, hash)

# Password validation rules
PASSWORD_RULES = {
    "min_length": 8,
    "max_length": 128,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": False,  # NIST no longer recommends
    "check_common": True,      # Check against common passwords
}
```

### Secrets Management

```python
from pydantic_settings import BaseSettings
from pydantic import SecretStr
from functools import lru_cache

class AuthSettings(BaseSettings):
    """
    Authentication settings with secure handling.

    Load from environment variables or Azure Key Vault.
    """
    # JWT
    jwt_private_key: SecretStr  # RSA private key (PEM)
    jwt_public_key: str         # RSA public key (can be public)
    jwt_algorithm: str = "RS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Azure AD
    azure_client_id: str
    azure_client_secret: SecretStr
    azure_tenant_id: str

    # Session
    session_secret: SecretStr
    redis_url: SecretStr

    # CSRF
    csrf_secret: SecretStr

    class Config:
        env_file = ".env"
        env_prefix = "AUTH_"

@lru_cache()
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
```

### Security Headers

```python
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.netrunsystems.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "X-CSRF-Token", "X-Tenant-Id"],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.netrunsystems.com", "*.netrunsystems.com"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

### Audit Logging

```python
import structlog
from datetime import datetime
from typing import Optional

logger = structlog.get_logger()

async def log_auth_event(
    event_type: str,
    user_id: Optional[str],
    success: bool,
    request: Request,
    details: dict = None,
):
    """
    Log authentication event for audit trail.

    Events to log:
    - login_attempt, login_success, login_failure
    - logout
    - token_refresh
    - password_change, password_reset
    - mfa_enable, mfa_disable
    - permission_change
    """
    await logger.ainfo(
        "auth_event",
        event_type=event_type,
        user_id=user_id,
        success=success,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        timestamp=datetime.utcnow().isoformat(),
        correlation_id=request.state.correlation_id,
        details=details,
    )
```

---

## 11. Implementation Roadmap

### Phase 1: Core Authentication (Week 1-2)

- [ ] Set up project structure with FastAPI
- [ ] Implement JWT handling with PyJWT (RS256)
- [ ] Create user model and database schema
- [ ] Implement password hashing with Argon2
- [ ] Build registration and login endpoints
- [ ] Add refresh token rotation
- [ ] Implement logout with token revocation

### Phase 2: OAuth Integration (Week 3)

- [ ] Integrate Authlib for OAuth client
- [ ] Implement Azure AD multi-tenant flow
- [ ] Add PKCE support for public clients
- [ ] Build OAuth callback handlers
- [ ] Implement token exchange endpoints

### Phase 3: Session Management (Week 4)

- [ ] Set up Redis session store
- [ ] Implement secure cookie handling
- [ ] Add CSRF protection
- [ ] Build session-based auth alternative
- [ ] Implement sliding session expiration

### Phase 4: Authorization (Week 5)

- [ ] Design RBAC permission model
- [ ] Implement permission checking dependencies
- [ ] Add scope-based authorization
- [ ] Build multi-tenant context resolution
- [ ] Create admin endpoints

### Phase 5: Security Hardening (Week 6)

- [ ] Add rate limiting with Redis
- [ ] Implement audit logging
- [ ] Add security headers middleware
- [ ] Set up CORS properly
- [ ] Penetration testing and fixes

### Phase 6: Production Readiness (Week 7-8)

- [ ] Azure managed identity integration
- [ ] Key rotation procedures
- [ ] Monitoring and alerting
- [ ] Documentation and API specs
- [ ] Performance optimization

---

## 12. Sources

### FastAPI Security

1. [FastAPI Official Security Tutorial](https://fastapi.tiangolo.com/tutorial/security/) - Official documentation on OAuth2, JWT, and security patterns
2. [OAuth2 with Password and JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) - Official FastAPI JWT implementation guide
3. [TestDriven.io - Securing FastAPI with JWT](https://testdriven.io/blog/fastapi-jwt-auth/) - Production-ready JWT authentication guide
4. [Better Stack - Authentication Guide](https://betterstack.com/community/guides/scaling-python/authentication-fastapi/) - Complete authentication and authorization guide
5. [FreeCodeCamp - JWT Authentication in FastAPI](https://www.freecodecamp.org/news/how-to-add-jwt-authentication-in-fastapi/) - Practical JWT implementation guide

### Azure AD / Entra ID

6. [Microsoft Learn - MSAL Authentication Flows](https://learn.microsoft.com/en-us/entra/identity-platform/msal-authentication-flows) - Official MSAL flow documentation
7. [MSAL Python Best Practices](https://github.com/AzureAD/microsoft-authentication-library-for-python/wiki/Best-practices) - Official MSAL Python best practices wiki
8. [Azure Identity Client Library](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme) - DefaultAzureCredential and managed identity guide
9. [Multi-tenant App Conversion](https://learn.microsoft.com/en-us/entra/identity-platform/howto-convert-app-to-be-multi-tenant) - Converting single-tenant to multi-tenant apps
10. [Azure Credential Chains](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication/credential-chains) - Credential chain patterns for Python

### JWT Best Practices

11. [PyJWT Documentation](https://pyjwt.readthedocs.io/en/latest/usage.html) - Official PyJWT usage guide
12. [PyJWT Algorithms](https://pyjwt.readthedocs.io/en/stable/algorithms.html) - Supported signing algorithms
13. [WorkOS - JWT in Python](https://workos.com/blog/how-to-handle-jwt-in-python) - JWT handling best practices (recommends PyJWT over python-jose)
14. [Auth0 - JWT in Python](https://auth0.com/blog/how-to-handle-jwt-in-python/) - Comprehensive JWT guide
15. [Miguel Grinberg - JWT Public Key Signatures](https://blog.miguelgrinberg.com/post/json-web-tokens-with-public-key-signatures/page/0) - RS256 implementation guide

### OAuth 2.0 / OIDC

16. [Authlib Documentation](https://docs.authlib.org/en/latest/) - Official Authlib documentation
17. [Authlib OAuth2 Session](https://docs.authlib.org/en/latest/client/oauth2.html) - OAuth2 client implementation
18. [OAuth.net - PKCE](https://oauth.net/2/pkce/) - PKCE specification and best practices
19. [OAuth.net - Python Libraries](https://oauth.net/code/python/) - Python OAuth library comparison
20. [Stefaan Lippens - PKCE Flow](https://www.stefaanlippens.net/oauth-code-flow-pkce.html) - Step-by-step PKCE implementation

### Session Management & CSRF

21. [FastAPI CSRF Protect](https://pypi.org/project/fastapi-csrf-protect/) - CSRF protection library for FastAPI
22. [StackHawk - CSRF Protection in FastAPI](https://www.stackhawk.com/blog/csrf-protection-in-fastapi/) - CSRF protection patterns
23. [Security in FastAPI - Best Practices Part II](https://blog.stackademic.com/security-in-fastapi-best-practices-to-protect-your-application-part-ii-1b2f285a9709) - Session and CSRF security

### OWASP & Security

24. [OWASP API Security Top 10](https://owasp.org/API-Security/) - Official OWASP API security risks
25. [OWASP API Security Project](https://owasp.org/www-project-api-security/) - API security best practices
26. [Pynt - OWASP API Top 10 Guide](https://www.pynt.io/learning-hub/owasp-top-10-guide/owasp-api-top-10) - Comprehensive OWASP guide with mitigations
27. [Vidoc Security - API Security for Python](https://blog.vidocsecurity.com/blog/api-security-best-practices-for-developers) - Python-specific API security tips

### FastAPI-Users & Alternatives

28. [FastAPI-Users GitHub](https://github.com/fastapi-users/fastapi-users) - Library status (maintenance mode notice)
29. [FastAPI-Users Documentation](https://fastapi-users.github.io/fastapi-users/latest/) - Features and configuration
30. [Awesome FastAPI](https://github.com/mjhea0/awesome-fastapi) - Curated list of FastAPI authentication libraries

---

## Appendix A: Code Examples Repository Structure

```
Service_59_Unified_Authentication/
├── src/
│   └── netrun_auth/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry
│       ├── config.py            # Settings with Pydantic
│       ├── dependencies.py      # Auth dependencies
│       ├── models/
│       │   ├── user.py          # User model
│       │   ├── token.py         # Token models
│       │   └── session.py       # Session model
│       ├── services/
│       │   ├── jwt.py           # JWT handler
│       │   ├── session.py       # Session store
│       │   ├── oauth.py         # OAuth client
│       │   └── azure.py         # Azure AD integration
│       ├── routers/
│       │   ├── auth.py          # Auth endpoints
│       │   ├── oauth.py         # OAuth endpoints
│       │   └── users.py         # User endpoints
│       ├── middleware/
│       │   ├── security.py      # Security headers
│       │   └── rate_limit.py    # Rate limiting
│       └── utils/
│           ├── password.py      # Password hashing
│           └── audit.py         # Audit logging
├── tests/
├── pyproject.toml
└── README.md
```

---

## Appendix B: Environment Variables

```bash
# JWT Configuration
AUTH_JWT_PRIVATE_KEY_PATH=/secrets/jwt_private.pem
AUTH_JWT_PUBLIC_KEY_PATH=/secrets/jwt_public.pem
AUTH_JWT_ALGORITHM=RS256
AUTH_JWT_ACCESS_EXPIRE_MINUTES=15
AUTH_JWT_REFRESH_EXPIRE_DAYS=7

# Azure AD Configuration
AUTH_AZURE_CLIENT_ID=[AZURE_CLIENT_ID]
AUTH_AZURE_CLIENT_SECRET=[AZURE_CLIENT_SECRET]
AUTH_AZURE_TENANT_ID=organizations  # or specific tenant

# Session Configuration
AUTH_SESSION_SECRET=[SESSION_SECRET_KEY]
AUTH_REDIS_URL=redis://localhost:6379/0

# CSRF Configuration
AUTH_CSRF_SECRET=[CSRF_SECRET_KEY]

# Security
AUTH_ALLOWED_ORIGINS=https://app.netrunsystems.com
AUTH_TRUSTED_HOSTS=api.netrunsystems.com
```

---

*Report Generated: November 25, 2025*
*SDLC Compliance: v2.1 - All sources verified*
*Confidence Level: HIGH - Multiple authoritative sources cross-referenced*
