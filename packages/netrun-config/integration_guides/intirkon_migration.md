# Intirkon Configuration Migration Guide

**Project**: Intirkon (FastAPI + Azure Key Vault)
**Current Config File**: `intirkon/src/config.py`
**Current LOC**: 437
**Expected LOC**: 120
**LOC Reduction**: 317 (73%)
**Migration Time**: 1.5 hours (similar to Intirkast, slightly smaller codebase)
**Difficulty**: Medium

---

## Before Migration Analysis

### Current Structure (437 LOC)

Like Intirkast, Intirkon has Azure Key Vault integration. Similar pattern with slightly more custom configuration.

**LOC Breakdown**:
- 140 LOC: Standard configuration
- 110 LOC: Validators
- 75 LOC: Property methods
- 112 LOC: Key Vault integration + Intirkon-specific config

---

## Quick Migration Path

**Reference**: See `intirkast_migration.md` for detailed Key Vault integration steps.

### Key Differences from Intirkast

Intirkon may have additional custom fields beyond Intirkast. Identify these during Step 3-4.

---

## Migration Steps (Abbreviated)

### Step 1-2: Update Imports & Base Class (3 minutes)

```python
# FROM
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# TO
from netrun_config import BaseConfig, KeyVaultMixin, Field, get_settings
```

```python
# FROM
class Config(BaseSettings):
    model_config = SettingsConfigDict(...)

# TO
class Config(BaseConfig, KeyVaultMixin):
    """Intirkon configuration with Azure Key Vault integration."""
```

### Step 3: Add Key Vault URL Field (1 minute)

```python
    KEY_VAULT_URL: Optional[str] = Field(default=None, env="KEY_VAULT_URL")
```

### Step 4: Identify & Keep Custom Fields (5 minutes)

Look for fields unique to Intirkon (not in BaseConfig standard list):
- Database, Redis, logging, security (REMOVE - inherited)
- Project-specific integration fields (KEEP)

Example custom fields to keep:
```python
    # Any Intirkon-specific configuration
```

### Step 5-7: Remove Duplicates & Update Key Vault (8 minutes)

- Remove standard validators (environment, secrets, CORS)
- Remove standard property methods (is_production, database_url_async, redis_url_full)
- Replace manual Key Vault code with `get_keyvault_secret()`

### Step 8-10: Update Dependencies & Test (5 minutes)

```toml
netrun-config>=1.0.0
```

```bash
pytest
python -c "from src.config import get_settings; print(get_settings())"
```

---

## After Migration (120 LOC)

```python
# intirkon/src/config.py (120 LOC)

from netrun_config import BaseConfig, KeyVaultMixin, Field, get_settings
from pydantic import field_validator
from typing import Optional

class Config(BaseConfig, KeyVaultMixin):
    """
    Intirkon configuration with Azure Key Vault integration.

    Inherits from BaseConfig: (standard settings, validators, properties)
    Inherits from KeyVaultMixin: (get_keyvault_secret(), credential selection)
    """

    # Azure Key Vault URL
    KEY_VAULT_URL: Optional[str] = Field(default=None, env="KEY_VAULT_URL")

    # ========================================================================
    # Intirkon-Specific Configuration (identify during migration)
    # ========================================================================
    # Add any custom fields unique to Intirkon here


def get_intirkon_settings() -> Config:
    """Get Intirkon settings instance (cached via netrun_config.get_settings)."""
    return get_settings(Config)
```

---

## Validation Checklist

- [ ] Current config.py is 437 LOC
- [ ] Identified all Intirkon-specific custom fields
- [ ] Updated imports correctly
- [ ] Changed base class to `BaseConfig, KeyVaultMixin`
- [ ] Removed standard validators and property methods
- [ ] Updated Key Vault secret loading to use `get_keyvault_secret()`
- [ ] Updated dependencies
- [ ] All tests pass
- [ ] Settings load correctly with Key Vault fallback

---

## Expected Results

**LOC Reduction**: 437 → 120 = **317 LOC removed (73% reduction)**
**Migration Time**: 1.5 hours
**Time Savings**: 6.5 hours vs. building from scratch

---

## Key Vault Troubleshooting

See `intirkast_migration.md` "Troubleshooting" section for Key Vault authentication issues.

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
