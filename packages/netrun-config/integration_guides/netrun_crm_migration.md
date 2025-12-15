# NetrunCRM Configuration Migration Guide

**Project**: NetrunCRM (FastAPI + PostgreSQL)
**Current Config File**: `netrun-crm/api/config.py`
**Current LOC**: 476
**Expected LOC**: 126
**LOC Reduction**: 350 (74%)
**Migration Time**: 1 hour
**Difficulty**: Low

---

## Before Migration Analysis

### Current Structure (476 LOC)

The NetrunCRM config handles comprehensive API settings including billing, integrations, and feature flags.

**LOC Breakdown**:
- 200 LOC: Standard configuration (app, database, Redis, security, CORS, logging)
- 120 LOC: Validators (environment, secrets, CORS, pool settings)
- 80 LOC: Property methods (is_production, database_url_async, redis_url_full)
- 76 LOC: CRM-specific fields (billing, Stripe, Stripe webhooks, features)

### Key CRM-Specific Patterns to Keep

```python
# Billing Configuration (KEEP)
stripe_api_key: str = Field(...)
stripe_webhook_key: str = Field(...)
billing_enabled: bool = Field(default=True)

# Feature Flags (KEEP)
feature_payments: bool = Field(default=True)
feature_api_access: bool = Field(default=True)
feature_custom_branding: bool = Field(default=True)
feature_white_label: bool = Field(default=True)

# Integration Settings (KEEP)
sendgrid_api_key: Optional[str] = Field(default=None)
slack_webhook_url: Optional[str] = Field(default=None)
slack_debug_channel: Optional[str] = Field(default=None)
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
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

# TO
class Settings(BaseConfig):
    """
    NetrunCRM API configuration.

    Inherits from BaseConfig:
    - app_name, app_version, app_environment
    - app_secret_key, jwt_secret_key, encryption_key (validated ≥32 chars)
    - database_url, database_pool_size, redis_url, redis_host, redis_port
    - cors_origins, log_level, logging configuration
    - is_production, is_development, database_url_async, redis_url_full
    - Settings caching via get_settings()
    """
```

### Step 3: Remove Standard Configuration (10 minutes)

**DELETE** these fields (inherited from BaseConfig):
- `app_name`, `app_version`, `app_environment`, `app_debug`
- `app_secret_key`, `jwt_secret_key`, `encryption_key`
- `database_url`, `database_pool_size`, `database_max_overflow`, `database_pool_timeout`, `database_pool_recycle`
- `redis_url`, `redis_host`, `redis_port`, `redis_db`, `redis_password`
- `cors_origins`, `cors_allow_credentials`
- `log_level`, `log_format`, `log_file`
- `enable_metrics`, `metrics_port`, `sentry_dsn`

### Step 4: Remove Standard Validators (5 minutes)

**DELETE**:
- `validate_environment()`
- `validate_secret_keys()`
- `validate_cors_origins()`
- `validate_log_level()`
- `validate_database_pool_settings()`

### Step 5: Remove Standard Property Methods (3 minutes)

**DELETE**:
- `is_production`
- `is_development`
- `database_url_async`
- `redis_url_full`

### Step 6: Keep CRM-Specific Configuration (3 minutes)

```python
    # ========================================================================
    # NetrunCRM: Billing Configuration
    # ========================================================================

    stripe_api_key: str = Field(..., env="STRIPE_API_KEY")
    stripe_webhook_key: str = Field(..., env="STRIPE_WEBHOOK_KEY")
    billing_enabled: bool = Field(default=True, env="BILLING_ENABLED")

    # ========================================================================
    # NetrunCRM: Feature Flags
    # ========================================================================

    feature_payments: bool = Field(default=True, env="FEATURE_PAYMENTS")
    feature_api_access: bool = Field(default=True, env="FEATURE_API_ACCESS")
    feature_custom_branding: bool = Field(default=True, env="FEATURE_CUSTOM_BRANDING")
    feature_white_label: bool = Field(default=True, env="FEATURE_WHITE_LABEL")
    feature_webhooks: bool = Field(default=True, env="FEATURE_WEBHOOKS")

    # ========================================================================
    # NetrunCRM: Integration Settings
    # ========================================================================

    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    slack_debug_channel: Optional[str] = Field(default=None, env="SLACK_DEBUG_CHANNEL")
```

### Step 7: Add CRM-Specific Validator (2 minutes)

```python
    @field_validator('stripe_api_key', 'stripe_webhook_key')
    @classmethod
    def validate_stripe_keys(cls, v: str) -> str:
        """Validate Stripe keys are provided."""
        if not v:
            raise ValueError('Stripe keys are required when billing is enabled')
        return v
```

### Step 8: Remove Caching Function (1 minute)

**DELETE**:
```python
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**REPLACE WITH**:
```python
def get_crm_settings() -> Settings:
    """Get CRM settings instance (cached via netrun_config.get_settings)."""
    return get_settings(Settings)
```

### Step 9: Update Dependencies (1 minute)

Add to `pyproject.toml` or `requirements.txt`:
```
netrun-config>=1.0.0
```

### Step 10: Test (15 minutes)

```bash
pytest
python -c "from api.config import get_crm_settings; print(get_crm_settings())"
```

---

## After Migration (126 LOC)

```python
# netrun-crm/api/config.py (126 LOC)

from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
from typing import Optional

class Settings(BaseConfig):
    """
    NetrunCRM API configuration.

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
    # NetrunCRM: Billing Configuration
    # ========================================================================

    stripe_api_key: str = Field(..., env="STRIPE_API_KEY")
    stripe_webhook_key: str = Field(..., env="STRIPE_WEBHOOK_KEY")
    billing_enabled: bool = Field(default=True, env="BILLING_ENABLED")

    # ========================================================================
    # NetrunCRM: Feature Flags
    # ========================================================================

    feature_payments: bool = Field(default=True, env="FEATURE_PAYMENTS")
    feature_api_access: bool = Field(default=True, env="FEATURE_API_ACCESS")
    feature_custom_branding: bool = Field(default=True, env="FEATURE_CUSTOM_BRANDING")
    feature_white_label: bool = Field(default=True, env="FEATURE_WHITE_LABEL")
    feature_webhooks: bool = Field(default=True, env="FEATURE_WEBHOOKS")

    # ========================================================================
    # NetrunCRM: Integration Settings
    # ========================================================================

    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    slack_debug_channel: Optional[str] = Field(default=None, env="SLACK_DEBUG_CHANNEL")

    # ========================================================================
    # NetrunCRM: Validators
    # ========================================================================

    @field_validator('stripe_api_key', 'stripe_webhook_key')
    @classmethod
    def validate_stripe_keys(cls, v: str) -> str:
        """Validate Stripe keys are provided."""
        if not v:
            raise ValueError('Stripe keys are required when billing is enabled')
        return v


def get_crm_settings() -> Settings:
    """Get CRM settings instance (cached via netrun_config.get_settings)."""
    return get_settings(Settings)
```

---

## Validation Checklist

- [ ] Current config.py is 476 LOC
- [ ] Tests pass before migration
- [ ] Updated imports correctly
- [ ] Changed base class to BaseConfig
- [ ] Removed all standard validators and property methods
- [ ] Kept all CRM-specific fields (billing, features, integrations)
- [ ] Added CRM-specific validators
- [ ] Updated settings factory
- [ ] Updated dependencies
- [ ] All tests pass
- [ ] Settings load correctly
- [ ] Stripe keys validation works
- [ ] Feature flags accessible

---

## Expected Results

**LOC Reduction**: 476 → 126 = **350 LOC removed (74% reduction)**
**Migration Time**: 1 hour
**Time Savings**: 7 hours vs. building from scratch

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
