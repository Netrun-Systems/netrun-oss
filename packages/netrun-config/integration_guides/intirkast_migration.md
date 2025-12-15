# Intirkast Configuration Migration Guide

**Project**: Intirkast (FastAPI + Azure)
**Current Config File**: `Intirkast/src/backend/app/core/config.py` + Azure Key Vault integration
**Current LOC**: 380
**Expected LOC**: 115
**LOC Reduction**: 265 (70%)
**Migration Time**: 2 hours (includes Key Vault setup)
**Difficulty**: Medium

---

## Before Migration Analysis

### Current Structure (380 LOC)

Intirkast is the first project with Azure Key Vault integration, requiring special attention.

**LOC Breakdown**:
- 120 LOC: Standard configuration
- 100 LOC: Validators (environment, secrets, CORS, pool settings)
- 80 LOC: Property methods
- 80 LOC: Azure Key Vault integration logic (KeyVaultService class + manual secret loading)

### Key Intirkast-Specific Patterns to Keep

```python
# Intirkast-specific fields (KEEP)
# (Usually minimal - mostly standard config + Key Vault integration)
```

---

## Important: Key Vault Integration

Intirkast currently has manual Key Vault integration. With `netrun-config`, use the `KeyVaultMixin` instead:

**Before** (Intirkast's approach):
```python
# Separate KeyVaultService class
class KeyVaultService:
    def __init__(self, vault_url: str):
        self._cache = {}
        self.client = SecretClient(vault_url, credential)

    def get_secret(self, secret_name: str) -> str:
        # Manual caching, fallback logic
        pass

# In config.py - manual integration
@property
def database_url_resolved(self) -> str:
    if self.is_production:
        kv = KeyVaultService(self.key_vault_url)
        return kv.get_secret("database-url")
    return self.database_url
```

**After** (netrun-config approach):
```python
# Use KeyVaultMixin from netrun_config
class AppSettings(BaseConfig, KeyVaultMixin):
    KEY_VAULT_URL: Optional[str] = Field(default=None)

    @property
    def database_url_resolved(self) -> str:
        if self.is_production and self.KEY_VAULT_URL:
            return self.get_keyvault_secret("database-url")
        return self.database_url
```

**Benefits**:
- LRU cache instead of manual dictionary
- Thread-safe caching
- Automatic Managed Identity selection (production vs. dev)
- 80 LOC removed from Intirkast

---

## Migration Steps

### Step 1: Update Imports (2 minutes)

```python
# FROM
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from app.services.key_vault import KeyVaultService  # TO BE REMOVED

# TO
from netrun_config import BaseConfig, KeyVaultMixin, Field, get_settings
from pydantic import field_validator
```

### Step 2: Change Base Class (1 minute)

```python
# FROM
class Settings(BaseSettings):
    model_config = SettingsConfigDict(...)

# TO
class Settings(BaseConfig, KeyVaultMixin):
    """
    Intirkast configuration with Azure Key Vault integration.

    Inherits from BaseConfig: (standard settings, validators, properties)
    Inherits from KeyVaultMixin: (get_keyvault_secret(), credential selection)
    """
```

### Step 3: Add Key Vault URL Field (1 minute)

Add this field to your config (if not already present):

```python
    # Azure Key Vault (from KeyVaultMixin)
    KEY_VAULT_URL: Optional[str] = Field(default=None, env="KEY_VAULT_URL")
```

### Step 4: Remove Manual Key Vault Integration (10 minutes)

**DELETE**:
- `KeyVaultService` class (or move to separate file if other modules use it)
- `@property def database_url_resolved()` if it manually calls KeyVaultService
- `_get_credential()` method (now in KeyVaultMixin)
- Manual secret caching logic

### Step 5: Remove Standard Validators and Property Methods (8 minutes)

**DELETE**:
- `validate_environment()`, `validate_secret_keys()`, etc.
- `is_production`, `is_development`, `database_url_async`, `redis_url_full`

### Step 6: Update Database URL Resolution (2 minutes)

Replace manual Key Vault calls:

```python
# BEFORE (Intirkast)
@property
def database_url_resolved(self) -> str:
    """Get database URL from Key Vault or environment."""
    if self.ENVIRONMENT == "production" and self.KEY_VAULT_URL:
        kv = KeyVaultService(self.KEY_VAULT_URL)
        return kv.get_secret("database-url")
    return self.DATABASE_URL

# AFTER (with netrun-config)
@property
def database_url_resolved(self) -> str:
    """Get database URL from Key Vault or environment."""
    if self.is_production and self.KEY_VAULT_URL:
        return self.get_keyvault_secret("database-url") or self.database_url
    return self.database_url
```

### Step 7: Remove Caching Function (1 minute)

**DELETE** `@lru_cache() def get_settings()` and **REPLACE WITH**:

```python
def get_intirkast_settings() -> Settings:
    """Get Intirkast settings instance (cached via netrun_config.get_settings)."""
    return get_settings(Settings)
```

### Step 8: Update Dependencies (1 minute)

Add to `pyproject.toml` or `requirements.txt`:
```
netrun-config>=1.0.0
```

Keep Azure dependencies:
```
azure-identity>=1.0.0
azure-keyvault-secrets>=4.0.0
```

### Step 9: Key Vault Testing (10 minutes)

In development, test without Key Vault:

```bash
# .env file
KEY_VAULT_URL=  # Empty string
DATABASE_URL=postgresql://localhost/intirkast

# Test settings load with fallback
pytest
python -c "from app.core.config import get_intirkast_settings; print(get_intirkast_settings().database_url_resolved)"
```

In production-like environment, test with Key Vault:

```bash
# Ensure Azure CLI is authenticated
az login

# Set Key Vault URL
export KEY_VAULT_URL=https://my-vault.vault.azure.net/

# Test settings load with Key Vault
python -c "from app.core.config import get_intirkast_settings; print(get_intirkast_settings().database_url_resolved)"
```

### Step 10: Test & Validate (15 minutes)

```bash
# Run full test suite
pytest

# Verify settings load (dev mode, no Key Vault)
python -c "from app.core.config import get_intirkast_settings; s = get_intirkast_settings(); print(f'DB URL: {s.database_url_resolved}'); print(f'Redis URL: {s.redis_url_full}')"
```

---

## After Migration (115 LOC)

```python
# Intirkast/src/backend/app/core/config.py (115 LOC)

from netrun_config import BaseConfig, KeyVaultMixin, Field, get_settings
from pydantic import field_validator
from typing import Optional

class Settings(BaseConfig, KeyVaultMixin):
    """
    Intirkast configuration with Azure Key Vault integration.

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

    Inherits from KeyVaultMixin:
    - get_keyvault_secret(secret_name) - with LRU caching
    - Automatic Managed Identity selection (prod vs. dev)
    - Graceful fallback to environment variables
    """

    # Azure Key Vault URL (required for production)
    KEY_VAULT_URL: Optional[str] = Field(default=None, env="KEY_VAULT_URL")

    # ========================================================================
    # Intirkast-Specific Configuration (if any custom fields exist)
    # ========================================================================
    # Add project-specific fields here

    # ========================================================================
    # Resolved Properties Using Key Vault
    # ========================================================================

    @property
    def database_url_resolved(self) -> str:
        """Get database URL from Key Vault (production) or environment (development)."""
        if self.is_production and self.KEY_VAULT_URL:
            resolved = self.get_keyvault_secret("database-url")
            return resolved or self.database_url or ""
        return self.database_url or ""


def get_intirkast_settings() -> Settings:
    """Get Intirkast settings instance (cached via netrun_config.get_settings)."""
    return get_settings(Settings)
```

---

## Validation Checklist

- [ ] Current config.py is 380 LOC
- [ ] Tests pass before migration
- [ ] Updated imports correctly
- [ ] Changed base class to `BaseConfig, KeyVaultMixin`
- [ ] Added `KEY_VAULT_URL` field
- [ ] Removed `KeyVaultService` class (or moved to separate module)
- [ ] Removed all standard validators and property methods
- [ ] Updated database_url_resolved to use `get_keyvault_secret()`
- [ ] Updated settings factory
- [ ] Updated dependencies (added netrun-config)
- [ ] All tests pass (dev mode, no Key Vault)
- [ ] Settings load correctly with fallback
- [ ] Tested with Azure CLI authentication (if available)

---

## Key Vault Setup for Production

If not already configured, follow these steps:

1. **Create Azure Key Vault**:
   ```bash
   az keyvault create --resource-group myResourceGroup --name myKeyVault
   ```

2. **Add secrets**:
   ```bash
   az keyvault secret set --vault-name myKeyVault --name database-url --value "postgresql://..."
   ```

3. **Configure Managed Identity**:
   - In App Service: Identity → System assigned → On
   - In Key Vault: Access policies → Add → Select principal

4. **Set environment variable**:
   ```bash
   export KEY_VAULT_URL=https://myKeyVault.vault.azure.net/
   ```

---

## Expected Results

**LOC Reduction**: 380 → 115 = **265 LOC removed (70% reduction)**

Includes:
- 100 LOC: Standard config + validators (inherited from BaseConfig)
- 80 LOC: Manual Key Vault integration (replaced by KeyVaultMixin)
- Remaining: Only custom fields and Key Vault usage

**Migration Time**: 2 hours (1 hour refactor + 1 hour Key Vault setup and testing)
**Time Savings**: 6 hours vs. building from scratch

---

## Troubleshooting

### Key Vault Authentication Error

**Problem**: `AuthenticationError` when running in production

**Solution**:
1. Check Managed Identity is enabled: `az app show --resource-group myRG --name myApp --query identity`
2. Check Key Vault access policy: `az keyvault show --name myKeyVault --query properties.accessPolicies`
3. Check secret exists: `az keyvault secret show --vault-name myKeyVault --name database-url`

### Fallback Not Working

**Problem**: Settings don't fall back to environment variables

**Solution**:
- Check `KEY_VAULT_URL` is empty or None: `export KEY_VAULT_URL=""`
- Check environment variables are set: `echo $DATABASE_URL`
- KeyVaultMixin automatically falls back when vault_url is not set

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
**Next Project**: Intirkon (similar Azure setup)
