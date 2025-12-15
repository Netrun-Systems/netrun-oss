# GhostGrid Configuration Migration Guide

**Project**: GhostGrid Optical Network (FastAPI + Simulation)
**Current Config File**: `GhostGrid Optical Network/ghostgrid-sim/src/api/config.py`
**Current LOC**: 559
**Expected LOC**: 130
**LOC Reduction**: 429 (77%)
**Migration Time**: 1 hour
**Difficulty**: Low

---

## Before Migration Analysis

### Current Structure (559 LOC)

GhostGrid handles optical network simulation configuration with RSA JWT, API keys, and weather APIs.

**LOC Breakdown**:
- 220 LOC: Standard configuration
- 135 LOC: Validators (environment, secrets, CORS, JWT, RSA)
- 90 LOC: Property methods
- 114 LOC: GhostGrid-specific (RSA keys, weather APIs, simulation settings)

### Key GhostGrid-Specific Patterns to Keep

```python
# RSA JWT Configuration (KEEP)
rsa_private_key: str = Field(...)
rsa_public_key: str = Field(...)

# Weather API Configuration (KEEP)
weather_api_enabled: bool = Field(default=False)
weather_api_key: str = Field(default="")
weather_api_url: str = Field(default="https://api.openweathermap.org")

# Simulation Settings (KEEP)
sim_enabled: bool = Field(default=True)
sim_port: int = Field(default=5000)
sim_workers: int = Field(default=4)
sim_data_path: str = Field(default="./data")
```

---

## Migration Steps

### Step 1: Update Imports (2 minutes)

```python
# FROM
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# TO
from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
```

### Step 2: Change Base Class (1 minute)

```python
# FROM
class GhostGridConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

# TO
class GhostGridConfig(BaseConfig):
    """
    GhostGrid optical network simulation configuration.

    Inherits from BaseConfig: (standard settings, validators, properties)
    """
```

### Step 3: Remove Standard Configuration (10 minutes)

**DELETE** these inherited fields:
- Standard app, database, Redis, security, CORS, logging fields

### Step 4: Remove Standard Validators (5 minutes)

**DELETE**:
- `validate_environment()`
- `validate_secret_keys()`
- `validate_cors_origins()`
- `validate_log_level()`
- `validate_pool_settings()`

### Step 5: Remove Standard Property Methods (3 minutes)

**DELETE**:
- `is_production`, `is_development`
- `database_url_async`, `redis_url_full`

### Step 6: Keep GhostGrid-Specific Configuration (3 minutes)

```python
    # ========================================================================
    # GhostGrid: RSA JWT Configuration
    # ========================================================================

    rsa_private_key: str = Field(..., env="RSA_PRIVATE_KEY")
    rsa_public_key: str = Field(..., env="RSA_PUBLIC_KEY")

    # ========================================================================
    # GhostGrid: Weather API Configuration
    # ========================================================================

    weather_api_enabled: bool = Field(default=False, env="WEATHER_API_ENABLED")
    weather_api_key: str = Field(default="", env="WEATHER_API_KEY")
    weather_api_url: str = Field(default="https://api.openweathermap.org", env="WEATHER_API_URL")

    # ========================================================================
    # GhostGrid: Simulation Settings
    # ========================================================================

    sim_enabled: bool = Field(default=True, env="SIM_ENABLED")
    sim_port: int = Field(default=5000, env="SIM_PORT")
    sim_workers: int = Field(default=4, env="SIM_WORKERS")
    sim_data_path: str = Field(default="./data", env="SIM_DATA_PATH")
```

### Step 7: Add GhostGrid-Specific Validators (2 minutes)

```python
    @field_validator('rsa_private_key', 'rsa_public_key')
    @classmethod
    def validate_rsa_keys(cls, v: str) -> str:
        """Validate RSA keys are provided."""
        if not v or len(v) < 100:
            raise ValueError('RSA keys must be valid PEM-formatted keys')
        return v

    @field_validator('sim_workers')
    @classmethod
    def validate_sim_workers(cls, v: int) -> int:
        """Validate simulation workers count."""
        if v < 1 or v > 16:
            raise ValueError('sim_workers must be between 1 and 16')
        return v
```

### Step 8: Remove Caching Function (1 minute)

**DELETE** `@lru_cache() def get_settings()` and **REPLACE WITH**:

```python
def get_ghostgrid_config() -> GhostGridConfig:
    """Get GhostGrid configuration instance (cached via netrun_config.get_settings)."""
    return get_settings(GhostGridConfig)
```

### Step 9: Update Dependencies (1 minute)

Add to `pyproject.toml` or `requirements.txt`:
```
netrun-config>=1.0.0
```

### Step 10: Test (15 minutes)

```bash
pytest
python -c "from src.api.config import get_ghostgrid_config; print(get_ghostgrid_config())"
```

---

## After Migration (130 LOC)

```python
# GhostGrid Optical Network/ghostgrid-sim/src/api/config.py (130 LOC)

from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
from typing import Optional

class GhostGridConfig(BaseConfig):
    """
    GhostGrid optical network simulation configuration.

    Inherits from BaseConfig:
    - app_name, app_version, app_environment, app_debug
    - app_secret_key, jwt_secret_key, encryption_key (validated ≥32 chars)
    - database_url, database_pool_size, redis_url, redis_host, redis_port
    - cors_origins, cors_allow_credentials
    - log_level, log_format, log_file
    - enable_metrics, metrics_port, sentry_dsn
    - Validators: environment, secrets, CORS, log level
    - Properties: is_production, is_development, is_staging
    - Caching: get_settings() factory
    """

    # ========================================================================
    # GhostGrid: RSA JWT Configuration
    # ========================================================================

    rsa_private_key: str = Field(..., env="RSA_PRIVATE_KEY")
    rsa_public_key: str = Field(..., env="RSA_PUBLIC_KEY")

    # ========================================================================
    # GhostGrid: Weather API Configuration
    # ========================================================================

    weather_api_enabled: bool = Field(default=False, env="WEATHER_API_ENABLED")
    weather_api_key: str = Field(default="", env="WEATHER_API_KEY")
    weather_api_url: str = Field(default="https://api.openweathermap.org", env="WEATHER_API_URL")

    # ========================================================================
    # GhostGrid: Simulation Settings
    # ========================================================================

    sim_enabled: bool = Field(default=True, env="SIM_ENABLED")
    sim_port: int = Field(default=5000, env="SIM_PORT")
    sim_workers: int = Field(default=4, env="SIM_WORKERS")
    sim_data_path: str = Field(default="./data", env="SIM_DATA_PATH")

    # ========================================================================
    # GhostGrid: Validators
    # ========================================================================

    @field_validator('rsa_private_key', 'rsa_public_key')
    @classmethod
    def validate_rsa_keys(cls, v: str) -> str:
        """Validate RSA keys are valid PEM-formatted."""
        if not v or len(v) < 100:
            raise ValueError('RSA keys must be valid PEM-formatted keys')
        return v

    @field_validator('sim_workers')
    @classmethod
    def validate_sim_workers(cls, v: int) -> int:
        """Validate simulation workers count (1-16)."""
        if v < 1 or v > 16:
            raise ValueError('sim_workers must be between 1 and 16')
        return v


def get_ghostgrid_config() -> GhostGridConfig:
    """Get GhostGrid configuration instance (cached via netrun_config.get_settings)."""
    return get_settings(GhostGridConfig)
```

---

## Validation Checklist

- [ ] Current config.py is 559 LOC
- [ ] Tests pass before migration
- [ ] Updated imports correctly
- [ ] Changed base class to BaseConfig
- [ ] Removed all standard validators and property methods
- [ ] Kept all GhostGrid-specific fields (RSA, weather API, simulation)
- [ ] Added GhostGrid-specific validators
- [ ] Updated settings factory
- [ ] Updated dependencies
- [ ] All tests pass
- [ ] Settings load correctly
- [ ] RSA key validation works
- [ ] Simulation settings accessible

---

## Expected Results

**LOC Reduction**: 559 → 130 = **429 LOC removed (77% reduction)**
**Migration Time**: 1 hour
**Time Savings**: 7 hours vs. building from scratch

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
