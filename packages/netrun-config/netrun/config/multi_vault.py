"""
Multi-vault support for Azure Key Vault.

Allows configuration of multiple Key Vault instances for different purposes
(e.g., 'default', 'dev', 'certificates', 'shared-secrets').
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .cache import CachedSecret, SecretCache, SecretCacheConfig

logger = logging.getLogger(__name__)

# Optional Azure dependencies
try:
    from azure.core.credentials import TokenCredential
    from azure.core.exceptions import ResourceNotFoundError
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.debug("Azure SDK not available. Multi-vault integration disabled.")


@dataclass
class VaultConfig:
    """
    Configuration for a single Key Vault instance.

    Attributes:
        url: Key Vault URL (e.g., "https://my-vault.vault.azure.net/")
        credential: Azure credential (optional, uses DefaultAzureCredential if None)
        cache_config: Cache configuration for this vault (optional)
        enabled: Whether this vault is enabled
    """

    url: str
    credential: Optional["TokenCredential"] = None
    cache_config: Optional[SecretCacheConfig] = None
    enabled: bool = True


class MultiVaultClient:
    """
    Multi-vault Azure Key Vault client with caching.

    Manages multiple Key Vault instances for different purposes with
    separate caching and credential configurations.

    Features:
    - Multiple vault support ('default', 'dev', 'certificates', etc.)
    - Per-vault TTL caching
    - Automatic credential management
    - Secret rotation detection
    - Graceful degradation (disabled vaults don't block operations)

    Example:
        >>> vaults = {
        ...     'default': VaultConfig(url="https://prod-vault.vault.azure.net/"),
        ...     'dev': VaultConfig(url="https://dev-vault.vault.azure.net/"),
        ...     'certificates': VaultConfig(url="https://cert-vault.vault.azure.net/")
        ... }
        >>> client = MultiVaultClient(vaults, is_production=True)
        >>> db_password = client.get_secret("database-password")
        >>> cert = client.get_secret("ssl-certificate", vault='certificates')
    """

    def __init__(
        self,
        vaults: dict[str, VaultConfig],
        is_production: bool = False,
        default_cache_config: Optional[SecretCacheConfig] = None,
    ):
        """
        Initialize multi-vault client.

        Args:
            vaults: Dictionary mapping vault names to VaultConfig
            is_production: Whether running in production (affects credential selection)
            default_cache_config: Default cache config for vaults without specific config
        """
        if not AZURE_AVAILABLE:
            logger.warning("Azure SDK not available. Multi-vault disabled.")
            self._enabled = False
            return

        self.vaults = vaults
        self.is_production = is_production
        self.default_cache_config = default_cache_config or SecretCacheConfig()

        # Initialize clients and caches
        self._clients: dict[str, SecretClient] = {}
        self._caches: dict[str, SecretCache] = {}
        self._enabled = True

        self._initialize_vaults()

    def _initialize_vaults(self) -> None:
        """Initialize Key Vault clients and caches for all configured vaults."""
        for vault_name, config in self.vaults.items():
            if not config.enabled:
                logger.info(f"🔐 Vault '{vault_name}' disabled (skipping)")
                continue

            try:
                # Use vault-specific or default credential
                credential = config.credential or self._get_azure_credential()

                # Create client
                client = SecretClient(vault_url=config.url, credential=credential)
                self._clients[vault_name] = client

                # Create cache
                cache_config = config.cache_config or self.default_cache_config
                self._caches[vault_name] = SecretCache(cache_config)

                logger.info(
                    f"🔐 Vault '{vault_name}' initialized: {config.url} "
                    f"(TTL: {cache_config.default_ttl_seconds}s)"
                )

            except Exception as e:
                logger.error(
                    f"❌ Vault '{vault_name}' initialization failed: {e}. "
                    f"Vault disabled."
                )
                config.enabled = False

    def _get_azure_credential(self) -> "TokenCredential":
        """Get Azure credential (Managed Identity in prod, DefaultAzureCredential in dev)."""
        if self.is_production:
            return ManagedIdentityCredential()
        return DefaultAzureCredential()

    def get_secret(
        self, secret_name: str, vault: str = "default"
    ) -> Optional[str]:
        """
        Get secret from specified vault with caching.

        Args:
            secret_name: Name of secret in Key Vault
            vault: Vault name (default: 'default')

        Returns:
            Secret value or None if not found or vault disabled

        Example:
            >>> client.get_secret("database-url")  # Uses 'default' vault
            'postgresql://...'
            >>> client.get_secret("ssl-cert", vault='certificates')
            '-----BEGIN CERTIFICATE-----...'
        """
        # Validate vault exists and is enabled
        if vault not in self.vaults:
            logger.error(f"❌ Vault '{vault}' not configured")
            return None

        if not self.vaults[vault].enabled:
            logger.debug(f"⚠️ Vault '{vault}' disabled")
            return None

        client = self._clients.get(vault)
        cache = self._caches.get(vault)

        if client is None or cache is None:
            logger.error(f"❌ Vault '{vault}' not initialized")
            return None

        # Check cache first
        cached = cache.get(secret_name)
        if cached and not cached.is_expired():
            return cached.value

        # Fetch from Key Vault
        try:
            secret = client.get_secret(secret_name)
            logger.debug(
                f"✅ Key Vault '{vault}': Loaded '{secret_name}' "
                f"(version: {secret.properties.version})"
            )

            # Cache with version tracking
            cache.set(
                secret_name,
                secret.value,
                version=secret.properties.version,
            )

            return secret.value

        except ResourceNotFoundError:
            logger.warning(
                f"⚠️ Key Vault '{vault}': Secret '{secret_name}' not found"
            )
            return None

        except Exception as e:
            logger.error(
                f"❌ Key Vault '{vault}' error for '{secret_name}': {e}"
            )
            return None

    async def get_secret_async(
        self, secret_name: str, vault: str = "default"
    ) -> Optional[str]:
        """
        Get secret asynchronously (future enhancement).

        Args:
            secret_name: Name of secret
            vault: Vault name

        Returns:
            Secret value or None
        """
        # TODO: Implement async version with aiohttp-based Azure SDK
        logger.warning("Async not yet implemented, falling back to sync")
        return self.get_secret(secret_name, vault)

    def check_secret_version(
        self, secret_name: str, vault: str = "default"
    ) -> Optional[str]:
        """
        Get current secret version without fetching value.

        Args:
            secret_name: Name of secret
            vault: Vault name

        Returns:
            Current version ID or None if not found
        """
        client = self._clients.get(vault)
        if client is None:
            return None

        try:
            # Get secret properties only (no value)
            properties = client.get_secret(secret_name).properties
            return properties.version

        except ResourceNotFoundError:
            logger.debug(
                f"Secret '{secret_name}' not found in vault '{vault}'"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error checking version for '{secret_name}' in vault '{vault}': {e}"
            )
            return None

    def has_secret_rotated(
        self, secret_name: str, vault: str = "default"
    ) -> bool:
        """
        Check if secret has been rotated since last fetch.

        Args:
            secret_name: Name of secret
            vault: Vault name

        Returns:
            True if secret version changed or not in cache
        """
        cache = self._caches.get(vault)
        if cache is None:
            return True

        current_version = self.check_secret_version(secret_name, vault)
        if current_version is None:
            return True

        return cache.has_version_changed(secret_name, current_version)

    def refresh_if_rotated(
        self, secret_name: str, vault: str = "default"
    ) -> Optional[str]:
        """
        Refresh secret only if version changed.

        Args:
            secret_name: Name of secret
            vault: Vault name

        Returns:
            Secret value (refreshed if rotated) or None
        """
        cache = self._caches.get(vault)
        if cache is None:
            return self.get_secret(secret_name, vault)

        if self.has_secret_rotated(secret_name, vault):
            logger.info(
                f"🔄 Secret '{secret_name}' rotated in vault '{vault}', refreshing cache"
            )
            cache.invalidate(secret_name)
            return self.get_secret(secret_name, vault)

        # Return cached value
        cached = cache.get(secret_name)
        return cached.value if cached else None

    def invalidate_cache(
        self, secret_name: Optional[str] = None, vault: Optional[str] = None
    ) -> None:
        """
        Invalidate cache for specific secret or entire vault.

        Args:
            secret_name: Name of secret to invalidate (optional)
            vault: Vault name (optional, defaults to all vaults)
        """
        if vault is not None:
            # Invalidate specific vault
            cache = self._caches.get(vault)
            if cache:
                if secret_name:
                    cache.invalidate(secret_name)
                else:
                    cache.clear()
        else:
            # Invalidate all vaults
            for cache in self._caches.values():
                if secret_name:
                    cache.invalidate(secret_name)
                else:
                    cache.clear()

    def get_cache_stats(self, vault: Optional[str] = None) -> dict:
        """
        Get cache statistics.

        Args:
            vault: Vault name (optional, returns stats for all vaults if None)

        Returns:
            Dictionary with cache statistics
        """
        if vault is not None:
            cache = self._caches.get(vault)
            if cache:
                return {vault: cache.get_stats()}
            return {}

        # Return stats for all vaults
        return {
            vault_name: cache.get_stats()
            for vault_name, cache in self._caches.items()
        }

    def list_vaults(self) -> list[str]:
        """
        Get list of configured vault names.

        Returns:
            List of vault names
        """
        return list(self.vaults.keys())

    def is_vault_enabled(self, vault: str) -> bool:
        """
        Check if vault is enabled.

        Args:
            vault: Vault name

        Returns:
            True if vault exists and is enabled
        """
        config = self.vaults.get(vault)
        return config.enabled if config else False
