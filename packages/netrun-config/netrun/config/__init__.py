"""
Netrun Systems Unified Configuration Library
=============================================

A standardized configuration management library for all Netrun Systems projects.

Features:
- Pydantic v2 BaseSettings with validation
- Azure Key Vault integration with TTL caching
- Multi-vault support for different secret sources
- Secret rotation detection
- Environment-specific configuration
- Caching and performance optimization
- Security best practices (32-char secrets, CORS parsing, etc.)
- Optional netrun-errors integration for standardized error handling
- Optional netrun-logging integration for structured logging

Example:
    >>> from netrun.config import BaseConfig, Field, get_settings
    >>>
    >>> class MyAppSettings(BaseConfig):
    ...     app_name: str = Field(default="MyApp")
    ...     custom_setting: str = Field(..., env="CUSTOM_SETTING")
    >>>
    >>> settings = get_settings(MyAppSettings)
    >>> print(settings.app_name)
    MyApp
    >>> print(settings.is_production)
    False

Author: Netrun Systems
Version: 2.0.0
License: MIT
"""

__version__ = "2.0.0"

from .base import BaseConfig, get_settings, reload_settings
from .cache import CachedSecret, SecretCache, SecretCacheConfig
from .exceptions import (
    ConfigError,
    KeyVaultError,
    ValidationError,
    raise_keyvault_unavailable,
    raise_validation_error,
)
from .keyvault import KeyVaultMixin
from .multi_vault import MultiVaultClient, VaultConfig
from .settings_source import (
    AzureKeyVaultRefreshableSettingsSource,
    AzureKeyVaultSettingsSource,
)

# Re-export Pydantic Field for convenience
from pydantic import Field

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
