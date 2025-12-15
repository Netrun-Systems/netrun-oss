"""
Azure Key Vault integration for netrun-config.

Provides a mixin class for seamless Azure Key Vault integration with
automatic fallback to environment variables for local development.

LEGACY COMPATIBILITY: This module maintains backward compatibility with v1.0.0.
For new implementations, use MultiVaultClient and AzureKeyVaultSettingsSource.
"""

import logging
import os
from typing import Dict, Optional

from .cache import SecretCache, SecretCacheConfig

logger = logging.getLogger(__name__)

# Optional Azure dependencies
try:
    from azure.core.exceptions import ResourceNotFoundError
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.debug("Azure SDK not available. Key Vault integration disabled.")


class KeyVaultMixin:
    """
    Mixin class for Azure Key Vault integration.

    Add this mixin to your config class to automatically load secrets
    from Azure Key Vault in production.

    Features:
    - Managed Identity authentication (no credentials)
    - Automatic fallback to environment variables
    - In-memory caching (instance-level dictionary)
    - Development-friendly (optional Key Vault)
    - Lazy initialization (initialized on first secret request)

    Example:
        >>> from netrun_config import BaseConfig, KeyVaultMixin
        >>> from pydantic import Field
        >>>
        >>> class MySettings(BaseConfig, KeyVaultMixin):
        ...     key_vault_url: Optional[str] = Field(default=None)
        ...     database_url: Optional[str] = Field(default=None)
        ...
        ...     @property
        ...     def database_url_resolved(self) -> str:
        ...         if self.is_production and self.key_vault_url:
        ...             return self.get_keyvault_secret("database-url") or self.database_url
        ...         return self.database_url
        >>>
        >>> settings = MySettings()
        >>> db_url = settings.database_url_resolved
    """

    def _ensure_kv_initialized(self) -> None:
        """
        Lazy initialization of Key Vault client with TTL caching.

        This ensures the Key Vault client is initialized only when needed,
        working around Pydantic v2's initialization lifecycle.

        v1.1.0: Now uses SecretCache with TTL support instead of simple dict.
        """
        # Check if already initialized
        try:
            object.__getattribute__(self, "__kv_initialized")
            return  # Already initialized
        except AttributeError:
            pass  # Not initialized yet

        # Initialize private attributes (using __ prefix to avoid conflicts with properties)
        object.__setattr__(self, "__kv_client", None)
        object.__setattr__(self, "__kv_enabled", False)

        # v1.1.0: Use SecretCache instead of dict for TTL support
        cache_config = SecretCacheConfig(
            default_ttl_seconds=getattr(self, "keyvault_cache_ttl_seconds", 28800),  # 8 hours default
            max_cache_size=getattr(self, "keyvault_max_cache_size", 500),
        )
        object.__setattr__(self, "__secret_cache", SecretCache(cache_config))
        object.__setattr__(self, "__kv_initialized", True)

        # Get key_vault_url attribute if it exists
        vault_url = getattr(self, "key_vault_url", None) or getattr(
            self, "KEY_VAULT_URL", None
        )

        # Only initialize if Azure SDK is available and Key Vault URL is set
        if AZURE_AVAILABLE and vault_url:
            try:
                credential = self._get_azure_credential()
                client = SecretClient(vault_url=vault_url, credential=credential)
                object.__setattr__(self, "__kv_client", client)
                object.__setattr__(self, "__kv_enabled", True)
                logger.info(f"🔐 Key Vault enabled: {vault_url}")
            except Exception as e:
                logger.warning(
                    f"⚠️ Key Vault initialization failed: {e}. Fallback to env vars."
                )

    @property
    def _kv_enabled(self) -> bool:
        """Check if Key Vault is enabled (lazy property)."""
        self._ensure_kv_initialized()
        return object.__getattribute__(self, "__kv_enabled")

    def _get_azure_credential(self):
        """Get Azure credential (Managed Identity in prod, CLI in dev)."""
        if hasattr(self, "is_production") and self.is_production:
            return ManagedIdentityCredential()
        else:
            return DefaultAzureCredential()

    def get_keyvault_secret(self, secret_name: str) -> Optional[str]:
        """
        Get secret from Azure Key Vault with TTL caching.

        Args:
            secret_name: Name of secret in Key Vault (e.g., "database-url")

        Returns:
            Secret value or None if not found

        Fallback:
            If Key Vault disabled or secret not found, falls back to
            environment variable (e.g., DATABASE_URL)

        v1.1.0: Now uses TTL-based caching with automatic expiration.
        """
        # Ensure Key Vault is initialized
        self._ensure_kv_initialized()

        # Access private attributes using object.__getattribute__ to bypass Pydantic
        secret_cache: SecretCache = object.__getattribute__(self, "__secret_cache")
        kv_enabled = object.__getattribute__(self, "__kv_enabled")

        # Check cache first (cache handles expiration automatically)
        cached = secret_cache.get(secret_name)
        if cached and not cached.is_expired():
            return cached.value

        # Fallback to environment variable if Key Vault disabled
        if not kv_enabled:
            env_var = secret_name.upper().replace("-", "_")
            value = os.getenv(env_var)
            if value:
                # Cache environment variable value with TTL
                secret_cache.set(secret_name, value)
            return value

        # Fetch from Key Vault
        kv_client = object.__getattribute__(self, "__kv_client")
        try:
            secret = kv_client.get_secret(secret_name)
            logger.debug(
                f"✅ Key Vault: Loaded '{secret_name}' (version: {secret.properties.version})"
            )
            # Cache with version tracking for rotation detection
            secret_cache.set(
                secret_name,
                secret.value,
                version=secret.properties.version,
            )
            return secret.value
        except ResourceNotFoundError:
            logger.warning(
                f"⚠️ Key Vault: Secret '{secret_name}' not found. Fallback to env."
            )
            env_var = secret_name.upper().replace("-", "_")
            value = os.getenv(env_var)
            if value:
                secret_cache.set(secret_name, value)
            return value
        except Exception as e:
            logger.error(f"❌ Key Vault error for '{secret_name}': {e}")
            return None

    def clear_keyvault_cache(self):
        """
        Clear Key Vault secret cache (useful for testing).

        v1.1.0: Now uses SecretCache.clear() method.
        """
        self._ensure_kv_initialized()
        secret_cache: SecretCache = object.__getattribute__(self, "__secret_cache")
        secret_cache.clear()

    def get_keyvault_cache_stats(self) -> dict:
        """
        Get Key Vault cache statistics.

        Returns:
            Dictionary with cache metrics

        v1.1.0: New method for cache observability.
        """
        self._ensure_kv_initialized()
        secret_cache: SecretCache = object.__getattribute__(self, "__secret_cache")
        return secret_cache.get_stats()
