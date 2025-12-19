"""
Backwards compatibility shim for netrun-config v2.0.0+

DEPRECATED: This import path (netrun_config) is deprecated as of v2.0.0.
Please update your imports to use the namespace package:

    OLD: from netrun_config import BaseConfig, get_settings
    NEW: from netrun.config import BaseConfig, get_settings

This compatibility shim will be removed in v3.0.0 (planned Q2 2026).

For migration instructions, see:
https://github.com/netrunsystems/netrun-config/blob/main/MIGRATION.md
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from 'netrun_config' is deprecated. "
    "Please update to 'from netrun.config import ...' instead. "
    "This compatibility layer will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all public symbols from netrun.config
from netrun.config import (
    # Core Configuration
    BaseConfig,
    Field,
    get_settings,
    reload_settings,
    # Legacy Key Vault (v1.0.0 compatibility)
    KeyVaultMixin,
    # TTL Caching (v1.1.0)
    SecretCache,
    SecretCacheConfig,
    CachedSecret,
    # Multi-Vault Support (v1.1.0)
    MultiVaultClient,
    VaultConfig,
    # Pydantic Settings Source Integration (v1.1.0)
    AzureKeyVaultSettingsSource,
    AzureKeyVaultRefreshableSettingsSource,
    # Exceptions
    ConfigError,
    KeyVaultError,
    ValidationError,
    # Error Factories (v1.2.0)
    raise_validation_error,
    raise_keyvault_unavailable,
    # Metadata
    __version__,
)

__all__ = [
    # Core Configuration
    "BaseConfig",
    "Field",
    "get_settings",
    "reload_settings",
    # Legacy Key Vault (v1.0.0 compatibility)
    "KeyVaultMixin",
    # TTL Caching (v1.1.0)
    "SecretCache",
    "SecretCacheConfig",
    "CachedSecret",
    # Multi-Vault Support (v1.1.0)
    "MultiVaultClient",
    "VaultConfig",
    # Pydantic Settings Source Integration (v1.1.0)
    "AzureKeyVaultSettingsSource",
    "AzureKeyVaultRefreshableSettingsSource",
    # Exceptions
    "ConfigError",
    "KeyVaultError",
    "ValidationError",
    # Error Factories (v1.2.0)
    "raise_validation_error",
    "raise_keyvault_unavailable",
    # Metadata
    "__version__",
]
