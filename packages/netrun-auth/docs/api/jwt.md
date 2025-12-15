# JWT Manager API

Complete reference for JWT token generation, validation, and management.

## Overview

The `JWTManager` class handles:
- RS256 JWT token generation and validation
- Token pair generation (access + refresh tokens)
- Token refresh with security validation
- Token blacklisting for revocation
- Rotating RSA key pairs with 90-day rotation

## KeyPair Class

Represents an RSA key pair with rotation support.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `key_id` | `str` | Unique identifier for key pair |
| `private_key` | `RSAPrivateKey` | RSA private key object |
| `public_key` | `RSAPublicKey` | RSA public key object |
| `created_at` | `datetime` | Key creation timestamp |
| `expires_at` | `datetime` | Key expiration (90 days after creation) |

### Methods

#### is_expired()

```python
def is_expired(self) -> bool:
    """Check if key pair has expired."""
```

Check if key pair has reached expiration date.

**Returns**: `bool` - True if expired, False otherwise

**Example**:

```python
key_pair = jwt_manager.key_pairs["key_id"]

if key_pair.is_expired():
    print("Key pair is expired, rotation recommended")
```

#### get_private_pem()

```python
def get_private_pem(self) -> bytes:
    """Get private key in PEM format."""
```

Export private key as PEM-encoded bytes.

**Returns**: `bytes` - PEM-encoded private key

**Example**:

```python
pem_bytes = key_pair.get_private_pem()

with open("private_key.pem", "wb") as f:
    f.write(pem_bytes)
```

#### get_public_pem()

```python
def get_public_pem(self) -> bytes:
    """Get public key in PEM format."""
```

Export public key as PEM-encoded bytes.

**Returns**: `bytes` - PEM-encoded public key

**Example**:

```python
pem_bytes = key_pair.get_public_pem()

with open("public_key.pem", "wb") as f:
    f.write(pem_bytes)
```

## JWTManager Class

RS256 JWT token manager with Redis-backed blacklisting.

### Initialization

```python
from netrun_auth import JWTManager, AuthConfig
import redis.asyncio as redis

config = AuthConfig()
redis_client = redis.from_url(config.redis_url)

jwt_manager = JWTManager(config, redis_client)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `config` | `AuthConfig` | Authentication configuration |
| `redis_client` | `redis.Redis` | Redis client for blacklist |
| `key_pairs` | `Dict[str, KeyPair]` | Active key pairs |
| `current_key_id` | `str` | ID of current signing key |

### Methods

#### generate_token_pair()

```python
async def generate_token_pair(
    user_id: str,
    organization_id: Optional[str] = None,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    custom_claims: Optional[Dict[str, Any]] = None
) -> TokenPair:
    """
    Generate access and refresh token pair.

    Args:
        user_id: User unique identifier
        organization_id: Organization identifier (optional)
        roles: List of user roles (optional)
        permissions: List of user permissions (optional)
        session_id: Session identifier (optional, auto-generated if not provided)
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)
        custom_claims: Additional JWT claims (optional)

    Returns:
        TokenPair with access_token, refresh_token, and expires_in

    Raises:
        AuthenticationError: If configuration is invalid

    Example:
        token_pair = await jwt_manager.generate_token_pair(
            user_id="user123",
            organization_id="org456",
            roles=["user", "developer"],
            permissions=["users:read", "projects:create"],
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0..."
        )

        return {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": "Bearer",
            "expires_in": token_pair.expires_in
        }
    """
```

**Returns**: `TokenPair`

TokenPair model:

```python
class TokenPair(BaseModel):
    access_token: str              # JWT token (15 min expiry)
    refresh_token: str             # JWT token (30 day expiry)
    token_type: str = "Bearer"     # Token type
    expires_in: int                # Seconds until access token expires
```

**Security Notes**:
- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 30 days (configurable)
- Both tokens use RS256 signing with rotating keys
- Sessions are tracked in Redis

#### validate_token()

```python
async def validate_token(
    token: str,
    token_type: Optional[TokenType] = None,
    verify_signature: bool = True,
    verify_exp: bool = True,
    verify_aud: bool = True,
    verify_iss: bool = True
) -> TokenClaims:
    """
    Validate JWT token and return claims.

    Args:
        token: JWT token string
        token_type: Expected token type (optional)
        verify_signature: Verify RSA signature (default: True)
        verify_exp: Verify expiration (default: True)
        verify_aud: Verify audience claim (default: True)
        verify_iss: Verify issuer claim (default: True)

    Returns:
        TokenClaims with decoded claims

    Raises:
        TokenInvalidError: Token signature invalid
        TokenExpiredError: Token has expired
        TokenBlacklistedError: Token is revoked
        AuthenticationError: Token format invalid

    Example:
        try:
            claims = await jwt_manager.validate_token(token)
            print(f"User: {claims.user_id}")
            print(f"Roles: {claims.roles}")
        except TokenExpiredError:
            # Generate new token using refresh token
            new_token = await jwt_manager.refresh_token(refresh_token)
        except TokenInvalidError:
            # Return 401 Unauthorized
            raise HTTPException(status_code=401, detail="Invalid token")
    """
```

**Returns**: `TokenClaims`

TokenClaims model:

```python
class TokenClaims(BaseModel):
    jti: str                       # JWT unique ID
    sub: str                       # Subject (user_id)
    typ: TokenType                 # Token type (access/refresh)
    iat: int                       # Issued at timestamp
    exp: int                       # Expiration timestamp
    nbf: int = 0                   # Not before timestamp
    iss: str                       # Issuer
    aud: str                       # Audience
    user_id: str                   # User ID
    organization_id: Optional[str] # Organization ID
    roles: List[str]               # User roles
    permissions: List[str]         # User permissions
    session_id: Optional[str]      # Session ID
    ip_address: Optional[str]      # IP address
    user_agent: Optional[str]      # User agent
```

#### refresh_token()

```python
async def refresh_token(
    refresh_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> TokenPair:
    """
    Generate new access token using refresh token.

    Args:
        refresh_token: Refresh token from login
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)

    Returns:
        TokenPair with new access and refresh tokens

    Raises:
        TokenInvalidError: Refresh token is invalid
        TokenExpiredError: Refresh token is expired
        TokenBlacklistedError: Refresh token is revoked
        AuthenticationError: Token validation failed

    Example:
        # When access token expires (401 response)
        refresh_response = await jwt_manager.refresh_token(
            refresh_token=user_refresh_token,
            ip_address=request.client.host
        )

        # Return new tokens to client
        return {
            "access_token": refresh_response.access_token,
            "refresh_token": refresh_response.refresh_token,
            "expires_in": refresh_response.expires_in
        }
    """
```

**Returns**: `TokenPair`

**Security Notes**:
- Old refresh token is blacklisted to prevent reuse
- New refresh token is issued with updated timestamp
- IP address and user agent validation (if available)

#### blacklist_token()

```python
async def blacklist_token(
    token: str,
    reason: Optional[str] = None,
    ttl: Optional[int] = None
) -> bool:
    """
    Revoke token by adding to blacklist.

    Args:
        token: JWT token to revoke
        reason: Reason for revocation (audit logging)
        ttl: Time-to-live in seconds (default: token expiry)

    Returns:
        bool - True if token was blacklisted

    Raises:
        AuthenticationError: If token cannot be decoded

    Example:
        # On logout
        token_from_header = request.headers.get("Authorization", "").replace("Bearer ", "")

        await jwt_manager.blacklist_token(
            token=token_from_header,
            reason="user_logout"
        )

        return {"message": "Logged out successfully"}
    """
```

**Returns**: `bool`

**Security Notes**:
- Token is stored in Redis with TTL matching token expiration
- After token expiry, entry is automatically deleted
- Blacklist check on every token validation

#### is_blacklisted()

```python
async def is_blacklisted(token: str) -> bool:
    """
    Check if token has been revoked.

    Args:
        token: JWT token to check

    Returns:
        bool - True if token is blacklisted

    Example:
        if await jwt_manager.is_blacklisted(token):
            raise TokenBlacklistedError("Token has been revoked")
    """
```

**Returns**: `bool`

## Configuration

### AuthConfig

Settings for JWT token generation:

```python
from netrun_auth import AuthConfig

config = AuthConfig(
    # JWT Configuration
    jwt_algorithm="RS256",                      # Signing algorithm
    jwt_issuer="my-app-name",                   # Issuer claim
    jwt_audience="my-api",                      # Audience claim
    access_token_expiry_minutes=15,             # Access token TTL
    refresh_token_expiry_days=30,               # Refresh token TTL

    # Key Management
    jwt_private_key_path="/path/to/private.pem",
    jwt_public_key_path="/path/to/public.pem",

    # Redis
    redis_url="redis://localhost:6379/0",
    redis_key_prefix="netrun:auth:",
    redis_ttl_buffer_seconds=300
)
```

## Exception Handling

### TokenInvalidError

```python
from netrun_auth.exceptions import TokenInvalidError

try:
    claims = await jwt_manager.validate_token(token)
except TokenInvalidError as e:
    print(f"Error code: {e.error_code}")  # TOKEN_INVALID
    print(f"Status: {e.status_code}")     # 401
    # Return 401 Unauthorized
```

### TokenExpiredError

```python
from netrun_auth.exceptions import TokenExpiredError

try:
    claims = await jwt_manager.validate_token(token)
except TokenExpiredError as e:
    # Request refresh using refresh token
    print("Token expired, use refresh token")
    # Return 401 with hint to refresh
```

### TokenBlacklistedError

```python
from netrun_auth.exceptions import TokenBlacklistedError

try:
    claims = await jwt_manager.validate_token(token)
except TokenBlacklistedError as e:
    print("Token has been revoked")
    # Return 401 Unauthorized
```

## Complete Example

```python
from fastapi import FastAPI, Depends, HTTPException, status
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.types import TokenPair, TokenClaims
from netrun_auth.exceptions import (
    TokenInvalidError,
    TokenExpiredError,
    TokenBlacklistedError
)
import redis.asyncio as redis

app = FastAPI()

# Initialize
config = AuthConfig()
redis_client = redis.from_url(config.redis_url)
jwt_manager = JWTManager(config, redis_client)

@app.post("/login")
async def login(username: str, password: str) -> dict:
    """Generate tokens on successful login."""
    # Validate credentials...
    user_id = "user123"

    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_id,
        roles=["user"],
        permissions=["users:read"]
    )

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "expires_in": token_pair.expires_in
    }

@app.post("/refresh")
async def refresh(refresh_token: str) -> dict:
    """Refresh access token."""
    try:
        token_pair = await jwt_manager.refresh_token(refresh_token)
        return {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "expires_in": token_pair.expires_in
        }
    except (TokenInvalidError, TokenExpiredError) as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/logout")
async def logout(token: str):
    """Logout by blacklisting token."""
    await jwt_manager.blacklist_token(token, reason="user_logout")
    return {"message": "Logged out"}

@app.get("/validate")
async def validate(token: str) -> dict:
    """Validate token and return claims."""
    try:
        claims = await jwt_manager.validate_token(token)
        return claims.to_dict()
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
```

## Security Best Practices

1. **Key Rotation**: Keys rotate automatically every 90 days
2. **Token Expiry**: Access tokens expire in 15 minutes minimum
3. **Refresh Tokens**: Stored securely, single-use on refresh
4. **Blacklisting**: Revoked tokens checked on every request
5. **RS256 Signing**: Asymmetric cryptography (private key signing, public key validation)

## Performance Considerations

- Token validation is fast: ~1ms per token
- Blacklist lookup uses Redis: ~1-5ms depending on network
- Key rotation is transparent and automatic
- No database queries required (JWT stateless design)

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
