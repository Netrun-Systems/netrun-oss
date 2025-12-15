# Exception Reference

Complete reference for netrun-auth exception classes.

## Exception Hierarchy

```
Exception
├── AuthenticationError (status_code: 401)
│   ├── TokenInvalidError
│   ├── TokenExpiredError
│   ├── TokenBlacklistedError
│   ├── APIKeyInvalidError
│   ├── SessionExpiredError
│   ├── RateLimitExceededError
│   └── AuthorizationError (status_code: 403)
│       ├── PermissionDeniedError
│       └── RoleNotFoundError
```

## AuthenticationError

Base exception for all authentication failures.

### Properties

```python
message: str              # Error message
error_code: str           # Error code (e.g., "AUTH_ERROR")
status_code: int          # HTTP status code (default: 401)
details: Dict[str, Any]   # Additional error details
```

### Methods

```python
def to_dict(self) -> Dict[str, Any]:
    """Convert exception to JSON-serializable dictionary."""
    return {
        "error": self.error_code,
        "message": self.message,
        "details": self.details
    }
```

### Example

```python
from netrun_auth.exceptions import AuthenticationError

raise AuthenticationError(
    message="Invalid credentials",
    error_code="INVALID_CREDENTIALS",
    status_code=401,
    details={"reason": "User not found"}
)
```

## TokenInvalidError

Invalid JWT token signature or format.

### Status Code
401 Unauthorized

### Error Code
`TOKEN_INVALID`

### Causes

- Token signature invalid
- Token format malformed
- Token algorithm not recognized
- Token claims invalid

### Example

```python
from netrun_auth.exceptions import TokenInvalidError
from fastapi import HTTPException

try:
    claims = await jwt_manager.validate_token(token)
except TokenInvalidError as e:
    raise HTTPException(status_code=401, detail=str(e))
```

### JSON Response

```json
{
    "error": "TOKEN_INVALID",
    "message": "Invalid token",
    "details": {}
}
```

## TokenExpiredError

JWT token has expired.

### Status Code
401 Unauthorized

### Error Code
`TOKEN_EXPIRED`

### Causes

- Access token older than 15 minutes
- Refresh token older than 30 days
- Manually blacklisted token

### Example

```python
from netrun_auth.exceptions import TokenExpiredError

try:
    claims = await jwt_manager.validate_token(token)
except TokenExpiredError as e:
    # Client should refresh token
    raise HTTPException(
        status_code=401,
        detail="Token expired, please refresh"
    )
```

### Recovery

Use refresh token to get new access token:

```python
new_token_pair = await jwt_manager.refresh_token(refresh_token)
```

### JSON Response

```json
{
    "error": "TOKEN_EXPIRED",
    "message": "Token has expired",
    "details": {
        "expiration": "2025-11-25T12:00:00Z"
    }
}
```

## TokenBlacklistedError

Token has been revoked (logged out or invalidated).

### Status Code
401 Unauthorized

### Error Code
`TOKEN_BLACKLISTED`

### Causes

- User logged out
- Admin revoked token
- Security incident revocation
- Compromised token

### Example

```python
from netrun_auth.exceptions import TokenBlacklistedError

try:
    claims = await jwt_manager.validate_token(token)
except TokenBlacklistedError as e:
    # User must login again
    raise HTTPException(status_code=401, detail="Token revoked")
```

### JSON Response

```json
{
    "error": "TOKEN_BLACKLISTED",
    "message": "Token has been revoked",
    "details": {
        "reason": "user_logout"
    }
}
```

## APIKeyInvalidError

Invalid or missing API key.

### Status Code
401 Unauthorized

### Error Code
`API_KEY_INVALID`

### Causes

- API key not provided
- API key format invalid
- API key not found
- API key expired
- API key inactive

### Example

```python
from netrun_auth.exceptions import APIKeyInvalidError

try:
    # Validate API key
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise APIKeyInvalidError("API key required")
except APIKeyInvalidError as e:
    raise HTTPException(status_code=401, detail=str(e))
```

### JSON Response

```json
{
    "error": "API_KEY_INVALID",
    "message": "Invalid API key",
    "details": {}
}
```

## SessionExpiredError

User session has expired.

### Status Code
401 Unauthorized

### Error Code
`SESSION_EXPIRED`

### Causes

- Session TTL exceeded
- User logged out
- Admin invalidated session
- Device token revoked

### Example

```python
from netrun_auth.exceptions import SessionExpiredError

try:
    session = await session_manager.validate_session(session_id)
except SessionExpiredError as e:
    raise HTTPException(status_code=401, detail="Session expired")
```

### JSON Response

```json
{
    "error": "SESSION_EXPIRED",
    "message": "Session has expired",
    "details": {
        "expiration": "2025-11-25T15:30:00Z"
    }
}
```

## RateLimitExceededError

Rate limit exceeded for user or IP.

### Status Code
429 Too Many Requests

### Error Code
`RATE_LIMIT_EXCEEDED`

### Causes

- Too many requests in time window
- Brute force detection
- API quota exceeded

### Example

```python
from netrun_auth.exceptions import RateLimitExceededError

try:
    await rate_limiter.check_limit(user_id)
except RateLimitExceededError as e:
    raise HTTPException(
        status_code=429,
        detail="Rate limit exceeded",
        headers={"Retry-After": str(e.details["retry_after"])}
    )
```

### JSON Response

```json
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
        "retry_after": 60
    }
}
```

## AuthorizationError

Base exception for permission/authorization failures.

### Status Code
403 Forbidden

### Error Code
`AUTHORIZATION_ERROR`

### Example

```python
from netrun_auth.exceptions import AuthorizationError

raise AuthorizationError(
    message="Insufficient permissions",
    error_code="PERMISSION_DENIED"
)
```

## PermissionDeniedError

User lacks required permission.

### Status Code
403 Forbidden

### Error Code
`PERMISSION_DENIED`

### Causes

- User role lacks permission
- Permission revoked
- Organization-level restriction
- Resource-level restriction

### Example

```python
from netrun_auth.exceptions import PermissionDeniedError

if not user.has_permission("users:delete"):
    raise PermissionDeniedError(
        message="Cannot delete users",
        permission="users:delete"
    )
```

### JSON Response

```json
{
    "error": "PERMISSION_DENIED",
    "message": "Permission denied",
    "details": {
        "required_permission": "users:delete"
    }
}
```

## RoleNotFoundError

Required role not found in system.

### Status Code
403 Forbidden

### Error Code
`ROLE_NOT_FOUND`

### Causes

- Role doesn't exist
- Role was deleted
- Role name misspelled

### Example

```python
from netrun_auth.exceptions import RoleNotFoundError

role = rbac.get_role("nonexistent_role")
if not role:
    raise RoleNotFoundError(
        message="Role not found",
        role="nonexistent_role"
    )
```

### JSON Response

```json
{
    "error": "ROLE_NOT_FOUND",
    "message": "Required role not found",
    "details": {
        "required_role": "nonexistent_role"
    }
}
```

## Exception Handling Patterns

### Global Exception Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from netrun_auth.exceptions import AuthenticationError

app = FastAPI()

@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    """Handle all authentication exceptions globally."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )
```

### Route-Level Handling

```python
from fastapi import HTTPException
from netrun_auth.exceptions import TokenExpiredError, TokenInvalidError

@app.get("/protected")
async def protected_route():
    try:
        claims = await jwt_manager.validate_token(token)
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token expired")
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Dependency-Level Handling

```python
from fastapi import Depends, HTTPException
from netrun_auth.dependencies import get_current_user
from netrun_auth.exceptions import PermissionDeniedError

def require_admin():
    async def dependency(user = Depends(get_current_user)):
        if "admin" not in user.roles:
            raise HTTPException(status_code=403, detail="Admin required")
        return user
    return dependency

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user = Depends(require_admin())
):
    return {"deleted": user_id}
```

## Error Response Format

All exceptions return consistent JSON:

```json
{
    "error": "ERROR_CODE",
    "message": "Human readable message",
    "details": {
        "field": "value"
    }
}
```

## Common Exception Scenarios

### Scenario 1: Expired Token

```
Request: GET /protected (with 30-day-old access token)
        ↓
Middleware: Validates token
        ↓
Exception: TokenExpiredError
        ↓
Response: 401 {"error": "TOKEN_EXPIRED"}
        ↓
Client: Uses refresh token to get new access token
        ↓
Retry: GET /protected (with new access token) ✓
```

### Scenario 2: Invalid Credentials

```
Request: POST /login {"email": "user@example.com", "password": "wrong"}
        ↓
Route Handler: Checks credentials
        ↓
Exception: AuthenticationError("Invalid credentials")
        ↓
Response: 401 {"error": "AUTHENTICATION_ERROR"}
        ↓
Client: Prompts user to try again
```

### Scenario 3: Insufficient Permissions

```
Request: DELETE /users/123 (user has "user" role, not "admin")
        ↓
Dependency: require_permissions("users:delete")
        ↓
Check: User has permission?
        ↓
Exception: PermissionDeniedError("users:delete")
        ↓
Response: 403 {"error": "PERMISSION_DENIED"}
        ↓
Client: Shows "Not authorized for this action"
```

### Scenario 4: Rate Limited

```
Request: GET /api/data (user made 100 requests in 1 minute)
        ↓
Middleware: Check rate limit
        ↓
Exception: RateLimitExceededError(retry_after=60)
        ↓
Response: 429 {"error": "RATE_LIMIT_EXCEEDED", "retry_after": 60}
        ↓
Client: Waits 60 seconds before retry
```

## Testing Exceptions

```python
import pytest
from fastapi.testclient import TestClient
from netrun_auth.exceptions import TokenExpiredError

client = TestClient(app)

def test_expired_token():
    """Test handling of expired token."""
    expired_token = "expired_jwt_token"

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401
    assert response.json()["error"] == "TOKEN_EXPIRED"

def test_missing_permission():
    """Test permission denial."""
    response = client.delete(
        "/users/123",
        headers={"Authorization": f"Bearer {user_token}"}
    )

    assert response.status_code == 403
    assert response.json()["error"] == "PERMISSION_DENIED"
```

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
