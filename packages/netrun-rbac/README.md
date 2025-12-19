# netrun-rbac

**Multi-tenant Role-Based Access Control (RBAC) with PostgreSQL Row-Level Security (RLS)**

Extracted from [Intirkast](https://github.com/netrunsystems/intirkast) SaaS platform (85% code reuse, 12h time savings).

## Migration Notice (v2.0.0)

**BREAKING CHANGE**: This package has been migrated to namespace package structure.

**New Import Path:**
```python
# OLD (deprecated, will be removed in v3.0.0)
from netrun_rbac import require_role, Role, RLSPolicyGenerator

# NEW (required for v2.0.0+)
from netrun.rbac import require_role, Role, RLSPolicyGenerator
```

**Backwards Compatibility**: The old `netrun_rbac` import path still works in v2.0.0 but will issue a deprecation warning. Update your imports before v3.0.0.

**Migration Steps:**
1. Update all imports from `netrun_rbac` to `netrun.rbac`
2. Install `netrun-core>=1.0.0` as a dependency
3. Test your application with the new imports
4. Remove any suppressed deprecation warnings

## Features

- **Role Hierarchy**: `owner` > `admin` > `member` > `viewer`
- **FastAPI Integration**: Dependency injection for route protection
- **PostgreSQL RLS**: Row-Level Security policy generators
- **Tenant Isolation**: Multi-tenant database scoping
- **Resource Ownership**: Validate user access to resources
- **Project-Agnostic**: Placeholder configuration for any project

## Installation

```bash
pip install netrun-rbac
```

## Quick Start

### 1. Configure Authentication (Placeholder)

Replace the `get_current_user` placeholder with your authentication dependency:

```python
# your_app/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    """Your authentication logic here"""
    # Decode JWT, validate session, etc.
    payload = decode_jwt_token(token)

    return {
        "user_id": payload["sub"],
        "tenant_id": payload["tenant_id"],
        "email": payload["email"],
        "roles": payload.get("roles", ["member"]),
    }
```

### 2. Protect Routes with RBAC

```python
from fastapi import FastAPI, Depends
from netrun.rbac import require_role, require_admin, require_owner

app = FastAPI()

# Owner-only access
@app.delete("/api/tenant/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    user: dict = Depends(require_owner())
):
    return {"status": "deleted"}

# Admin or owner access (hierarchical)
@app.post("/api/users/invite")
async def invite_user(
    invite_data: InviteRequest,
    user: dict = Depends(require_admin())
):
    return {"status": "invited"}

# Member, admin, or owner access
@app.post("/api/content/schedule")
async def schedule_content(
    content_data: ContentRequest,
    user: dict = Depends(require_role("member"))
):
    return {"status": "scheduled"}
```

### 3. Multiple Allowed Roles (Non-Hierarchical)

```python
from netrun.rbac import require_roles

@app.patch("/api/posts/{post_id}")
async def update_post(
    post_id: str,
    post_data: UpdatePostRequest,
    user: dict = Depends(require_roles(["member", "admin", "owner"]))
):
    return {"status": "updated"}
```

### 4. Resource Ownership Validation

```python
from netrun.rbac import check_resource_ownership
from fastapi import HTTPException

@app.patch("/api/posts/{post_id}")
async def update_post(
    post_id: str,
    post_data: UpdatePostRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get post from database
    post = await db.get(Post, post_id)

    # Check ownership (owner/admin can edit all, others can edit own)
    if not check_resource_ownership(user, post.user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update post...
    return {"status": "updated"}
```

## PostgreSQL Row-Level Security (RLS)

### Enable RLS on Tables

```python
from netrun.rbac import RLSPolicyGenerator
from sqlalchemy import text

# Generate RLS setup for a table
statements = RLSPolicyGenerator.generate_rls_for_table("users")

async with engine.begin() as conn:
    for stmt in statements:
        await conn.execute(text(stmt))
```

**Generated SQL:**

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON users
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);
```

### Set Tenant Context (Per-Request)

```python
from netrun.rbac import set_tenant_context
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db_with_tenant(request: Request):
    """Database session with tenant context"""
    async with AsyncSessionLocal() as session:
        try:
            # Set PostgreSQL session variable
            await set_tenant_context(
                session,
                tenant_id=request.state.tenant_id,
                user_id=request.state.user_id
            )

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Use in routes
@app.get("/api/users")
async def list_users(db: AsyncSession = Depends(get_db_with_tenant)):
    # All queries automatically filtered by tenant_id
    result = await db.execute(select(User))
    return result.scalars().all()
```

### Generate Alembic Migrations

```python
from netrun.rbac import RLSPolicyGenerator

# Generate upgrade migration
migration_up = RLSPolicyGenerator.generate_migration_up(
    tables=["users", "posts", "comments"],
    read_only_tables=["audit_logs"]  # Immutable audit logs
)

print(migration_up)
```

**Output:**

```python
def upgrade() -> None:
    # Enable RLS on users
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON users
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
    """)

    # Enable RLS on audit_logs (read-only)
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_read_policy ON audit_logs
            FOR SELECT
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
    """)
    op.execute("""
        CREATE POLICY tenant_insert_policy ON audit_logs
            FOR INSERT
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
    """)
```

## Role Hierarchy

```
owner (level 3)
  └─ Full control: billing, tenant settings, delete tenant
     ├─ admin (level 2)
     │  └─ Manage team: invite users, edit all content
     │     ├─ member (level 1)
     │     │  └─ Create/edit own content: schedule posts, generate videos
     │     │     └─ viewer (level 0)
     │     │        └─ Read-only access: view content, analytics
```

## Permission Mappings

| Role   | Permissions                                                                 |
|--------|-----------------------------------------------------------------------------|
| viewer | users:read, tenant:read, content:read, billing:read                         |
| member | + content:create, content:update (own)                                      |
| admin  | + content:delete, users:create, users:update, invitations:create/delete     |
| owner  | + tenant:update/delete, billing:update, users:delete                        |

## Advanced Usage

### Custom Session Variable Names

```python
# Generate RLS policy with custom session variable
policy = RLSPolicyGenerator.create_tenant_isolation_policy(
    table_name="organizations",
    tenant_column="org_id",
    session_variable="app.current_org_id",
    policy_name="org_isolation_policy"
)
```

### Read-Only Tables (Audit Logs)

```python
# Generate RLS for immutable audit logs
statements = RLSPolicyGenerator.generate_rls_for_table(
    "audit_logs",
    read_only=True  # Allow SELECT and INSERT, prevent UPDATE/DELETE
)
```

### Check Specific Permissions

```python
from netrun.rbac import RoleHierarchy, Permission

# Check if role has specific permission
can_delete = RoleHierarchy.has_permission("admin", Permission.CONTENT_DELETE)
# Returns: True
```

## Tenant Isolation Testing (v2.1 - CRITICAL SECURITY FEATURE)

The `netrun-rbac` package includes comprehensive tenant isolation testing utilities to prove that cross-tenant data access is impossible.

### Why Tenant Isolation Testing Matters

In multi-tenant applications, a single misconfigured query can expose all customer data. These testing utilities provide:

- **Contract tests** that MUST pass before every release
- **Escape path detection** for CI/CD pipelines
- **Background task context preservation** verification
- **Compliance documentation** for SOC2, ISO27001, NIST audits

### Quick Start: Tenant Isolation Testing

```python
from netrun.rbac import (
    assert_tenant_isolation,
    TenantTestContext,
    TenantEscapePathScanner,
    ci_fail_on_findings,
)

# 1. Assert queries include tenant filter
query = select(Item).where(Item.status == "active")
await assert_tenant_isolation(query)  # FAILS - no tenant filter!

query = select(Item).where(Item.tenant_id == tenant_id, Item.status == "active")
await assert_tenant_isolation(query)  # PASSES

# 2. Test cross-tenant isolation with TenantTestContext
async with TenantTestContext(db_session) as ctx:
    # Create data in tenant A
    item_a = Item(name="Secret", tenant_id=ctx.tenant_a_id)
    session.add(item_a)
    await session.commit()

    # Switch to tenant B and verify isolation
    await ctx.switch_to_tenant_b()

    result = await session.execute(select(Item))
    items = result.scalars().all()
    assert len(items) == 0  # CRITICAL: Tenant B must NOT see Tenant A's data!

# 3. Scan codebase for escape paths (CI/CD integration)
scanner = TenantEscapePathScanner()
findings = scanner.scan_directory("./src")
sys.exit(ci_fail_on_findings(findings))  # Fails CI on critical findings
```

### Contract Tests

Create tests that prove isolation is impossible:

```python
import pytest
from netrun.rbac import TenantTestContext, tenant_isolation_test
from netrun.rbac.exceptions import TenantIsolationError

class TestTenantIsolation:
    """These tests MUST pass before any release."""

    @pytest.mark.asyncio
    @pytest.mark.tenant_isolation
    @tenant_isolation_test
    async def test_cross_tenant_read_impossible(self, db_session):
        """Tenant B MUST NOT see Tenant A's data."""
        async with TenantTestContext(db_session) as ctx:
            # Create secret data in Tenant A
            await db_session.execute(
                text("INSERT INTO items (id, name, tenant_id) VALUES (:id, :name, :tid)"),
                {"id": "item-1", "name": "Secret", "tid": ctx.tenant_a_id}
            )
            await db_session.commit()

            # Switch to Tenant B
            await ctx.switch_to_tenant_b()

            # Query should return empty due to RLS
            result = await db_session.execute(text("SELECT * FROM items"))
            items = result.fetchall()

            assert len(items) == 0, "CRITICAL: Cross-tenant data leak detected!"

    @pytest.mark.asyncio
    @pytest.mark.tenant_isolation
    @tenant_isolation_test
    async def test_cross_tenant_write_impossible(self, db_session):
        """Tenant B MUST NOT modify Tenant A's data."""
        async with TenantTestContext(db_session) as ctx:
            # Create data in Tenant A
            await db_session.execute(
                text("INSERT INTO items (id, name, tenant_id) VALUES (:id, :name, :tid)"),
                {"id": "item-1", "name": "Original", "tid": ctx.tenant_a_id}
            )
            await db_session.commit()

            # Switch to Tenant B and try to modify
            await ctx.switch_to_tenant_b()
            result = await db_session.execute(
                text("UPDATE items SET name = 'Hacked' WHERE id = 'item-1'")
            )

            assert result.rowcount == 0, "CRITICAL: Cross-tenant write detected!"
```

### Background Task Context Preservation

Background tasks lose request context by default. Use `BackgroundTaskTenantContext` to preserve tenant scope:

```python
from netrun.rbac import BackgroundTaskTenantContext

# WRONG - loses tenant context
background_tasks.add_task(process_items)

# RIGHT - preserves tenant context
background_tasks.add_task(
    BackgroundTaskTenantContext(tenant_id, session_factory).run(process_items)
)
```

### Escape Path Scanner

Scan your codebase for potential tenant isolation bypasses:

```python
from netrun.rbac import TenantEscapePathScanner, EscapePathSeverity

scanner = TenantEscapePathScanner()

# Scan a single file
findings = scanner.scan_file("./app/repositories.py")

# Scan entire directory
findings = scanner.scan_directory(
    "./src",
    exclude_patterns=["**/tests/**", "**/__pycache__/**"]
)

# Generate reports
print(scanner.generate_report(findings, format="markdown"))

# CI integration
critical = [f for f in findings if f.severity == EscapePathSeverity.CRITICAL]
if critical:
    sys.exit(1)
```

### Detected Escape Paths

The scanner detects these common vulnerabilities:

| Category | Severity | Description |
|----------|----------|-------------|
| `raw_sql` | CRITICAL | Raw DELETE/UPDATE without tenant filter |
| `raw_sql` | HIGH | Raw SELECT without tenant filter |
| `pagination` | HIGH | Pagination queries without tenant scope |
| `aggregation` | MEDIUM | Aggregation functions that could leak metrics |
| `background` | HIGH | Background tasks without context preservation |
| `union` | HIGH | UNION queries without tenant filters |
| `subquery` | MEDIUM | Subqueries without tenant correlation |

### Compliance Mapping

These tests address the following compliance requirements:

| Framework | Control | Description |
|-----------|---------|-------------|
| SOC2 | CC6.1 | Logical and Physical Access Controls |
| SOC2 | CC6.2 | Role-Based Access Control |
| ISO27001 | A.9.4 | System and Application Access Control |
| ISO27001 | A.9.4.1 | Information Access Restriction |
| NIST | AC-4 | Information Flow Enforcement |
| NIST | AC-6 | Least Privilege |

Get documentation for auditors:

```python
from netrun.rbac import get_compliance_documentation

docs = get_compliance_documentation()
print(docs)  # Formatted compliance documentation
```

## Testing

Run tests:

```bash
pytest tests/
```

Run tests with coverage:

```bash
pytest --cov=netrun.rbac --cov-report=html
```

Run tenant isolation tests only:

```bash
pytest -m tenant_isolation -v
```

Run escape path scanner in CI:

```bash
python -c "
from netrun.rbac import TenantEscapePathScanner, ci_fail_on_findings
scanner = TenantEscapePathScanner()
findings = scanner.scan_directory('./src')
exit(ci_fail_on_findings(findings))
"
```

## Architecture

### Extracted From: Intirkast SaaS Platform

**Source Files:**
- `middleware/rbac.py` → `netrun_rbac/dependencies.py`
- `middleware/tenant_context.py` → `netrun_rbac/tenant.py`
- `migrations/versions/001_initial_schema_creation.py` → `netrun_rbac/policies.py`
- `tests/test_rls_isolation.py` → Testing patterns

**Code Reuse:** 85% (12h time savings)

**Adaptations:**
- Removed Intirkast-specific models (User, Post, etc.)
- Replaced hard-coded auth with placeholder pattern
- Generalized table names and session variables
- Added configurable role hierarchy

## Security Considerations

1. **PostgreSQL RLS Enforcement:** Database-level security (cannot be bypassed by application code)
2. **SQL Injection Prevention:** RLS policies prevent cross-tenant SQL injection
3. **Session Variable Scoping:** `SET LOCAL` ensures variables cleared after transaction
4. **Audit Logging:** Track user_id in session variable for immutable audit trails
5. **Role Validation:** Type-safe enum validation prevents invalid roles

## Requirements

- Python 3.8+
- FastAPI 0.100+
- SQLAlchemy 2.0+
- PostgreSQL 12+ (for Row-Level Security support)

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

## Support

- **Documentation:** [GitHub Repository](https://github.com/netrunsystems/netrun-service-library)
- **Issues:** [GitHub Issues](https://github.com/netrunsystems/netrun-service-library/issues)
- **Commercial Support:** support@netrunsystems.com

## Credits

Developed by **Netrun Systems** (https://netrunsystems.com)

Extracted from production-tested Intirkast SaaS platform with 20+ tenant-scoped tables.

## Related Packages

- `netrun-auth`: JWT authentication and Azure AD integration
- `netrun-db-pool`: PostgreSQL connection pooling
- `netrun-env`: Environment variable validation
- `netrun-errors`: Standardized error handling
