# netrun-config

Unified configuration management for Netrun Systems portfolio projects.

## Features

- **Type-Safe Configuration**: Built on Pydantic v2 with automatic validation
- **Azure Key Vault Integration**: Seamless secrets management for production
- **Environment-Specific**: Development, staging, production, testing environments
- **Security Best Practices**: 32-char secret validation, SecretStr support, CORS parsing
- **Caching**: LRU cache for performance optimization
- **Framework Integration**: Works seamlessly with FastAPI, Flask, Django

## Installation

```bash
pip install netrun-config
```

With Azure Key Vault support:

```bash
pip install netrun-config[azure]
```

## Quick Start

### Basic Usage

```python
from netrun_config import BaseConfig, Field, get_settings

class MyAppSettings(BaseConfig):
    app_name: str = Field(default="MyApp")
    api_key: str = Field(..., env="API_KEY")

settings = get_settings(MyAppSettings)
print(settings.app_name)  # "MyApp"
print(settings.is_production)  # False (default: development)
```

### Environment Variables

Create a `.env` file:

```bash
APP_NAME=MyAwesomeApp
APP_ENVIRONMENT=development
APP_SECRET_KEY=your-32-character-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/db
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Azure Key Vault Integration

```python
from netrun_config import BaseConfig, KeyVaultMixin, Field

class ProductionSettings(BaseConfig, KeyVaultMixin):
    KEY_VAULT_URL: str = Field(default=None, env="KEY_VAULT_URL")
    database_password: str = Field(default=None, env="DATABASE_PASSWORD")

    @property
    def database_password_resolved(self) -> str:
        if self.is_production and self.KEY_VAULT_URL:
            return self.get_keyvault_secret("database-password") or ""
        return self.database_password

settings = get_settings(ProductionSettings)
```

## Built-in Configuration

`BaseConfig` includes common configuration patterns from 12 Netrun Systems projects:

### Application Settings
- `app_name`: Application name (default: "Netrun Application")
- `app_version`: Application version (default: "1.0.0")
- `app_environment`: Environment (development, staging, production, testing)
- `app_debug`: Debug mode (default: False)

### Security Settings
- `app_secret_key`: Application secret key (validated ≥32 chars)
- `jwt_secret_key`: JWT secret key (validated ≥32 chars)
- `jwt_algorithm`: JWT algorithm (default: "HS256")
- `jwt_access_token_expire_minutes`: Access token TTL (default: 15)
- `jwt_refresh_token_expire_days`: Refresh token TTL (default: 7)

### CORS Settings
- `cors_origins`: Allowed CORS origins (parses comma-separated strings)
- `cors_allow_credentials`: Allow credentials (default: True)

### Database Settings
- `database_url`: Database connection URL
- `database_pool_size`: Connection pool size (default: 10)
- `database_max_overflow`: Max overflow connections (default: 20)
- `database_pool_timeout`: Pool timeout in seconds (default: 30)
- `database_pool_recycle`: Pool recycle time in seconds (default: 3600)

### Redis Settings
- `redis_url`: Redis connection URL
- `redis_host`: Redis host (default: "localhost")
- `redis_port`: Redis port (default: 6379)
- `redis_db`: Redis database (default: 0)
- `redis_password`: Redis password

### Logging Settings
- `log_level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_format`: Log format (default: "json")
- `log_file`: Log file path

### Monitoring Settings
- `enable_metrics`: Enable metrics (default: True)
- `metrics_port`: Metrics port (default: 9090)
- `sentry_dsn`: Sentry DSN for error tracking

### Azure Settings
- `azure_subscription_id`: Azure subscription ID
- `azure_tenant_id`: Azure tenant ID
- `azure_client_id`: Azure client ID
- `azure_client_secret`: Azure client secret

## Property Methods

### Environment Checks
```python
settings.is_production  # True if environment == "production"
settings.is_development  # True if environment == "development"
settings.is_staging  # True if environment == "staging"
settings.is_testing  # True if environment == "testing"
```

### Database URL Transformation
```python
settings.database_url  # postgresql://user:pass@localhost/db
settings.database_url_async  # postgresql+asyncpg://user:pass@localhost/db
```

### Redis URL Construction
```python
settings.redis_url_full  # redis://:password@localhost:6379/0
```

## Validation

All configurations are validated at startup with clear error messages:

```python
# Invalid environment
BaseConfig(app_environment="invalid")
# ValidationError: Environment must be one of: ['development', 'staging', 'production', 'testing']

# Short secret key
BaseConfig(app_secret_key="short")
# ValidationError: Secret keys must be at least 32 characters long

# Invalid log level
BaseConfig(log_level="TRACE")
# ValidationError: Log level must be one of: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
```

## FastAPI Integration

```python
from typing import Annotated
from fastapi import Depends, FastAPI
from netrun_config import BaseConfig, get_settings

app = FastAPI()
SettingsDep = Annotated[BaseConfig, Depends(get_settings)]

@app.get("/")
async def root(settings: SettingsDep):
    return {"app": settings.app_name, "version": settings.app_version}
```

## Testing

Override settings in tests:

```python
import pytest
from netrun_config import BaseConfig, get_settings, reload_settings

@pytest.fixture
def test_settings(monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    reload_settings()  # Clear cache
    yield get_settings()
```

## Azure Key Vault Setup

### Local Development (Azure CLI)

```bash
az login
az account set --subscription <subscription-id>
```

### Production (Managed Identity)

1. Enable Managed Identity on Azure App Service or VM
2. Grant Key Vault access:
   ```bash
   az keyvault set-policy --name <vault-name> \
     --object-id <managed-identity-id> \
     --secret-permissions get list
   ```
3. Set environment variable:
   ```bash
   KEY_VAULT_URL=https://<vault-name>.vault.azure.net
   ```

## Roadmap: Advanced Key Vault Features (v2.0)

Research completed December 2025 identified 15+ enterprise features for future releases.
See `RESEARCH_KEYVAULT_ADVANCED_PATTERNS_v1.0.md` for full analysis.

### Phase 1: Foundation (Q1 2026)
- **TTL-Based Caching**: 8-hour cache with configurable TTL per Microsoft best practices
- **Pydantic Settings Source**: Native `settings_customise_sources()` integration
- **Improved Credential Chain**: `DefaultAzureCredential` with optimized exclusions

### Phase 2: Enterprise (Q1-Q2 2026)
- **Multi-Vault Support**: Environment-specific vault configuration
- **Batch Prefetching**: Async bulk secret loading at startup
- **Lazy Loading Descriptors**: On-demand secret resolution
- **Secret Rotation Detection**: Poll-based version checking

### Phase 3: Advanced (Q2 2026)
- **Certificate Management**: Full certificate lifecycle support
- **Key Management**: Encryption key operations (wrap/unwrap, encrypt/decrypt)
- **Audit Logging**: Structured logging with compliance support (SOC2, ISO27001)
- **Event Grid Integration**: Real-time rotation notifications

### Competitive Comparison

| Feature | pydantic-settings | dynaconf | netrun-config (v2.0) |
|---------|-------------------|----------|----------------------|
| Azure KV TTL Cache | No | No | Planned |
| Multi-Vault | No | No | Planned |
| Rotation Detection | No | No | Planned |
| Certificate Mgmt | No | No | Planned |
| Audit Logging | No | No | Planned |

## Examples

See the `examples/` directory:
- `basic_usage.py`: Simple .env configuration
- `keyvault_integration.py`: Azure Key Vault integration
- `fastapi_integration.py`: FastAPI dependency injection

## Architecture

`netrun-config` consolidates configuration patterns from 12 Netrun Systems projects:

- **3,200 LOC** duplicate configuration code → **480 LOC** core library
- **85%** code reduction
- **89.7%** reusability across projects

### Source Projects
- Wilbur (578 LOC) → 128 LOC (78% reduction)
- NetrunCRM (476 LOC) → 126 LOC (74% reduction)
- GhostGrid (559 LOC) → 130 LOC (77% reduction)
- Intirkast (380 LOC) → 115 LOC (70% reduction)
- +8 additional projects

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `pytest`
- Code coverage ≥ 80%: `pytest --cov`
- Code formatted: `black .`
- Linting passes: `ruff check .`

## License

MIT License - Copyright (c) 2025 Netrun Systems

## Author

Daniel Garza (daniel@netrunsystems.com)

## Version

1.1.0 - December 2025

### Latest Release Notes

**Build Status:**
- Tests: 197 passed, 16 skipped (Azure-specific tests)
- Test Coverage: 100% on core modules
- Distribution: Successfully built and validated
- Artifacts:
  - Source: netrun_config-1.1.0.tar.gz (40K)
  - Wheel: netrun_config-1.1.0-py3-none-any.whl (22K)
- Twine Validation: PASSED

**Key Features:**
- Multi-vault client with cache management
- Secret rotation detection
- Pydantic Settings Source integration
- LRU caching with TTL support
- Comprehensive validators for environment, secrets, CORS, database URLs

## Links

- Documentation: [GitHub README](https://github.com/netrunsystems/netrun-config)
- Issues: [GitHub Issues](https://github.com/netrunsystems/netrun-config/issues)
- PyPI: [netrun-config](https://pypi.org/project/netrun-config/)
