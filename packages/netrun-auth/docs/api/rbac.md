# RBAC Manager API

Complete reference for Role-Based Access Control management.

## Overview

The `RBACManager` class provides:
- Role definition and management
- Permission aggregation
- Role hierarchy and inheritance
- Permission validation
- Built-in role templates

## RBACManager Class

### Initialization

```python
from netrun_auth import RBACManager

rbac = RBACManager()
```

Built-in roles automatically initialized:
- `viewer` - Read-only access
- `user` - Standard user with read/write
- `admin` - Full administrative access
- `super_admin` - System-wide access

### Adding Roles

```python
from netrun_auth import RBACManager
from netrun_auth.types import Role

rbac = RBACManager()

# Create and add role
developer_role = Role(
    name="developer",
    permissions=[
        "projects:read",
        "projects:create",
        "projects:update",
        "services:read",
        "services:execute",
        "code:push",
        "code:review"
    ],
    description="Developer role with project access"
)

rbac.add_role(developer_role)
```

### Role Hierarchy

Create roles that inherit from other roles:

```python
# Parent role
viewer_role = Role(
    name="viewer",
    permissions=["users:read", "projects:read"],
    description="Read-only access"
)
rbac.add_role(viewer_role)

# Child role inheriting from viewer
user_role = Role(
    name="user",
    permissions=["projects:create", "projects:update"],
    inherits_from=["viewer"],  # Inherits viewer permissions
    description="User with create/update on own projects"
)
rbac.add_role(user_role)

# User with "user" role has:
# - users:read (inherited)
# - projects:read (inherited)
# - projects:create (own)
# - projects:update (own)
```

### Permission Model

Permissions follow `resource:action` format:

```
users:read          # Read user data
users:create        # Create new users
users:update        # Update user data
users:delete        # Delete users
users:*             # All user actions

projects:read       # Read project data
projects:create     # Create projects
projects:update     # Update projects
projects:delete     # Delete projects

admin:*             # All admin actions
system:*            # All system-level actions
```

## Methods

### add_role()

```python
def add_role(self, role: Role) -> None:
    """
    Add new role to system.

    Args:
        role: Role object with name, permissions, and optional inheritance

    Raises:
        ValueError: If role name already exists

    Example:
        rbac.add_role(Role(
            name="editor",
            permissions=["posts:read", "posts:create", "posts:edit"],
            description="Content editor"
        ))
    """
```

### get_role()

```python
def get_role(self, role_name: str) -> Optional[Role]:
    """
    Get role by name.

    Args:
        role_name: Name of role to retrieve

    Returns:
        Role object or None if not found

    Example:
        admin_role = rbac.get_role("admin")
        if admin_role:
            print(f"Admin permissions: {admin_role.permissions}")
    """
```

### has_permission()

```python
def has_permission(
    self,
    user_roles: List[str],
    permission: str
) -> bool:
    """
    Check if user (via roles) has specific permission.

    Args:
        user_roles: List of role names assigned to user
        permission: Permission string in resource:action format

    Returns:
        bool - True if user has permission

    Example:
        user_roles = ["developer"]
        if rbac.has_permission(user_roles, "projects:create"):
            # User can create projects
            pass
    """
```

### get_user_permissions()

```python
def get_user_permissions(
    self,
    user_roles: List[str]
) -> List[str]:
    """
    Get all permissions for user (aggregated from roles).

    Args:
        user_roles: List of role names

    Returns:
        List of unique permission strings

    Example:
        roles = ["user", "developer"]
        perms = rbac.get_user_permissions(roles)
        # Returns aggregated permissions from both roles
    """
```

### get_role_permissions()

```python
def get_role_permissions(self, role_name: str) -> List[str]:
    """
    Get all permissions for role (including inherited).

    Args:
        role_name: Name of role

    Returns:
        List of unique permission strings (including inherited)

    Example:
        perms = rbac.get_role_permissions("user")
        # Returns user permissions + inherited permissions from parent roles
    """
```

### list_roles()

```python
def list_roles(self) -> List[str]:
    """
    List all available role names.

    Returns:
        List of role names

    Example:
        roles = rbac.list_roles()
        # Returns ["viewer", "user", "admin", "super_admin", ...]
    """
```

### update_role()

```python
def update_role(
    self,
    role_name: str,
    permissions: Optional[List[str]] = None,
    description: Optional[str] = None
) -> None:
    """
    Update existing role.

    Args:
        role_name: Name of role to update
        permissions: New permission list (replaces current)
        description: New description

    Raises:
        ValueError: If role not found

    Example:
        rbac.update_role(
            "developer",
            permissions=["projects:read", "projects:create", "code:review"]
        )
    """
```

### delete_role()

```python
def delete_role(self, role_name: str) -> None:
    """
    Delete role from system.

    Args:
        role_name: Name of role to delete

    Raises:
        ValueError: If role not found or is built-in

    Example:
        rbac.delete_role("custom_role")
    """
```

## Role Model

```python
from netrun_auth.types import Role

class Role(BaseModel):
    name: str                           # Role name (unique)
    permissions: List[str]              # Permission list
    inherits_from: Optional[List[str]]  # Parent roles
    description: Optional[str]          # Human-readable description

    def has_permission(self, permission: str) -> bool
    def add_permission(self, permission: str) -> None
    def remove_permission(self, permission: str) -> None
```

## Permission Class

```python
from netrun_auth.types import Permission

class Permission(BaseModel):
    resource: str  # Resource name (e.g., "users", "projects")
    action: str    # Action name (e.g., "read", "write", "delete")

    def __str__(self) -> str:
        """Returns 'resource:action' format."""
        return f"{resource}:{action}"

    @classmethod
    def from_string(cls, permission_str: str) -> "Permission":
        """Parse from 'resource:action' string."""
        resource, action = permission_str.split(":")
        return Permission(resource=resource, action=action)
```

## Permission Matching

### Exact Match

```python
rbac.has_permission(["admin"], "users:read")  # True if permission exists exactly
```

### Wildcard Actions

```python
# User has "users:*" permission
rbac.has_permission(["admin"], "users:read")   # True (matches *)
rbac.has_permission(["admin"], "users:create") # True (matches *)
rbac.has_permission(["admin"], "users:delete") # True (matches *)

# But not other resources
rbac.has_permission(["admin"], "projects:read")  # False
```

### Wildcard Resources

```python
# User has "admin:*" permission
rbac.has_permission(["admin"], "admin:read")      # True
rbac.has_permission(["admin"], "admin:delete")    # True
rbac.has_permission(["admin"], "users:read")      # False

# Super admin with "*:*"
rbac.has_permission(["super_admin"], "anything:anything")  # True
```

## Built-in Roles

### viewer

Read-only access across system:

```python
permissions = [
    "users:read",
    "organizations:read",
    "projects:read",
    "services:read"
]
```

### user

Standard user with read/write on owned resources:

```python
permissions = [
    "users:read",
    "users:update_self",
    "organizations:read",
    "projects:read",
    "projects:create",
    "projects:update",
    "services:read",
    "services:execute"
]
inherits_from = ["viewer"]
```

### admin

Full administrative access:

```python
permissions = [
    "users:read",
    "users:create",
    "users:update",
    "users:delete",
    "organizations:read",
    "organizations:update",
    "projects:*",
    "services:*",
    "admin:access"
]
inherits_from = ["user"]
```

### super_admin

System-wide access:

```python
permissions = [
    "users:*",
    "organizations:*",
    "projects:*",
    "services:*",
    "admin:*",
    "system:*"
]
```

## Complete Example

```python
from netrun_auth import RBACManager
from netrun_auth.types import Role

# Initialize RBAC manager
rbac = RBACManager()

# 1. Create custom roles
project_manager = Role(
    name="project_manager",
    permissions=[
        "projects:read",
        "projects:create",
        "projects:update",
        "teams:manage",
        "users:read"
    ],
    description="Project management role"
)
rbac.add_role(project_manager)

security_officer = Role(
    name="security_officer",
    permissions=[
        "audit:read",
        "audit:export",
        "users:audit",
        "admin:access"
    ],
    description="Security and audit role"
)
rbac.add_role(security_officer)

# 2. Check permissions
user_roles = ["user", "project_manager"]

print(rbac.has_permission(user_roles, "projects:create"))     # True
print(rbac.has_permission(user_roles, "admin:access"))        # False
print(rbac.has_permission(user_roles, "users:read"))          # True

# 3. Get aggregated permissions
all_perms = rbac.get_user_permissions(user_roles)
print(all_perms)
# Output: ['users:read', 'users:update_self', 'organizations:read',
#          'projects:read', 'projects:create', 'projects:update',
#          'services:read', 'services:execute', 'teams:manage']

# 4. List available roles
print(rbac.list_roles())
# Output: ['viewer', 'user', 'admin', 'super_admin', 'project_manager', 'security_officer']

# 5. Update role
rbac.update_role(
    "project_manager",
    permissions=[
        "projects:read",
        "projects:create",
        "projects:update",
        "projects:delete",
        "teams:manage",
        "users:read"
    ]
)

# 6. Get role details
pm_role = rbac.get_role("project_manager")
print(f"Permissions: {pm_role.permissions}")
print(f"Description: {pm_role.description}")
```

## Integration with FastAPI

```python
from fastapi import FastAPI, Depends
from netrun_auth import RBACManager, get_current_user
from netrun_auth.types import User

app = FastAPI()
rbac = RBACManager()

@app.post("/projects")
async def create_project(user: User = Depends(get_current_user)):
    """Check permission before creating project."""
    if not rbac.has_permission(user.roles, "projects:create"):
        raise HTTPException(status_code=403, detail="Cannot create projects")

    # Create project...
    return {"project_id": "proj123"}

@app.get("/permissions")
async def get_my_permissions(user: User = Depends(get_current_user)):
    """Get user's aggregated permissions."""
    permissions = rbac.get_user_permissions(user.roles)
    return {"roles": user.roles, "permissions": permissions}
```

## Performance

- Permission check: O(n) where n = number of roles
- Typical check: <1ms
- Caching recommended for high-traffic applications
- RBAC manager is stateless and thread-safe

## Best Practices

1. **Use Meaningful Names**: `users:delete` instead of `ud`
2. **Hierarchical Structure**: Child roles inherit from parents
3. **Fine-Grained Permissions**: Specific action:resource combinations
4. **Wildcard Sparingly**: Use `*` only for superuser roles
5. **Document Roles**: Add descriptions for clarity
6. **Audit Changes**: Log role and permission updates

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
