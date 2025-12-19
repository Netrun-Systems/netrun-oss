# Migration Guide: netrun-logging v2.0.0

## Overview

Version 2.0.0 introduces **namespace packaging** to align with Python standards and enable better package organization across the Netrun ecosystem.

**Breaking Change**: Import paths have changed from `netrun_logging` to `netrun.logging`.

**Backwards Compatibility**: A deprecation shim is included to support old imports until v3.0.0.

---

## Quick Migration

### Core Imports

```python
# ❌ OLD (deprecated):
from netrun_logging import configure_logging, get_logger
from netrun_logging import generate_correlation_id, bind_context

# ✅ NEW:
from netrun.logging import configure_logging, get_logger
from netrun.logging import generate_correlation_id, bind_context
```

### Middleware Imports

```python
# ❌ OLD (deprecated):
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.middleware.fastapi import CorrelationIdMiddleware

# ✅ NEW:
from netrun.logging.middleware import add_logging_middleware
from netrun.logging.middleware.fastapi import CorrelationIdMiddleware
```

### Formatter Imports

```python
# ❌ OLD (deprecated):
from netrun_logging.formatters import JsonFormatter

# ✅ NEW:
from netrun.logging.formatters import JsonFormatter
```

### Integration Imports

```python
# ❌ OLD (deprecated):
from netrun_logging.integrations.azure_insights import configure_azure_insights

# ✅ NEW:
from netrun.logging.integrations.azure_insights import configure_azure_insights
```

---

## Step-by-Step Migration

### 1. Update Dependencies

Update your `requirements.txt` or `pyproject.toml`:

```txt
# Update version
netrun-logging>=2.0.0
```

### 2. Find and Replace Imports

Use your IDE's find-and-replace feature:

**Find**: `from netrun_logging`
**Replace**: `from netrun.logging`

**Find**: `import netrun_logging`
**Replace**: `import netrun.logging as netrun_logging`

### 3. Test with Deprecation Warnings

Run your application and look for deprecation warnings:

```python
DeprecationWarning: netrun_logging is deprecated.
Use 'from netrun.logging import ...' instead.
This module will be removed in version 3.0.0.
```

### 4. Verify Functionality

All functionality remains identical - only import paths have changed:

```python
# Both work in v2.0.0 (old path shows deprecation warning)
from netrun_logging import configure_logging  # ⚠️ Deprecated
from netrun.logging import configure_logging  # ✅ Recommended

# API is identical
configure_logging(app_name="test", environment="dev")
logger = get_logger(__name__)
logger.info("test_message", user_id=123)
```

---

## What's New in v2.0.0

### Namespace Packaging

- Aligned with Python namespace package standards (PEP 420)
- Better integration with other `netrun.*` packages
- Improved IDE autocomplete and type hints

### Build System Migration

- Migrated from setuptools to Hatchling
- Cleaner build configuration
- Faster package builds

### Optional Dependencies

New optional dependency groups for ecosystem integration:

```bash
# Install with error handling integration
pip install netrun-logging[errors]

# Install with config integration
pip install netrun-logging[config]

# Install with auth integration
pip install netrun-logging[auth]

# Install all integrations
pip install netrun-logging[all]
```

---

## Compatibility Matrix

| Version | Import Path | Status | Notes |
|---------|-------------|--------|-------|
| v1.x | `netrun_logging` | ✅ Supported | Legacy path |
| v2.x | `netrun_logging` | ⚠️ Deprecated | Works with warning |
| v2.x | `netrun.logging` | ✅ Recommended | New namespace path |
| v3.x | `netrun_logging` | ❌ Removed | Will raise ImportError |
| v3.x | `netrun.logging` | ✅ Required | Only supported path |

---

## Common Migration Issues

### Issue 1: IDE Not Finding `netrun.logging`

**Problem**: IDE shows `netrun.logging` as unresolved import.

**Solution**: Rebuild IDE index or restart IDE after installing v2.0.0.

### Issue 2: Type Hints Not Working

**Problem**: Type hints for `netrun.logging` not recognized.

**Solution**: Ensure `py.typed` marker is included (automatically handled in v2.0.0).

### Issue 3: Circular Import with Old Path

**Problem**: Using both old and new paths causes circular imports.

**Solution**: Migrate all imports to new path (`netrun.logging`) at once.

---

## Ecosystem Integration

v2.0.0 works seamlessly with other Netrun packages:

```python
from netrun.errors import NetrunException, InvalidCredentialsError
from netrun.logging import configure_logging, bind_error_context
from netrun.config import get_config

# All packages use consistent namespace structure
configure_logging(app_name="my-service")
config = get_config()

try:
    # Business logic
    pass
except InvalidCredentialsError as e:
    bind_error_context(e.error_code, e.status_code)
    logger.error("authentication_failed", reason=str(e))
```

---

## Timeline

- **December 18, 2025**: v2.0.0 released with deprecation warnings
- **March 2026** (estimated): v3.0.0 removes backwards compatibility shim
- **Recommendation**: Migrate to `netrun.logging` imports immediately

---

## Support

- **GitHub Issues**: https://github.com/netrun-services/netrun-logging/issues
- **Email**: daniel@netrunsystems.com
- **Documentation**: https://netrun-logging.readthedocs.io

---

*Last Updated: December 18, 2025*
*Version: 2.0.0*
