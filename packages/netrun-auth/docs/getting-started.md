# Getting Started Guide

Step-by-step tutorial to integrate netrun-auth into your FastAPI application.

## 5-Minute Quick Start

### Step 1: Install Package

```bash
pip install netrun-auth[fastapi]
```

### Step 2: Create Configuration

Create `.env` file:

```env
NETRUN_AUTH_JWT_ISSUER=my-api
NETRUN_AUTH_JWT_AUDIENCE=my-users
NETRUN_AUTH_REDIS_URL=redis://localhost:6379/0
```

### Step 3: Generate Keys

```bash
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

Set in `.env`:

```env
NETRUN_AUTH_JWT_PRIVATE_KEY_PATH=./private_key.pem
NETRUN_AUTH_JWT_PUBLIC_KEY_PATH=./public_key.pem
```

### Step 4: Create FastAPI App

Create `main.py`:

```python
from fastapi import FastAPI, Depends
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import get_current_user
from netrun_auth.types import User
import redis.asyncio as redis

# Initialize
config = AuthConfig()
jwt_manager = JWTManager(config)
redis_client = redis.from_url(config.redis_url)

app = FastAPI()

# Add middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)

# Protected route
@app.get("/me")
async def get_profile(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id}

# Login endpoint (example)
@app.post("/login")
async def login(username: str, password: str):
    # Validate credentials in your user database...
    user_id = "user123"

    # Generate tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_id,
        organization_id="org456",
        roles=["user"]
    )

    return token_pair.model_dump()
```

### Step 5: Test

```bash
# Start Redis
redis-server

# Start server
uvicorn main:app --reload

# Get token (in another terminal)
curl -X POST http://localhost:8000/login \
  -d "username=demo&password=password"

# Use token
TOKEN="<access_token_from_login>"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me
```

## Complete Tutorial

### 1. Setup Project

Create project structure:

```
my-api/
├── main.py
├── config.py
├── auth.py
├── models.py
├── .env
├── private_key.pem
└── public_key.pem
```

### 2. Configuration (config.py)

```python
from netrun_auth import AuthConfig
import os

# Load from environment
config = AuthConfig()

# Verify configuration
def verify_config():
    """Verify all required configuration is present."""
    required = [
        "jwt_issuer",
        "jwt_audience",
        "redis_url"
    ]

    for item in required:
        if not getattr(config, item):
            raise ValueError(f"Missing configuration: {item}")

    print("Configuration verified successfully")

# Import and call on startup
if __name__ == "__main__":
    verify_config()
```

### 3. Authentication Module (auth.py)

```python
from netrun_auth import (
    JWTManager,
    RBACManager,
    PasswordManager,
    AuthConfig
)
import redis.asyncio as redis
from typing import Optional

# Global instances
config = AuthConfig()
jwt_manager: Optional[JWTManager] = None
rbac_manager: Optional[RBACManager] = None
password_manager: Optional[PasswordManager] = None
redis_client: Optional[redis.Redis] = None

async def initialize():
    """Initialize authentication managers."""
    global jwt_manager, rbac_manager, password_manager, redis_client

    redis_client = redis.from_url(config.redis_url)
    jwt_manager = JWTManager(config, redis_client)
    rbac_manager = RBACManager()
    password_manager = PasswordManager(config)

async def shutdown():
    """Clean up resources."""
    if redis_client:
        await redis_client.close()
```

### 4. Models (models.py)

```python
from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str

class UserInfo(BaseModel):
    """User information model."""
    user_id: str
    email: str
    display_name: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
```

### 5. Main Application (main.py)

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import redis.asyncio as redis

from config import config
from auth import initialize as init_auth, shutdown as shutdown_auth
from auth import jwt_manager, redis_client
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import (
    get_current_user,
    require_roles,
    require_permissions
)
from netrun_auth.types import User
from netrun_auth.exceptions import AuthenticationError
from models import LoginRequest, TokenResponse, RefreshTokenRequest

app = FastAPI(
    title="My API",
    description="API with netrun-auth authentication",
    version="1.0.0"
)

# Lifecycle events
@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    await init_auth()

    # Add middleware
    app.add_middleware(
        AuthenticationMiddleware,
        jwt_manager=jwt_manager,
        redis_client=redis_client,
        config=config
    )

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await shutdown_auth()

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    # TODO: Verify credentials against your user database
    # This is a simplified example

    if request.email == "demo@example.com" and request.password == "password":
        user_id = "user123"

        # Generate tokens
        token_pair = await jwt_manager.generate_token_pair(
            user_id=user_id,
            organization_id="org456",
            roles=["user"],
            permissions=["users:read", "projects:read"]
        )

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    try:
        token_pair = await jwt_manager.refresh_token(request.refresh_token)

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )

@app.post("/auth/logout")
async def logout(user: User = Depends(get_current_user)):
    """Logout by blacklisting current token."""
    # TODO: Implement token extraction from request
    return {"message": "Logged out successfully"}

# Protected endpoints
@app.get("/me")
async def get_profile(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "user_id": user.user_id,
        "roles": user.roles,
        "permissions": user.permissions
    }

@app.get("/admin")
async def admin_only(user: User = Depends(require_roles("admin"))):
    """Admin-only endpoint."""
    return {"message": f"Admin access for {user.user_id}"}

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_permissions("users:delete"))
):
    """Delete user (requires users:delete permission)."""
    # TODO: Implement user deletion
    return {"message": f"Deleted user {user_id}"}

# Error handling
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request, exc):
    """Handle authentication errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 6. Run Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis
redis-server

# Run server
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Common Tasks

### Generate User Tokens

```python
# In your login endpoint or user service
token_pair = await jwt_manager.generate_token_pair(
    user_id="user123",
    organization_id="org456",
    roles=["user", "developer"],
    permissions=["users:read", "projects:create", "projects:read"]
)

# Return to client
return {
    "access_token": token_pair.access_token,
    "refresh_token": token_pair.refresh_token,
    "token_type": "Bearer",
    "expires_in": token_pair.expires_in
}
```

### Validate Tokens

```python
from netrun_auth.exceptions import TokenInvalidError, TokenExpiredError

try:
    claims = await jwt_manager.validate_token(token)
    print(f"Token valid for user: {claims.user_id}")
except TokenExpiredError:
    print("Token has expired")
except TokenInvalidError:
    print("Token is invalid")
```

### Check User Permissions

```python
from netrun_auth.dependencies import require_permissions

@app.post("/projects/{project_id}")
async def update_project(
    project_id: str,
    user: User = Depends(require_permissions("projects:update"))
):
    """Only users with projects:update permission can access."""
    return {"project_id": project_id, "updated": True}
```

### Create Custom Roles

```python
from netrun_auth import RBACManager
from netrun_auth.types import Role

rbac = RBACManager()

# Create custom role
custom_role = Role(
    name="project_manager",
    permissions=[
        "projects:read",
        "projects:create",
        "projects:update",
        "users:read",
        "teams:manage"
    ],
    description="Project management role"
)

rbac.add_role(custom_role)
```

### Implement Multi-Tenant Support

```python
@app.get("/organizations/{org_id}/data")
async def get_org_data(
    org_id: str,
    user: User = Depends(get_current_user)
):
    """Get organization data (user must belong to org)."""
    if user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this organization"
        )

    # Return organization-specific data
    return {"org_id": org_id, "data": []}
```

## Next Steps

1. **API Reference** - Explore [JWT Manager API](./api/jwt.md)
2. **Azure AD** - Setup [Azure AD integration](./integrations/azure-ad.md)
3. **Security** - Read [security best practices](./security/best-practices.md)
4. **Examples** - See [complete examples](./examples/fastapi-app.md)

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
