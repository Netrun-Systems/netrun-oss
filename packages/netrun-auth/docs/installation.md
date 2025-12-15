# Installation Guide

Complete setup and configuration instructions for netrun-auth.

## Requirements

- Python 3.9+
- Redis 6.0+ (for token blacklisting and rate limiting)
- FastAPI 0.95+ (optional, for middleware)

## Installation Options

### Basic Installation

Install the core authentication library:

```bash
pip install netrun-auth
```

This installs the minimum dependencies:
- `pydantic` (2.0+)
- `pydantic-settings`
- `PyJWT` (2.8+)
- `cryptography` (41.0+)
- `passlib` (1.7+)
- `argon2-cffi` (23.0+)
- `redis` (5.0+)

### With FastAPI Support

For FastAPI middleware and dependency injection:

```bash
pip install netrun-auth[fastapi]
```

Adds:
- `fastapi` (0.95+)
- `starlette` (0.26+)

### With Azure AD Support

For Azure AD/Entra ID integration:

```bash
pip install netrun-auth[azure]
```

Adds:
- `msal` (1.26+) - Microsoft Authentication Library
- `PyJWK` (1.1+) - JWKS support
- `httpx` (0.25+) - Async HTTP client

### With OAuth 2.0 Support

For OAuth 2.0 provider integration:

```bash
pip install netrun-auth[oauth]
```

Adds:
- `authlib` (1.3+) - OAuth library
- `httpx` (0.25+) - Async HTTP client

### Full Installation

Install all optional dependencies:

```bash
pip install netrun-auth[all]
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
# JWT Configuration
NETRUN_AUTH_JWT_ISSUER=my-app-name
NETRUN_AUTH_JWT_AUDIENCE=my-api-audience
NETRUN_AUTH_ACCESS_TOKEN_EXPIRY_MINUTES=15
NETRUN_AUTH_REFRESH_TOKEN_EXPIRY_DAYS=30

# Key Management (option 1: file paths)
NETRUN_AUTH_JWT_PRIVATE_KEY_PATH=/path/to/private_key.pem
NETRUN_AUTH_JWT_PUBLIC_KEY_PATH=/path/to/public_key.pem

# Key Management (option 2: direct content)
# NETRUN_AUTH_JWT_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
# NETRUN_AUTH_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."

# Redis Configuration
NETRUN_AUTH_REDIS_URL=redis://localhost:6379/0
NETRUN_AUTH_REDIS_KEY_PREFIX=netrun:auth:
NETRUN_AUTH_REDIS_TTL_BUFFER_SECONDS=300

# Password Configuration
NETRUN_AUTH_PASSWORD_MIN_LENGTH=12
NETRUN_AUTH_PASSWORD_REQUIRE_UPPERCASE=true
NETRUN_AUTH_PASSWORD_REQUIRE_NUMBERS=true
NETRUN_AUTH_PASSWORD_REQUIRE_SPECIAL=true

# Rate Limiting
NETRUN_AUTH_RATE_LIMIT_ENABLED=true
NETRUN_AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE=60
NETRUN_AUTH_RATE_LIMIT_BURST_SIZE=10

# Azure Key Vault (optional, for key rotation)
NETRUN_AUTH_AZURE_KEY_VAULT_URL=https://my-vault.vault.azure.us/
NETRUN_AUTH_AZURE_KEY_VAULT_SECRET_NAME=netrun-jwt-private-key

# Azure AD Integration (optional)
NETRUN_AUTH_AZURE_AD_TENANT_ID=00000000-0000-0000-0000-000000000000
NETRUN_AUTH_AZURE_AD_CLIENT_ID=00000000-0000-0000-0000-000000000000
NETRUN_AUTH_AZURE_AD_CLIENT_SECRET=your-secret-here
NETRUN_AUTH_AZURE_AD_REDIRECT_URI=http://localhost:8000/auth/callback
```

### Programmatic Configuration

Load configuration in Python:

```python
from netrun_auth import AuthConfig

# Load from environment variables (NETRUN_AUTH_* prefix)
config = AuthConfig()

# Override specific values
config = AuthConfig(
    jwt_issuer="my-app",
    redis_url="redis://myredis:6379/0",
    access_token_expiry_minutes=30
)

# Access configuration values
print(config.jwt_issuer)
print(config.redis_url)
print(config.access_token_expiry_minutes)
```

## Key Generation

### Option 1: Generate New Keys

Generate fresh RSA key pairs:

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# Save to files
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
with open("private_key.pem", "wb") as f:
    f.write(private_pem)

public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
with open("public_key.pem", "wb") as f:
    f.write(public_pem)
```

### Option 2: Using OpenSSL

Generate keys via OpenSSL:

```bash
# Generate private key
openssl genrsa -out private_key.pem 2048

# Extract public key
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

### Option 3: Use Azure Key Vault

Store keys in Azure Key Vault for automatic rotation:

```python
from netrun_auth import AuthConfig

config = AuthConfig(
    azure_key_vault_url="https://my-vault.vault.azure.us/",
    azure_key_vault_secret_name="netrun-jwt-private-key"
)
```

## Redis Setup

### Local Development

Run Redis locally via Docker:

```bash
docker run -d \
  --name netrun-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes
```

Connect:

```python
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379/0")
```

### Production

Use managed Redis service:

- **Azure**: Azure Cache for Redis
- **AWS**: ElastiCache
- **Google Cloud**: Cloud Memorystore
- **Self-hosted**: Redis Enterprise

Configure connection URL:

```python
config = AuthConfig(
    redis_url="redis://username:password@redis-host:6379/0"
)
```

## FastAPI Integration

### Add Middleware

```python
from fastapi import FastAPI
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
import redis.asyncio as redis

app = FastAPI()

# Initialize dependencies
config = AuthConfig()
jwt_manager = JWTManager(config)
redis_client = redis.from_url(config.redis_url)

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)
```

### Protect Routes

```python
from fastapi import Depends
from netrun_auth import get_current_user, require_roles
from netrun_auth.types import User

@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id}

@app.delete("/admin")
async def admin_only(user: User = Depends(require_roles("admin"))):
    return {"message": "Admin access granted"}
```

## Database Integration

netrun-auth is authentication-focused and doesn't require a specific database. However, you'll want to:

1. **Store Users**: Your user database schema
2. **Store Roles/Permissions**: Usually in same database
3. **Store API Keys**: For service-to-service authentication

Example schema (SQLAlchemy):

```python
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True)
    display_name = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

class Role(Base):
    __tablename__ = "roles"

    role_id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True)
    permissions = Column(String(2000))  # JSON list
    description = Column(String(500))

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(String(36), ForeignKey("users.user_id"), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.role_id"), primary_key=True)
```

## Verification

Verify installation by importing core modules:

```python
# Test imports
from netrun_auth import (
    JWTManager,
    AuthConfig,
    RBACManager,
    PasswordManager,
    AuthenticationError
)
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import get_current_user

print("netrun-auth installation successful!")
```

## Troubleshooting

### Redis Connection Error

```
ConnectionError: Error -2 connecting to localhost:6379
```

**Solution**: Ensure Redis is running
```bash
# Check Redis status
redis-cli ping  # Should return PONG

# Or use Docker
docker ps | grep redis
```

### Missing Dependencies

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution**: Install with extras
```bash
pip install netrun-auth[all]
```

### Key File Not Found

```
FileNotFoundError: [Errno 2] No such file or directory: 'private_key.pem'
```

**Solution**: Generate keys or set environment variables
```bash
# Generate keys
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Or set in .env
NETRUN_AUTH_JWT_PRIVATE_KEY_PATH=/full/path/to/private_key.pem
NETRUN_AUTH_JWT_PUBLIC_KEY_PATH=/full/path/to/public_key.pem
```

## Next Steps

- [Getting Started](./getting-started.md) - Quick tutorial
- [API Reference](./api/jwt.md) - Detailed API documentation
- [Security Best Practices](./security/best-practices.md) - Security guidelines
- [Azure AD Integration](./integrations/azure-ad.md) - Enterprise SSO setup

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
