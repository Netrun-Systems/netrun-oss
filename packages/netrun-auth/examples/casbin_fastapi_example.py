"""
Casbin RBAC Integration Example - FastAPI

Demonstrates netrun-auth v1.1.0 Casbin integration with:
- Multi-tenant RBAC
- FastAPI middleware authorization
- Custom resource mapping
- PostgreSQL persistence (optional)

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-03
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

# Import netrun-auth components
from netrun_auth import (
    CasbinRBACManager,
    CasbinAuthMiddleware,
    AuthenticationMiddleware,
    JWTManager,
    AuthConfig,
    get_current_user,
    User,
)
from netrun_auth.middleware_casbin import path_prefix_mapper


# ============================================================================
# Configuration
# ============================================================================

class AppConfig:
    """Application configuration."""
    MULTI_TENANT = True
    DATABASE_URL = "postgresql://user:pass@localhost/netrun_auth"  # Optional
    USE_REDIS = False  # Set to True to use Redis adapter


# ============================================================================
# Models
# ============================================================================

class UserResponse(BaseModel):
    """User response model."""
    user_id: str
    email: str
    organization_id: str
    roles: List[str]


class PermissionRequest(BaseModel):
    """Permission request model."""
    user_id: str
    role: str
    organization_id: str


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Casbin RBAC Example",
    description="netrun-auth v1.1.0 Casbin integration demo",
    version="1.1.0",
)


# ============================================================================
# Initialization
# ============================================================================

# Initialize authentication components
config = AuthConfig()
jwt_manager = JWTManager(config)

# Initialize Casbin RBAC manager
rbac_manager = CasbinRBACManager(multi_tenant=AppConfig.MULTI_TENANT)

# Optional: Use PostgreSQL adapter for persistence
if AppConfig.DATABASE_URL:
    try:
        from casbin_async_sqlalchemy_adapter import Adapter
        adapter = Adapter(AppConfig.DATABASE_URL)
        rbac_manager = CasbinRBACManager(
            adapter=adapter,
            multi_tenant=AppConfig.MULTI_TENANT
        )
        print("✓ Using PostgreSQL adapter for Casbin policies")
    except ImportError:
        print("! PostgreSQL adapter not available, using memory adapter")

# Optional: Use Redis adapter for distributed caching
if AppConfig.USE_REDIS:
    try:
        from casbin_redis_adapter import Adapter
        adapter = Adapter("redis://localhost:6379")
        rbac_manager = CasbinRBACManager(
            adapter=adapter,
            multi_tenant=AppConfig.MULTI_TENANT
        )
        print("✓ Using Redis adapter for Casbin policies")
    except ImportError:
        print("! Redis adapter not available, using memory adapter")


@app.on_event("startup")
async def startup():
    """Initialize RBAC policies on startup."""
    print("Initializing Casbin RBAC Manager...")
    await rbac_manager.initialize()

    # Setup default roles and permissions
    print("Setting up default RBAC policies...")

    # Organization 1 permissions
    org1 = "org1"
    await rbac_manager.add_permission_for_role("admin", "/api/users", "read", tenant_id=org1)
    await rbac_manager.add_permission_for_role("admin", "/api/users", "create", tenant_id=org1)
    await rbac_manager.add_permission_for_role("admin", "/api/users", "update", tenant_id=org1)
    await rbac_manager.add_permission_for_role("admin", "/api/users", "delete", tenant_id=org1)
    await rbac_manager.add_permission_for_role("admin", "/api/projects", "read", tenant_id=org1)
    await rbac_manager.add_permission_for_role("admin", "/api/projects", "create", tenant_id=org1)
    await rbac_manager.add_permission_for_role("admin", "/api/projects", "delete", tenant_id=org1)

    await rbac_manager.add_permission_for_role("user", "/api/projects", "read", tenant_id=org1)
    await rbac_manager.add_permission_for_role("user", "/api/projects", "create", tenant_id=org1)

    await rbac_manager.add_permission_for_role("viewer", "/api/projects", "read", tenant_id=org1)

    # Assign roles to users in org1
    await rbac_manager.add_role_for_user("admin_user", "admin", tenant_id=org1)
    await rbac_manager.add_role_for_user("regular_user", "user", tenant_id=org1)
    await rbac_manager.add_role_for_user("viewer_user", "viewer", tenant_id=org1)

    # Organization 2 permissions (separate tenant)
    org2 = "org2"
    await rbac_manager.add_permission_for_role("admin", "/api/users", "read", tenant_id=org2)
    await rbac_manager.add_permission_for_role("admin", "/api/users", "create", tenant_id=org2)
    await rbac_manager.add_role_for_user("admin_user_org2", "admin", tenant_id=org2)

    print("✓ RBAC policies initialized successfully")


# ============================================================================
# Middleware
# ============================================================================

# Add authentication middleware (validates JWT and sets request.state.user)
app.add_middleware(AuthenticationMiddleware, jwt_manager=jwt_manager)

# Add Casbin authorization middleware
# Custom resource mapper: map URL prefixes to resource names
resource_mapper = path_prefix_mapper({
    "/api/users": "/api/users",
    "/api/projects": "/api/projects",
    "/api/admin": "/api/admin",
})

app.add_middleware(
    CasbinAuthMiddleware,
    rbac_manager=rbac_manager,
    excluded_paths=["/", "/health", "/docs", "/redoc", "/openapi.json", "/admin/permissions"],
    resource_mapper=resource_mapper,
)


# ============================================================================
# Public Routes (No Authentication Required)
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Casbin RBAC Example API",
        "version": "1.1.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "users": "/api/users",
            "projects": "/api/projects",
            "admin": "/admin/permissions",
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "rbac": "casbin"}


# ============================================================================
# Protected Routes (Authentication + Authorization Required)
# ============================================================================

@app.get("/api/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_current_user)):
    """
    Get all users (requires admin role).

    Permission: /api/users:read
    """
    # Authorization already enforced by CasbinAuthMiddleware
    return [
        UserResponse(
            user_id="user1",
            email="user1@example.com",
            organization_id=current_user.organization_id,
            roles=["admin"]
        ),
        UserResponse(
            user_id="user2",
            email="user2@example.com",
            organization_id=current_user.organization_id,
            roles=["user"]
        ),
    ]


@app.post("/api/users", response_model=UserResponse)
async def create_user(current_user: User = Depends(get_current_user)):
    """
    Create new user (requires admin role).

    Permission: /api/users:create
    """
    return UserResponse(
        user_id="new_user",
        email="new_user@example.com",
        organization_id=current_user.organization_id,
        roles=["user"]
    )


@app.get("/api/projects")
async def get_projects(current_user: User = Depends(get_current_user)):
    """
    Get all projects (requires user or admin role).

    Permission: /api/projects:read
    """
    return {
        "projects": [
            {"id": "proj1", "name": "Project Alpha"},
            {"id": "proj2", "name": "Project Beta"},
        ],
        "organization_id": current_user.organization_id,
    }


@app.post("/api/projects")
async def create_project(current_user: User = Depends(get_current_user)):
    """
    Create new project (requires user or admin role).

    Permission: /api/projects:create
    """
    return {
        "project": {"id": "proj_new", "name": "New Project"},
        "created_by": current_user.user_id,
    }


@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete project (requires admin role).

    Permission: /api/projects:delete
    """
    return {
        "deleted": True,
        "project_id": project_id,
        "deleted_by": current_user.user_id,
    }


# ============================================================================
# Admin Routes (Permission Management)
# ============================================================================

@app.post("/admin/permissions/assign")
async def assign_permission(
    request: PermissionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Assign role to user (admin only).

    Note: This endpoint is excluded from middleware authorization
    and manually checks for admin role.
    """
    # Manual permission check (since this is excluded from middleware)
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Assign role
    success = await rbac_manager.add_role_for_user(
        user_id=request.user_id,
        role=request.role,
        tenant_id=request.organization_id
    )

    return {
        "success": success,
        "user_id": request.user_id,
        "role": request.role,
        "organization_id": request.organization_id,
    }


@app.get("/admin/permissions/roles/{user_id}")
async def get_user_roles(
    user_id: str,
    organization_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all roles for a user (admin only)."""
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    roles = await rbac_manager.get_roles_for_user(
        user_id=user_id,
        tenant_id=organization_id
    )

    return {
        "user_id": user_id,
        "organization_id": organization_id,
        "roles": roles,
    }


@app.get("/admin/permissions/role/{role}")
async def get_role_permissions(
    role: str,
    organization_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all permissions for a role (admin only)."""
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    permissions = await rbac_manager.get_permissions_for_role(
        role=role,
        tenant_id=organization_id
    )

    return {
        "role": role,
        "organization_id": organization_id,
        "permissions": [{"resource": r, "action": a} for r, a in permissions],
    }


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
        }
    )


# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print("Starting Casbin RBAC Example API")
    print("="*70)
    print("\nEndpoints:")
    print("  - Docs: http://localhost:8000/docs")
    print("  - Health: http://localhost:8000/health")
    print("  - Users: http://localhost:8000/api/users (admin only)")
    print("  - Projects: http://localhost:8000/api/projects (user/admin)")
    print("\nDefault Users:")
    print("  - admin_user (org1): Full access to users and projects")
    print("  - regular_user (org1): Read/create projects only")
    print("  - viewer_user (org1): Read projects only")
    print("  - admin_user_org2 (org2): Full access in org2 (isolated)")
    print("\n" + "="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
