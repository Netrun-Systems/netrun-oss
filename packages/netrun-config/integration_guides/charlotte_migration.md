# Charlotte Configuration Migration Guide

**Project**: Charlotte (FastAPI application)
**Current Config File**: `Charlotte/src/config.py` (or similar)
**Current LOC**: 250
**Expected LOC**: 80
**LOC Reduction**: 170 (68%)
**Migration Time**: 1 hour
**Difficulty**: Low

---

## Before Migration Analysis

### Current Structure (250 LOC)

Charlotte is a mid-sized configuration, likely with some custom application-specific settings.

**LOC Breakdown**:
- 100 LOC: Standard configuration
- 75 LOC: Standard validators and property methods
- 75 LOC: Custom Charlotte-specific configuration and methods

---

## Migration Steps

### Step 1-2: Update Imports & Base Class (3 minutes)

```python
# FROM
from pydantic_settings import BaseSettings, SettingsConfigDict

# TO
from netrun_config import BaseConfig, Field, get_settings
```

```python
# FROM
class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(...)

# TO
class AppConfig(BaseConfig):
    """Charlotte configuration."""
```

### Step 3: Remove Standard Configuration (8 minutes)

Delete inherited fields (app, database, Redis, logging, security, CORS).

### Step 4: Remove Standard Validators (5 minutes)

Delete: validate_environment(), validate_secret_keys(), validate_cors_origins(), validate_log_level()

### Step 5: Keep Custom Configuration (3 minutes)

Identify Charlotte-specific fields and keep them.

### Step 6: Remove Standard Property Methods (2 minutes)

Delete: is_production, is_development, database_url_async, redis_url_full

### Step 7: Keep Custom Methods (2 minutes)

Keep any Charlotte-specific helper or getter methods.

### Step 8: Update Settings Factory (1 minute)

```python
def get_charlotte_config() -> AppConfig:
    """Get Charlotte configuration (cached)."""
    return get_settings(AppConfig)
```

### Step 9: Update Dependencies (1 minute)

```toml
netrun-config>=1.0.0
```

### Step 10: Test (10 minutes)

```bash
pytest
python -c "from src.config import get_charlotte_config; print(get_charlotte_config())"
```

---

## After Migration (80 LOC)

```python
# Charlotte/src/config.py (80 LOC)

from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
from typing import Optional

class AppConfig(BaseConfig):
    """
    Charlotte configuration.

    Inherits from BaseConfig:
    - All standard application, security, database, and logging settings
    - All validators (environment, secrets, CORS, log level)
    - All property methods (is_production, is_development, etc.)
    - Settings caching via get_settings()
    """

    # ========================================================================
    # Charlotte-Specific Configuration (identify during migration)
    # ========================================================================
    # Add any custom fields unique to Charlotte here
    # Example:
    # feature_x: bool = Field(default=True, env="FEATURE_X")


def get_charlotte_config() -> AppConfig:
    """Get Charlotte configuration instance (cached)."""
    return get_settings(AppConfig)
```

---

## Validation Checklist

- [ ] Current config.py is 250 LOC
- [ ] Tests pass before migration
- [ ] Updated imports correctly
- [ ] Changed base class to BaseConfig
- [ ] Removed standard validators and property methods
- [ ] Identified Charlotte-specific fields
- [ ] Kept any custom methods
- [ ] Updated dependencies
- [ ] All tests pass
- [ ] Settings load correctly

---

## Expected Results

**LOC Reduction**: 250 → 80 = **170 LOC removed (68% reduction)**
**Migration Time**: 1 hour
**Time Savings**: 7 hours vs. building from scratch

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
