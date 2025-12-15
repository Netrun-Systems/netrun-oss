# FastAPI Dependencies API

Complete reference for FastAPI dependency injection functions.

## Overview

FastAPI dependencies for:
- Extracting authenticated users
- Role-based authorization
- Permission-based authorization
- Multi-tenant access control

All dependencies raise `HTTPException(status_code=401 or 403)` on authorization failure.

## Core Dependencies

### get_auth_context()

```python
from fastapi import Depends, Request
from netrun_auth.dependencies import get_auth_context
from netrun_auth.types import AuthContext

@app.get("/protected")
async def protected(auth: AuthContext = Depends(get_auth_context)):
    """Get full authentication context from middleware."""
    return {
        "user_id": auth.user_id,
        "organization_id": auth.organization_id,
        "roles": auth.roles,
        "permissions": auth.permissions,
        "authenticated_at": auth.authenticated_at,
        "auth_method": auth.auth_method,
        "session_id": auth.session_id,
        "ip_address": auth.ip_address,
        "user_agent": auth.user_agent
    }
```

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated

**Returns**: `AuthContext`

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `user_id` | `str` | User unique identifier |
| `organization_id` | `Optional[str]` | Organization ID |
| `roles` | `List[str]` | User roles |
| `permissions` | `List[str]` | User permissions |
| `session_id` | `str` | Session identifier |
| `authenticated_at` | `datetime` | Authentication timestamp |
| `auth_method` | `str` | JWT, API_KEY, or OAUTH |
| `token_jti` | `Optional[str]` | JWT unique ID |
| `ip_address` | `Optional[str]` | Client IP |
| `user_agent` | `Optional[str]` | Client user agent |

### get_current_user()

```python
from fastapi import Depends
from netrun_auth.dependencies import get_current_user
from netrun_auth.types import User

@app.get("/me")
async def get_profile(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "roles": user.roles,
        "permissions": user.permissions,
        "organization_id": user.organization_id
    }
```

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated

**Returns**: `User`

**User Model**:

```python
class User(BaseModel):
    user_id: str                    # User unique ID
    organization_id: Optional[str]  # Organization ID
    roles: List[str]                # User roles
    permissions: List[str]          # User permissions
    session_id: Optional[str]       # Session ID
    email: Optional[str]            # User email
    display_name: Optional[str]     # Display name

    # Helper methods
    def has_role(self, role: str) -> bool
    def has_any_role(self, *roles: str) -> bool
    def has_all_roles(self, *roles: str) -> bool
    def has_permission(self, permission: str) -> bool
    def has_any_permission(self, *permissions: str) -> bool
    def has_all_permissions(self, *permissions: str) -> bool
```

## Optional Authentication

### get_current_user_optional()

```python
from typing import Optional
from fastapi import Depends
from netrun_auth.dependencies import get_current_user_optional
from netrun_auth.types import User

@app.get("/public-data")
async def get_public_data(user: Optional[User] = Depends(get_current_user_optional)):
    """Access public data, enhanced if authenticated."""
    if user:
        return {
            "data": ["public", "private"],
            "user_id": user.user_id
        }
    return {
        "data": ["public"],
        "user_id": None
    }
```

**Raises**: None (returns None if not authenticated)

**Returns**: `Optional[User]`

## Role-Based Authorization

### require_roles()

```python
from fastapi import Depends
from netrun_auth.dependencies import require_roles
from netrun_auth.types import User

@app.get("/admin")
async def admin_only(user: User = Depends(require_roles("admin"))):
    """Require admin role (OR logic - user needs at least one)."""
    return {"message": f"Admin access for {user.user_id}"}

@app.get("/managers")
async def managers(user: User = Depends(require_roles("manager", "admin", "super_admin"))):
    """Require one of: manager, admin, or super_admin."""
    return {"message": "Manager access granted"}
```

**Parameters**:
- `*roles` - Variable number of role names (OR logic)

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated
- `HTTPException(status_code=403)` - If user lacks required role

**Returns**: `User`

### require_all_roles()

```python
from fastapi import Depends
from netrun_auth.dependencies import require_all_roles
from netrun_auth.types import User

@app.delete("/secure-operation")
async def secure_op(user: User = Depends(require_all_roles("admin", "security_clearance"))):
    """Require ALL specified roles (AND logic)."""
    return {"message": "Secure operation executed"}
```

**Parameters**:
- `*roles` - Variable number of role names (AND logic)

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated
- `HTTPException(status_code=403)` - If user lacks all required roles

**Returns**: `User`

## Permission-Based Authorization

### require_permissions()

```python
from fastapi import Depends
from netrun_auth.dependencies import require_permissions
from netrun_auth.types import User

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_permissions("users:delete"))
):
    """Require one of the specified permissions (OR logic)."""
    return {"message": f"Deleted user {user_id}"}

@app.post("/projects")
async def create_project(user: User = Depends(require_permissions("projects:create", "admin:all"))):
    """User needs projects:create OR admin:all permission."""
    return {"project_id": "proj123"}
```

**Format**: Permission strings in `resource:action` format

**Examples**:
- `users:read` - Read users
- `users:delete` - Delete users
- `projects:create` - Create projects
- `admin:*` - All admin permissions
- `*:*` - All permissions

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated
- `HTTPException(status_code=403)` - If user lacks required permission

**Returns**: `User`

### require_all_permissions()

```python
from fastapi import Depends
from netrun_auth.dependencies import require_all_permissions
from netrun_auth.types import User

@app.patch("/critical-config")
async def update_config(
    user: User = Depends(require_all_permissions("admin:config", "audit:log"))
):
    """Require ALL specified permissions (AND logic)."""
    return {"config": "updated"}
```

**Parameters**:
- `*permissions` - Variable number of permission strings (AND logic)

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated
- `HTTPException(status_code=403)` - If user lacks all required permissions

**Returns**: `User`

## Organization-Based Access Control

### require_organization()

```python
from fastapi import Depends, Path
from netrun_auth.dependencies import require_organization
from netrun_auth.types import User

@app.get("/organizations/{org_id}/data")
async def get_org_data(
    org_id: str = Path(...),
    user: User = Depends(require_organization)
):
    """Ensure user belongs to specified organization."""
    if user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized for this org")

    return {"org_id": org_id, "data": []}
```

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated
- `HTTPException(status_code=403)` - If user not in organization

**Returns**: `User`

## Self-Service with Override

### require_self_or_permission()

```python
from fastapi import Depends, Path
from netrun_auth.dependencies import require_self_or_permission
from netapi.types import User

@app.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: str = Path(...),
    user: User = Depends(require_self_or_permission("users:read"))
):
    """Allow user to access own profile OR require users:read permission."""
    # User can access their own profile or if they have users:read permission
    if user.user_id == user_id or user.has_permission("users:read"):
        return {"user_id": user_id, "data": {}}

    raise HTTPException(status_code=403, detail="Not authorized")
```

**Parameters**:
- `*permissions` - Permissions that override self-service restriction

**Raises**:
- `HTTPException(status_code=401)` - If not authenticated
- `HTTPException(status_code=403)` - If user can't access

**Returns**: `User`

## Combining Dependencies

### Multiple Authorization Checks

```python
from fastapi import Depends
from netrun_auth.dependencies import require_roles, require_permissions
from netrun_auth.types import User

# Custom dependency combining multiple checks
def admin_with_delete_permission(user: User = Depends(require_roles("admin"))):
    """Require admin role AND delete permission."""
    if not user.has_permission("users:delete"):
        raise HTTPException(status_code=403, detail="Delete permission required")
    return user

@app.delete("/critical-user/{user_id}")
async def delete_critical_user(
    user_id: str,
    user: User = Depends(admin_with_delete_permission)
):
    """Require admin role with delete permission."""
    return {"deleted": user_id}
```

### Conditional Dependencies

```python
from fastapi import Depends, Query
from netrun_auth.dependencies import get_current_user_optional
from netrun_auth.types import User
from typing import Optional

@app.get("/search")
async def search(
    query: str = Query(...),
    user: Optional[User] = Depends(get_current_user_optional),
    limit: int = Query(default=10)
):
    """Search with optional authentication for enhanced results."""
    if user:
        # Logged-in user: 100 results
        max_results = 100
    else:
        # Anonymous: 10 results
        max_results = 10

    return {
        "query": query,
        "results": [],
        "limit": min(limit, max_results)
    }
```

## Error Responses

### 401 Unauthorized

No authentication provided or token invalid:

```json
{
    "detail": "Authentication required"
}
```

### 403 Forbidden

Authenticated but lacks required role/permission:

```json
{
    "detail": "Insufficient permissions"
}
```

## Helper Methods on User

```python
user: User = Depends(get_current_user)

# Check single role
if user.has_role("admin"):
    # Admin-only logic

# Check multiple roles (OR)
if user.has_any_role("admin", "manager"):
    # Admin or manager

# Check multiple roles (AND)
if user.has_all_roles("admin", "security"):
    # Both admin and security roles

# Check permission
if user.has_permission("users:delete"):
    # Can delete users

# Check multiple permissions (OR)
if user.has_any_permission("users:delete", "admin:delete"):
    # Can delete

# Check multiple permissions (AND)
if user.has_all_permissions("projects:create", "projects:deploy"):
    # Can create and deploy
```

## Complete Example

```python
from fastapi import FastAPI, Depends, Path
from netrun_auth.dependencies import (
    get_auth_context,
    get_current_user,
    require_roles,
    require_permissions,
    get_current_user_optional
)
from netrun_auth.types import User, AuthContext
from typing import Optional

app = FastAPI()

# Public endpoint
@app.get("/public")
async def public_endpoint():
    return {"message": "Public access"}

# Optional authentication
@app.get("/optional")
async def optional_auth(user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return {"authenticated": True, "user_id": user.user_id}
    return {"authenticated": False}

# Required authentication
@app.get("/protected")
async def protected(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id}

# Role-based
@app.get("/admin")
async def admin_only(user: User = Depends(require_roles("admin"))):
    return {"message": "Admin access"}

# Permission-based
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str = Path(...),
    user: User = Depends(require_permissions("users:delete"))
):
    return {"deleted": user_id}

# Full context
@app.get("/context")
async def get_context(auth: AuthContext = Depends(get_auth_context)):
    return {
        "user_id": auth.user_id,
        "organization_id": auth.organization_id,
        "authenticated_at": auth.authenticated_at,
        "auth_method": auth.auth_method
    }
```

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
