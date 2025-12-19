#!/usr/bin/env python3
"""
Netrun Service Library - Authentication Example

Demonstrates netrun-auth features including JWT management,
RBAC with Casbin, and FastAPI middleware integration.

Requirements:
    pip install netrun-auth[all] netrun-logging
    pip install fastapi uvicorn

Run:
    uvicorn auth_example:app --reload
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, Request, HTTPException
from pydantic import BaseModel

# ============================================================================
# LOGGING (Optional but recommended)
# ============================================================================
from netrun_logging import configure_logging, get_logger

configure_logging(service_name="auth-demo", environment="development")
logger = get_logger(__name__)

# ============================================================================
# JWT MANAGEMENT
# ============================================================================
from netrun_auth import JWTManager
from netrun_auth.models import TokenPayload

# Initialize JWT manager
jwt_manager = JWTManager(
    secret_key="your-secure-secret-key-change-in-production",
    algorithm="HS256",
    expiry_minutes=60,
)

# Create tokens
def demo_jwt_creation():
    """Demonstrate JWT token creation."""
    # Simple token
    simple_token = jwt_manager.create_token(sub="user-123")
    print(f"Simple token: {simple_token[:50]}...")

    # Token with roles and custom claims
    full_token = jwt_manager.create_token(
        sub="user-456",
        roles=["admin", "user"],
        custom_claims={
            "tenant_id": "tenant-abc",
            "email": "admin@example.com",
        },
    )
    print(f"Full token: {full_token[:50]}...")

    # Decode token
    payload = jwt_manager.decode_token(full_token)
    print(f"Decoded payload: sub={payload.sub}, roles={payload.roles}")

    return full_token


# ============================================================================
# RBAC WITH CASBIN
# ============================================================================
from netrun_auth.rbac import RBACManager

# Initialize RBAC manager
rbac_manager = RBACManager()

# Define policies
rbac_manager.add_policy("admin", "/api/users", "write")
rbac_manager.add_policy("admin", "/api/users", "read")
rbac_manager.add_policy("user", "/api/users", "read")
rbac_manager.add_policy("user", "/api/profile", "*")

# Add role inheritance
rbac_manager.add_role_for_user("alice", "admin")
rbac_manager.add_role_for_user("bob", "user")


def demo_rbac():
    """Demonstrate RBAC permission checking."""
    # Check permissions
    print("\nRBAC Permission Checks:")
    print(f"alice -> /api/users (write): {rbac_manager.check('alice', '/api/users', 'write')}")
    print(f"alice -> /api/users (read): {rbac_manager.check('alice', '/api/users', 'read')}")
    print(f"bob -> /api/users (write): {rbac_manager.check('bob', '/api/users', 'write')}")
    print(f"bob -> /api/users (read): {rbac_manager.check('bob', '/api/users', 'read')}")
    print(f"bob -> /api/profile (read): {rbac_manager.check('bob', '/api/profile', 'read')}")


# ============================================================================
# PASSWORD HASHING
# ============================================================================
from netrun_auth.password import PasswordHasher

# Initialize password hasher (Argon2 by default)
password_hasher = PasswordHasher()


def demo_password_hashing():
    """Demonstrate secure password hashing."""
    password = "my-secure-password"

    # Hash password
    hashed = password_hasher.hash(password)
    print(f"\nPassword Hashing:")
    print(f"Original: {password}")
    print(f"Hashed: {hashed[:50]}...")

    # Verify password
    is_valid = password_hasher.verify(password, hashed)
    print(f"Verification: {is_valid}")

    # Wrong password
    is_invalid = password_hasher.verify("wrong-password", hashed)
    print(f"Wrong password: {is_invalid}")


# ============================================================================
# MFA / TOTP
# ============================================================================
from netrun_auth.mfa import TOTPManager

totp_manager = TOTPManager()


def demo_mfa():
    """Demonstrate MFA/TOTP setup and verification."""
    print("\nMFA/TOTP Demo:")

    # Generate secret for user
    secret = totp_manager.generate_secret()
    print(f"TOTP Secret: {secret}")

    # Generate provisioning URI for authenticator apps
    uri = totp_manager.get_provisioning_uri(
        secret=secret,
        account_name="user@example.com",
        issuer_name="NetrunDemo",
    )
    print(f"Provisioning URI: {uri[:80]}...")

    # Generate current code (in production, user enters this from their app)
    current_code = totp_manager.generate_code(secret)
    print(f"Current TOTP Code: {current_code}")

    # Verify code
    is_valid = totp_manager.verify_code(secret, current_code)
    print(f"Code Valid: {is_valid}")


# ============================================================================
# FASTAPI INTEGRATION
# ============================================================================
app = FastAPI(title="Auth Demo", version="1.0.0")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


# Simulated user database
USERS_DB = {
    "admin": {
        "password_hash": password_hasher.hash("admin123"),
        "roles": ["admin", "user"],
    },
    "demo": {
        "password_hash": password_hasher.hash("demo123"),
        "roles": ["user"],
    },
}


async def get_current_user(request: Request) -> Optional[TokenPayload]:
    """Extract and validate JWT from request."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    try:
        return jwt_manager.decode_token(token)
    except Exception as e:
        logger.warning("token_validation_failed", error=str(e))
        return None


def require_auth(user: Optional[TokenPayload] = Depends(get_current_user)) -> TokenPayload:
    """Require authenticated user."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_role(required_role: str):
    """Require specific role."""
    def role_checker(user: TokenPayload = Depends(require_auth)) -> TokenPayload:
        if required_role not in (user.roles or []):
            raise HTTPException(status_code=403, detail=f"Role '{required_role}' required")
        return user
    return role_checker


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT."""
    user = USERS_DB.get(request.username)
    if not user or not password_hasher.verify(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt_manager.create_token(
        sub=request.username,
        roles=user["roles"],
    )

    logger.info("user_logged_in", username=request.username)
    return TokenResponse(access_token=token)


@app.get("/auth/me")
async def get_me(user: TokenPayload = Depends(require_auth)):
    """Get current user info."""
    return {"user_id": user.sub, "roles": user.roles}


@app.get("/admin/users")
async def list_users(user: TokenPayload = Depends(require_role("admin"))):
    """Admin-only endpoint."""
    return {"users": list(USERS_DB.keys())}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


# ============================================================================
# STANDALONE DEMO
# ============================================================================
def main():
    """Run standalone demonstrations."""
    print("=" * 60)
    print("Netrun Auth Demo")
    print("=" * 60)

    print("\n1. JWT Token Creation")
    demo_jwt_creation()

    print("\n2. RBAC Permission Checking")
    demo_rbac()

    print("\n3. Password Hashing")
    demo_password_hashing()

    print("\n4. MFA/TOTP")
    demo_mfa()

    print("\n" + "=" * 60)
    print("Run with: uvicorn auth_example:app --reload")
    print("Then test:")
    print("  POST /auth/login  {username: 'admin', password: 'admin123'}")
    print("  GET  /auth/me     (with Bearer token)")
    print("  GET  /admin/users (admin role required)")
    print("=" * 60)


if __name__ == "__main__":
    main()
