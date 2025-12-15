# Casbin RBAC Integration - netrun-auth v1.1.0

## Overview

netrun-auth v1.1.0 introduces **Casbin-backed RBAC** as an enterprise-grade alternative to the in-memory RBAC manager. Casbin provides:

- **Pluggable Storage Backends**: PostgreSQL, Redis, or in-memory
- **Multi-Tenant Support**: Domain-based isolation for SaaS applications
- **Role Hierarchy**: Inherit permissions from parent roles
- **Scalability**: Distributed authorization with persistent storage
- **Battle-Tested**: Used by Google, Microsoft, and other enterprises

## Installation

### Basic Installation (Memory Adapter)

```bash
pip install casbin>=1.36.0
```

### With PostgreSQL Adapter

```bash
pip install 'netrun-auth[casbin]'
pip install casbin-async-sqlalchemy-adapter>=1.0.0
```

### With Redis Adapter

```bash
pip install 'netrun-auth[casbin]'
pip install casbin-redis-adapter>=1.0.0
```

### Full Installation (All Features)

```bash
pip install 'netrun-auth[all]'
```

## Quick Start

### 1. Basic Setup (Memory Backend)

```python
from netrun_auth import CasbinRBACManager

# Initialize manager
rbac_manager = CasbinRBACManager()
await rbac_manager.initialize()

# Add roles and permissions
await rbac_manager.add_permission_for_role("admin", "users", "read")
await rbac_manager.add_permission_for_role("admin", "users", "write")
await rbac_manager.add_role_for_user("user123", "admin")

# Check permissions
has_permission = await rbac_manager.check_permission(
    user_id="user123",
    resource="users",
    action="read"
)
print(has_permission)  # True
```

### 2. Multi-Tenant Setup

```python
from netrun_auth import CasbinRBACManager

# Enable multi-tenant mode
rbac_manager = CasbinRBACManager(multi_tenant=True)
await rbac_manager.initialize()

# Add permissions for specific tenants
await rbac_manager.add_permission_for_role(
    role="admin",
    resource="users",
    action="write",
    tenant_id="org1"
)

await rbac_manager.add_role_for_user(
    user_id="user123",
    role="admin",
    tenant_id="org1"
)

# Check permissions with tenant isolation
has_permission = await rbac_manager.check_permission(
    user_id="user123",
    resource="users",
    action="write",
    tenant_id="org1"  # Required in multi-tenant mode
)
print(has_permission)  # True

# User doesn't have permission in org2
has_permission_org2 = await rbac_manager.check_permission(
    user_id="user123",
    resource="users",
    action="write",
    tenant_id="org2"
)
print(has_permission_org2)  # False
```

### 3. PostgreSQL Backend (Production)

```python
from casbin_async_sqlalchemy_adapter import Adapter
from netrun_auth import CasbinRBACManager

# Create PostgreSQL adapter
adapter = Adapter("postgresql://user:pass@localhost/db")

# Initialize manager with persistent storage
rbac_manager = CasbinRBACManager(
    adapter=adapter,
    multi_tenant=True
)
await rbac_manager.initialize()

# Permissions persist across restarts!
await rbac_manager.add_permission_for_role("admin", "users", "delete", tenant_id="org1")
```

### 4. Redis Backend (Distributed)

```python
from casbin_redis_adapter import Adapter
from netrun_auth import CasbinRBACManager

# Create Redis adapter
adapter = Adapter("redis://localhost:6379")

# Initialize manager with distributed storage
rbac_manager = CasbinRBACManager(adapter=adapter)
await rbac_manager.initialize()

# Permissions shared across multiple application instances
await rbac_manager.add_role_for_user("user123", "admin")
```

## FastAPI Integration

### Basic Middleware Setup

```python
from fastapi import FastAPI, Depends
from netrun_auth import (
    CasbinRBACManager,
    CasbinAuthMiddleware,
    AuthenticationMiddleware,
    get_current_user,
    User
)

app = FastAPI()

# Initialize Casbin manager
rbac_manager = CasbinRBACManager(multi_tenant=True)

@app.on_event("startup")
async def startup():
    await rbac_manager.initialize()

    # Setup default permissions
    await rbac_manager.add_permission_for_role("admin", "/api/users", "read")
    await rbac_manager.add_permission_for_role("admin", "/api/users", "create")
    await rbac_manager.add_permission_for_role("user", "/api/projects", "read")

# Add authentication middleware first
app.add_middleware(AuthenticationMiddleware, jwt_manager=jwt_manager)

# Add Casbin authorization middleware
app.add_middleware(
    CasbinAuthMiddleware,
    rbac_manager=rbac_manager,
    excluded_paths=["/health", "/docs", "/openapi.json"]
)

@app.get("/api/users")
async def get_users(current_user: User = Depends(get_current_user)):
    # Authorization already enforced by middleware
    return {"users": ["user1", "user2"]}
```

### Custom Resource Mapping

```python
from netrun_auth.middleware_casbin import path_prefix_mapper

# Map URL paths to resource names
resource_mapper = path_prefix_mapper({
    "/api/v1/users": "users",
    "/api/v1/projects": "projects",
    "/api/v1/admin": "admin"
})

app.add_middleware(
    CasbinAuthMiddleware,
    rbac_manager=rbac_manager,
    resource_mapper=resource_mapper
)
```

### Regex-Based Resource Mapping

```python
from netrun_auth.middleware_casbin import regex_resource_mapper

# Use regex patterns for complex URL structures
resource_mapper = regex_resource_mapper([
    (r"^/api/users(/.*)?$", "users"),
    (r"^/api/projects/[^/]+/tasks(/.*)?$", "tasks"),
    (r"^/api/admin(/.*)?$", "admin"),
])

app.add_middleware(
    CasbinAuthMiddleware,
    rbac_manager=rbac_manager,
    resource_mapper=resource_mapper
)
```

## Factory Function for Backend Selection

```python
from netrun_auth import get_rbac_manager

# Memory backend (default)
rbac = get_rbac_manager(backend="memory")

# Casbin with memory adapter
rbac = get_rbac_manager(backend="casbin")
await rbac.initialize()

# Casbin with PostgreSQL
from casbin_async_sqlalchemy_adapter import Adapter
adapter = Adapter("postgresql://...")
rbac = get_rbac_manager(
    backend="casbin-postgres",
    adapter=adapter,
    multi_tenant=True
)
await rbac.initialize()

# Casbin with Redis
from casbin_redis_adapter import Adapter
adapter = Adapter("redis://localhost:6379")
rbac = get_rbac_manager(
    backend="casbin-redis",
    adapter=adapter
)
await rbac.initialize()
```

## User Model Integration

The `User` model now supports Casbin permission checks:

```python
from netrun_auth import User

user = User(
    user_id="user123",
    organization_id="org1",
    roles=["admin"],
    permissions=[]
)

# Check permission using Casbin enforcer
enforcer = rbac_manager.get_enforcer()
has_permission = await user.has_permission_casbin(
    enforcer,
    resource="users",
    action="write"
)

# With explicit tenant_id
has_permission = await user.has_permission_casbin(
    enforcer,
    resource="users",
    action="write",
    tenant_id="org1"
)
```

## Backwards Compatibility

All existing netrun-auth RBAC features continue to work:

```python
from netrun_auth import RBACManager, get_rbac_manager

# Legacy in-memory RBAC (default behavior unchanged)
rbac = get_rbac_manager()  # Returns RBACManager instance
rbac.check_permission(user, "users:read")

# Decorators still work
from netrun_auth import require_role, require_permission

@require_role("admin")
def admin_function(user: User):
    pass

@require_permission("users:delete")
def delete_user(user: User, user_id: str):
    pass
```

## Casbin Model Configuration

### Single-Tenant Model (`rbac_model.conf`)

```conf
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

### Multi-Tenant Model (`rbac_model_tenant.conf`)

```conf
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
```

## Advanced Usage

### Role Hierarchy

```python
# Create role hierarchy with Casbin
await rbac_manager.add_permission_for_role("viewer", "projects", "read")
await rbac_manager.add_permission_for_role("editor", "projects", "write")
await rbac_manager.add_permission_for_role("admin", "projects", "delete")

# Editor inherits viewer permissions (manual setup with grouping)
await rbac_manager.add_role_for_user("editor_role", "viewer")
await rbac_manager.add_role_for_user("admin_role", "editor_role")
```

### Wildcard Permissions

```python
# Grant all actions on users resource
await rbac_manager.add_permission_for_role("super_admin", "users", "*")

# Grant read on all resources
await rbac_manager.add_permission_for_role("global_viewer", "*", "read")
```

### Batch Operations

```python
# Add multiple permissions at once
permissions = [
    ("admin", "users", "read"),
    ("admin", "users", "write"),
    ("admin", "users", "delete"),
]

for role, resource, action in permissions:
    await rbac_manager.add_permission_for_role(role, resource, action)
```

### Audit and Introspection

```python
# Get all roles for user
roles = await rbac_manager.get_roles_for_user("user123")
print(f"User roles: {roles}")

# Get all permissions for role
permissions = await rbac_manager.get_permissions_for_role("admin")
print(f"Admin permissions: {permissions}")

# Get all users with specific role
users = await rbac_manager.get_users_for_role("admin")
print(f"Admin users: {users}")
```

## Performance Considerations

### Memory Backend
- **Pros**: Fast, simple, no external dependencies
- **Cons**: Not persistent, not suitable for distributed systems
- **Use Case**: Development, testing, single-instance deployments

### PostgreSQL Backend
- **Pros**: Persistent, ACID guarantees, supports large datasets
- **Cons**: Database latency, requires connection pooling
- **Use Case**: Production multi-tenant SaaS, enterprise deployments

### Redis Backend
- **Pros**: Fast, distributed, shared across instances
- **Cons**: Eventual consistency, requires Redis cluster for HA
- **Use Case**: High-throughput APIs, distributed microservices

### Caching Strategy

Casbin has built-in caching. For production, consider:

```python
# Reload policy periodically (if using database adapter)
import asyncio

async def reload_policy_periodically():
    while True:
        await asyncio.sleep(300)  # 5 minutes
        await rbac_manager.clear_cache()

# Start background task
asyncio.create_task(reload_policy_periodically())
```

## Migration from In-Memory RBAC

### Step 1: Update Dependencies

```bash
pip install 'netrun-auth[casbin]'
```

### Step 2: Update Initialization

**Before:**
```python
from netrun_auth import get_rbac_manager

rbac = get_rbac_manager()  # In-memory RBACManager
```

**After:**
```python
from netrun_auth import get_rbac_manager

rbac = get_rbac_manager(backend="casbin")
await rbac.initialize()
```

### Step 3: Update Middleware (Optional)

**Before:**
```python
# Authorization handled by dependencies
from netrun_auth import require_permissions

@app.get("/users")
async def get_users(user: User = Depends(require_permissions(["users:read"]))):
    return {"users": []}
```

**After:**
```python
# Authorization handled by middleware
app.add_middleware(CasbinAuthMiddleware, rbac_manager=rbac)

@app.get("/users")
async def get_users(user: User = Depends(get_current_user)):
    # Permission already checked by middleware
    return {"users": []}
```

## Testing

Run Casbin integration tests:

```bash
# Install test dependencies
pip install 'netrun-auth[dev,casbin]'

# Run Casbin-specific tests
pytest tests/test_rbac_casbin.py -v
pytest tests/test_middleware_casbin.py -v
```

## Troubleshooting

### Issue: "casbin package is required"

**Solution:**
```bash
pip install casbin>=1.36.0
```

### Issue: "tenant_id is required for multi-tenant mode"

**Solution:** Always provide `tenant_id` when using `multi_tenant=True`:
```python
await rbac_manager.check_permission(
    user_id="user123",
    resource="users",
    action="read",
    tenant_id="org1"  # Required!
)
```

### Issue: "CasbinRBACManager not initialized"

**Solution:** Call `initialize()` after creating manager:
```python
rbac_manager = CasbinRBACManager()
await rbac_manager.initialize()  # Required!
```

### Issue: Permissions not persisting across restarts

**Solution:** Use PostgreSQL or Redis adapter (not memory):
```python
from casbin_async_sqlalchemy_adapter import Adapter
adapter = Adapter("postgresql://...")
rbac_manager = CasbinRBACManager(adapter=adapter)
await rbac_manager.initialize()
```

## API Reference

### CasbinRBACManager

**Constructor:**
```python
CasbinRBACManager(
    model_path: str | None = None,
    policy_path: str | None = None,
    adapter: Any = None,
    multi_tenant: bool = False
)
```

**Methods:**

- `async initialize()` - Initialize Casbin enforcer (required)
- `async check_permission(user_id, resource, action, tenant_id=None)` - Check permission
- `async add_role_for_user(user_id, role, tenant_id=None)` - Assign role to user
- `async remove_role_for_user(user_id, role, tenant_id=None)` - Remove role from user
- `async get_roles_for_user(user_id, tenant_id=None)` - Get user's roles
- `async add_permission_for_role(role, resource, action, tenant_id=None)` - Add permission to role
- `async remove_permission_for_role(role, resource, action, tenant_id=None)` - Remove permission
- `async get_permissions_for_role(role, tenant_id=None)` - Get role's permissions
- `async get_users_for_role(role, tenant_id=None)` - Get users with role
- `async delete_role(role, tenant_id=None)` - Delete role
- `async clear_cache()` - Clear Casbin cache
- `get_enforcer()` - Get underlying Casbin enforcer

### CasbinAuthMiddleware

**Constructor:**
```python
CasbinAuthMiddleware(
    app,
    rbac_manager: CasbinRBACManager,
    excluded_paths: List[str] | None = None,
    resource_mapper: Callable | None = None,
    action_mapper: Callable | None = None
)
```

**Default Excluded Paths:**
- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`

**Default HTTP Method Mapping:**
- `GET` → `read`
- `POST` → `create`
- `PUT` → `update`
- `PATCH` → `update`
- `DELETE` → `delete`

## License

MIT License - See LICENSE file for details.

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/netrunsystems/netrun-auth/issues
- Documentation: https://docs.netrunsystems.com/auth
- Email: daniel@netrunsystems.com

---

**netrun-auth v1.1.0** - Enterprise-Grade Authentication & Authorization for Python
