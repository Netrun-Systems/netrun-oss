# netrun-auth v1.1.0

Unified authentication library for Netrun Systems portfolio (Service #59).

## Latest Changes (v1.1.0)

- Fixed missing `Any` type import in `rbac.py` for proper type checking
- Improved type safety in RBAC manager factory function
- All tests passing (111 passed, 172 skipped)
- Distribution artifacts validated with twine

## Features

- **JWT Authentication**: RS256 asymmetric signing with rotating key pairs
- **Role-Based Access Control (RBAC)**: Permission model with role aggregation and hierarchy
- **Password Hashing**: Argon2id algorithm (OWASP recommended)
- **FastAPI Integration**: Middleware and dependency injection for seamless integration
- **Token Blacklisting**: Redis-backed token revocation for secure logout
- **Rate Limiting**: Configurable rate limits per user/organization
- **Security Headers**: OWASP Secure Headers Project compliant
- **Audit Logging**: Comprehensive authentication event logging
- **Session Management**: Multi-device session tracking and management
- **Azure Integration**: Azure AD/Entra ID and Key Vault support (optional)
- **OAuth 2.0**: Generic OAuth 2.0 client integration (optional)

## Installation

### Basic Installation

```bash
pip install netrun-auth
```

### With FastAPI Support

```bash
pip install netrun-auth[fastapi]
```

### With Azure AD Support

```bash
pip install netrun-auth[azure]
```

### With All Optional Dependencies

```bash
pip install netrun-auth[all]
```

## Quick Start

### 1. Configure Environment

Create a `.env` file:

```env
NETRUN_AUTH_JWT_ISSUER=your-app-name
NETRUN_AUTH_JWT_AUDIENCE=your-api-audience
NETRUN_AUTH_REDIS_URL=redis://localhost:6379/0
NETRUN_AUTH_JWT_PRIVATE_KEY_PATH=/path/to/private_key.pem
NETRUN_AUTH_JWT_PUBLIC_KEY_PATH=/path/to/public_key.pem
```

### 2. Initialize JWT Manager

```python
from netrun_auth import JWTManager, AuthConfig
import redis.asyncio as redis

# Load configuration
config = AuthConfig()

# Initialize Redis
redis_client = redis.from_url(config.redis_url)

# Create JWT manager
jwt_manager = JWTManager(config, redis_client)
```

### 3. Add Middleware to FastAPI

```python
from fastapi import FastAPI
from netrun_auth.middleware import AuthenticationMiddleware

app = FastAPI()

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)
```

### 4. Protect Routes with Dependencies

```python
from fastapi import Depends
from netrun_auth.dependencies import (
    get_current_user,
    require_permissions,
    require_roles
)
from netrun_auth import User

@app.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "user_id": user.user_id,
        "roles": user.roles,
        "permissions": user.permissions
    }

@app.get("/admin")
async def admin_route(user: User = Depends(require_roles("admin"))):
    return {"message": "Admin access granted"}

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_permissions("users:delete"))
):
    return {"message": f"Deleted user {user_id}"}
```

### 5. Generate Token Pairs

```python
# Generate tokens for user
token_pair = await jwt_manager.generate_token_pair(
    user_id="user_123",
    organization_id="org_456",
    roles=["user", "admin"],
    permissions=["users:read", "users:write"],
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0"
)

print(f"Access Token: {token_pair.access_token}")
print(f"Refresh Token: {token_pair.refresh_token}")
print(f"Expires In: {token_pair.expires_in} seconds")
```

### 6. Password Hashing

```python
from netrun_auth import PasswordManager

password_manager = PasswordManager()

# Hash a password
password_hash = password_manager.hash_password("SecurePassword123!")

# Verify password
is_valid = password_manager.verify_password("SecurePassword123!", password_hash)

# Check if rehashing needed (algorithm update)
if password_manager.needs_rehash(password_hash):
    new_hash = password_manager.hash_password("SecurePassword123!")
```

## RBAC (Role-Based Access Control)

### Default Roles

- **viewer**: Read-only access to all resources
- **user**: Standard user with read/write access
- **admin**: Full administrative access
- **super_admin**: System-level administrative access

### Permission Format

Permissions follow the `resource:action` format:

- `users:read` - Read user information
- `users:write` - Create/update users
- `users:delete` - Delete users
- `admin:*` - All admin actions (wildcard)

### Custom Roles

```python
from netrun_auth import get_rbac_manager, Role

rbac = get_rbac_manager()

# Define custom role
custom_role = Role(
    name="project_manager",
    permissions=[
        "projects:read",
        "projects:create",
        "projects:update",
        "users:read"
    ],
    inherits_from=["user"],
    description="Project management role"
)

rbac.add_role(custom_role)
```

### Check Permissions

```python
from netrun_auth import User

user = User(
    user_id="user_123",
    roles=["admin"],
    permissions=["users:delete"]
)

# Check single permission
if user.has_permission("users:delete"):
    print("User can delete users")

# Check multiple permissions (OR logic)
if user.has_any_permission("users:delete", "admin:delete"):
    print("User can delete")

# Check role
if user.has_role("admin"):
    print("User is admin")
```

## Configuration

All configuration via environment variables with `NETRUN_AUTH_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `NETRUN_AUTH_JWT_ALGORITHM` | `RS256` | JWT signing algorithm |
| `NETRUN_AUTH_JWT_ISSUER` | `netrun-auth` | JWT issuer claim |
| `NETRUN_AUTH_JWT_AUDIENCE` | `netrun-api` | JWT audience claim |
| `NETRUN_AUTH_ACCESS_TOKEN_EXPIRY_MINUTES` | `15` | Access token expiry |
| `NETRUN_AUTH_REFRESH_TOKEN_EXPIRY_DAYS` | `30` | Refresh token expiry |
| `NETRUN_AUTH_JWT_PRIVATE_KEY_PATH` | None | Path to RSA private key |
| `NETRUN_AUTH_JWT_PUBLIC_KEY_PATH` | None | Path to RSA public key |
| `NETRUN_AUTH_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `NETRUN_AUTH_PASSWORD_MIN_LENGTH` | `12` | Minimum password length |
| `NETRUN_AUTH_RATE_LIMIT_DEFAULT_REQUESTS` | `100` | Requests per window |
| `NETRUN_AUTH_RATE_LIMIT_DEFAULT_WINDOW_SECONDS` | `900` | Rate limit window (15 min) |

## Security Standards

- **NIST SP 800-63B** compliant token handling
- **OWASP Authentication Cheat Sheet** compliant
- **SOC2** audit trail support
- **Argon2id** password hashing (OWASP recommended)
- **RS256** JWT signing (asymmetric, recommended for production)
- **Token blacklisting** for secure logout
- **Rate limiting** for brute-force protection
- **Security headers** (OWASP Secure Headers Project)

## Architecture

```
netrun_auth/
├── __init__.py          # Public API exports
├── jwt.py              # JWT token management (RS256, key rotation)
├── password.py         # Password hashing (Argon2id)
├── rbac.py             # Role-Based Access Control
├── middleware.py       # FastAPI authentication middleware
├── dependencies.py     # FastAPI dependency injection
├── types.py            # Pydantic models (TokenClaims, User, AuthContext)
├── exceptions.py       # Custom exception hierarchy
├── config.py           # Configuration via Pydantic Settings
└── integrations/
    ├── azure_ad.py     # Azure AD/Entra ID (optional)
    └── oauth.py        # Generic OAuth 2.0 (optional)
```

## Development

### Setup Development Environment

```bash
git clone <repo-url>
cd Service_59_Unified_Authentication
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black netrun_auth/

# Lint
ruff netrun_auth/

# Type check
mypy netrun_auth/
```

## License

Proprietary - Netrun Systems

## Author

Daniel Garza <daniel.garza@netrunsystems.com>

## Support

For issues and questions: https://github.com/netrun-systems/netrun-auth/issues
