# Complete FastAPI Application Example

Full-featured FastAPI application with netrun-auth authentication.

## Project Structure

```
my-api/
├── main.py                 # FastAPI application
├── config.py               # Configuration
├── models.py               # Pydantic models
├── auth_handlers.py        # Authentication routes
├── protected_routes.py     # Protected endpoints
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── private_key.pem         # RSA private key
└── public_key.pem          # RSA public key
```

## 1. Environment Configuration (.env)

```env
# JWT Configuration
NETRUN_AUTH_JWT_ISSUER=my-api
NETRUN_AUTH_JWT_AUDIENCE=my-users
NETRUN_AUTH_ACCESS_TOKEN_EXPIRY_MINUTES=15
NETRUN_AUTH_REFRESH_TOKEN_EXPIRY_DAYS=30

# Key Management
NETRUN_AUTH_JWT_PRIVATE_KEY_PATH=./private_key.pem
NETRUN_AUTH_JWT_PUBLIC_KEY_PATH=./public_key.pem

# Redis
NETRUN_AUTH_REDIS_URL=redis://localhost:6379/0

# Password Policy
NETRUN_AUTH_PASSWORD_MIN_LENGTH=12
NETRUN_AUTH_PASSWORD_REQUIRE_UPPERCASE=true
NETRUN_AUTH_PASSWORD_REQUIRE_NUMBERS=true
NETRUN_AUTH_PASSWORD_REQUIRE_SPECIAL=true

# Rate Limiting
NETRUN_AUTH_RATE_LIMIT_ENABLED=true
NETRUN_AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

## 2. Configuration Module (config.py)

```python
from netrun_auth import AuthConfig
import os

# Load configuration from environment
config = AuthConfig()

# Verify required settings
def verify_configuration():
    """Verify all required configuration is present."""
    required_fields = [
        "jwt_issuer",
        "jwt_audience",
        "redis_url"
    ]

    for field in required_fields:
        value = getattr(config, field, None)
        if not value:
            raise ValueError(f"Missing required configuration: {field}")

    print(f"Configuration verified:")
    print(f"  Issuer: {config.jwt_issuer}")
    print(f"  Audience: {config.jwt_audience}")
    print(f"  Redis: {config.redis_url}")

if __name__ == "__main__":
    verify_configuration()
```

## 3. Models (models.py)

```python
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    display_name: str

class UserCreate(UserBase):
    """User creation model."""
    password: str

class User(UserBase):
    """User response model."""
    user_id: str
    roles: List[str] = []
    permissions: List[str] = []
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
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

class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str

class RoleAssignment(BaseModel):
    """Role assignment model."""
    user_id: str
    role: str
```

## 4. Main Application (main.py)

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis.asyncio as redis
import logging

from config import config
from models import (
    UserCreate, LoginRequest, TokenResponse,
    RefreshTokenRequest, ChangePasswordRequest
)
from netrun_auth import (
    JWTManager, AuthConfig, RBACManager, PasswordManager
)
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import (
    get_current_user,
    require_roles,
    require_permissions,
    get_current_user_optional
)
from netrun_auth.types import User
from netrun_auth.exceptions import AuthenticationError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
jwt_manager: JWTManager = None
rbac_manager: RBACManager = None
password_manager: PasswordManager = None
redis_client: redis.Redis = None

# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    global jwt_manager, rbac_manager, password_manager, redis_client

    logger.info("Starting up...")

    redis_client = redis.from_url(config.redis_url)
    jwt_manager = JWTManager(config, redis_client)
    rbac_manager = RBACManager()
    password_manager = PasswordManager(config)

    logger.info("Authentication managers initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if redis_client:
        await redis_client.close()
    logger.info("Application shut down")

# Create FastAPI app
app = FastAPI(
    title="Secure API with netrun-auth",
    description="Complete example with authentication and authorization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)

# Exception handlers
@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request, exc: AuthenticationError):
    """Handle authentication exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

# Health check (public)
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ==================== Authentication Endpoints ====================

@app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
async def register(request: UserCreate):
    """Register new user."""

    # Validate password strength
    errors = password_manager.validate_password(request.password)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid password", "details": errors}
        )

    # Check if user exists
    # existing_user = await db.get_user_by_email(request.email)
    # if existing_user:
    #     raise HTTPException(status_code=409, detail="User already exists")

    # Hash password
    hashed_password = password_manager.hash_password(request.password)

    # Create user (mock)
    # user = await db.create_user(
    #     email=request.email,
    #     display_name=request.display_name,
    #     password_hash=hashed_password
    # )

    user_id = "user123"  # Mock

    # Generate tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_id,
        roles=["user"]
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in
    )

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """Login with email and password."""

    # Get user from database
    # user = await db.get_user_by_email(request.email)
    # if not user:
    #     raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    # if not password_manager.verify_password(request.password, user.password_hash):
    #     raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = "user123"  # Mock
    roles = ["user"]

    # Generate tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_id,
        roles=roles,
        permissions=["users:read", "projects:read"]
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in
    )

@app.post("/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token."""

    try:
        token_pair = await jwt_manager.refresh_token(request.refresh_token)
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/logout", tags=["Authentication"])
async def logout(user: User = Depends(get_current_user)):
    """Logout by blacklisting token."""
    # Token would be extracted from request and blacklisted
    return {"message": "Logged out successfully"}

@app.post("/auth/change-password", tags=["Authentication"])
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user)
):
    """Change user password."""

    # Get user from database
    # current_user = await db.get_user(user.user_id)

    # Verify current password
    # if not password_manager.verify_password(
    #     request.current_password,
    #     current_user.password_hash
    # ):
    #     raise HTTPException(status_code=401, detail="Current password incorrect")

    # Validate new password
    errors = password_manager.validate_password(request.new_password)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid password", "details": errors}
        )

    # Hash and update
    # new_hash = password_manager.hash_password(request.new_password)
    # current_user.password_hash = new_hash
    # await db.save(current_user)

    return {"message": "Password changed successfully"}

# ==================== User Endpoints ====================

@app.get("/me", tags=["Users"])
async def get_profile(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "user_id": user.user_id,
        "roles": user.roles,
        "permissions": user.permissions
    }

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(
    user_id: str,
    user: User = Depends(require_permissions("users:read"))
):
    """Get user by ID (requires users:read permission)."""
    # user_data = await db.get_user(user_id)
    return {
        "user_id": user_id,
        "email": "user@example.com",
        "display_name": "User Name"
    }

@app.delete("/users/{user_id}", tags=["Users"])
async def delete_user(
    user_id: str,
    user: User = Depends(require_permissions("users:delete"))
):
    """Delete user (requires users:delete permission)."""
    # await db.delete_user(user_id)
    return {"message": f"User {user_id} deleted"}

# ==================== Admin Endpoints ====================

@app.get("/admin", tags=["Admin"])
async def admin_panel(user: User = Depends(require_roles("admin"))):
    """Admin panel (requires admin role)."""
    return {
        "message": "Welcome to admin panel",
        "user_id": user.user_id
    }

@app.post("/admin/users/{user_id}/roles/{role}", tags=["Admin"])
async def assign_role(
    user_id: str,
    role: str,
    user: User = Depends(require_roles("admin"))
):
    """Assign role to user (admin only)."""

    # Verify role exists
    if not rbac_manager.get_role(role):
        raise HTTPException(status_code=404, detail="Role not found")

    # Assign role
    # await db.assign_role(user_id, role)

    return {"message": f"Role {role} assigned to user {user_id}"}

@app.post("/admin/audit-log", tags=["Admin"])
async def get_audit_log(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(require_roles("admin"))
):
    """Get audit log (admin only)."""
    # logs = await db.get_audit_logs(skip=skip, limit=limit)
    return {
        "total": 0,
        "logs": []
    }

# ==================== Optional Routes ====================

@app.get("/public-data", tags=["Public"])
async def get_public_data(user: User = Depends(get_current_user_optional)):
    """Get public data (works with or without authentication)."""
    if user:
        return {
            "data": ["public", "private"],
            "authenticated": True,
            "user_id": user.user_id
        }
    return {
        "data": ["public"],
        "authenticated": False
    }

@app.get("/roles", tags=["Admin"])
async def list_roles(user: User = Depends(require_roles("admin"))):
    """List all available roles."""
    return {"roles": rbac_manager.list_roles()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
```

## 5. Requirements (requirements.txt)

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6

# Authentication
netrun-auth[all]==1.0.0
PyJWT==2.8.1
cryptography==41.0.7
passlib==1.7.4
argon2-cffi==23.1.0

# Async
redis==5.0.1
httpx==0.25.2

# Database (if using)
sqlalchemy==2.0.23
asyncpg==0.29.0

# Utilities
python-dotenv==1.0.0
```

## 6. Running the Application

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate keys
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Start Redis
redis-server

# Configure .env file
cp .env.example .env
```

### Run Server

```bash
# Development
uvicorn main:app --reload

# Production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

Access at: http://localhost:8000

API Docs: http://localhost:8000/docs (Swagger UI)

## 7. Testing the API

### Register User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "display_name": "John Doe",
    "password": "SecurePass123!"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### Use Token

```bash
TOKEN="<access_token_from_login>"

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## 8. Integration Testing

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register():
    """Test user registration."""
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login():
    """Test login."""
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    assert response.json()["token_type"] == "Bearer"

def test_protected_without_token():
    """Test protected endpoint without token."""
    response = client.get("/me")
    assert response.status_code == 401

def test_protected_with_token():
    """Test protected endpoint with token."""
    # Login first
    login_response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    token = login_response.json()["access_token"]

    # Access protected endpoint
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "user_id" in response.json()
```

## 9. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NETRUN_AUTH_REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Run with: `docker-compose up`

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
