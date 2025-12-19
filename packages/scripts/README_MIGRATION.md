# Namespace Migration Guide

This guide covers the automated migration of Netrun Service Library packages from flat structure (`netrun_*`) to namespace structure (`netrun.*`).

## Overview

The migration script automates the conversion of existing packages to use PEP 420 namespace packages, providing:

- **Automatic restructuring**: Moves source files to namespace structure
- **Import rewriting**: Updates all imports to new namespace paths
- **Backwards compatibility**: Creates deprecation shims for old imports
- **Validation**: Ensures syntax correctness and completeness
- **Safety**: Creates backups and supports rollback

## Quick Start

### Dry Run (Preview Changes)

Always start with a dry run to preview changes:

```bash
cd /data/workspace/github/Netrun_Service_Library_v2/packages/scripts

# Preview all packages
python migrate_to_namespace.py --dry-run

# Preview specific package
python migrate_to_namespace.py --package netrun-errors --dry-run
```

### Migrate All Packages

```bash
# Migrate all netrun-* packages
python migrate_to_namespace.py

# Check the logs for any errors
```

### Migrate Specific Package

```bash
# Migrate just netrun-errors
python migrate_to_namespace.py --package netrun-errors

# Migrate without compatibility shim
python migrate_to_namespace.py --package netrun-errors --skip-shim
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without writing files |
| `--package NAME` | Migrate only the specified package (e.g., `netrun-errors`) |
| `--skip-shim` | Skip creation of backwards compatibility shims |
| `--packages-dir PATH` | Path to packages directory (default: `../`) |
| `-v`, `--verbose` | Enable verbose logging |

## What Gets Changed

### 1. Directory Structure

**Before:**
```
netrun-errors/
├── netrun_errors/
│   ├── __init__.py
│   ├── base.py
│   ├── auth.py
│   └── handlers.py
├── tests/
└── pyproject.toml
```

**After:**
```
netrun-errors/
├── netrun/
│   ├── __init__.py          # Namespace package marker
│   └── errors/              # Subpackage
│       ├── __init__.py
│       ├── base.py
│       ├── auth.py
│       └── handlers.py
├── netrun_errors/           # Compatibility shim (deprecated)
│   └── __init__.py
├── tests/
└── pyproject.toml
```

### 2. Import Statements

**Before:**
```python
from netrun_errors import NetrunException
from netrun_errors.auth import InvalidCredentialsError
import netrun_errors.handlers
```

**After:**
```python
from netrun.errors import NetrunException
from netrun.errors.auth import InvalidCredentialsError
import netrun.errors.handlers
```

### 3. pyproject.toml Updates

**Before:**
```toml
[project]
name = "netrun-errors"
version = "1.1.0"
dependencies = [
    "fastapi>=0.115.0",
]

[tool.hatch.build.targets.wheel]
packages = ["netrun_errors"]

[tool.pytest.ini_options]
addopts = [
    "--cov=netrun_errors",
]

[tool.coverage.run]
source = ["netrun_errors"]
```

**After:**
```toml
[project]
name = "netrun-errors"
version = "2.0.0"           # Bumped to 2.0.0 (breaking change)
dependencies = [
    "netrun-core>=1.0.0",   # Added
    "fastapi>=0.115.0",
]

[tool.hatch.build.targets.wheel]
packages = ["netrun/errors"]

[tool.pytest.ini_options]
addopts = [
    "--cov=netrun.errors",
]

[tool.coverage.run]
source = ["netrun.errors"]
```

### 4. Compatibility Shim

A deprecation shim is created at `netrun_errors/__init__.py`:

```python
"""
Backwards compatibility shim for netrun_errors.

DEPRECATED: This import path is deprecated. Use 'from netrun.errors' instead.
This compatibility layer will be removed in version 3.0.0.
"""

import warnings

warnings.warn(
    "Importing from 'netrun_errors' is deprecated. "
    "Use 'from netrun.errors' instead. "
    "This compatibility layer will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from netrun.errors import *  # Re-export everything
```

## Migration Process Details

### Step 1: Backup Creation

- Creates timestamped backup: `netrun-errors.backup.20251218_143022`
- Full copy of package directory
- Used for rollback if needed

### Step 2: Directory Restructuring

- Creates `netrun/` namespace directory
- Creates `netrun/{subpackage}/` subdirectory
- Creates namespace `__init__.py` with PEP 420 marker
- Moves all source files to new location
- Removes old directory

### Step 3: Import Rewriting

Updates all Python files (`.py`) with new imports:

**Patterns Detected:**
- `from netrun_errors import ...` → `from netrun.errors import ...`
- `from netrun_errors.module import ...` → `from netrun.errors.module import ...`
- `import netrun_errors` → `import netrun.errors`
- `import netrun_errors.module` → `import netrun.errors.module`

**Files Updated:**
- Source files in `netrun/{subpackage}/`
- Test files in `tests/`
- README.md examples (if present)

### Step 4: pyproject.toml Updates

- Changes `packages = ["netrun_errors"]` → `packages = ["netrun/errors"]`
- Bumps version to `2.0.0` (major breaking change)
- Adds `netrun-core>=1.0.0` dependency
- Updates test coverage paths

### Step 5: Compatibility Shim

Unless `--skip-shim` is used:
- Creates `netrun_errors/__init__.py` shim
- Re-exports all symbols from new location
- Issues `DeprecationWarning` on import
- Maintains backwards compatibility for existing code

### Step 6: Validation

- Verifies new directory structure exists
- Checks Python syntax in all migrated files
- Validates pyproject.toml changes
- Reports any errors found

## Safety Features

### Automatic Backups

Every migration creates a timestamped backup:
```
packages/
├── netrun-errors/
└── netrun-errors.backup.20251218_143022/
```

### Rollback Capability

If migration fails, rollback manually:

```bash
# Remove failed migration
rm -rf netrun-errors

# Restore from backup
mv netrun-errors.backup.20251218_143022 netrun-errors
```

### Dry Run Mode

Test migration without any changes:
```bash
python migrate_to_namespace.py --dry-run
```

Preview includes:
- Directory changes
- File movements
- Import updates
- pyproject.toml modifications

### Validation Checks

After migration:
- ✓ New directory structure created
- ✓ All Python files moved
- ✓ Syntax validation passed
- ✓ pyproject.toml updated correctly
- ✓ Old directory removed (or shim created)

## Post-Migration Steps

### 1. Run Tests

```bash
cd netrun-errors
python -m pytest
```

### 2. Build Package

```bash
python -m build
```

### 3. Test Installation

```bash
# Install in development mode
pip install -e .

# Test new imports
python -c "from netrun.errors import NetrunException; print('Success!')"

# Test old imports (should show deprecation warning)
python -c "from netrun_errors import NetrunException"
```

### 4. Update Documentation

Update any documentation referencing old import paths:
- README.md
- API documentation
- Code examples
- Tutorial guides

### 5. Publish New Version

```bash
# Build distribution
python -m build

# Upload to PyPI
twine upload dist/netrun-errors-2.0.0*
```

## Troubleshooting

### Migration Fails with Syntax Error

**Problem:** Validation detects syntax error in migrated file.

**Solution:**
1. Check the error log for specific file and line number
2. Review the import rewriting pattern
3. Fix syntax manually
4. Re-run validation

### Old Directory Still Exists

**Problem:** Old `netrun_errors/` directory remains after migration.

**Solution:**
- If `--skip-shim` NOT used: This is the compatibility shim (expected)
- If `--skip-shim` used: Migration may have failed, check logs

### Imports Not Updated

**Problem:** Some import statements still reference old paths.

**Solution:**
1. Check if imports use non-standard syntax
2. Update manually if needed
3. Common patterns:
   ```python
   # These are updated automatically
   from netrun_errors import X
   import netrun_errors

   # These may need manual updates
   __import__("netrun_errors")
   importlib.import_module("netrun_errors")
   ```

### Tests Fail After Migration

**Problem:** Test suite fails with import errors.

**Solution:**
1. Check test files were updated:
   ```bash
   grep -r "from netrun_" tests/
   ```
2. Update any missed imports manually
3. Check for dynamic imports or string-based imports

### Version Conflict

**Problem:** `netrun-core>=1.0.0` not found.

**Solution:**
Ensure netrun-core is published or available:
```bash
# Install from local directory
pip install -e ../netrun-core

# Or skip dependency for testing
pip install --no-deps -e .
```

## Migration Checklist

Use this checklist when migrating packages:

- [ ] Run dry run and review changes
- [ ] Backup current state manually (optional, auto-backup created)
- [ ] Run migration script
- [ ] Review migration summary for errors
- [ ] Run test suite: `python -m pytest`
- [ ] Build package: `python -m build`
- [ ] Test new imports: `python -c "from netrun.{pkg} import ..."`
- [ ] Test old imports with deprecation: `python -c "from netrun_{pkg} import ..."`
- [ ] Update documentation with new import paths
- [ ] Commit changes: `git add . && git commit -m "Migrate to namespace structure"`
- [ ] Tag release: `git tag v2.0.0`
- [ ] Publish to PyPI: `twine upload dist/*`

## Example Output

```
Netrun Namespace Migration Script v1.0.0
Packages directory: /data/workspace/github/Netrun_Service_Library_v2/packages
Mode: LIVE
Compatibility shims: ENABLED

Found 13 package(s) to migrate:
  - netrun-auth
  - netrun-config
  - netrun-cors
  - netrun-db-pool
  - netrun-dogfood
  - netrun-env
  - netrun-errors
  - netrun-llm
  - netrun-logging
  - netrun-oauth
  - netrun-pytest-fixtures
  - netrun-ratelimit
  - netrun-rbac

============================================================
Starting migration: netrun-errors
============================================================

2025-12-18 14:30:22 - INFO - Initialized migrator for netrun-errors
2025-12-18 14:30:22 - INFO -   Old module: netrun_errors
2025-12-18 14:30:22 - INFO -   New module: netrun/errors
2025-12-18 14:30:22 - INFO - Created backup: .../netrun-errors.backup.20251218_143022
2025-12-18 14:30:22 - INFO - Created namespace structure: .../netrun/errors
2025-12-18 14:30:22 - INFO - Moved source files from .../netrun_errors to .../netrun/errors
2025-12-18 14:30:22 - INFO - Updating imports in 8 Python files...
2025-12-18 14:30:22 - INFO - Updated 15 import statements
2025-12-18 14:30:22 - INFO - Updated pyproject.toml: Updated packages declaration, Bumped version to 2.0.0, Added netrun-core>=1.0.0 dependency
2025-12-18 14:30:22 - INFO - Created compatibility shim: .../netrun_errors/__init__.py
2025-12-18 14:30:22 - INFO - Validating migration...
2025-12-18 14:30:22 - INFO - ✓ Found 8 Python files in new location
2025-12-18 14:30:22 - INFO - ✓ pyproject.toml updated correctly
2025-12-18 14:30:22 - INFO - ✓ Validation passed

============================================================
Migration completed: netrun-errors
============================================================

============================================================
Migration Summary: netrun-errors
============================================================
Changes made: 24
  - Backup created: .../netrun-errors.backup.20251218_143022
  - Created namespace __init__.py: .../netrun/__init__.py
  - Created directory: .../netrun/errors
  - Moved: __init__.py -> .../netrun/errors/__init__.py
  - Moved: base.py -> .../netrun/errors/base.py
  - Moved: auth.py -> .../netrun/errors/auth.py
  - Moved: authorization.py -> .../netrun/errors/authorization.py
  - Moved: resource.py -> .../netrun/errors/resource.py
  - Moved: service.py -> .../netrun/errors/service.py
  - Moved: handlers.py -> .../netrun/errors/handlers.py
  ... and 14 more

============================================================

============================================================
FINAL SUMMARY
============================================================
Total packages: 13
Successful: 13
Failed: 0

Successful migrations:
  ✓ netrun-auth
  ✓ netrun-config
  ✓ netrun-cors
  ✓ netrun-db-pool
  ✓ netrun-dogfood
  ✓ netrun-env
  ✓ netrun-errors
  ✓ netrun-llm
  ✓ netrun-logging
  ✓ netrun-oauth
  ✓ netrun-pytest-fixtures
  ✓ netrun-ratelimit
  ✓ netrun-rbac

============================================================
```

## Best Practices

### 1. Test Incrementally

Migrate one package at a time initially:
```bash
python migrate_to_namespace.py --package netrun-errors
# Test thoroughly
python migrate_to_namespace.py --package netrun-logging
# Test thoroughly
# ... etc
```

### 2. Start with Leaf Packages

Migrate packages with no internal dependencies first:
1. netrun-errors (no dependencies)
2. netrun-logging (no dependencies)
3. netrun-config (depends on netrun-errors)
4. ... etc

### 3. Keep Compatibility Shims

Don't use `--skip-shim` unless:
- Package is not yet published
- No external consumers exist
- You can update all consumers immediately

### 4. Communicate Breaking Change

When publishing v2.0.0:
- Update CHANGELOG.md with migration guide
- Add deprecation notice to README.md
- Announce on communication channels
- Provide migration timeline (e.g., shims removed in v3.0.0)

## Support

For issues or questions:
- **Documentation**: See `/data/workspace/github/Netrun_Service_Library_v2/packages/NAMESPACE_DESIGN.md`
- **Issues**: Create issue in repository
- **Contact**: dev@netrunsystems.com

---

**Version**: 1.0.0
**Last Updated**: December 18, 2025
**Author**: Netrun Systems
