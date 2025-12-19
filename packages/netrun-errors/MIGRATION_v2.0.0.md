# Migration Guide: netrun-errors v1.x to v2.0.0

## Overview

Version 2.0.0 introduces namespace packaging, changing the import path from `netrun_errors` to `netrun.errors`. This aligns with Python namespace package standards and enables better organization across the Netrun ecosystem.

## What Changed

### Package Structure

**Before (v1.x):**
```
netrun-errors/
├── netrun_errors/
│   ├── __init__.py
│   ├── auth.py
│   ├── authorization.py
│   ├── base.py
│   ├── handlers.py
│   ├── middleware.py
│   ├── resource.py
│   └── service.py
└── pyproject.toml
```

**After (v2.0.0):**
```
netrun-errors/
├── netrun/                      # Namespace package (no __init__.py)
│   └── errors/                 # Actual package
│       ├── __init__.py
│       ├── auth.py
│       ├── authorization.py
│       ├── base.py
│       ├── handlers.py
│       ├── middleware.py
│       ├── resource.py
│       ├── service.py
│       └── py.typed           # PEP 561 type marker
├── netrun_errors/             # Backwards compatibility shim
│   └── __init__.py           # Re-exports from netrun.errors
└── pyproject.toml            # Updated for namespace packaging
```

## Migration Steps

### Step 1: Update Import Statements

**All imports need to change from `netrun_errors` to `netrun.errors`:**

```python
# OLD (deprecated):
from netrun_errors import NetrunException
from netrun_errors import InvalidCredentialsError, ResourceNotFoundError
from netrun_errors import install_exception_handlers, install_error_logging_middleware

# NEW (recommended):
from netrun.errors import NetrunException
from netrun.errors import InvalidCredentialsError, ResourceNotFoundError
from netrun.errors import install_exception_handlers, install_error_logging_middleware
```

### Step 2: Search and Replace

**Automated migration:**

```bash
# Find all files using old imports
grep -r "from netrun_errors import" .

# Replace in all Python files
find . -name "*.py" -type f -exec sed -i 's/from netrun_errors import/from netrun.errors import/g' {} +
find . -name "*.py" -type f -exec sed -i 's/import netrun_errors/import netrun.errors/g' {} +
```

### Step 3: Verify Functionality

All functionality remains identical:
- Same exception classes
- Same status codes and error codes
- Same middleware and handlers
- Same correlation ID generation
- Same integration with netrun-logging

## Backwards Compatibility

### Deprecation Timeline

- **v2.0.0 (Current)**: Old imports work with deprecation warning
- **v2.x**: Continued support with warnings
- **v3.0.0 (Future)**: Old imports removed entirely

### Deprecation Warning

When using old imports, you'll see:

```
DeprecationWarning: netrun_errors is deprecated. Use 'from netrun.errors import ...' instead.
This module will be removed in version 3.0.0.
```

### Suppressing Warnings (Not Recommended)

If you need time to migrate, suppress warnings temporarily:

```python
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='netrun_errors')
```

**However, this is NOT recommended. Migrate as soon as possible.**

## Why This Change?

### Benefits of Namespace Packaging

1. **Standard Python Practice**: Aligns with PEP 420 namespace packages
2. **Ecosystem Organization**: All Netrun packages can share `netrun.*` namespace
3. **Package Discovery**: Related packages are grouped logically
4. **Type Checking**: PEP 561 `py.typed` marker enables better IDE support
5. **Future Growth**: Enables `netrun.auth`, `netrun.config`, `netrun.db`, etc.

### Example Ecosystem

```
netrun-core       → netrun.core
netrun-errors     → netrun.errors
netrun-logging    → netrun.logging
netrun-auth       → netrun.auth
netrun-config     → netrun.config
netrun-db-pool    → netrun.db.pool
```

## Testing Your Migration

### Manual Testing

```python
# Test new imports
from netrun.errors import NetrunException, InvalidCredentialsError

try:
    raise InvalidCredentialsError()
except InvalidCredentialsError as e:
    print(f"Status: {e.status_code}, Code: {e.error_code}")
    # Output: Status: 401, Code: AUTH_INVALID_CREDENTIALS
```

### Automated Testing

```bash
# Run your existing test suite
pytest

# All tests should pass without changes (except import statements)
```

## Dependencies Update

### pyproject.toml

If you have `netrun-errors` as a dependency, no changes needed:

```toml
[project]
dependencies = [
    "netrun-errors>=2.0.0",  # Version bump recommended
    # ... other dependencies
]
```

### requirements.txt

```txt
netrun-errors>=2.0.0
```

## Common Issues

### Issue: Import Error After Upgrade

**Problem:**
```python
ModuleNotFoundError: No module named 'netrun_errors'
```

**Solution:**
- Ensure you're using `netrun-errors>=2.0.0`
- Update all imports to `netrun.errors`
- Clear Python cache: `find . -name "*.pyc" -delete && find . -name "__pycache__" -delete`

### Issue: Type Checking Fails

**Problem:**
Type checkers (mypy, pyright) don't recognize namespace imports.

**Solution:**
Update type checker configuration:

```toml
# pyproject.toml
[tool.mypy]
namespace_packages = true
```

### Issue: Multiple netrun.* Packages Conflict

**Problem:**
Installing multiple namespace packages causes import issues.

**Solution:**
Ensure all `netrun.*` packages are namespace packages (no `__init__.py` in `netrun/`).

## Rollback Procedure

If you encounter issues and need to rollback:

```bash
# Downgrade to v1.x
pip install netrun-errors==1.1.0

# Revert import changes
find . -name "*.py" -type f -exec sed -i 's/from netrun.errors import/from netrun_errors import/g' {} +
```

## Support

If you encounter migration issues:
- **Email**: dev@netrunsystems.com
- **GitHub Issues**: https://github.com/netrun-systems/netrun-errors/issues
- **Documentation**: https://github.com/netrun-systems/netrun-errors

## Changelog

### v2.0.0 (2025-12-18)

**Breaking Changes:**
- Namespace packaging: `netrun_errors` → `netrun.errors`
- Major version bump due to import path change

**New Features:**
- PEP 561 `py.typed` marker for better type checking
- Namespace package support for ecosystem growth
- Added `netrun-core>=1.0.0` dependency

**Backwards Compatibility:**
- Old `netrun_errors` imports work with deprecation warning
- No functional changes to exception classes or behavior
- Will be removed in v3.0.0

**Migration:**
- Update all imports from `netrun_errors` to `netrun.errors`
- See MIGRATION_v2.0.0.md for detailed migration guide

---

**Version**: 2.0.0
**Date**: 2025-12-18
**Author**: Netrun Systems
