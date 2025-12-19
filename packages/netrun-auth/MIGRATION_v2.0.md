# Migration Guide: netrun-auth v1.x → v2.0.0

## Overview

netrun-auth v2.0.0 introduces a **BREAKING CHANGE** by migrating from the flat `netrun_auth` package structure to the namespace `netrun.auth` structure. This aligns with the Netrun Systems portfolio-wide namespace standardization.

## What Changed?

### Before (v1.x)
```python
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.integrations.azure_ad import AzureADClient
```

### After (v2.0.0)
```python
from netrun.auth import JWTManager, AuthConfig
from netrun.auth.middleware import AuthenticationMiddleware
from netrun.auth.integrations.azure_ad import AzureADClient
```

## Directory Structure Changes

### Before (v1.x)
```
netrun_auth/
├── __init__.py
├── jwt.py
├── middleware.py
├── integrations/
│   ├── azure_ad.py
│   └── ...
└── ...
```

### After (v2.0.0)
```
netrun/
└── auth/
    ├── __init__.py
    ├── py.typed          # NEW: PEP 561 type marker
    ├── jwt.py
    ├── middleware.py
    ├── integrations/
    │   ├── azure_ad.py
    │   └── ...
    └── ...

netrun_auth/              # DEPRECATED: Compatibility shim
    └── __init__.py       # Re-exports from netrun.auth with deprecation warning
```

## Migration Steps

### Step 1: Update Dependencies

**pyproject.toml:**
```toml
[project]
dependencies = [
    "netrun-core>=1.0.0",    # NEW: Required dependency
    "netrun-auth>=2.0.0",
]

[project.optional-dependencies]
logging = [
    "netrun-logging>=2.0.0",  # Updated to namespace version
]
```

**requirements.txt:**
```txt
netrun-core>=1.0.0
netrun-auth>=2.0.0
netrun-logging>=2.0.0  # Optional, if using logging integration
```

### Step 2: Update Imports

Use find/replace across your codebase:

**Search for:**
```python
from netrun_auth
```

**Replace with:**
```python
from netrun.auth
```

**Search for:**
```python
import netrun_auth.
```

**Replace with:**
```python
import netrun.auth.
```

### Step 3: Update Import Statements

| Old Import (v1.x) | New Import (v2.0+) |
|-------------------|-------------------|
| `from netrun_auth import JWTManager` | `from netrun.auth import JWTManager` |
| `from netrun_auth.middleware import AuthenticationMiddleware` | `from netrun.auth.middleware import AuthenticationMiddleware` |
| `from netrun_auth.dependencies import get_current_user` | `from netrun.auth.dependencies import get_current_user` |
| `from netrun_auth.integrations.azure_ad import AzureADClient` | `from netrun.auth.integrations.azure_ad import AzureADClient` |
| `from netrun_auth.integrations.azure_ad_b2c import AzureADB2CClient` | `from netrun.auth.integrations.azure_ad_b2c import AzureADB2CClient` |
| `from netrun_auth.integrations.oauth import OAuthClient` | `from netrun.auth.integrations.oauth import OAuthClient` |

### Step 4: Run Tests

```bash
# Install updated dependencies
pip install -e .

# Run your test suite
pytest

# Check for deprecation warnings
python -W default::DeprecationWarning -m pytest
```

### Step 5: Verify No Deprecation Warnings

If you still see deprecation warnings like:
```
DeprecationWarning: netrun_auth is deprecated. Use 'from netrun.auth import ...' instead.
```

Search for remaining old imports:
```bash
# Find all remaining old imports
grep -r "from netrun_auth" --include="*.py" .
grep -r "import netrun_auth" --include="*.py" .
```

## Backwards Compatibility

### Compatibility Shim (v2.0.0 - v2.x)

A compatibility shim is provided in v2.0.0 that re-exports all APIs from `netrun.auth` with a deprecation warning:

```python
# This still works in v2.0.0 but is DEPRECATED
from netrun_auth import JWTManager

# You'll see this warning:
# DeprecationWarning: netrun_auth is deprecated. Use 'from netrun.auth import ...' instead.
# This compatibility module will be removed in version 3.0.0.
```

**Important:** The compatibility shim will be **REMOVED in v3.0.0**. Update your code before upgrading to v3.x.

## New Dependencies

### netrun-core

v2.0.0 introduces a dependency on `netrun-core>=1.0.0`, which provides shared namespace utilities and common types across all Netrun packages.

### netrun-logging (Optional)

If you use the `logging` optional dependency, update to `netrun-logging>=2.0.0` (namespace version).

## Breaking Changes Summary

1. **Package import path changed**: `netrun_auth` → `netrun.auth`
2. **New required dependency**: `netrun-core>=1.0.0`
3. **Updated optional dependency**: `netrun-logging>=2.0.0` (if used)
4. **Compatibility shim added**: Old imports work with deprecation warning (removed in v3.0.0)

## Non-Breaking Changes

1. **API remains identical**: All function signatures, classes, and behavior unchanged
2. **Configuration unchanged**: All environment variables and config options remain the same
3. **Database schemas unchanged**: No database migrations required
4. **Redis keys unchanged**: Existing tokens and blacklist entries continue working

## Rollback Instructions

If you encounter issues and need to rollback:

```bash
# Downgrade to v1.3.0
pip install netrun-auth==1.3.0

# Or pin to v1.x in your requirements
netrun-auth>=1.3.0,<2.0.0
```

## Timeline

- **v2.0.0 (2025-12-18)**: Namespace migration, compatibility shim added
- **v2.x (ongoing)**: Compatibility shim maintained with deprecation warnings
- **v3.0.0 (TBD)**: Compatibility shim removed, old imports will fail

## Support

If you encounter migration issues:
1. Check the [GitHub Issues](https://github.com/netrun-systems/netrun-auth/issues)
2. Review the [full documentation](https://docs.netrunsystems.com/auth/migration)
3. Contact support: daniel.garza@netrunsystems.com

## Example Migration

### Before (v1.x)

```python
# app.py (v1.x)
from fastapi import FastAPI, Depends
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.middleware import AuthenticationMiddleware
from netrun_auth.dependencies import get_current_user
from netrun_auth import User
import redis.asyncio as redis

app = FastAPI()
config = AuthConfig()
redis_client = redis.from_url(config.redis_url)
jwt_manager = JWTManager(config, redis_client)

app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)

@app.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id}
```

### After (v2.0.0)

```python
# app.py (v2.0.0)
from fastapi import FastAPI, Depends
from netrun.auth import JWTManager, AuthConfig
from netrun.auth.middleware import AuthenticationMiddleware
from netrun.auth.dependencies import get_current_user
from netrun.auth import User
import redis.asyncio as redis

app = FastAPI()
config = AuthConfig()
redis_client = redis.from_url(config.redis_url)
jwt_manager = JWTManager(config, redis_client)

app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)

@app.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id}
```

**Only the import statements changed!** The rest of your code remains identical.

---

**Version**: 1.0  
**Date**: 2025-12-18  
**Author**: Netrun Systems
