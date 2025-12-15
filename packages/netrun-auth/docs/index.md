# netrun-auth v1.0.0

Unified authentication library for the Netrun Systems portfolio.

A production-ready authentication framework providing JWT authentication, RBAC, password security, and multi-protocol integration (Azure AD, OAuth 2.0) with FastAPI middleware and dependency injection.

## Key Features

- **JWT Authentication**: RS256 asymmetric signing with 90-day key rotation
- **Role-Based Access Control**: Permission model with role hierarchy and aggregation
- **Password Security**: Argon2id hashing (OWASP/NIST compliant)
- **FastAPI Integration**: Seamless middleware and dependency injection
- **Token Blacklisting**: Redis-backed token revocation for secure logout
- **Rate Limiting**: Configurable rate limits with Redis backend
- **Azure AD Integration**: Full Entra ID support with multi-tenant capabilities
- **OAuth 2.0 Support**: Pre-configured providers (Google, GitHub, Okta, Auth0)
- **Security Headers**: OWASP Secure Headers Project compliant
- **Audit Logging**: Comprehensive authentication event tracking
- **Session Management**: Multi-device session tracking

## Quick Start

### Installation

```bash
# Basic installation
pip install netrun-auth

# With FastAPI support
pip install netrun-auth[fastapi]

# With Azure AD support
pip install netrun-auth[azure]

# All optional dependencies
pip install netrun-auth[all]
```

### Basic Usage

```python
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import get_current_user
from fastapi import FastAPI, Depends

# Initialize configuration and JWT manager
config = AuthConfig()
jwt_manager = JWTManager(config)

# Create FastAPI app
app = FastAPI()

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    config=config
)

# Protect routes with dependency injection
@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user.user_id}"}
```

### Generate Tokens

```python
from datetime import datetime, timezone
from netrun_auth.types import TokenClaims

# Generate access and refresh token pair
token_pair = await jwt_manager.generate_token_pair(
    user_id="user123",
    organization_id="org456",
    roles=["user", "developer"],
    permissions=["users:read", "projects:create"]
)

# Use tokens
print(token_pair.access_token)      # JWT access token
print(token_pair.refresh_token)     # JWT refresh token
print(token_pair.expires_in)        # Seconds until expiry
```

### Role-Based Access Control

```python
from netrun_auth import require_roles, require_permissions

# Require specific roles (OR logic - user needs at least one)
@app.get("/admin")
async def admin_only(user: User = Depends(require_roles("admin", "super_admin"))):
    return {"message": "Admin access granted"}

# Require specific permissions (OR logic - user needs at least one)
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_permissions("users:delete", "admin:delete"))
):
    return {"message": f"Deleted user {user_id}"}
```

## Compliance & Security

netrun-auth implements security best practices from:

- **NIST SP 800-63B**: Digital identity guidelines for authentication
- **OWASP Top 10**: Authentication cheat sheet
- **SOC2**: Security control frameworks
- **RS256 Standard**: Asymmetric JWT signing with RSA 2048-bit keys

## Core Concepts

### Tokens

- **Access Token**: 15-minute expiry, used for API requests
- **Refresh Token**: 30-day expiry, used to obtain new access tokens
- **API Key Token**: Long-lived key for service-to-service authentication

### Claims

JWT claims include:

- **Standard Claims**: `jti`, `sub`, `iat`, `exp`, `iss`, `aud`
- **Application Claims**: `user_id`, `organization_id`, `roles`, `permissions`, `session_id`
- **Security Claims**: `ip_address`, `user_agent`

### Roles & Permissions

- **Roles**: Groups of permissions (e.g., "admin", "user", "viewer")
- **Permissions**: Resource:action format (e.g., "users:read", "projects:delete")
- **Hierarchy**: Roles can inherit from parent roles
- **Aggregation**: User permissions aggregate from all assigned roles

### RBAC Model

```
User → Roles → Permissions
       ↓
    Role Hierarchy (inheritance)
       ↓
    Permission Aggregation
```

## Documentation

- [Installation Guide](./installation.md) - Detailed setup and configuration
- [Getting Started](./getting-started.md) - Step-by-step tutorial
- [API Reference](./api/jwt.md) - Complete API documentation
  - [JWT Manager](./api/jwt.md)
  - [Middleware](./api/middleware.md)
  - [Dependencies](./api/dependencies.md)
  - [RBAC Manager](./api/rbac.md)
  - [Password Manager](./api/password.md)
  - [Exceptions](./api/exceptions.md)
- [Integrations](./integrations/azure-ad.md)
  - [Azure AD](./integrations/azure-ad.md)
  - [OAuth 2.0](./integrations/oauth.md)
- [Security](./security/best-practices.md)
  - [Best Practices](./security/best-practices.md)
  - [Compliance](./security/compliance.md)
- [Examples](./examples/fastapi-app.md)
  - [Complete FastAPI Application](./examples/fastapi-app.md)
  - [Multi-tenant Setup](./examples/multi-tenant.md)

## Source Code

- **Repository**: https://github.com/netrunsystems/netrun-service-library-v2
- **Service**: Service #59 Unified Authentication
- **Python Package**: `netrun_auth`
- **Version**: 1.0.0

## Support

For issues, questions, or feature requests, contact the Netrun Systems development team.

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
**Author**: Netrun Systems
