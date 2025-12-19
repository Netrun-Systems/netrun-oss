# Netrun Namespace Package Migration Guide

## Overview

Starting with v2.0.0, all Netrun packages have migrated to **namespace packages** under the unified `netrun` namespace. This modernizes our Python package structure, improves IDE support, and provides a unified import interface across all Netrun services.

**Migration Date:** December 18, 2025
**Supported Python Versions:** 3.8+
**Backwards Compatibility:** v2.x maintains full compatibility with v1.x imports (with deprecation warnings)

---

## What Changed?

### Import Path Transformation

All `netrun_*` packages are now organized under the `netrun` namespace:

| Package Name | Old Import | New Import | Status |
|---|---|---|---|
| **Authentication** | `from netrun_auth import ...` | `from netrun.auth import ...` | ✅ Migrated |
| **Configuration** | `from netrun_config import ...` | `from netrun.config import ...` | ✅ Migrated |
| **Error Handling** | `from netrun_errors import ...` | `from netrun.errors import ...` | ✅ Migrated |
| **Structured Logging** | `from netrun_logging import ...` | `from netrun.logging import ...` | ✅ Migrated |
| **Database Pooling** | `from netrun_db_pool import ...` | `from netrun.db import ...` | ✅ Migrated |
| **LLM Orchestration** | `from netrun_llm import ...` | `from netrun.llm import ...` | ✅ Migrated |
| **CORS Middleware** | `from netrun_cors import ...` | `from netrun.cors import ...` | ✅ Migrated |
| **RBAC & RLS** | `from netrun_rbac import ...` | `from netrun.rbac import ...` | ✅ Migrated |
| **OAuth Adapters** | `from netrun_oauth import ...` | `from netrun.oauth import ...` | ✅ Migrated |
| **Environment Validation** | `from netrun_env import ...` | `from netrun.env import ...` | ✅ Migrated |
| **Rate Limiting** | `from netrun_ratelimit import ...` | `from netrun.ratelimit import ...` | ✅ Migrated |
| **Testing Fixtures** | `from netrun_pytest_fixtures import ...` | `from netrun.pytest import ...` | ✅ Migrated |
| **MCP Server** | `from netrun_dogfood import ...` | `from netrun.dogfood import ...` | ✅ Migrated |

### Package Structure

```
OLD (v1.x):
netrun_auth/
├── __init__.py
├── jwt.py
├── middleware.py
└── ...

NEW (v2.0+):
netrun-core/
├── netrun/
│   ├── __init__.py (namespace marker)
│   └── ...

netrun-auth/
├── netrun/
│   └── auth/
│       ├── __init__.py
│       ├── jwt.py
│       ├── middleware.py
│       └── ...
└── netrun_auth/  (compatibility shim for v1.x imports)
    └── ...
```

---

## Quick Migration Steps

### Step 1: Identify Your Imports

Search your codebase for all `netrun_*` imports:

```bash
# Find all netrun imports
grep -r "from netrun_" . --include="*.py"
grep -r "import netrun_" . --include="*.py"
```

### Step 2: Update Your Package Versions

Upgrade to v2.0.0 or later:

```bash
# Upgrade all Netrun packages
pip install --upgrade \
    netrun-auth \
    netrun-config \
    netrun-errors \
    netrun-logging \
    netrun-db-pool \
    netrun-llm
```

### Step 3: Migrate Imports

Update your import statements:

```python
# OLD - Still works in v2.x with deprecation warning
from netrun_auth import JWTAuthMiddleware, generate_token
from netrun_config import Settings
from netrun_errors import NetrunException
from netrun_logging import get_logger, configure_logging
from netrun_db_pool import AsyncSessionPool

# NEW - Recommended for v2.x+
from netrun.auth import JWTAuthMiddleware, generate_token
from netrun.config import Settings
from netrun.errors import NetrunException
from netrun.logging import get_logger, configure_logging
from netrun.db import AsyncSessionPool
```

Use a search-and-replace tool for bulk migration:

```bash
# Using sed (macOS/Linux)
sed -i 's/from netrun_auth/from netrun.auth/g' **/*.py
sed -i 's/from netrun_config/from netrun.config/g' **/*.py
sed -i 's/from netrun_errors/from netrun.errors/g' **/*.py
sed -i 's/from netrun_logging/from netrun.logging/g' **/*.py
sed -i 's/from netrun_db_pool/from netrun.db/g' **/*.py
sed -i 's/from netrun_llm/from netrun.llm/g' **/*.py

# Or using find/xargs
find . -name "*.py" -exec sed -i 's/from netrun_/from netrun./g' {} \;
```

### Step 4: Test Your Application

Run your test suite to verify the migration:

```bash
pytest tests/
pytest --cov=src/  # with coverage
```

### Step 5: Verify No Deprecation Warnings

The migration is complete when there are no deprecation warnings:

```python
import warnings
warnings.filterwarnings('error', category=DeprecationWarning)
# Now deprecation warnings will raise exceptions
```

---

## Backwards Compatibility

### What Still Works in v2.x

The v2.0.0 release maintains **full backwards compatibility** with v1.x imports. Old import paths continue to work but emit deprecation warnings:

```python
>>> from netrun_auth import JWTAuthMiddleware
DeprecationWarning: netrun_auth is deprecated. Use 'from netrun.auth import ...' instead.
>>>
```

### Migration Timeline

| Version | Status | Support |
|---------|--------|---------|
| **v1.x** | End-of-Life (Nov 2025) | No updates, security only |
| **v2.x** | Current (Dec 2025) | Full support, backwards compatible |
| **v3.0** | Planned (Q2 2026) | Removes compatibility shims |

### Breaking Changes in v3.0

When v3.0.0 is released (estimated Q2 2026):
- Old `netrun_*` imports will no longer work
- Compatibility shims will be removed
- All users must migrate to `netrun.*` imports

**Recommended Action:** Migrate now to avoid urgent updates later.

---

## Benefits of Namespace Packages

### 1. Unified Import Structure

```python
# All packages under single namespace
from netrun import auth, config, logging, db, errors

# Clearer module organization
from netrun.auth import JWTAuthMiddleware
from netrun.db import AsyncSessionPool
```

### 2. Better IDE Support

- **Improved autocomplete**: IDEs recognize `netrun.*` hierarchy
- **Type hints**: Better type inference and validation
- **Code navigation**: Jump to definition works across namespace packages

### 3. Reduced Naming Conflicts

- Single namespace eliminates `netrun_` prefix variations
- No confusion between `netrun_db_pool` vs `netrun_db`
- Clear parent-child relationships

### 4. Easier Discovery

```python
# Browse available modules
from netrun import *  # Shows: auth, config, logging, db, errors, ...

# Or use IDE's module browser
# netrun.
#   ├── auth
#   ├── config
#   ├── db
#   ├── errors
#   ├── logging
#   └── ...
```

### 5. PEP 420 Compliance

- Uses Python 3.3+ implicit namespace packages (PEP 420)
- No `__init__.py` required in namespace directories
- Better Python ecosystem integration
- Improved type checking with PEP 561

---

## Automated Migration Tool

### Using the Migration Script

A Python script is provided to validate import migration:

```bash
# Check for unmigrated imports in your project
python /data/workspace/github/Netrun_Service_Library_v2/packages/scripts/migrate_to_namespace.py \
    --check-imports /path/to/your/project

# Show detailed report
python .../migrate_to_namespace.py \
    --check-imports /path/to/your/project \
    --verbose

# Auto-fix imports (use with caution, test afterwards)
python .../migrate_to_namespace.py \
    --auto-fix /path/to/your/project \
    --backup  # Creates backup before modifying
```

### Script Output

```
Migration Report
================

Status: COMPLETE
Migrated Imports: 45
Remaining Old Imports: 0
Deprecation Warnings: 0

Package Distribution:
  netrun.auth: 12
  netrun.config: 8
  netrun.db: 15
  netrun.logging: 7
  netrun.errors: 3

Timestamp: 2025-12-18 10:30:45 UTC
```

---

## Package Dependencies

### netrun-core (New in v2.0.0)

The foundation package that all others depend on:

```bash
pip install netrun-core>=2.0.0
```

Provides:
- PEP 420 namespace package marker
- Shared utilities and base classes
- Version information for all packages
- Type hints support (py.typed marker)

### Dependency Graph

```
Your Application
│
├── netrun-auth >= 2.0.0
│   └── netrun-core >= 2.0.0
│
├── netrun-config >= 2.0.0
│   └── netrun-core >= 2.0.0
│
├── netrun-logging >= 2.0.0
│   └── netrun-core >= 2.0.0
│
└── netrun-db >= 2.0.0
    └── netrun-core >= 2.0.0
```

### Installing Core Separately (Not Required)

Core is installed automatically as a dependency:

```bash
# Direct installation (optional, auto-installed)
pip install netrun-core>=2.0.0

# After installation, it's just a marker package
# You don't directly import from netrun-core
```

---

## Common Migration Scenarios

### Scenario 1: FastAPI Application

**Before (v1.x):**
```python
from fastapi import FastAPI
from netrun_auth import JWTAuthMiddleware
from netrun_config import Settings
from netrun_logging import configure_logging
from netrun_errors import exception_handler

app = FastAPI()
configure_logging()
app.add_middleware(JWTAuthMiddleware)
```

**After (v2.x):**
```python
from fastapi import FastAPI
from netrun.auth import JWTAuthMiddleware
from netrun.config import Settings
from netrun.logging import configure_logging
from netrun.errors import exception_handler

app = FastAPI()
configure_logging()
app.add_middleware(JWTAuthMiddleware)
```

### Scenario 2: Multi-Tenant Database Access

**Before (v1.x):**
```python
from netrun_db_pool import AsyncSessionPool, TenantContext
from netrun_rbac import enforce_tenant_access

async def get_user(user_id: str, tenant_id: str):
    session_pool = AsyncSessionPool()
    async with session_pool.session(tenant_id) as session:
        enforce_tenant_access(session, user_id, tenant_id)
        return await session.execute(...)
```

**After (v2.x):**
```python
from netrun.db import AsyncSessionPool, TenantContext
from netrun.rbac import enforce_tenant_access

async def get_user(user_id: str, tenant_id: str):
    session_pool = AsyncSessionPool()
    async with session_pool.session(tenant_id) as session:
        enforce_tenant_access(session, user_id, tenant_id)
        return await session.execute(...)
```

### Scenario 3: Testing with Fixtures

**Before (v1.x):**
```python
from netrun_pytest_fixtures import (
    async_client_fixture,
    db_session_fixture,
    auth_token_fixture
)

# Fixtures auto-discovered by pytest
```

**After (v2.x):**
```python
from netrun.pytest import (
    async_client_fixture,
    db_session_fixture,
    auth_token_fixture
)

# Fixtures auto-discovered by pytest
```

### Scenario 4: LLM Integration

**Before (v1.x):**
```python
from netrun_llm import LLMOrchestrator, FallbackChain

orchestrator = LLMOrchestrator(
    chains={
        'default': FallbackChain([...])
    }
)
```

**After (v2.x):**
```python
from netrun.llm import LLMOrchestrator, FallbackChain

orchestrator = LLMOrchestrator(
    chains={
        'default': FallbackChain([...])
    }
)
```

---

## Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'netrun.auth'"

**Cause:** Package not installed or version is v1.x

**Solution:**
```bash
# Verify installation
pip list | grep netrun-auth

# Upgrade to v2.x
pip install --upgrade netrun-auth>=2.0.0

# Verify import
python -c "from netrun.auth import JWTAuthMiddleware; print('OK')"
```

### Issue 2: DeprecationWarning on Import

**Cause:** Using old `netrun_*` import paths

**Solution:**
```python
# OLD - triggers warning
from netrun_auth import JWTAuthMiddleware

# NEW - no warning
from netrun.auth import JWTAuthMiddleware
```

To find all deprecation warnings:
```bash
python -W error::DeprecationWarning your_app.py  # Fails on first warning
python -W all::DeprecationWarning your_app.py    # Shows all warnings
```

### Issue 3: "netrun.db" vs "netrun_db_pool" Confusion

**Clarification:**
- `netrun-db-pool` package is imported as `netrun.db` (not `netrun.db_pool`)
- This improves readability and consistency

```python
# Correct
from netrun.db import AsyncSessionPool

# Incorrect (old package name)
from netrun.db_pool import AsyncSessionPool  # This won't work

# Also incorrect (old import style)
from netrun_db_pool import AsyncSessionPool  # Deprecated warning
```

### Issue 4: Type Checking Errors

**Cause:** mypy can't find types in namespace packages

**Solution:**
```bash
# Ensure py.typed marker is present
python -c "import netrun.auth; print(netrun.auth.__file__)"

# Update mypy configuration
cat mypy.ini
[mypy]
python_version = 3.10
namespace_packages = True
```

---

## Testing Your Migration

### Pre-Migration Checklist

- [ ] Python 3.8+ installed
- [ ] All unit tests passing
- [ ] No deprecated import warnings currently
- [ ] IDE/linter configured for namespace packages
- [ ] Backup of current environment created

### Migration Checklist

- [ ] All `netrun_*` imports replaced with `netrun.*`
- [ ] All test cases passing
- [ ] No deprecation warnings
- [ ] Type checking (mypy) passes
- [ ] Linting (black, ruff) passes
- [ ] Integration tests passing

### Post-Migration Validation

```bash
# Run comprehensive test
pytest tests/ -v

# Check for any remaining old imports
grep -r "netrun_" . --include="*.py" | grep -v ".pyc"

# Validate no deprecation warnings
python -W error::DeprecationWarning -m pytest tests/

# Type check
mypy src/
```

---

## Migration Support Matrix

### Supported Scenarios

| Scenario | Status | Notes |
|----------|--------|-------|
| **Python 3.8** | ✅ Full support | All packages compatible |
| **Python 3.9** | ✅ Full support | All packages compatible |
| **Python 3.10** | ✅ Full support | Recommended minimum |
| **Python 3.11** | ✅ Full support | Latest stable |
| **Python 3.12** | ✅ Full support | Latest preview |
| **Virtual environments** | ✅ Full support | Recommended |
| **Conda environments** | ✅ Full support | Full compatibility |
| **Docker containers** | ✅ Full support | Use pip install v2.x |

### Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| **Linux** | ✅ Fully tested | Primary development platform |
| **macOS** | ✅ Fully tested | Intel and Apple Silicon |
| **Windows** | ✅ Full support | PowerShell and CMD compatible |
| **Azure Container Apps** | ✅ Fully tested | Production ready |

---

## FAQ

### Q: Do I need to install netrun-core separately?

**A:** No, it's automatically installed as a dependency of all Netrun v2.x packages. You can verify it's present:

```bash
pip list | grep netrun-core
netrun-core                   2.0.0
```

### Q: Will my existing code break?

**A:** No, v2.x maintains full backwards compatibility with v1.x. Old import paths continue to work but emit deprecation warnings:

```python
>>> from netrun_auth import JWTAuthMiddleware
<stdin>:1: DeprecationWarning: netrun_auth is deprecated. Use 'from netrun.auth import ...' instead.
>>>
```

Update at your convenience before v3.0.0 (Q2 2026).

### Q: What's the performance impact?

**A:** Namespace packages have no performance impact. Namespace lookups are optimized in Python 3.3+. You may see negligible improvements in import time due to namespace package optimizations.

### Q: Can I use both old and new imports in the same project?

**A:** Yes, Python allows mixing old and new imports:

```python
# This works but generates deprecation warnings
from netrun_auth import JWTAuthMiddleware  # Old style (warns)
from netrun.config import Settings          # New style (no warning)
```

However, we recommend migrating all imports to new style for consistency.

### Q: How do I migrate a large codebase?

**A:** Use the automated migration script:

```bash
# Check for issues
python migrate_to_namespace.py --check-imports /path/to/project --verbose

# Create backup
cp -r /path/to/project /path/to/project.backup

# Auto-fix imports
python migrate_to_namespace.py --auto-fix /path/to/project --backup

# Test
cd /path/to/project && pytest tests/
```

### Q: What about IDE support?

**A:** All major IDEs support PEP 420 namespace packages:
- **PyCharm**: Fully supported, auto-completes `netrun.*` paths
- **VS Code**: Fully supported with Pylance
- **Sublime Text**: Supported with LSP configuration
- **Vim/Neovim**: Supported with LSP clients

### Q: Is there a migration deadline?

**A:** No hard deadline, but we recommend migrating before v3.0.0 (estimated Q2 2026). After v3.0.0 releases, old imports will no longer work.

### Q: Can I pin to v1.x forever?

**A:** Technically yes, but not recommended. v1.x will receive security updates until v3.0.0 releases, after which updates stop.

---

## Support & Resources

### Getting Help

- **Documentation:** [Netrun Package Docs](https://docs.netrunsystems.com/packages/)
- **Issues:** Report on GitHub package repositories
- **Discussions:** GitHub Discussions in service library repo
- **Email:** engineering@netrunsystems.com

### Related Documentation

- [CHANGELOG_v2.0.0.md](./CHANGELOG_v2.0.0.md) - Detailed change log
- [README.md](./README.md) - Package overview
- Individual package READMEs for API details

### Version History

- **v1.0.0** (November 2025): Initial release with `netrun_*` imports
- **v2.0.0** (December 18, 2025): Namespace package migration
- **v3.0.0** (Q2 2026): Removal of compatibility shims

---

## Contributing

Found an issue with the migration documentation? Submit a PR:

1. Fork the repository
2. Create a branch: `git checkout -b docs/namespace-migration-fix`
3. Make changes with clear commit messages
4. Submit a pull request

All contributions should follow the [Contributing Guidelines](../CONTRIBUTING.md).

---

**Document Version:** 1.0
**Last Updated:** December 18, 2025
**Maintained By:** Netrun Systems Engineering
**Status:** Approved for v2.0.0 Release
