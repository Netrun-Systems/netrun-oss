# Authentication System Update - netrun-auth

**Package**: netrun-auth (PyPI)
**Version**: 1.3.0
**Date**: 2025-12-07
**Status**: Completed

---

## Overview

The `netrun-auth` package has been updated to include Azure AD B2C support, enabling consumer identity management with social login capabilities. This is a core authentication library for the Netrun Systems portfolio.

---

## Completed Tasks

### v1.3.0 - Azure AD B2C Integration

- [x] **B2C Configuration** (`integrations/azure_ad_b2c.py`)
  - `AzureADB2CConfig` dataclass
  - `B2CUserFlowConfig` for user flow policies
  - Environment variable support
  - JWKS URI generation per user flow

- [x] **B2C User Flows** (`B2CUserFlow` enum)
  - SIGNUP_SIGNIN - Combined sign-up/sign-in
  - PASSWORD_RESET - Self-service password reset
  - PROFILE_EDIT - Profile editing

- [x] **B2C Token Claims** (`B2CTokenClaims` dataclass)
  - Standard OIDC claims (sub, name, email)
  - B2C-specific claims (emails array, tfp, idp, idp_access_token)
  - Extension attribute support
  - Helper properties:
    - `user_id` - oid or sub
    - `primary_email` - First email from array
    - `display_name` - Name with fallback
    - `identity_provider` - IDP or 'local'
    - `is_social_login` - Social provider detection

- [x] **B2C Client** (`AzureADB2CClient` class)
  - JWKS-based token validation with PyJWKClient
  - Authorization URL generation with PKCE
  - Code exchange for tokens
  - Claims mapping to local format
  - User flow management
  - Error detection helpers

- [x] **FastAPI Integration**
  - `initialize_b2c()` - Initialize B2C client
  - `get_b2c_client()` - Dependency injection
  - `get_current_user_b2c()` - Route dependency
  - `extract_bearer_token()` - Header extraction
  - `is_b2c_configured()` - Configuration check

- [x] **Package Updates**
  - Version bump: 1.2.0 -> 1.3.0
  - New optional dependency group: `netrun-auth[b2c]`
  - Updated keywords: azure-ad-b2c, social-login
  - Updated `__all__` exports

- [x] **Tests** (`tests/test_azure_ad_b2c.py`)
  - 31 unit tests passing
  - Configuration tests
  - Claims parsing tests
  - Client method tests
  - FastAPI helper tests
  - Error detection tests

---

## Installation

```bash
# Basic installation
pip install netrun-auth

# With B2C support
pip install netrun-auth[b2c]

# All features
pip install netrun-auth[all]
```

---

## Usage Example

```python
from netrun_auth.integrations.azure_ad_b2c import (
    AzureADB2CConfig,
    AzureADB2CClient,
    B2CUserFlow,
    initialize_b2c,
    get_current_user_b2c,
)
from fastapi import FastAPI, Depends

app = FastAPI()

# Configure B2C
config = AzureADB2CConfig(
    tenant_name="netrunsystems",
    client_id="your-client-id",
    tenant_id="your-tenant-id",
)
initialize_b2c(config)

# Protected route
@app.get("/api/profile")
async def get_profile(claims = Depends(get_current_user_b2c)):
    return {
        "user_id": claims.user_id,
        "email": claims.primary_email,
        "name": claims.display_name,
        "is_social": claims.is_social_login,
    }
```

---

## Environment Variables

```env
# Azure AD B2C Configuration
AZURE_B2C_TENANT_NAME=netrunsystems
AZURE_B2C_CLIENT_ID=your-client-id
AZURE_B2C_CLIENT_SECRET=your-secret  # Optional for confidential apps
AZURE_B2C_TENANT_ID=your-tenant-id

# User Flow Policies
AZURE_B2C_SIGNUP_SIGNIN_POLICY=B2C_1_signup_signin
AZURE_B2C_PASSWORD_RESET_POLICY=B2C_1_password_reset
AZURE_B2C_PROFILE_EDIT_POLICY=B2C_1_profile_edit

# Redirect URI
AZURE_B2C_REDIRECT_URI=https://yourapp.com/auth/callback
```

---

## API Reference

### Configuration

```python
@dataclass
class AzureADB2CConfig:
    tenant_name: str           # B2C tenant name (without .onmicrosoft.com)
    client_id: str             # Application (client) ID
    tenant_id: str = None      # Directory (tenant) ID
    client_secret: str = None  # Client secret (for confidential apps)
    redirect_uri: str = "http://localhost:3000"
    scopes: List[str] = ["openid", "profile", "email"]
    user_flows: B2CUserFlowConfig = B2CUserFlowConfig()
```

### Token Claims

```python
@dataclass
class B2CTokenClaims:
    sub: str                   # Subject identifier
    aud: str                   # Audience
    iss: str                   # Issuer
    exp: int                   # Expiration
    iat: int                   # Issued at
    name: str = None           # Display name
    given_name: str = None     # First name
    family_name: str = None    # Last name
    emails: List[str] = None   # Email addresses (B2C array)
    email: str = None          # Single email (standard)
    tfp: str = None            # Trust framework policy
    idp: str = None            # Identity provider
    oid: str = None            # Object ID

    # Properties
    @property
    def user_id(self) -> str: ...
    @property
    def primary_email(self) -> str: ...
    @property
    def display_name(self) -> str: ...
    @property
    def identity_provider(self) -> str: ...
    @property
    def is_social_login(self) -> bool: ...
```

### Client Methods

```python
class AzureADB2CClient:
    async def validate_token(
        self,
        token: str,
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
        validate_audience: bool = True,
        validate_issuer: bool = True,
    ) -> B2CTokenClaims: ...

    def get_authorization_url(
        self,
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
        state: str = None,
        nonce: str = None,
        **kwargs,
    ) -> Tuple[str, str, str]: ...  # (url, state, code_verifier)

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
        flow: B2CUserFlow = B2CUserFlow.SIGNUP_SIGNIN,
    ) -> Dict[str, Any]: ...

    def map_claims_to_local(
        self,
        claims: B2CTokenClaims,
        role_mapping: Dict[str, str] = None,
    ) -> Dict[str, Any]: ...

    @staticmethod
    def is_password_reset_error(error: str) -> bool: ...

    @staticmethod
    def is_cancelled_error(error: str) -> bool: ...
```

---

## Pending Tasks

- [ ] Add refresh token handling
- [ ] Add token caching with Redis
- [ ] Add MFA enforcement support
- [ ] Add custom policy support
- [ ] Add B2C admin operations (Graph API)
- [ ] Publish to PyPI

---

## Related Files

```
netrun_auth/
├── __init__.py                    # Package exports (updated)
├── integrations/
│   ├── __init__.py               # Integration exports (updated)
│   ├── azure_ad.py               # Standard Azure AD
│   ├── azure_ad_b2c.py           # NEW: Azure AD B2C
│   └── oauth.py                  # Generic OAuth
└── ...

tests/
└── test_azure_ad_b2c.py          # NEW: B2C tests

pyproject.toml                     # Updated version & deps
```

---

## Dependencies

### Required (b2c extra)
- `msal>=1.26.0` - Microsoft Authentication Library
- `httpx>=0.26.0` - Async HTTP client
- `pyjwt[crypto]>=2.8.0` - JWT handling with cryptography

### Core
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Settings management

---

## Changelog

### v1.3.0 (2025-12-07)
- Added Azure AD B2C integration
- Full B2C support with user flows (sign-up, password reset, profile edit)
- Social identity provider support (Google, Facebook, etc.)
- B2C-specific claims mapping (emails array, tfp, idp)
- PKCE support for SPA applications
- FastAPI dependency injection helpers

### v1.2.0 (2025-12-05)
- Deep netrun-logging integration
- Structured logging for authentication events

### v1.1.0 (2025-11-26)
- Casbin RBAC integration

### v1.0.0 (2025-11-25)
- Initial release with JWT, password hashing, RBAC
