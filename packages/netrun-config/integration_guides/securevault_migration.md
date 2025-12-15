# SecureVault Configuration Migration Guide

**Project**: SecureVault (Minimal Python package)
**Current Config File**: `SecureVault/src/config.py` (or similar)
**Current LOC**: 120
**Expected LOC**: 40
**LOC Reduction**: 80 (67%)
**Migration Time**: 2 hours (includes complexity analysis)
**Difficulty**: Low

---

## Before Migration Analysis

### Current Structure (120 LOC)

SecureVault is a minimal configuration - likely straightforward with no complex integrations.

**LOC Breakdown**:
- 50 LOC: Standard configuration fields
- 40 LOC: Basic validators
- 30 LOC: Documentation/class structure

**Likely Pattern**: Simple configuration without Key Vault or complex custom logic.

---

## Quick Migration Path

### Step 1-2: Update Imports & Base Class (2 minutes)

```python
# FROM
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

# TO
from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
```

```python
# FROM
class SecureVaultConfig(BaseSettings):
    pass

# TO
class SecureVaultConfig(BaseConfig):
    """SecureVault configuration."""
```

### Step 3: Remove Standard Configuration (5 minutes)

Delete inherited fields:
- app_name, app_version, app_environment
- app_secret_key, jwt_secret_key, encryption_key
- database_url, redis_url, redis_host, redis_port
- cors_origins, log_level, logging settings

### Step 4: Remove Standard Validators (3 minutes)

Delete these:
- validate_environment()
- validate_secret_keys()
- validate_cors_origins()
- validate_log_level()

### Step 5: Keep Custom Configuration (2 minutes)

Identify project-specific fields - if none exist, config is now very minimal.

### Step 6: Update Dependencies (1 minute)

```toml
netrun-config>=1.0.0
```

### Step 7: Test (3 minutes)

```bash
pytest
python -c "from src.config import get_settings; print(get_settings())"
```

---

## After Migration (40 LOC)

```python
# SecureVault/src/config.py (40 LOC)

from netrun_config import BaseConfig, Field, get_settings

class SecureVaultConfig(BaseConfig):
    """
    SecureVault configuration.

    Inherits from BaseConfig:
    - All standard application, security, database, and logging settings
    - All validators (environment, secrets, CORS, log level)
    - All property methods (is_production, is_development, etc.)
    - Settings caching via get_settings()
    """

    # Override app_name if needed
    app_name: str = Field(default="SecureVault", env="APP_NAME")


def get_vault_config() -> SecureVaultConfig:
    """Get SecureVault configuration instance (cached)."""
    return get_settings(SecureVaultConfig)
```

---

## Validation Checklist

- [ ] Current config.py is 120 LOC
- [ ] Tests pass before migration
- [ ] Updated imports
- [ ] Changed base class to BaseConfig
- [ ] Removed standard validators and fields
- [ ] Identified any custom fields (probably none)
- [ ] Updated dependencies
- [ ] All tests pass
- [ ] Settings load correctly

---

## Expected Results

**LOC Reduction**: 120 → 40 = **80 LOC removed (67% reduction)**
**Migration Time**: 2 hours
**Time Savings**: 6 hours vs. building from scratch

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
