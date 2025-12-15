# Azure AD Integration Guide

Complete integration guide for Azure AD/Entra ID authentication.

## Overview

The Azure AD integration provides:
- Authorization Code Flow with PKCE
- Client Credentials Flow (service-to-service)
- On-Behalf-Of Flow (API delegation)
- Device Code Flow (CLI/device apps)
- Multi-tenant support
- Token validation with JWKS
- Claims mapping to netrun-auth format

## Prerequisites

1. Azure account with admin access
2. Registered Azure AD application
3. Application credentials (client ID, secret)
4. Redirect URI configured

## Azure AD Setup

### Step 1: Register Application

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **+ New registration**
4. Fill in application details:
   - **Name**: netrun-auth-app
   - **Supported account types**: Choose based on needs
   - **Redirect URI**: http://localhost:8000/auth/callback
5. Click **Register**

### Step 2: Configure Credentials

1. Go to **Certificates & secrets**
2. Click **+ New client secret**
3. Fill in description and expiry
4. Copy the **Value** (not ID)
5. Save securely in environment variables

### Step 3: Configure API Permissions

1. Go to **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add permissions:
   - `User.Read` (required)
   - `User.ReadWrite` (for profile updates)
   - `Directory.Read.All` (for admin operations)
6. Click **Grant admin consent**

### Step 4: Configure Redirect URI

1. Go to **Authentication**
2. Add redirect URIs:
   - Production: `https://your-domain.com/auth/callback`
   - Development: `http://localhost:8000/auth/callback`
3. Enable **ID token** and **Access token**
4. Click **Save**

## Configuration

### Environment Variables

```env
NETRUN_AUTH_AZURE_AD_TENANT_ID=00000000-0000-0000-0000-000000000000
NETRUN_AUTH_AZURE_AD_CLIENT_ID=00000000-0000-0000-0000-000000000000
NETRUN_AUTH_AZURE_AD_CLIENT_SECRET=your-secret-here
NETRUN_AUTH_AZURE_AD_REDIRECT_URI=http://localhost:8000/auth/callback
NETRUN_AUTH_AZURE_AD_SCOPES=User.Read,openid,profile,email
```

### Python Configuration

```python
from netrun_auth.integrations.azure_ad import AzureADConfig, AzureADClient

# Load from environment
config = AzureADConfig(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-secret"
)

# Or with custom authority
config = AzureADConfig(
    tenant_id="common",  # Multi-tenant
    client_id="your-client-id",
    client_secret="your-secret",
    authority="https://login.microsoftonline.com/common"
)

client = AzureADClient(config)
```

## Authorization Code Flow (Web Apps)

Standard OAuth 2.0 flow for web applications.

### Step 1: Generate Authorization URL

```python
from fastapi import FastAPI
from netrun_auth.integrations.azure_ad import AzureADConfig, AzureADClient

app = FastAPI()
azure_client = AzureADClient(AzureADConfig(...))

@app.get("/auth/login")
async def login():
    """Redirect to Azure AD login."""
    auth_url, state, pkce_verifier = azure_client.get_authorization_url()

    # Store state and pkce_verifier in session for verification
    # response.set_cookie("state", state)
    # response.set_cookie("pkce_verifier", pkce_verifier)

    return {"redirect_url": auth_url}
```

### Step 2: Handle Callback

```python
@app.get("/auth/callback")
async def callback(code: str, state: str):
    """Handle Azure AD callback."""
    # Verify state from cookie
    # stored_state = request.cookies.get("state")
    # if state != stored_state:
    #     raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for token
    token_response = await azure_client.authorization_code_flow(
        code=code,
        state=state,
        pkce_verifier="saved_pkce_verifier"  # From session
    )

    # Get user info
    user_info = await azure_client.get_user_info(token_response["access_token"])

    # Generate netrun-auth tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_info["id"],
        organization_id=user_info.get("organization_id"),
        roles=["user"]
    )

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "expires_in": token_pair.expires_in
    }
```

## Client Credentials Flow (Service-to-Service)

For service-to-service authentication without user involvement.

### Configuration

```python
config = AzureADConfig(
    tenant_id="your-tenant-id",
    client_id="service-principal-id",
    client_secret="service-principal-secret"
)

client = AzureADClient(config)
```

### Authentication

```python
@app.on_event("startup")
async def startup():
    """Authenticate service on startup."""
    token_response = await client.client_credentials_flow(
        scopes=["https://graph.microsoft.com/.default"]
    )

    # Use token to call Microsoft Graph or other APIs
    global service_token
    service_token = token_response["access_token"]

@app.get("/service-operation")
async def service_operation():
    """Perform operation with service credentials."""
    # Use service_token for API calls
    headers = {"Authorization": f"Bearer {service_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )

    return response.json()
```

## On-Behalf-Of Flow (API Delegation)

User A's credentials delegated to service for API calls.

### Scenario

```
User
  ↓ (provides token to service)
Service A
  ↓ (uses OBO to get new token)
Service B API
```

### Implementation

```python
@app.post("/api/delegate")
async def delegate_request(
    user_token: str,
    target_api: str
):
    """Delegate user's token to access target API."""

    # Exchange user's token for target service token
    delegated_token = await client.on_behalf_of_flow(
        assertion=user_token,  # User's Azure AD token
        scopes=[f"{target_api}/.default"],
        requested_token_use="on_behalf_of"
    )

    # Call target API with delegated token
    headers = {"Authorization": f"Bearer {delegated_token['access_token']}"}

    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(
            f"https://{target_api}/api/data",
            headers=headers
        )

    return response.json()
```

## Device Code Flow (CLI/IoT)

For devices without web browser (CLI tools, IoT devices).

### User Perspective

```
1. User runs: "myapp auth login"
2. Gets response: "Go to device.microsoft.com, enter code: ABC123"
3. User opens browser, enters code
4. App polls for completion
5. Login succeeds, token saved
```

### Implementation

```python
@app.post("/cli/login")
async def cli_login():
    """Start device code flow for CLI."""

    device_code_info = await client.device_code_flow_initiate()

    return {
        "device_code": device_code_info["device_code"],
        "user_code": device_code_info["user_code"],
        "verification_uri": device_code_info["verification_uri"],
        "expires_in": device_code_info["expires_in"],
        "interval": device_code_info["interval"]
    }

@app.post("/cli/login-poll")
async def cli_login_poll(device_code: str):
    """Poll for device code completion."""

    try:
        token_response = await client.device_code_flow_poll(device_code)

        # Token received, device is logged in
        return {
            "access_token": token_response["access_token"],
            "refresh_token": token_response.get("refresh_token")
        }

    except AuthenticationPendingError:
        # Still waiting for user to complete login
        return {"status": "pending"}

    except AuthenticationError as e:
        # User denied or flow expired
        return {"error": e.message}
```

## Token Validation with JWKS

Validate Azure AD tokens using public key set.

### Implementation

```python
from jwt import PyJWKClient
import jwt as pyjwt

class AzureTokenValidator:
    """Validate Azure AD tokens."""

    def __init__(self, tenant_id: str):
        jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self.jwks_client = PyJWKClient(jwks_uri)

    async def validate_token(
        self,
        token: str,
        client_id: str,
        issuer: str
    ) -> dict:
        """Validate Azure AD token."""

        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        claims = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
            options={"verify_exp": True}
        )

        return claims
```

## Multi-Tenant Support

Handle multiple Azure AD tenants.

### Configuration

```python
# Single tenant
single_tenant_config = AzureADConfig(
    tenant_id="specific-tenant-id"
)

# Multi-tenant (common endpoint)
multi_tenant_config = AzureADConfig(
    tenant_id="common",
    authority="https://login.microsoftonline.com/common"
)
```

### Validation

```python
async def validate_multi_tenant_token(token: str) -> dict:
    """Validate token from any tenant."""

    claims = pyjwt.decode(
        token,
        options={"verify_signature": False}  # Unverified to get issuer
    )

    issuer = claims["iss"]
    tenant_id = issuer.split("/")[3]

    # Validate with tenant-specific validator
    validator = AzureTokenValidator(tenant_id)

    return await validator.validate_token(
        token,
        client_id=config.client_id,
        issuer=issuer
    )
```

## Claims Mapping

Map Azure AD claims to netrun-auth format.

```python
def map_azure_claims_to_user(azure_claims: dict) -> dict:
    """Map Azure AD claims to netrun-auth User model."""

    return {
        "user_id": azure_claims["oid"],                    # Object ID
        "email": azure_claims.get("preferred_username"),   # Email
        "display_name": azure_claims.get("name"),          # Full name
        "organization_id": extract_organization(azure_claims),
        "roles": extract_roles(azure_claims),
        "permissions": []  # Fetch from database based on roles
    }

def extract_organization(azure_claims: dict) -> str:
    """Extract organization from Azure claims."""

    # Option 1: From custom claim
    if "org_id" in azure_claims:
        return azure_claims["org_id"]

    # Option 2: From tenant ID
    return azure_claims.get("tid")

def extract_roles(azure_claims: dict) -> List[str]:
    """Extract roles from Azure AD groups."""

    # Azure AD provides groups in "groups" claim
    group_ids = azure_claims.get("groups", [])

    # Map group IDs to role names
    roles = {
        "group-id-1": "admin",
        "group-id-2": "developer",
        "group-id-3": "viewer"
    }

    return [roles[gid] for gid in group_ids if gid in roles]
```

## Complete Example

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.integrations.azure_ad import AzureADConfig, AzureADClient

app = FastAPI()

# Initialize
auth_config = AuthConfig()
jwt_manager = JWTManager(auth_config)

azure_config = AzureADConfig(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-secret",
    redirect_uri="http://localhost:8000/auth/callback"
)
azure_client = AzureADClient(azure_config)

# Login endpoint
@app.get("/auth/azure-login")
async def azure_login():
    """Redirect to Azure AD login."""
    auth_url, state, pkce = azure_client.get_authorization_url()
    return RedirectResponse(url=auth_url)

# Callback endpoint
@app.get("/auth/callback")
async def azure_callback(code: str, state: str):
    """Handle Azure AD callback."""
    try:
        # Exchange authorization code for token
        token = await azure_client.authorization_code_flow(code)

        # Get user info
        user_info = await azure_client.get_user_info(token["access_token"])

        # Generate netrun-auth tokens
        token_pair = await jwt_manager.generate_token_pair(
            user_id=user_info["id"],
            roles=["user"]
        )

        return {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": "Bearer"
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# Protected endpoint
@app.get("/me")
async def get_profile(user = Depends(get_current_user)):
    """Get current user profile."""
    return {"user_id": user.user_id, "email": user.email}
```

## Troubleshooting

### CORS Errors

```
Access to XMLHttpRequest has been blocked by CORS policy
```

**Solution**: Configure CORS in FastAPI

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### Invalid Redirect URI

```
AADSTS50011: The redirect URI specified in the request does not match
```

**Solution**: Ensure redirect URI matches exactly in Azure Portal

```
Azure Portal:
  Redirect URI: https://your-domain.com/auth/callback

Code:
  redirect_uri="https://your-domain.com/auth/callback"
```

### PKCE Verification Failed

```
AADSTS50159: No suitable signing key found
```

**Solution**: Ensure PKCE verifier matches challenge

```python
# Generate
auth_url, state, pkce_verifier = azure_client.get_authorization_url()

# Store securely
session["pkce_verifier"] = pkce_verifier

# Use
token = await azure_client.authorization_code_flow(
    code=code,
    pkce_verifier=session["pkce_verifier"]  # Must match
)
```

## Security Best Practices

1. **Never commit secrets**: Use environment variables
2. **Validate state parameter**: Prevent CSRF attacks
3. **Use PKCE**: Required for public clients
4. **Validate token signature**: Use JWKS
5. **Verify audience**: Ensure token intended for your app
6. **Store tokens securely**: Use httponly cookies or secure storage
7. **Implement refresh token rotation**: Rotate on each refresh
8. **Log authentication events**: Audit trail for compliance

## Next Steps

- [FastAPI Integration](../api/middleware.md)
- [Password Security](../api/password.md)
- [Security Best Practices](../security/best-practices.md)

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
