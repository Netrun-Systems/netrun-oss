# Multi-Tenant Setup

Complete guide for multi-tenant SaaS application with netrun-auth.

## Architecture

```
SaaS Application
├── Organization A
│   ├── User 1 (org_id: org-a)
│   ├── User 2 (org_id: org-a)
│   └── Data (scoped to org-a)
├── Organization B
│   ├── User 3 (org_id: org-b)
│   ├── User 4 (org_id: org-b)
│   └── Data (scoped to org-b)
└── Organization C
    └── ...
```

## Database Schema

```sql
-- Organizations
CREATE TABLE organizations (
    org_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50),  -- free, pro, enterprise
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(org_id),
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, email)  -- Email unique within organization
);

-- User Roles
CREATE TABLE user_roles (
    user_id VARCHAR(36) NOT NULL REFERENCES users(user_id),
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(org_id),
    role VARCHAR(100) NOT NULL,
    PRIMARY KEY (user_id, org_id, role)
);

-- Organization Data (example)
CREATE TABLE projects (
    project_id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(org_id),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX (org_id)  -- Fast lookup by organization
);
```

## Token Generation with Organization

### Single Tenant Token

```python
# User logging in
token_pair = await jwt_manager.generate_token_pair(
    user_id=user_id,
    organization_id=org_id,  # Critical: include org_id
    roles=["user", "developer"],
    permissions=["projects:read", "projects:create"]
)
```

### Multi-Tenant Token Claims

```python
{
    "jti": "unique-token-id",
    "sub": "user123",
    "typ": "access",
    "iat": 1700000000,
    "exp": 1700900000,
    "iss": "my-saas-api",
    "aud": "my-saas-users",
    "user_id": "user123",
    "organization_id": "org-456",  # Organization scoping
    "roles": ["user", "developer"],
    "permissions": ["projects:read", "projects:create"],
    "session_id": "session-xyz"
}
```

## Route-Level Tenant Isolation

### Verify User Belongs to Organization

```python
from fastapi import FastAPI, Depends, Path
from netrun_auth.dependencies import get_current_user
from netrun_auth.types import User

app = FastAPI()

@app.get("/organizations/{org_id}/projects")
async def get_org_projects(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """Get projects for organization (verify ownership)."""

    # Verify user belongs to this organization
    if user.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized for this organization"
        )

    # User's org_id is cryptographically signed in JWT
    # Safe to use for database query scoping
    projects = await db.query_projects(org_id)

    return {"org_id": org_id, "projects": projects}
```

### Database Query Scoping

```python
# Good: Always scope by org_id
@app.get("/organizations/{org_id}/users")
async def get_org_users(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """Get users in organization."""

    # Verify authorization
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    # Query ALWAYS includes org_id filter
    users = await db.query(
        "SELECT * FROM users WHERE org_id = :org_id",
        {"org_id": org_id}
    )

    return users

# Bad: Missing org_id filter (data leak!)
@app.get("/organizations/{org_id}/users")
async def get_org_users_bad(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """VULNERABLE: Missing org_id filter."""

    # NO! Missing org_id in query - data leak!
    users = await db.query("SELECT * FROM users")

    return users
```

## Subdomains Per Organization

### Multi-Tenant with Subdomains

```
app.example.com          (sign up/sign in)
org-a.example.com        (Organization A data)
org-b.example.com        (Organization B data)
```

### Extract Organization from Subdomain

```python
from fastapi import FastAPI, Request
from netrun_auth.dependencies import get_current_user

app = FastAPI()

def get_organization_from_subdomain(request: Request) -> str:
    """Extract organization from subdomain."""

    host = request.headers.get("host", "")
    parts = host.split(".")

    if len(parts) >= 3:
        # Format: org-a.example.com
        return parts[0]

    # Default/main domain
    return None

def require_organization_subdomain():
    """Dependency to verify user owns subdomain organization."""

    async def dependency(
        request: Request,
        user: User = Depends(get_current_user)
    ) -> User:
        org_id = get_organization_from_subdomain(request)

        if not org_id or user.organization_id != org_id:
            raise HTTPException(status_code=403)

        return user

    return dependency

@app.get("/projects")
async def list_projects(user: User = Depends(require_organization_subdomain())):
    """List projects for organization (verified via subdomain)."""
    return await db.get_projects(user.organization_id)
```

## Multi-Tenant Admin Endpoints

### Organization Management

```python
@app.post("/admin/organizations", tags=["Admin"])
async def create_organization(
    request: CreateOrgRequest,
    user: User = Depends(require_roles("super_admin"))
):
    """Create new organization (super admin only)."""

    # Generate org_id
    org_id = secrets.token_urlsafe(16)

    # Create organization
    org = await db.create_organization(
        org_id=org_id,
        name=request.name,
        plan=request.plan
    )

    return {"org_id": org_id, "name": org.name}

@app.post("/admin/organizations/{org_id}/users/{user_id}/assign-role")
async def assign_org_role(
    org_id: str = Path(...),
    user_id: str = Path(...),
    role: str = Query(...),
    admin: User = Depends(require_roles("admin"))
):
    """Assign role to user within organization."""

    # Verify admin belongs to this organization
    if admin.organization_id != org_id:
        raise HTTPException(status_code=403)

    # Assign role scoped to organization
    await db.assign_user_role(user_id, org_id, role)

    return {"message": f"Role {role} assigned to user {user_id}"}

@app.get("/admin/organizations/{org_id}/audit-log")
async def get_org_audit_log(
    org_id: str = Path(...),
    skip: int = Query(default=0),
    limit: int = Query(default=100),
    admin: User = Depends(require_roles("admin"))
):
    """Get audit log for organization (admin only)."""

    # Verify admin belongs to this organization
    if admin.organization_id != org_id:
        raise HTTPException(status_code=403)

    # Fetch organization-scoped audit logs
    logs = await db.get_audit_logs(
        org_id=org_id,
        skip=skip,
        limit=limit
    )

    return {"org_id": org_id, "logs": logs}
```

### Cross-Organization Restrictions

```python
# Super Admin Only: Can see all organizations
@app.get("/super-admin/organizations")
async def list_all_orgs(admin: User = Depends(require_roles("super_admin"))):
    """List all organizations (super admin only)."""
    return await db.get_all_organizations()

# Org Admin: Can only see their organization
@app.get("/admin/organization")
async def get_my_org(admin: User = Depends(require_roles("admin"))):
    """Get my organization (admin role in any org)."""
    return await db.get_organization(admin.organization_id)

# Regular User: Can only see basic org info
@app.get("/organizations/{org_id}")
async def get_org_info(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """Get basic organization info."""
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    return await db.get_organization(org_id)
```

## Multi-Tenant Onboarding

### Invite Users to Organization

```python
from datetime import datetime, timedelta, timezone

@app.post("/organizations/{org_id}/invites", tags=["Users"])
async def invite_user(
    org_id: str = Path(...),
    request: InviteUserRequest,
    user: User = Depends(require_permissions("users:invite"))
):
    """Invite user to organization."""

    # Verify user belongs to organization
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    # Create invite token (1 hour expiry)
    invite_token = await jwt_manager.generate_invite_token(
        email=request.email,
        org_id=org_id,
        roles=request.roles,
        expires_in=3600
    )

    # Send invite email
    invite_link = f"https://{org_id}.example.com/accept-invite?token={invite_token}"
    await send_email(
        request.email,
        "Join our organization",
        f"Click here to join: {invite_link}"
    )

    return {"message": "Invite sent"}

@app.post("/accept-invite", tags=["Users"])
async def accept_invite(request: AcceptInviteRequest):
    """Accept organization invite."""

    # Validate invite token
    claims = await jwt_manager.validate_token(request.invite_token)

    org_id = claims.get("org_id")
    email = claims.get("email")
    roles = claims.get("roles", ["user"])

    # Check if user exists
    user = await db.get_user_by_email(email)

    if not user:
        # Create new user
        user = await db.create_user(
            email=email,
            org_id=org_id,
            password_hash=password_manager.hash_password(request.password),
            display_name=request.display_name
        )
    else:
        # Add user to organization
        await db.add_user_to_organization(user.user_id, org_id)

    # Assign roles
    for role in roles:
        await db.assign_user_role(user.user_id, org_id, role)

    # Generate tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user.user_id,
        organization_id=org_id,
        roles=roles
    )

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": "Bearer"
    }
```

## Billing & Plan-Based Access

### Plan-Based Feature Access

```python
from enum import Enum

class Plan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

def require_plan(*plans: Plan):
    """Dependency to restrict feature to plans."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        org = await db.get_organization(user.organization_id)
        if org.plan not in plans:
            raise HTTPException(
                status_code=403,
                detail=f"Feature requires {plans[0]} plan or higher"
            )
        return user

    return dependency

@app.post("/organizations/{org_id}/api-keys")
async def create_api_key(
    org_id: str = Path(...),
    user: User = Depends(require_plan(Plan.PRO, Plan.ENTERPRISE))
):
    """Create API key (Pro+ plans only)."""
    # Verify ownership
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    api_key = secrets.token_urlsafe(32)
    # ... store API key ...
    return {"api_key": api_key}
```

## Complete Multi-Tenant Example

```python
from fastapi import FastAPI, Depends, HTTPException, Path, Query
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import get_current_user
from netrun_auth.types import User

app = FastAPI(title="Multi-Tenant SaaS")

# Initialize
config = AuthConfig()
jwt_manager = JWTManager(config)

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    config=config
)

# ===== Organization Routes =====

@app.get("/organizations/{org_id}", tags=["Organizations"])
async def get_organization(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """Get organization (user must belong to it)."""
    if user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "org_id": org_id,
        "name": "Organization Name",
        "users": []
    }

@app.get("/organizations/{org_id}/projects", tags=["Projects"])
async def get_org_projects(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """Get projects for organization."""
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    # All queries scoped by org_id
    return {
        "org_id": org_id,
        "projects": []
    }

@app.post("/organizations", tags=["Organizations"])
async def create_organization(
    request,
    user: User = Depends(get_current_user)
):
    """Create organization for user."""
    # User becomes org admin
    org_id = secrets.token_urlsafe(16)

    # ... create org in database ...
    # ... assign user as admin ...

    return {"org_id": org_id}

# ===== User Management =====

@app.get("/organizations/{org_id}/members", tags=["Users"])
async def list_org_members(
    org_id: str = Path(...),
    user: User = Depends(get_current_user)
):
    """List members of organization."""
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    return {"org_id": org_id, "members": []}

@app.post("/organizations/{org_id}/invites", tags=["Users"])
async def invite_member(
    org_id: str = Path(...),
    request,
    user: User = Depends(get_current_user)
):
    """Invite user to organization."""
    if user.organization_id != org_id:
        raise HTTPException(status_code=403)

    # ... send invite ...
    return {"message": "Invite sent"}
```

## Security Considerations

### Critical: Always Verify Organization

```python
# ALWAYS verify user.organization_id matches path parameter
# Never trust client to specify organization_id

# Good
if user.organization_id != request.org_id:
    raise HTTPException(status_code=403)

# Bad (data leak!)
# No verification - user could access any org
await db.get_data(user_specified_org_id)
```

### Audit Logging

```python
# Log all cross-organization access attempts
@app.get("/data/{org_id}")
async def get_data(org_id: str, user: User = Depends(get_current_user)):
    if user.organization_id != org_id:
        # Log security event
        logger.warning(
            "Unauthorized cross-organization access attempt",
            extra={
                "user_id": user.user_id,
                "user_org": user.organization_id,
                "target_org": org_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        raise HTTPException(status_code=403)
    # Process request
```

### Database Performance

```sql
-- Index on organization_id for fast filtering
CREATE INDEX idx_projects_org_id ON projects(org_id);
CREATE INDEX idx_users_org_id ON users(org_id);

-- Composite indexes for common queries
CREATE INDEX idx_user_projects ON projects(org_id, user_id);
```

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
