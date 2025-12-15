# Azure AD & OAuth 2.0 Integrations Guide

**Service**: #59 Unified Authentication
**Version**: 1.0.0 (Week 6)
**Date**: November 25, 2025
**Author**: Backend Engineer (Netrun Systems)

---

## Overview

This guide documents the Azure AD and OAuth 2.0 integrations for netrun-auth v1.0.0. These integrations provide production-ready authentication with enterprise identity providers.

**Implemented Features**:
- Azure AD / Entra ID authentication (all OAuth 2.0 flows)
- Generic OAuth 2.0 client (Google, GitHub, Okta, Auth0, custom)
- Multi-tenant Azure AD support
- PKCE for all authorization code flows
- Token validation with JWKS
- Claims mapping to netrun-auth format
- FastAPI integration helpers

---

## Azure AD Integration

### Supported Flows

| Flow | Use Case | Client Type | Requires Secret |
|------|----------|-------------|-----------------|
| **Authorization Code** | Web applications | Confidential | Yes |
| **Client Credentials** | Service-to-service | Confidential | Yes |
| **On-Behalf-Of** | API delegation | Confidential | Yes |
| **Device Code** | CLI/device apps | Public | No |

### Configuration

```python
from netrun_auth.integrations import AzureADConfig, AzureADClient

# Single-tenant configuration
config = AzureADConfig(
    tenant_id="your-tenant-id-guid",
    client_id="your-client-id-guid",
    client_secret="your-client-secret",  # From Azure portal
    redirect_uri="https://your-app.com/auth/callback",
    scopes=["User.Read", "offline_access"]
)

# Create client
azure_client = AzureADClient(config)
```

### Authorization Code Flow (Web Apps)

```python
# Step 1: Generate authorization URL
auth_url, state = azure_client.get_authorization_url(use_pkce=True)

# Store state in session for CSRF protection
request.session["azure_state"] = state

# Redirect user to auth_url
return RedirectResponse(url=auth_url)

# Step 2: Handle callback
async def azure_callback(code: str, state: str, request: Request):
    # Validate state
    stored_state = request.session.get("azure_state")
    if stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for tokens
    tokens = await azure_client.exchange_code_for_tokens(code, state)

    # tokens contains: access_token, refresh_token, expires_in
    return {"access_token": tokens["access_token"]}
```

### Client Credentials Flow (Service-to-Service)

```python
# Service-to-service authentication (no user context)
tokens = await azure_client.get_client_credentials_token(
    scopes=["https://graph.microsoft.com/.default"]
)

# Use access_token to call Microsoft Graph or other APIs
access_token = tokens["access_token"]
```

### Token Validation

```python
# Validate Azure AD token
try:
    claims = await azure_client.validate_azure_token(
        token=access_token,
        validate_audience=True,
        allowed_tenants=["tenant-1-id", "tenant-2-id"]  # Optional allowlist
    )

    # claims contains: oid, sub, email, name, tid, roles, groups
    user_id = claims["oid"]
    tenant_id = claims["tid"]

except TokenValidationError as e:
    # Token invalid, expired, or from unauthorized tenant
    raise HTTPException(status_code=401, detail=str(e))
```

### User Profile Retrieval

```python
# Get user profile from Microsoft Graph
user_profile = await azure_client.get_user_profile(access_token)

# user_profile contains: id, displayName, userPrincipalName, mail, etc.

# Get user's group memberships
groups = await azure_client.get_user_groups(access_token)
# groups is list of group IDs
```

### Claims Mapping

```python
# Map Azure AD claims to netrun-auth format
azure_claims = await azure_client.validate_azure_token(access_token)

local_claims = azure_client.map_azure_claims_to_local(
    azure_claims,
    organization_mapping={"azure-tenant-id": "local-org-123"}
)

# local_claims structure:
# {
#     "user_id": "azure-oid",
#     "organization_id": "local-org-123",
#     "email": "user@example.com",
#     "name": "User Name",
#     "roles": ["role1", "role2"],
#     "permissions": [],  # Populate based on roles
#     "azure_tenant_id": "azure-tenant-id",
#     "azure_oid": "azure-oid"
# }
```

### Multi-Tenant Azure AD

```python
from netrun_auth.integrations import AzureADMultiTenantClient

# Multi-tenant configuration (SaaS apps)
config = AzureADConfig(
    tenant_id="common",  # Accept any tenant
    client_id="your-client-id",
    client_secret="your-client-secret",
    redirect_uri="https://your-app.com/auth/callback"
)

# Create multi-tenant client
azure_client = AzureADMultiTenantClient(config)

# Authorization URL works for any tenant
auth_url, state = azure_client.get_authorization_url()

# Validate token from any tenant
claims = await azure_client.validate_azure_token(
    token,
    allowed_tenants=["allowed-tenant-1", "allowed-tenant-2"]  # Optional
)

# Validate tenant (for allowlist scenarios)
is_allowed = await azure_client.validate_tenant(
    tenant_id=claims["tid"],
    allowed_tenants=["allowed-1", "allowed-2"]
)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from netrun_auth.integrations import (
    initialize_azure_ad,
    get_azure_ad_client,
    get_current_user_azure
)

app = FastAPI()

# Initialize Azure AD on startup
@app.on_event("startup")
async def startup():
    config = AzureADConfig(
        tenant_id="[AZURE_TENANT_ID]",
        client_id="[AZURE_CLIENT_ID]",
        client_secret="[AZURE_CLIENT_SECRET]",
        redirect_uri="http://localhost:8000/auth/azure/callback"
    )
    initialize_azure_ad(config)

# Login endpoint
@app.get("/auth/azure/login")
async def azure_login(request: Request):
    azure_client = get_azure_ad_client()
    auth_url, state = azure_client.get_authorization_url()
    request.session["azure_state"] = state
    return RedirectResponse(url=auth_url)

# Callback endpoint
@app.get("/auth/azure/callback")
async def azure_callback(code: str, state: str, request: Request):
    stored_state = request.session.get("azure_state")
    if stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    azure_client = get_azure_ad_client()
    tokens = await azure_client.exchange_code_for_tokens(code, state)

    return {"access_token": tokens["access_token"]}

# Protected endpoint
@app.get("/api/profile")
async def get_profile(user: dict = Depends(get_current_user_azure)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "organization_id": user["organization_id"]
    }
```

---

## OAuth 2.0 Integration

### Supported Providers

| Provider | Pre-configured | Scopes |
|----------|---------------|--------|
| **Google** | Yes | openid, email, profile |
| **GitHub** | Yes | read:user, user:email |
| **Okta** | Yes | openid, email, profile |
| **Auth0** | Yes | openid, email, profile |
| **Custom** | No | User-defined |

### Configuration

```python
from netrun_auth.integrations import OAuthConfig, OAuthClient, OAuthProvider

# Google OAuth (pre-configured)
google_config = OAuthConfig.google(
    client_id="your-google-client-id",
    client_secret="your-google-client-secret",
    redirect_uri="http://localhost:8000/auth/google/callback"
)

google_client = OAuthClient(google_config)

# GitHub OAuth (pre-configured)
github_config = OAuthConfig.github(
    client_id="your-github-client-id",
    client_secret="your-github-client-secret",
    redirect_uri="http://localhost:8000/auth/github/callback"
)

github_client = OAuthClient(github_config)

# Okta OAuth (pre-configured)
okta_config = OAuthConfig.okta(
    client_id="your-okta-client-id",
    client_secret="your-okta-client-secret",
    redirect_uri="http://localhost:8000/auth/okta/callback",
    okta_domain="dev-12345.okta.com"
)

okta_client = OAuthClient(okta_config)

# Auth0 OAuth (pre-configured)
auth0_config = OAuthConfig.auth0(
    client_id="your-auth0-client-id",
    client_secret="your-auth0-client-secret",
    redirect_uri="http://localhost:8000/auth/auth0/callback",
    auth0_domain="dev-12345.us.auth0.com"
)

auth0_client = OAuthClient(auth0_config)

# Custom OAuth provider
custom_config = OAuthConfig(
    provider=OAuthProvider.CUSTOM,
    client_id="your-client-id",
    client_secret="your-client-secret",
    authorization_endpoint="https://provider.com/oauth/authorize",
    token_endpoint="https://provider.com/oauth/token",
    userinfo_endpoint="https://provider.com/oauth/userinfo",
    redirect_uri="http://localhost:8000/auth/callback",
    scopes=["read", "write"]
)

custom_client = OAuthClient(custom_config)
```

### Authorization Flow

```python
# Step 1: Generate authorization URL
auth_url, state = google_client.get_authorization_url()

# Store state for CSRF protection
request.session["oauth_state"] = state

# Redirect user
return RedirectResponse(url=auth_url)

# Step 2: Handle callback
async def oauth_callback(code: str, state: str, request: Request):
    # Validate state
    stored_state = request.session.get("oauth_state")
    if stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for tokens
    tokens = await google_client.exchange_code_for_tokens(code, state)

    # tokens contains: access_token, refresh_token, expires_in
    return tokens
```

### User Info Retrieval

```python
# Get user info from provider
user_info = await google_client.get_user_info(tokens["access_token"])

# user_info structure varies by provider:
# Google: { sub, email, name, email_verified, picture }
# GitHub: { id, login, email, name, avatar_url }
# Okta/Auth0: { sub, email, name, preferred_username }

# Map to local claims format
local_claims = google_client.map_provider_claims_to_local(user_info)

# local_claims structure:
# {
#     "user_id": "provider-user-id",
#     "email": "user@example.com",
#     "name": "User Name",
#     "username": "username",
#     "provider": "google",
#     "email_verified": true,
#     "picture": "https://example.com/photo.jpg"
# }
```

### Token Refresh

```python
# Refresh access token using refresh token
new_tokens = await google_client.refresh_access_token(refresh_token)

# new_tokens contains: access_token, expires_in
```

### OAuth Manager (Multiple Providers)

```python
from netrun_auth.integrations import OAuthManager, get_oauth_manager

# Create manager
oauth_manager = OAuthManager()

# Register multiple providers
oauth_manager.register_provider(google_config)
oauth_manager.register_provider(github_config)
oauth_manager.register_provider(okta_config)

# Get client for specific provider
google_client = oauth_manager.get_client(OAuthProvider.GOOGLE)
github_client = oauth_manager.get_client(OAuthProvider.GITHUB)

# List available providers
providers = oauth_manager.available_providers
# [OAuthProvider.GOOGLE, OAuthProvider.GITHUB, OAuthProvider.OKTA]
```

### FastAPI Integration (OAuth Router)

```python
from fastapi import FastAPI
from netrun_auth.integrations import (
    OAuthManager,
    OAuthConfig,
    OAuthProvider,
    create_oauth_router
)

app = FastAPI()

# Initialize OAuth manager
oauth_manager = OAuthManager()
oauth_manager.register_provider(OAuthConfig.google(...))
oauth_manager.register_provider(OAuthConfig.github(...))

# Create OAuth router (handles authorize + callback)
def handle_login_success(claims: dict) -> dict:
    """Called after successful OAuth login."""
    # Create session, generate JWT, etc.
    return {"user": claims, "session_token": "..."}

oauth_router = create_oauth_router(
    oauth_manager=oauth_manager,
    on_login_success=handle_login_success
)

# Include router
app.include_router(oauth_router)

# Routes created:
# GET /oauth/{provider}/authorize - Start OAuth flow
# GET /oauth/{provider}/callback - Handle OAuth callback

# Usage:
# Navigate to: /oauth/google/authorize
# After callback: /oauth/google/callback?code=...&state=...
```

---

## Security Features

### PKCE (Proof Key for Code Exchange)

All authorization code flows use PKCE by default to protect against authorization code interception attacks.

**How it works**:
1. Client generates random `code_verifier`
2. Client computes `code_challenge = SHA256(code_verifier)`
3. Authorization request includes `code_challenge`
4. Token exchange includes `code_verifier`
5. Server validates `SHA256(code_verifier) == code_challenge`

**Implementation**:
```python
# PKCE is automatic for all flows
auth_url, state = azure_client.get_authorization_url(use_pkce=True)  # Default

# PKCE verifier stored internally and retrieved during token exchange
tokens = await azure_client.exchange_code_for_tokens(code, state)
```

### State Parameter (CSRF Protection)

All authorization flows use the `state` parameter to prevent CSRF attacks.

**Best practices**:
```python
# Generate state
auth_url, state = oauth_client.get_authorization_url()

# Store state in session (server-side)
request.session["oauth_state"] = state

# Validate on callback
stored_state = request.session.get("oauth_state")
if stored_state != state:
    raise HTTPException(status_code=400, detail="CSRF detected")
```

### Token Validation

**Azure AD tokens are validated for**:
- Signature (using JWKS public keys)
- Expiration (`exp` claim)
- Audience (`aud` claim must match `client_id`)
- Issuer (`iss` claim from Azure AD)
- Tenant ID (optional allowlist)

**JWT validation is performed with hard-coded algorithm**:
```python
# SECURE - Algorithm hard-coded (no algorithm confusion attacks)
claims = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],  # ONLY RS256 allowed
    options={"verify_signature": True}
)
```

### Secrets Management

**Never hardcode credentials**:
```python
# ❌ BAD
config = AzureADConfig(
    client_secret="hardcoded-secret-123"
)

# ✅ GOOD
from os import getenv

config = AzureADConfig(
    client_secret=getenv("AZURE_CLIENT_SECRET")
)

# ✅ BEST (Azure Key Vault)
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

vault_client = SecretClient(
    vault_url=getenv("AZURE_KEYVAULT_URL"),
    credential=DefaultAzureCredential()
)

config = AzureADConfig(
    client_secret=vault_client.get_secret("azure-client-secret").value
)
```

---

## Error Handling

### Exception Types

```python
from netrun_auth.core.exceptions import (
    AuthenticationError,
    TokenValidationError,
    ConfigurationError
)

# AuthenticationError - OAuth flow failures
try:
    tokens = await oauth_client.exchange_code_for_tokens(code, state)
except AuthenticationError as e:
    # Token exchange failed, code invalid, etc.
    logger.error(f"OAuth failed: {e}")
    raise HTTPException(status_code=401, detail="Authentication failed")

# TokenValidationError - Invalid/expired tokens
try:
    claims = await azure_client.validate_azure_token(token)
except TokenValidationError as e:
    # Token expired, invalid signature, wrong audience, etc.
    logger.warning(f"Token validation failed: {e}")
    raise HTTPException(status_code=401, detail="Invalid token")

# ConfigurationError - Missing/invalid configuration
try:
    client = oauth_manager.get_client(OAuthProvider.GOOGLE)
except ConfigurationError as e:
    # Provider not registered
    logger.error(f"Configuration error: {e}")
    raise HTTPException(status_code=500, detail="OAuth not configured")
```

---

## Testing

### Unit Tests

```bash
# Run integration tests
pytest tests/test_integrations_azure_ad.py -v
pytest tests/test_integrations_oauth.py -v

# With coverage
pytest tests/test_integrations_*.py --cov=netrun_auth.integrations
```

### Mock Azure AD Tokens (Testing)

```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_azure_token_validation():
    """Test Azure AD token validation with mocked JWKS."""
    azure_client = AzureADClient(config)

    # Mock JWKS client
    with patch.object(azure_client, 'jwks_client') as mock_jwks:
        mock_signing_key = Mock()
        mock_signing_key.key = "test-public-key"
        mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key

        # Mock JWT decode
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "oid": "test-user-id",
                "sub": "test-subject",
                "email": "test@example.com",
                "tid": "test-tenant-id"
            }

            claims = await azure_client.validate_azure_token("test-token")

            assert claims["oid"] == "test-user-id"
```

---

## Code Metrics

**Implementation Statistics**:
- `azure_ad.py`: 576 LOC (complete implementation)
- `oauth.py`: 643 LOC (complete implementation)
- Total: 1,219 LOC
- Test coverage: 26 passing tests (31 total with 5 requiring MSAL mocking)
- Zero stub methods (`pass` statements)

**Security Compliance**:
- PKCE for all authorization code flows
- State parameter for CSRF protection
- Token validation with JWKS
- Hard-coded JWT algorithms (no algorithm confusion)
- Secure credential handling patterns

---

## References

**Source Documents**:
- `SECURITY_GUIDELINES.md` - Security requirements and best practices
- `examples/azure_oauth_integration.py` - Usage examples

**External Standards**:
- RFC 6749: OAuth 2.0 Authorization Framework
- RFC 7636: PKCE for OAuth
- RFC 7519: JSON Web Token (JWT)
- Microsoft Identity Platform documentation

**Azure AD Resources**:
- [Azure AD v2.0 endpoint](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-overview)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/overview)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)

**OAuth Providers**:
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [Okta OAuth](https://developer.okta.com/docs/reference/api/oidc/)
- [Auth0 OAuth](https://auth0.com/docs/authenticate/protocols/oauth)

---

**Document Classification**: INTERNAL - ENGINEERING REFERENCE
**Distribution**: Engineering Team
**Review Schedule**: Quarterly (next review: February 2026)

---

*End of Document*
