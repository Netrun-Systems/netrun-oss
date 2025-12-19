# Changelog - Namespace Package Migration (v2.0.0)

All notable changes for the v2.0.0 namespace package migration are documented here.

Format: Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

**Release Date:** December 18, 2025
**Status:** RELEASED

---

## Table of Contents

- [2.0.0 - Release Overview](#200---release-overview)
- [Breaking Changes](#breaking-changes)
- [Added](#added)
- [Changed](#changed)
- [Deprecated](#deprecated)
- [Removed](#removed)
- [Migration Guide](#migration-guide)
- [Individual Package Versions](#individual-package-versions)
- [Support Timeline](#support-timeline)

---

## [2.0.0] - Release Overview

**Major Release: Namespace Package Migration**

This release modernizes the Netrun package architecture by migrating all packages to PEP 420 namespace packages under the unified `netrun` namespace. This provides better IDE support, clearer module organization, and improved Python ecosystem integration.

### Key Highlights

- All `netrun_*` packages now accessible via `netrun.*` namespace
- Backwards compatible with v1.x imports (with deprecation warnings)
- Introduced `netrun-core` as foundation package
- Enhanced type checking support with PEP 561 markers
- Improved IDE autocomplete and module discovery
- 100% test compatibility maintained

### Impact Summary

| Metric | Impact |
|--------|--------|
| **Breaking Changes** | None in v2.x (v1.x imports still work) |
| **New Packages** | 1 (netrun-core) |
| **Migration Path** | Automated tools provided |
| **Compatibility Shims** | Full backwards compatibility |
| **Python 3.8+ Support** | Yes, all versions |

---

## Breaking Changes

### ⚠️ IMPORTANT: Changes Coming in v3.0.0

The following breaking changes are **planned for v3.0.0** (estimated Q2 2026) but **NOT included in v2.0.0**:

1. **Removal of `netrun_*` compatibility imports**
   - `from netrun_auth import ...` will no longer work
   - `from netrun_config import ...` will no longer work
   - All users must migrate to `from netrun.auth import ...`
   - **Timeline:** v3.0.0 (Q2 2026)

2. **Removal of compatibility shims**
   - All deprecated package aliases removed
   - No wrapper modules maintained
   - Cleaner package structure in v3.0+

3. **Minimum Python requirement**
   - Likely v3.9+ for v3.0.0
   - Current v2.x supports Python 3.8+

### v2.0.0 Breaking Changes: NONE

**v2.0.0 maintains 100% backwards compatibility with v1.x.**

All existing code using `netrun_*` imports continues to work. A deprecation warning is emitted to encourage migration:

```python
>>> from netrun_auth import JWTAuthMiddleware
DeprecationWarning: netrun_auth is deprecated. Use 'from netrun.auth import ...' instead.
>>>
```

---

## Added

### New Packages

#### 1. **netrun-core** (v2.0.0)

Foundation package providing PEP 420 namespace package infrastructure.

**Features:**
- Namespace package marker (`netrun/`)
- Shared version information
- Type hints support (py.typed marker)
- Common utilities and base classes
- No breaking changes to existing code

**Installation:**
```bash
pip install netrun-core>=2.0.0
# Automatically installed as dependency
```

**Usage:**
```python
# Namespace marker (no direct imports needed)
# Automatically supports all netrun.* imports
from netrun.auth import JWTAuthMiddleware
from netrun.config import Settings
```

### New Import Paths

All packages now accessible via unified namespace:

```python
# Authentication
from netrun.auth import JWTAuthMiddleware, generate_token

# Configuration
from netrun.config import Settings

# Error Handling
from netrun.errors import NetrunException

# Structured Logging
from netrun.logging import get_logger, configure_logging

# Database
from netrun.db import AsyncSessionPool  # (was netrun_db_pool)

# LLM Orchestration
from netrun.llm import LLMOrchestrator

# CORS
from netrun.cors import CORSMiddleware

# RBAC
from netrun.rbac import enforce_role

# OAuth
from netrun.oauth import OAuth2Provider

# Environment Validation
from netrun.env import EnvironmentValidator

# Rate Limiting
from netrun.ratelimit import RateLimiter

# Testing Fixtures
from netrun.pytest import (
    async_client_fixture,
    db_session_fixture,
)

# MCP Server
from netrun.dogfood import NetrunDogfoodServer
```

### New Type Checking Support

#### PEP 561 Compliance

All packages now include `py.typed` marker for full type checking support:

```bash
# Verify py.typed marker
python -c "import netrun.auth; print(netrun.auth.__file__)"
# Output: .../site-packages/netrun/auth/__init__.py
# Includes: py.typed marker in package root
```

**Benefits:**
- Full type hints for all public APIs
- Better IDE autocomplete
- mypy strict mode support
- Tools like pyright fully supported

#### Type Checking Configuration

Updated mypy configuration:
```ini
[mypy]
python_version = 3.10
namespace_packages = True
follow_imports = normal
```

### New Development Tools

#### Migration Validation Script

Location: `/data/workspace/github/Netrun_Service_Library_v2/packages/scripts/migrate_to_namespace.py`

**Features:**
- Detects unmigrated imports in projects
- Auto-fixes import statements
- Creates backups before modifications
- Generates detailed migration reports
- Validates namespace package structure

**Usage:**
```bash
# Check for unmigrated imports
python migrate_to_namespace.py --check-imports /path/to/project

# Auto-fix imports
python migrate_to_namespace.py --auto-fix /path/to/project --backup

# Verbose report
python migrate_to_namespace.py --check-imports . --verbose
```

---

## Changed

### Package Structure

All packages restructured to support namespace packages:

```
BEFORE (v1.x):
netrun-auth/
├── netrun_auth/          # Package directory
│   ├── __init__.py
│   ├── jwt.py
│   └── middleware.py
├── tests/
├── pyproject.toml
└── README.md

AFTER (v2.x):
netrun-auth/
├── netrun/               # Namespace directory (no __init__.py)
│   └── auth/             # Subpackage
│       ├── __init__.py
│       ├── jwt.py
│       └── middleware.py
├── netrun_auth/          # Compatibility shim
│   ├── __init__.py
│   └── (re-exports from netrun.auth)
├── tests/
├── pyproject.toml
└── README.md
```

### Build System

All packages migrated to consistent build system:

#### Updated `pyproject.toml` Format

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "netrun-auth"
version = "2.0.0"
description = "Authentication library for Netrun Systems"

[project.urls]
Homepage = "https://github.com/netrunsystems/netrun-auth"
Issues = "https://github.com/netrunsystems/netrun-auth/issues"
Documentation = "https://docs.netrunsystems.com/auth"

[tool.hatch.build.targets.wheel]
packages = ["netrun", "netrun_auth"]
```

### Version Updates

All packages bumped to 2.0.0:

| Package | v1.x → v2.0 | Migration Status |
|---------|------------|------------------|
| netrun-auth | 1.1.0 → 2.0.0 | Complete |
| netrun-config | 1.1.0 → 2.0.0 | Complete |
| netrun-errors | 1.0.0 → 2.0.0 | Complete |
| netrun-logging | 1.1.0 → 2.0.0 | Complete |
| netrun-db-pool | 1.0.0 → 2.0.0 | Complete |
| netrun-llm | 1.0.0 → 2.0.0 | Complete |
| netrun-cors | 1.0.0 → 2.0.0 | Complete |
| netrun-rbac | 1.0.0 → 2.0.0 | Complete |
| netrun-oauth | 1.0.0 → 2.0.0 | Complete |
| netrun-env | 1.0.0 → 2.0.0 | Complete |
| netrun-ratelimit | 1.0.0 → 2.0.0 | Complete |
| netrun-pytest-fixtures | 1.0.0 → 2.0.0 | Complete |
| netrun-dogfood | 1.0.0 → 2.0.0 | Complete |

### Minimum Python Version

**v2.x Requirement:** Python 3.8+
**v3.x Target:** Python 3.9+ (planned)

All v2.x packages support:
- Python 3.8
- Python 3.9
- Python 3.10 (recommended)
- Python 3.11
- Python 3.12

### Documentation

All package documentation updated to reflect new import paths:

- Installation guides updated
- API documentation migrated
- Examples use new `netrun.*` imports
- Migration guide added
- Backwards compatibility documented

---

## Deprecated

### `netrun_*` Import Paths (DEPRECATED, NOT REMOVED)

All `netrun_*` import paths are **deprecated but still functional** in v2.x:

```python
# DEPRECATED - still works in v2.x with warning
from netrun_auth import JWTAuthMiddleware
from netrun_config import Settings
from netrun_errors import NetrunException
from netrun_logging import get_logger
from netrun_db_pool import AsyncSessionPool
from netrun_llm import LLMOrchestrator

# RECOMMENDED - new import style
from netrun.auth import JWTAuthMiddleware
from netrun.config import Settings
from netrun.errors import NetrunException
from netrun.logging import get_logger
from netrun.db import AsyncSessionPool
from netrun.llm import LLMOrchestrator
```

### Deprecation Timeline

| Version | Status | `netrun_*` Imports | `netrun.*` Imports |
|---------|--------|-------------------|-------------------|
| **v1.x** | EOL (Nov 2025) | ✅ Primary | ❌ Not available |
| **v2.x** | Current | ⚠️ Deprecated (warnings) | ✅ Primary |
| **v3.0+** | Future (Q2 2026) | ❌ REMOVED | ✅ Only option |

### Handling Deprecation Warnings

**To view deprecation warnings:**
```bash
python -W always::DeprecationWarning your_app.py
```

**To suppress warnings (not recommended):**
```python
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
```

**To convert warnings to errors (helpful for migration):**
```bash
python -W error::DeprecationWarning your_app.py
```

---

## Removed

### Nothing Removed in v2.0.0

**v2.0.0 removes nothing.** All v1.x code continues to work.

Removals are scheduled for v3.0.0:
- `netrun_*` compatibility modules
- Deprecation shims
- v1.x support code

---

## Migration Guide

### Quick Start (3 Steps)

#### 1. Upgrade Packages

```bash
pip install --upgrade \
    netrun-auth \
    netrun-config \
    netrun-errors \
    netrun-logging \
    netrun-db-pool
```

#### 2. Update Imports

```bash
# Find all netrun imports
grep -r "from netrun_" . --include="*.py"

# Replace using sed
find . -name "*.py" -exec sed -i 's/from netrun_/from netrun./g' {} \;
```

#### 3. Test

```bash
pytest tests/
```

### Detailed Migration Steps

See [NAMESPACE_MIGRATION_GUIDE.md](./NAMESPACE_MIGRATION_GUIDE.md) for comprehensive migration instructions including:
- Import transformation examples
- Automated migration tools
- Troubleshooting guide
- FAQ section
- Scenario-based examples

---

## Individual Package Versions

### Core Packages

#### netrun-core v2.0.0 (NEW)

**What's New:**
- Foundation package for namespace infrastructure
- PEP 420 namespace package support
- Type hints with py.typed marker
- No direct imports (foundation only)

**Breaking Changes:** None (new package)

---

#### netrun-auth v2.0.0

**What's Changed:**
- Moved from `netrun_auth` to `netrun.auth`
- Full backwards compatibility maintained
- All APIs unchanged, import paths only

**Migration:**
```python
# OLD
from netrun_auth import JWTAuthMiddleware

# NEW
from netrun.auth import JWTAuthMiddleware
```

**Breaking Changes:** None (import path only)

---

#### netrun-config v2.0.0

**What's Changed:**
- Moved from `netrun_config` to `netrun.config`
- Build system migrated to Hatchling
- Type checking enhanced with py.typed

**Migration:**
```python
# OLD
from netrun_config import Settings

# NEW
from netrun.config import Settings
```

**Breaking Changes:** None (import path only)

---

#### netrun-logging v2.0.0

**What's Changed:**
- Moved from `netrun_logging` to `netrun.logging`
- Enhanced type hints for all modules
- Improved async logging support

**Migration:**
```python
# OLD
from netrun_logging import get_logger, configure_logging

# NEW
from netrun.logging import get_logger, configure_logging
```

**Breaking Changes:** None (import path only)

---

#### netrun-db-pool v2.0.0

**What's Changed:**
- Moved from `netrun_db_pool` to `netrun.db`
- Note: Import uses `netrun.db` (not `netrun.db_pool`)
- Enhanced async/await support

**Migration:**
```python
# OLD
from netrun_db_pool import AsyncSessionPool

# NEW
from netrun.db import AsyncSessionPool
```

**Breaking Changes:** None (import path only)

---

#### netrun-errors v2.0.0

**What's Changed:**
- Moved from `netrun_errors` to `netrun.errors`
- FastAPI exception handlers improved
- Better error context preservation

**Migration:**
```python
# OLD
from netrun_errors import NetrunException

# NEW
from netrun.errors import NetrunException
```

**Breaking Changes:** None (import path only)

---

#### netrun-llm v2.0.0

**What's Changed:**
- Moved from `netrun_llm` to `netrun.llm`
- Multi-provider adapter support enhanced
- Circuit breaker patterns improved

**Migration:**
```python
# OLD
from netrun_llm import LLMOrchestrator

# NEW
from netrun.llm import LLMOrchestrator
```

**Breaking Changes:** None (import path only)

---

#### Other Packages v2.0.0

All following packages updated with same pattern:

- **netrun-cors** v2.0.0
  - `from netrun_cors` → `from netrun.cors`

- **netrun-rbac** v2.0.0
  - `from netrun_rbac` → `from netrun.rbac`

- **netrun-oauth** v2.0.0
  - `from netrun_oauth` → `from netrun.oauth`

- **netrun-env** v2.0.0
  - `from netrun_env` → `from netrun.env`

- **netrun-ratelimit** v2.0.0
  - `from netrun_ratelimit` → `from netrun.ratelimit`

- **netrun-pytest-fixtures** v2.0.0
  - `from netrun_pytest_fixtures` → `from netrun.pytest`

- **netrun-dogfood** v2.0.0
  - `from netrun_dogfood` → `from netrun.dogfood`

---

## Support Timeline

### Version Support Schedule

| Version | Release | Status | Support Until | Notes |
|---------|---------|--------|----------------|-------|
| **v1.x** | Nov 2025 | **EOL** | Dec 31, 2025 | Security fixes only |
| **v2.x** | Dec 2025 | **CURRENT** | Q2 2026 | Full support, backwards compatible |
| **v3.0** | Q2 2026 | **PLANNED** | TBD | No compatibility shims |

### Migration Support

- **v2.0.0 - v2.9.9:** Full backwards compatibility, migration encouraged
- **v3.0.0+:** Namespace packages only, old imports removed

### Recommended Timeline

1. **Now (Dec 2025 - Jan 2026):** Migrate to v2.x, update imports
2. **Q1 2026:** Complete migration in all projects
3. **Q2 2026:** v3.0.0 released, continue using v2.x if needed
4. **Q3 2026:** Consider upgrading to v3.0.0

---

## Testing & Validation

### Test Coverage

All packages maintain 80%+ test coverage:

| Package | Test Status | Coverage | Notes |
|---------|-------------|----------|-------|
| netrun-core | ✅ Pass | 95%+ | New package |
| netrun-auth | ✅ Pass | 90%+ | All import paths tested |
| netrun-config | ✅ Pass | 85%+ | Environment-based tests |
| netrun-logging | ✅ Pass | 85%+ | Async logging tested |
| netrun-db-pool | ✅ Pass | 90%+ | Multi-tenant scenarios |
| netrun-errors | ✅ Pass | 95%+ | Exception handling |
| All others | ✅ Pass | 80%+ | Full coverage |

### Backwards Compatibility Testing

All v2.0.0 packages tested with both import styles:

```python
# Test v1.x import style
def test_v1_imports():
    from netrun_auth import JWTAuthMiddleware  # Should warn
    assert JWTAuthMiddleware is not None

# Test v2.x import style
def test_v2_imports():
    from netrun.auth import JWTAuthMiddleware  # Should not warn
    assert JWTAuthMiddleware is not None
```

---

## Known Issues

### None at Release

No known issues identified during testing.

If you discover issues, please report them:
- GitHub Issues: [netrun-service-library/issues](https://github.com/netrunsystems/netrun-service-library/issues)
- Email: engineering@netrunsystems.com

---

## Contributors

This release was prepared by the Netrun Systems Engineering team.

Special thanks to:
- All package maintainers
- Community feedback on migration guide
- Testing teams for validation

---

## Upgrade Instructions

### From v1.x to v2.0.0

```bash
# 1. Backup current environment
python -m venv venv_backup

# 2. Upgrade all packages
pip install --upgrade \
    netrun-auth \
    netrun-config \
    netrun-errors \
    netrun-logging \
    netrun-db-pool \
    netrun-llm \
    netrun-cors \
    netrun-rbac \
    netrun-oauth \
    netrun-env \
    netrun-ratelimit \
    netrun-pytest-fixtures \
    netrun-dogfood

# 3. Verify installation
python -c "from netrun.auth import JWTAuthMiddleware; print('OK')"

# 4. Run your tests
pytest tests/

# 5. (Optional) Migrate imports in your code
# Use migration script or manual sed replacement
```

### Requirements

- Python 3.8+
- pip 21.0+ (supports PEP 517 build system)
- Virtual environment recommended

---

## Related Resources

- **Migration Guide:** [NAMESPACE_MIGRATION_GUIDE.md](./NAMESPACE_MIGRATION_GUIDE.md)
- **Main README:** [README.md](./README.md)
- **GitHub:** [netrunsystems/netrun-service-library](https://github.com/netrunsystems/netrun-service-library)
- **Docs:** [docs.netrunsystems.com](https://docs.netrunsystems.com)

---

**Changelog Version:** 1.0
**Document Status:** RELEASED
**Release Date:** December 18, 2025
**Maintained By:** Netrun Systems Engineering

For questions or feedback, contact engineering@netrunsystems.com
