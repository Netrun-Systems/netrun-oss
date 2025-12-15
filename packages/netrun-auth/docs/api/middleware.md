# Authentication Middleware API

Complete reference for the FastAPI authentication middleware.

## Overview

The `AuthenticationMiddleware` class:
- Validates Bearer token authentication
- Extracts and validates JWT claims
- Injects auth context into request state
- Implements rate limiting
- Adds security headers
- Logs authentication events

## AuthenticationMiddleware Class

FastAPI middleware for request-level authentication.

### Initialization

```python
from fastapi import FastAPI
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth import JWTManager, AuthConfig
import redis.asyncio as redis

app = FastAPI()

config = AuthConfig()
jwt_manager = JWTManager(config)
redis_client = redis.from_url(config.redis_url)

app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app` | `ASGIApp` | Yes | FastAPI/Starlette application |
| `jwt_manager` | `JWTManager` | Yes | JWT token manager instance |
| `redis_client` | `redis.Redis` | No | Redis client for rate limiting |
| `config` | `AuthConfig` | No | Authentication configuration |

### Request Processing Flow

```
HTTP Request
    ↓
Check Exempt Paths
    ↓ (if not exempt)
Extract Authorization Header
    ↓
Validate JWT Token
    ↓
Extract Claims
    ↓
Check Blacklist
    ↓
Rate Limiting Check (if enabled)
    ↓
Inject into request.state.auth
    ↓
Log Authentication Event
    ↓
Proceed to Route Handler
    ↓
Add Security Headers
    ↓
HTTP Response
```

## Configuration

### Exempt Paths

Paths that bypass authentication:

```python
config = AuthConfig(
    auth_exempt_paths=[
        "/health",
        "/docs",
        "/openapi.json",
        "/auth/login",
        "/auth/register",
        "/public/info"
    ]
)
```

### Rate Limiting

Configure rate limiting in middleware:

```python
config = AuthConfig(
    rate_limit_enabled=True,
    rate_limit_requests_per_minute=60,
    rate_limit_burst_size=10
)

app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,  # Required for rate limiting
    config=config
)
```

### Security Headers

Automatically added by middleware:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Request Context

### Accessing Authentication Context

```python
from fastapi import Request

@app.get("/me")
async def get_me(request: Request):
    """Access auth context from request state."""
    if hasattr(request.state, "auth"):
        auth = request.state.auth
        return {
            "user_id": auth.user_id,
            "organization_id": auth.organization_id,
            "roles": auth.roles,
            "authenticated_at": auth.authenticated_at,
            "auth_method": auth.auth_method
        }
    else:
        return {"authenticated": False}
```

### Request State Properties

| Property | Type | Description |
|----------|------|-------------|
| `request.state.auth` | `AuthContext` | Full authentication context |
| `request.state.authenticated` | `bool` | Whether request is authenticated |
| `request.state.user_id` | `str` | User ID from token |

## AuthContext Model

```python
from netrun_auth.types import AuthContext

@app.get("/context")
async def get_context(request: Request) -> dict:
    """Get full authentication context."""
    if not hasattr(request.state, "auth"):
        return {"error": "Not authenticated"}

    auth: AuthContext = request.state.auth

    return {
        "user_id": auth.user_id,                    # User unique ID
        "organization_id": auth.organization_id,    # Organization ID
        "roles": auth.roles,                        # User roles
        "permissions": auth.permissions,            # User permissions
        "session_id": auth.session_id,              # Session ID
        "authenticated_at": auth.authenticated_at,  # Auth timestamp
        "auth_method": auth.auth_method,            # JWT, API_KEY, etc.
        "token_jti": auth.token_jti,                # JWT ID
        "ip_address": auth.ip_address,              # Client IP
        "user_agent": auth.user_agent               # Client user agent
    }
```

## Error Handling

### Authentication Failed (401)

```python
{
    "error": "AUTHENTICATION_FAILED",
    "message": "Invalid or missing authentication",
    "details": {
        "reason": "Missing Authorization header"
    }
}
```

### Rate Limited (429)

```python
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
        "retry_after": 60
    }
}
```

### Token Expired (401)

```python
{
    "error": "TOKEN_EXPIRED",
    "message": "Token has expired",
    "details": {
        "expiration": "2025-11-25T12:00:00Z"
    }
}
```

## Complete Example

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.exceptions import AuthenticationError
import redis.asyncio as redis
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Authenticated API")

# Initialize
config = AuthConfig(
    rate_limit_enabled=True,
    rate_limit_requests_per_minute=100
)
jwt_manager = JWTManager(config)
redis_client = redis.from_url(config.redis_url)

# Add middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)

# Custom error handler
@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    """Custom authentication error handler."""
    logger.warning(f"Auth error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

# Health check (public)
@app.get("/health")
async def health():
    """Public health endpoint."""
    return {"status": "healthy"}

# Protected endpoints
@app.get("/protected")
async def protected(request: Request):
    """Protected endpoint requiring authentication."""
    if not hasattr(request.state, "auth"):
        return {"error": "Not authenticated"}

    auth = request.state.auth
    return {
        "message": f"Hello {auth.user_id}",
        "organization": auth.organization_id,
        "roles": auth.roles
    }

@app.get("/admin-only")
async def admin_only(request: Request):
    """Admin-only endpoint."""
    if not hasattr(request.state, "auth"):
        return {"error": "Not authenticated"}

    auth = request.state.auth

    if "admin" not in auth.roles:
        return {"error": "Admin role required"}, 403

    return {"message": "Admin access granted"}

@app.get("/rate-limit-test")
async def rate_limit_test(request: Request):
    """Test rate limiting."""
    if hasattr(request.state, "auth"):
        return {
            "message": "Request successful",
            "user_id": request.state.user_id
        }
    return {"message": "Anonymous request"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Testing Authenticated Requests

### Using Bearer Token

```bash
# Generate token (from login endpoint)
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/protected
```

### Using Python Requests

```python
import requests

token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

response = requests.get(
    "http://localhost:8000/protected",
    headers={"Authorization": f"Bearer {token}"}
)

print(response.json())
```

### Using FastAPI TestClient

```python
from fastapi.testclient import TestClient

client = TestClient(app)

# Without authentication
response = client.get("/protected")
assert response.status_code == 401

# With token
token = "valid_jwt_token"
response = client.get(
    "/protected",
    headers={"Authorization": f"Bearer {token}"}
)
assert response.status_code == 200
```

## Middleware Ordering

Position middleware in correct order:

```python
from fastapi.middleware.cors import CORSMiddleware
from netrun_auth.middleware import AuthenticationMiddleware

app = FastAPI()

# 1. CORS (must be first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 2. Authentication
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)

# 3. Other middleware...
```

## Performance Considerations

- **Token Validation**: ~1-2ms per request
- **Blacklist Lookup**: ~1-5ms (Redis lookup)
- **Rate Limiting**: ~1-5ms per request
- **Security Headers**: <1ms per response

## Troubleshooting

### Missing Authorization Header

```
Error: "Missing Authorization header"
```

**Solution**: Include Bearer token in request

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/protected
```

### Invalid Token Format

```
Error: "Invalid token format"
```

**Solution**: Ensure token format is "Bearer <token>"

```python
auth_header = request.headers.get("Authorization")
if not auth_header or not auth_header.startswith("Bearer "):
    raise HTTPException(status_code=401)
```

### Rate Limited

```
Error: "Rate limit exceeded, retry after 60 seconds"
Status: 429
```

**Solution**: Implement retry logic with exponential backoff

```python
import time

max_retries = 3
for attempt in range(max_retries):
    response = requests.get(url, headers=headers)
    if response.status_code != 429:
        break
    time.sleep(2 ** attempt)
```

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
