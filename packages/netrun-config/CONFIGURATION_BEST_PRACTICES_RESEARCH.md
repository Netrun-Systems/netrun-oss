# Configuration Best Practices Research Report

## Service #63: Unified Configuration Management

**Research Date**: 2024-11-24
**Researcher**: Technical Research Agent
**Version**: 1.0
**SDLC Compliance**: v2.1

---

## Executive Summary

This research report provides comprehensive analysis of Python configuration management best practices to inform the design of Service #63 (Unified Configuration). The recommended stack combines **pydantic-settings** as the core framework with native Azure Key Vault integration, providing type-safe configuration with fail-fast validation and seamless cloud secrets management.

---

## 1. Library Comparison Matrix

| Feature | pydantic-settings | python-decouple | dynaconf |
|---------|-------------------|-----------------|----------|
| **Type Validation** | Native with Pydantic types | Manual cast functions | Optional via validators |
| **Environment Variables** | Automatic with prefix support | Manual load with cast | Automatic with layers |
| **.env File Support** | Built-in via SettingsConfigDict | Built-in | Built-in multi-format |
| **Nested Configuration** | Native with env_nested_delimiter | Manual | Native with layers |
| **Azure Key Vault** | Official AzureKeyVaultSettingsSource | None | HashiCorp Vault only |
| **AWS Secrets Manager** | Official AWSSecretsManagerSettingsSource | None | None |
| **GCP Secret Manager** | Official GoogleSecretManagerSettingsSource | None | None |
| **SecretStr Support** | Native (masks in logs) | None | None |
| **Multi-Environment** | Via source priority | Via file selection | Native env layers |
| **FastAPI Integration** | Official recommendation | Community patterns | Community patterns |
| **File Formats** | .env, TOML, YAML, JSON | .env, .ini | YAML, TOML, JSON, INI, Python |
| **Validation Errors** | Clear Pydantic errors | Runtime errors | Custom validators |
| **Learning Curve** | Medium (Pydantic knowledge) | Low | High |
| **Maintenance** | Active (Pydantic team) | Moderate | Active |
| **Stars (GitHub)** | Part of Pydantic (20k+) | 2.6k | 3.8k |

### Detailed Analysis

#### pydantic-settings (Recommended)

**Strengths**:
- Type-safe configuration with automatic validation
- Official cloud provider integrations (Azure, AWS, GCP)
- SecretStr type prevents accidental credential logging
- Clear validation error messages at startup (fail-fast)
- Official FastAPI recommendation
- Nested model support with delimiter parsing
- Configurable source priority

**Limitations**:
- Requires Pydantic knowledge
- JSON parsing for complex types in env vars
- Nested schema env var reading can be complex

**Source**: [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

#### python-decouple

**Strengths**:
- Simple, intuitive API
- Solves bool coercion problem (DEBUG=False evaluated correctly)
- Lightweight with minimal dependencies
- Can replace python-dotenv entirely

**Limitations**:
- No native type validation beyond cast
- No cloud secrets integration
- No nested configuration support
- Manual validation required

**Source**: [python-decouple PyPI](https://pypi.org/project/python-decouple/)

#### dynaconf

**Strengths**:
- Most flexible multi-format support
- Native environment layering (dev/staging/prod)
- HashiCorp Vault and Redis integration
- Lazy loading of values
- Pydantic validator support available

**Limitations**:
- No native Azure Key Vault (only HashiCorp Vault)
- Higher complexity and learning curve
- Overkill for simpler applications

**Source**: [Dynaconf Documentation](https://www.dynaconf.com/)

---

## 2. Recommended Stack

### Primary Recommendation: pydantic-settings + azure-keyvault-secrets

```
pydantic-settings[azure-key-vault]>=2.0.0
azure-identity>=1.15.0
python-dotenv>=1.0.0  # Optional, pydantic-settings handles .env natively
```

### Rationale

1. **Type Safety**: Native Pydantic validation catches configuration errors at startup
2. **Cloud-Native**: Official Azure Key Vault integration via `AzureKeyVaultSettingsSource`
3. **Security**: `SecretStr` type prevents credential logging
4. **Fail-Fast**: Validation errors surface immediately with clear messages
5. **FastAPI Alignment**: Official recommendation for FastAPI applications
6. **Source Priority**: Configurable precedence (env > .env > secrets > Key Vault > defaults)
7. **Enterprise Ready**: Supports all major cloud secret managers

### Installation

```bash
pip install "pydantic-settings[azure-key-vault]" azure-identity
```

---

## 3. API Design Recommendations

### 3.1 Settings Class Structure

```python
from pydantic import BaseModel, SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseModel):
    """Nested model for database configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "netrun"
    user: str = "app"
    password: SecretStr  # Never logged

class AzureSettings(BaseModel):
    """Nested model for Azure configuration."""
    tenant_id: str
    subscription_id: str
    key_vault_url: str | None = None

class Settings(BaseSettings):
    """
    Application settings with multi-source support.

    Priority (highest to lowest):
    1. Environment variables
    2. .env file
    3. Azure Key Vault (when configured)
    4. Default values
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "NetrunService"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = False

    # Nested configurations
    database: DatabaseSettings = DatabaseSettings()
    azure: AzureSettings | None = None

    # Secrets (using SecretStr)
    api_key: SecretStr | None = None
    jwt_secret: SecretStr | None = None
```

### 3.2 Environment Variable Patterns

```bash
# .env file example
APP_NAME=MyService
ENVIRONMENT=development
DEBUG=true

# Nested configuration via delimiter
DATABASE__HOST=localhost
DATABASE__PORT=5432
DATABASE__PASSWORD=secret_value

# Azure configuration
AZURE__TENANT_ID=00000000-0000-0000-0000-000000000000
AZURE__KEY_VAULT_URL=https://mykeyvault.vault.azure.net
```

### 3.3 Singleton Pattern with Caching

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    """
    Returns cached settings instance.

    Using lru_cache ensures settings are loaded once,
    avoiding repeated file I/O and Key Vault API calls.
    """
    return Settings()
```

### 3.4 FastAPI Dependency Injection

```python
from fastapi import Depends, FastAPI
from typing import Annotated

app = FastAPI()

SettingsDep = Annotated[Settings, Depends(get_settings)]

@app.get("/info")
async def get_info(settings: SettingsDep):
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
    }
```

---

## 4. Azure Key Vault Integration Pattern

### 4.1 Custom Settings Source Configuration

```python
import os
from azure.identity import DefaultAzureCredential
from pydantic_settings import (
    AzureKeyVaultSettingsSource,
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )

    # Configuration fields
    database_password: SecretStr | None = None
    api_key: SecretStr | None = None
    jwt_secret: SecretStr | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings source priority.

        Priority (highest to lowest):
        1. init_settings - Constructor arguments
        2. env_settings - Environment variables
        3. dotenv_settings - .env file
        4. file_secret_settings - Docker secrets directory
        5. azure_key_vault - Azure Key Vault (lowest, provides defaults)
        """
        sources = [
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        ]

        # Add Azure Key Vault if URL is configured
        key_vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
        if key_vault_url:
            azure_source = AzureKeyVaultSettingsSource(
                settings_cls,
                key_vault_url,
                DefaultAzureCredential(),
                # Map kebab-case Key Vault names to snake_case fields
                dash_to_underscore=True,
            )
            sources.append(azure_source)

        return tuple(sources)
```

### 4.2 Authentication Patterns

```python
from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    ClientSecretCredential,
    ChainedTokenCredential,
)

def get_azure_credential():
    """
    Get appropriate Azure credential based on environment.

    DefaultAzureCredential automatically handles:
    - Local dev: Azure CLI, VS Code, environment variables
    - Azure: Managed Identity (preferred)
    - CI/CD: Service Principal via environment variables
    """
    return DefaultAzureCredential()

# For explicit control in production
def get_production_credential():
    """Production credential with explicit fallback chain."""
    return ChainedTokenCredential(
        ManagedIdentityCredential(),  # Try managed identity first
        ClientSecretCredential(       # Fall back to service principal
            tenant_id=os.environ.get("AZURE_TENANT_ID"),
            client_id=os.environ.get("AZURE_CLIENT_ID"),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET"),
        ),
    )
```

### 4.3 Caching Strategy for Key Vault

```python
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Any

class CachedKeyVaultClient:
    """
    Key Vault client with local caching to reduce API calls.

    Azure Key Vault SDK does not provide built-in caching.
    Implement application-level caching for frequently accessed secrets.
    """

    def __init__(self, vault_url: str, cache_ttl_seconds: int = 300):
        self.client = SecretClient(
            vault_url=vault_url,
            credential=DefaultAzureCredential(),
        )
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache: dict[str, tuple[Any, datetime]] = {}

    def get_secret(self, name: str) -> str | None:
        """Get secret with caching."""
        # Check cache
        if name in self._cache:
            value, cached_at = self._cache[name]
            if datetime.now() - cached_at < self.cache_ttl:
                return value

        # Fetch from Key Vault
        try:
            secret = self.client.get_secret(name)
            self._cache[name] = (secret.value, datetime.now())
            return secret.value
        except Exception:
            return None

    def clear_cache(self):
        """Clear all cached secrets."""
        self._cache.clear()
```

### 4.4 Hybrid Configuration Pattern

```python
class HybridSettings(BaseSettings):
    """
    Settings that combine local .env for non-secrets
    and Azure Key Vault for secrets.

    Pattern:
    - .env: Non-sensitive configuration (app name, ports, feature flags)
    - Key Vault: Secrets (passwords, API keys, certificates)
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )

    # Non-secrets from .env
    app_name: str = "NetrunService"
    environment: str = "development"
    log_level: str = "INFO"

    # Secrets from Key Vault (fallback to env for local dev)
    database_password: SecretStr
    api_key: SecretStr

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings,
                                    env_settings, dotenv_settings,
                                    file_secret_settings):
        """Priority: env > .env > Key Vault"""
        sources = [init_settings, env_settings, dotenv_settings]

        key_vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
        if key_vault_url:
            sources.append(AzureKeyVaultSettingsSource(
                settings_cls,
                key_vault_url,
                DefaultAzureCredential(),
                dash_to_underscore=True,
            ))

        return tuple(sources)
```

---

## 5. Security Considerations

### 5.1 Never Log Credentials

```python
from pydantic import SecretStr
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # CORRECT: SecretStr masks value in logs
    database_password: SecretStr
    api_key: SecretStr

    # INCORRECT: str would expose in logs
    # database_password: str  # DON'T DO THIS

# SecretStr behavior
settings = Settings(database_password="super_secret", api_key="key123")
print(settings.database_password)  # Output: **********
print(settings.database_password.get_secret_value())  # Output: super_secret

# Safe logging
logger.info(f"Settings loaded: {settings}")  # Secrets are masked
```

### 5.2 .env File Security

```python
# .gitignore
.env
.env.local
.env.*.local
*.pem
*.key

# Provide template for team members
# .env.example (commit this)
APP_NAME=NetrunService
ENVIRONMENT=development
DATABASE__PASSWORD=  # Set locally, never commit
API_KEY=  # Set locally, never commit
```

### 5.3 Validation at Startup (Fail-Fast)

```python
from pydantic import ValidationError
import sys

def validate_settings():
    """
    Validate configuration at application startup.
    Exit immediately if configuration is invalid.
    """
    try:
        settings = Settings()

        # Additional custom validation
        if settings.environment == "production":
            if not settings.azure or not settings.azure.key_vault_url:
                raise ValueError("Key Vault URL required in production")

        return settings

    except ValidationError as e:
        print("Configuration Error:")
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            print(f"  - {field}: {error['msg']}")
        sys.exit(1)

    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)

# Application entry point
if __name__ == "__main__":
    settings = validate_settings()
    # Continue with application startup
```

### 5.4 Production Security Checklist

```markdown
## Pre-Deployment Security Checklist

- [ ] All secrets use SecretStr type
- [ ] .env files excluded from version control
- [ ] .env.example provided with empty values
- [ ] Production uses Key Vault, not .env files
- [ ] Managed Identity configured (no credential storage)
- [ ] Key Vault access logged and audited
- [ ] Secret rotation policy established
- [ ] CI/CD secrets configured separately (not in code)
- [ ] No secrets echoed in build logs
- [ ] HTTPS enforced for all secret transmission
```

### 5.5 Environment-Specific Patterns

```python
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    environment: Environment = Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def should_use_key_vault(self) -> bool:
        """Key Vault required in staging and production."""
        return self.environment in (Environment.STAGING, Environment.PRODUCTION)

    def validate_production_requirements(self):
        """Additional validation for production environment."""
        if self.is_production:
            assert self.api_key is not None, "API key required in production"
            assert self.database.password is not None, "DB password required"
```

---

## 6. Multi-Environment Support

### 6.1 Environment-Specific .env Files

```
project/
  .env                    # Shared defaults
  .env.development        # Development overrides
  .env.staging           # Staging overrides
  .env.production        # Production (usually empty - use Key Vault)
  .env.example           # Template (committed to git)
```

### 6.2 Loading Pattern

```python
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_env_file() -> str | tuple[str, ...]:
    """
    Determine which .env files to load based on ENVIRONMENT.

    Later files override earlier ones.
    """
    env = os.environ.get("ENVIRONMENT", "development")

    base_files = [".env"]
    env_specific = f".env.{env}"

    if os.path.exists(env_specific):
        return (".env", env_specific)
    return ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
    )
```

### 6.3 Priority Override Pattern

```python
# Pattern for layered configuration
from dotenv import dotenv_values

def load_layered_config() -> dict:
    """
    Load configuration with explicit layering.

    Priority (highest wins):
    1. OS environment variables
    2. .env.secret (local secrets, gitignored)
    3. .env.{environment} (environment-specific)
    4. .env (shared defaults)
    """
    env = os.environ.get("ENVIRONMENT", "development")

    config = {
        **dotenv_values(".env"),                    # Base defaults
        **dotenv_values(f".env.{env}"),            # Environment-specific
        **dotenv_values(".env.secret"),            # Local secrets
        **os.environ,                               # OS environment (highest)
    }
    return config
```

---

## 7. Testing Configuration

### 7.1 Test Settings Override

```python
import pytest
from unittest.mock import patch

@pytest.fixture
def test_settings():
    """Provide test configuration."""
    with patch.dict(os.environ, {
        "APP_NAME": "TestApp",
        "ENVIRONMENT": "testing",
        "DATABASE__HOST": "localhost",
        "DATABASE__PASSWORD": "test_password",
    }, clear=True):
        # Clear any cached settings
        get_settings.cache_clear()
        yield Settings()

def test_database_connection(test_settings):
    assert test_settings.database.host == "localhost"
    assert test_settings.database.password.get_secret_value() == "test_password"
```

### 7.2 Configuration Validation Tests

```python
import pytest
from pydantic import ValidationError

def test_invalid_environment_rejected():
    """Ensure invalid environment values fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(environment="invalid_env")

    assert "environment" in str(exc_info.value)

def test_missing_required_field():
    """Ensure missing required fields fail at startup."""
    with pytest.raises(ValidationError):
        # Assuming api_key is required
        Settings(api_key=None)
```

---

## 8. Implementation Recommendations for Service #63

### 8.1 Core Module Structure

```
Service_63_Unified_Configuration/
  netrun_config/
    __init__.py
    settings.py          # BaseSettings classes
    sources.py           # Custom settings sources
    key_vault.py         # Azure Key Vault integration
    validation.py        # Custom validators
    exceptions.py        # Configuration exceptions
  tests/
    test_settings.py
    test_key_vault.py
  .env.example
  pyproject.toml
  README.md
```

### 8.2 Public API Design

```python
# netrun_config/__init__.py
from .settings import Settings, get_settings
from .key_vault import CachedKeyVaultClient
from .validation import validate_at_startup
from .exceptions import ConfigurationError

__all__ = [
    "Settings",
    "get_settings",
    "CachedKeyVaultClient",
    "validate_at_startup",
    "ConfigurationError",
]
```

### 8.3 Integration with Service #61 (Unified Logging)

```python
from netrun_logging import get_logger
from netrun_config import get_settings, validate_at_startup

logger = get_logger(__name__)

def main():
    # Validate configuration first (fail-fast)
    settings = validate_at_startup()

    # Log configuration (secrets masked automatically)
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    logger.debug(f"Database host: {settings.database.host}")
    # SecretStr prevents: logger.debug(f"Password: {settings.database.password}")
```

---

## 9. Sources and References

### Official Documentation
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic Settings API Reference](https://docs.pydantic.dev/latest/api/pydantic_settings/)
- [Azure Key Vault Secrets Python Client](https://learn.microsoft.com/en-us/python/api/overview/azure/keyvault-secrets-readme?view=azure-python)
- [Azure Key Vault Python Quickstart](https://learn.microsoft.com/en-us/azure/key-vault/secrets/quick-create-python)
- [FastAPI Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)

### Community Resources
- [Environment Variables using Pydantic - Medium](https://medium.com/@mahimamanik.22/environment-variables-using-pydantic-ff6ccb2b8976)
- [Twelve-Factor Python Applications using Pydantic Settings](https://medium.com/datamindedbe/twelve-factor-python-applications-using-pydantic-settings-f74a69906f2f)
- [Managing Multiple Environments with Python-dotenv](https://trycatchdebug.net/news/1228776/python-dotenv-in-multiple-environments)
- [Pydantic BaseSettings vs Dynaconf Comparison](https://leapcell.io/blog/pydantic-basesettings-vs-dynaconf-a-modern-guide-to-application-configuration)
- [6 Essential Python Configuration Management Libraries](https://jsschools.com/python/6-essential-python-configuration-management-librar/)

### Security Best Practices
- [How to Handle Secrets in Python - GitGuardian](https://blog.gitguardian.com/how-to-handle-secrets-in-python/)
- [Managing Secrets in Python Applications Securely](https://securecodingpractices.com/managing-secrets-in-python-applications-securely/)
- [Best Practice: How to Store Secrets in Python Project](https://savelev.medium.com/best-practice-how-to-store-secrets-and-settings-in-python-project-e3ee45b3094c)
- [Working with Python Configuration Files - Configu](https://configu.com/blog/working-with-python-configuration-files-tutorial-best-practices/)

### Configuration Validation
- [Best Practices for Working with Configuration in Python](https://tech.preferred.jp/en/blog/working-with-configuration-in-python/)
- [Best Practices for Python-based Pipelines Configuration](https://belux.micropole.com/blog/python/blog-best-practices-for-configurations-in-python-based-pipelines/)

### Package Repositories
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/)
- [azure-keyvault-secrets PyPI](https://pypi.org/project/azure-keyvault-secrets/)
- [python-dotenv PyPI](https://pypi.org/project/python-dotenv/)
- [pydantic-settings-azure-app-configuration PyPI](https://pypi.org/project/pydantic-settings-azure-app-configuration/)
- [pydantic-azure-secrets GitHub](https://github.com/kewtree1408/pydantic-azure-secrets)

---

## 10. Micro-Retrospective

### What Went Well
1. Comprehensive coverage of all major Python configuration libraries with clear comparison matrix
2. Official pydantic-settings documentation provided excellent patterns for Azure Key Vault integration
3. Security best practices well-documented across multiple authoritative sources

### What Needs Improvement
1. Azure Key Vault SDK documentation fetch timed out - relied on search results and quickstart guide
2. Limited hands-on testing examples for the hybrid configuration pattern

### Action Items
1. **Validate code samples**: Test all code examples in Service #63 implementation before finalizing (by implementation start)
2. **Monitor pydantic-settings releases**: Track v2.x releases for new Azure integration features (ongoing)

### Patterns Discovered
- **Pattern**: Use `@lru_cache` decorator on settings getter to avoid repeated file/API reads
- **Anti-Pattern**: Using plain `str` for secrets instead of `SecretStr` - leads to credential exposure in logs

---

*Report generated by Technical Research Agent*
*Netrun Systems - Service Library v2*
