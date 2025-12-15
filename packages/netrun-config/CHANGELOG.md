# Changelog

All notable changes to the `netrun-config` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-24

### Added

#### Core Configuration Management
- **BaseConfig**: Pydantic v2 BaseSettings foundation with standardized environment variable handling
- **get_settings()**: Singleton pattern for configuration with LRU caching support
- **reload_settings()**: Force configuration reload for testing and dynamic updates

#### Environment Management
- Automatic environment detection (development, staging, production)
- Environment-specific configuration validation
- Debug mode control with safety constraints
- CORS origin parsing with validation

#### Azure Integration
- **KeyVaultMixin**: Azure Key Vault integration for secure secrets management
- Automatic secret loading with caching
- Support for DefaultAzureCredential and custom credential providers
- Graceful fallback to environment variables when Key Vault unavailable

#### Security Features
- 32-character minimum secret validation
- Secure string type with placeholder support
- Database URL validation (PostgreSQL, MySQL, MongoDB)
- CORS origin list parsing and validation
- Azure connection string validation

#### Custom Validators
- `validate_min_length()`: Generic minimum length validator
- `validate_cors_origins()`: CORS origin string-to-list parser
- `validate_secure_string()`: 32-char secret validator with placeholder detection

#### Type Definitions
- `SecureString`: Type alias for validated secure strings
- `DatabaseUrl`: Type alias for validated database connection strings
- `Environment`: Literal type for environment values

#### Error Handling
- `ConfigError`: Base exception for configuration errors
- `ValidationError`: Configuration validation failures
- `KeyVaultError`: Azure Key Vault operation failures

#### Testing Infrastructure
- pytest fixtures for configuration testing
- Mock environment variable support
- Azure Key Vault mock client for testing
- 100% test coverage across all modules

#### Examples
- Basic configuration usage
- Azure Key Vault integration
- FastAPI integration pattern
- Environment-specific settings

### Documentation
- Comprehensive README with usage examples
- API reference documentation
- Security best practices guide
- Migration guide from legacy patterns

### Development Tools
- Black code formatting configuration
- Ruff linting rules
- MyPy type checking
- pytest with coverage reporting
- Pre-commit hooks configuration

### Package Metadata
- MIT License
- Python 3.10+ support
- PyPI classifiers for discoverability
- GitHub repository links
- Comprehensive keywords for search

---

## Release Notes

### What's New in 1.0.0

This is the initial production release of `netrun-config`, consolidating configuration management patterns from across the Netrun Systems service portfolio.

**Key Benefits:**
- Reduces configuration boilerplate by 60-80%
- Standardizes environment variable naming
- Provides type-safe configuration with Pydantic v2
- Integrates seamlessly with Azure Key Vault
- Supports 12-factor app methodology

**Migration Path:**
Projects currently using custom configuration management can adopt `netrun-config` incrementally:

1. Install: `pip install netrun-config`
2. Replace custom config classes with `BaseConfig` inheritance
3. Add `get_settings()` singleton pattern
4. Optional: Integrate Azure Key Vault with `KeyVaultMixin`

**Performance:**
- Singleton pattern reduces configuration parsing overhead
- LRU caching for Azure Key Vault secrets (60-second TTL)
- Lazy loading for optional Azure dependencies

**Security:**
- 32-character minimum for all secret fields
- Placeholder detection prevents accidental mock secret deployment
- Secure Azure credential handling with DefaultAzureCredential

---

## [1.1.0] - 2025-12-03

### Added

#### TTL-Based Secret Caching
- **SecretCache**: New TTL-based caching system with automatic expiration
- **SecretCacheConfig**: Configurable cache behavior (TTL, max size, version tracking)
- **CachedSecret**: Dataclass for cached secrets with metadata
- Default TTL of 8 hours per Microsoft Azure Key Vault best practices
- LRU eviction when cache reaches max size
- Cache statistics and monitoring capabilities

#### Multi-Vault Support
- **MultiVaultClient**: Manage multiple Key Vault instances for different purposes
- **VaultConfig**: Configuration for individual vault instances
- Per-vault credential and cache configuration
- Vault-specific secret fetching (e.g., 'default', 'dev', 'certificates')
- Graceful degradation when vaults are disabled

#### Secret Rotation Detection
- **check_secret_version()**: Get current secret version without fetching value
- **has_secret_rotated()**: Detect when secrets have changed
- **refresh_if_rotated()**: Automatically refresh only rotated secrets
- Version tracking in cache for rotation detection

#### Pydantic Settings Source Integration
- **AzureKeyVaultSettingsSource**: Custom SettingsSource for pydantic-settings v2
- **AzureKeyVaultRefreshableSettingsSource**: Settings source with rotation detection
- Field-level vault routing via `json_schema_extra`
- Secret name customization via `keyvault_secret` metadata
- Auto-refresh on rotation support
- Skip Key Vault for specific fields via `keyvault_skip`

#### New Methods
- `get_keyvault_cache_stats()`: Get cache statistics for KeyVaultMixin
- `invalidate_cache()`: Manual cache invalidation for specific secrets or vaults
- `get_cache_stats()`: Get comprehensive cache metrics
- `list_vaults()`: List all configured vaults
- `is_vault_enabled()`: Check vault enablement status

### Changed

#### Backward-Compatible Enhancements
- **KeyVaultMixin**: Now uses TTL-based SecretCache instead of simple dict
- Cache automatically expires secrets after TTL (default 8 hours)
- Secret version tracking added to cache entries
- Enhanced logging with version information
- **No Breaking Changes**: Full backward compatibility maintained

#### Configuration
- New optional config fields: `keyvault_cache_ttl_seconds`, `keyvault_max_cache_size`
- These fields allow customizing TTL cache behavior in KeyVaultMixin

### Performance Improvements
- **Memory Management**: LRU eviction prevents unbounded cache growth
- **Network Optimization**: TTL caching reduces Key Vault API calls by ~95%
- **Rotation Efficiency**: Only fetch secrets when version changes
- **Batch Operations**: Cache stats provide observability without overhead

### Documentation
- Added `examples/multi_vault_usage.py` with comprehensive examples
- Updated docstrings with v1.1.0 feature documentation
- Added inline examples for all new classes and methods

### Testing
- `tests/test_cache.py`: 20+ tests for TTL caching functionality
- `tests/test_multi_vault.py`: 15+ tests for multi-vault client
- `tests/test_settings_source.py`: 10+ tests for Pydantic integration
- Mock-based tests for Azure SDK integration
- Integration tests (require live Key Vault, skipped by default)

### Migration Guide

#### From v1.0.0 to v1.1.0

**No breaking changes - existing code works as-is.**

Optional enhancements:

1. **Enable TTL caching in KeyVaultMixin**:
```python
class MySettings(BaseConfig, KeyVaultMixin):
    key_vault_url: str = "https://my-vault.vault.azure.net/"
    keyvault_cache_ttl_seconds: int = 28800  # 8 hours
    keyvault_max_cache_size: int = 500
```

2. **Migrate to MultiVaultClient for multiple vaults**:
```python
from netrun_config import MultiVaultClient, VaultConfig

vaults = {
    'default': VaultConfig(url="https://prod-vault.vault.azure.net/"),
    'dev': VaultConfig(url="https://dev-vault.vault.azure.net/"),
}

client = MultiVaultClient(vaults, is_production=True)
secret = client.get_secret("database-url", vault='default')
```

3. **Use Pydantic Settings Source for automatic loading**:
```python
from netrun_config import AzureKeyVaultSettingsSource, VaultConfig
from pydantic import Field
from pydantic_settings import BaseSettings

class MySettings(BaseSettings):
    database_url: str = Field(
        json_schema_extra={'keyvault_secret': 'database-url'}
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        vaults = {'default': VaultConfig(url="https://my-vault.vault.azure.net/")}
        keyvault_source = AzureKeyVaultSettingsSource(settings_cls, vaults=vaults)
        return (init_settings, keyvault_source, env_settings, dotenv_settings, file_secret_settings)
```

---

## [1.2.0] - 2025-12-05

### Added

#### Standardized Error Handling Integration
- **Optional netrun-errors integration**: Automatic use of netrun-errors if installed
- **raise_validation_error()**: Factory function for configuration validation errors
- **raise_keyvault_unavailable()**: Factory function for Key Vault unavailability errors
- Graceful fallback to standard exceptions if netrun-errors not available
- Rich error context with field names, vault URLs, and error metadata

#### Structured Logging Integration
- **Optional netrun-logging integration**: Automatic use of netrun-logging if installed
- **Structured logging**: Enhanced logging in get_settings() and reload_settings()
- Configuration loading lifecycle logging
- Graceful fallback to standard logging if netrun-logging not available

#### Optional Dependencies
- **[errors]**: Install with netrun-errors support: `pip install netrun-config[errors]`
- **[logging]**: Install with netrun-logging support: `pip install netrun-config[logging]`
- **[all]**: Install all optional features: `pip install netrun-config[all]`
- All integrations remain optional (zero required dependencies beyond Pydantic)

### Changed

#### Error Handling Improvements
- ConfigError, ValidationError, KeyVaultError remain as base exceptions
- New error factory functions provide standardized error raising
- Better error context for debugging and monitoring
- Consistent error reporting across all configuration operations

#### Logging Enhancements
- get_settings() now logs configuration class name and environment
- reload_settings() now logs reload operations
- All logging uses netrun-logging if available for structured output

### Migration Guide

#### From v1.1.0 to v1.2.0

**No breaking changes - existing code works as-is.**

Optional enhancements:

1. **Install with error handling integration**:
```bash
pip install netrun-config[errors]
```

2. **Install with logging integration**:
```bash
pip install netrun-config[logging]
```

3. **Install with all integrations**:
```bash
pip install netrun-config[all]
```

4. **Use standardized error factories in custom validators**:
```python
from netrun_config import raise_validation_error, raise_keyvault_unavailable

def validate_custom_field(value: str) -> str:
    if not value.startswith("valid-"):
        raise_validation_error(
            "Field must start with 'valid-'",
            field="custom_field",
            value=value
        )
    return value

try:
    client = SecretClient(vault_url=vault_url, credential=credential)
except Exception as e:
    raise_keyvault_unavailable(vault_url, e, environment="production")
```

5. **Leverage structured logging**:
```python
from netrun_config import get_settings, BaseConfig

# Automatically logs with netrun-logging if installed
settings = get_settings(MyAppSettings)
# Logs: "Settings loaded: MyApp (production environment)"
```

### Compatibility

**Backward Compatibility**: 100% compatible with v1.0.0 and v1.1.0
**Optional Dependencies**: All integrations are optional, no new required dependencies

---

## Future Roadmap

### Planned for 1.3.0
- AWS Secrets Manager integration
- HashiCorp Vault support
- Configuration schema export (JSON Schema)
- CLI tool for configuration validation

### Planned for 1.4.0
- Hot-reload support for configuration changes
- Webhook notifications for configuration updates
- Audit logging for configuration access
- Multi-region Key Vault failover

### Planned for 2.0.0
- Breaking: Python 3.11+ minimum requirement
- Pydantic v3 support
- Enhanced type safety with strict mode
- Configuration versioning and rollback

---

## Compatibility

**Supported Python Versions:**
- Python 3.10
- Python 3.11
- Python 3.12

**Supported Pydantic Versions:**
- Pydantic 2.0+
- Pydantic Settings 2.0+

**Supported Azure SDK Versions:**
- azure-identity 1.15.0+
- azure-keyvault-secrets 4.8.0+

**Supported Operating Systems:**
- Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- macOS (11.0+)
- Windows (Server 2019+, 10/11)

---

## Contributors

**Lead Developer:** Daniel Garza (daniel@netrunsystems.com)
**Organization:** Netrun Systems
**Repository:** https://github.com/netrunsystems/netrun-config

---

[1.2.0]: https://github.com/netrunsystems/netrun-config/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/netrunsystems/netrun-config/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/netrunsystems/netrun-config/releases/tag/v1.0.0
