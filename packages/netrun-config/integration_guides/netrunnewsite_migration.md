# NetrunnewSite Configuration Migration Guide

**Project**: NetrunnewSite (Minimal static/dynamic web project)
**Current Config File**: `NetrunnewSite/src/config.py` (or similar)
**Current LOC**: 80
**Expected LOC**: 30
**LOC Reduction**: 50 (63%)
**Migration Time**: 1 hour
**Difficulty**: Low

---

## Before Migration Analysis

### Current Structure (80 LOC)

NetrunnewSite is the most minimal configuration in the portfolio - likely just essential fields with minimal validation.

**LOC Breakdown**:
- 35 LOC: Standard configuration fields
- 30 LOC: Basic validators
- 15 LOC: Class structure/documentation

---

## Quick Migration Path

### Step 1-2: Update Imports & Base Class (2 minutes)

```python
# FROM
from pydantic_settings import BaseSettings

# TO
from netrun_config import BaseConfig, get_settings
```

```python
# FROM
class Config(BaseSettings):
    pass

# TO
class Config(BaseConfig):
    """NetrunnewSite configuration."""
```

### Step 3: Remove Standard Configuration (3 minutes)

Delete: app_name, app_version, app_environment, database_url, redis_url, etc.

### Step 4: Remove Standard Validators (2 minutes)

Delete: validate_environment(), validate_secret_keys(), etc.

### Step 5: Check for Custom Fields (1 minute)

If none exist, configuration is now inherited from BaseConfig only.

### Step 6: Update Settings Factory (1 minute)

```python
def get_config() -> Config:
    """Get NetrunnewSite configuration (cached)."""
    return get_settings(Config)
```

### Step 7: Update Dependencies (1 minute)

```toml
netrun-config>=1.0.0
```

### Step 8: Test (3 minutes)

```bash
pytest
python -c "from src.config import get_config; print(get_config())"
```

---

## After Migration (30 LOC)

```python
# NetrunnewSite/src/config.py (30 LOC)

from netrun_config import BaseConfig, get_settings

class Config(BaseConfig):
    """
    NetrunnewSite configuration.

    Inherits from BaseConfig:
    - All standard application, security, database, and logging settings
    - All validators (environment, secrets, CORS, log level)
    - All property methods (is_production, is_development, etc.)
    - Settings caching via get_settings()
    """
    pass


def get_config() -> Config:
    """Get NetrunnewSite configuration instance (cached)."""
    return get_settings(Config)
```

---

## Validation Checklist

- [ ] Current config.py is 80 LOC
- [ ] Tests pass before migration
- [ ] Updated imports
- [ ] Changed base class to BaseConfig
- [ ] Removed standard validators and fields
- [ ] No custom fields (or kept if any exist)
- [ ] Updated dependencies
- [ ] All tests pass
- [ ] Settings load correctly

---

## Expected Results

**LOC Reduction**: 80 → 30 = **50 LOC removed (63% reduction)**
**Migration Time**: 1 hour
**Time Savings**: 7 hours vs. building from scratch

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
**Final Project**: Last of the 8-project migration wave
