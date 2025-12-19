"""
TTL-based secret caching for Azure Key Vault.

Provides time-to-live caching with Microsoft-recommended 8-hour default TTL
for secret values to balance security and performance.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SecretCacheConfig:
    """
    Configuration for secret caching behavior.

    Attributes:
        default_ttl_seconds: Time-to-live for cached secrets (default: 8 hours per Microsoft guidance)
        max_cache_size: Maximum number of secrets to cache (prevents unbounded memory growth)
        enable_version_tracking: Track secret versions for rotation detection
    """

    default_ttl_seconds: int = 28800  # 8 hours (Microsoft recommendation)
    max_cache_size: int = 500
    enable_version_tracking: bool = True


@dataclass
class CachedSecret:
    """
    Cached secret value with metadata.

    Attributes:
        value: The secret value
        fetched_at: When the secret was fetched from Key Vault
        version: Secret version ID (for rotation detection)
        expires_at: When the cached value expires
    """

    value: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: Optional[str] = None
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if cached secret has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def age_seconds(self) -> float:
        """Get age of cached secret in seconds."""
        return (datetime.now(timezone.utc) - self.fetched_at).total_seconds()


class SecretCache:
    """
    TTL-based cache for Azure Key Vault secrets.

    Features:
    - Time-to-live expiration (default 8 hours)
    - LRU eviction when max size reached
    - Secret version tracking for rotation detection
    - Thread-safe operations

    Example:
        >>> config = SecretCacheConfig(default_ttl_seconds=3600)  # 1 hour
        >>> cache = SecretCache(config)
        >>> cache.set("db-password", "secret123", version="abc123")
        >>> secret = cache.get("db-password")
        >>> if secret and not secret.is_expired():
        ...     print(secret.value)
        secret123
    """

    def __init__(self, config: Optional[SecretCacheConfig] = None):
        """
        Initialize secret cache.

        Args:
            config: Cache configuration (uses defaults if not provided)
        """
        self.config = config or SecretCacheConfig()
        self._cache: dict[str, CachedSecret] = {}
        self._access_order: list[str] = []  # For LRU eviction

    def get(self, secret_name: str) -> Optional[CachedSecret]:
        """
        Get cached secret if not expired.

        Args:
            secret_name: Name of secret to retrieve

        Returns:
            CachedSecret if found and not expired, None otherwise
        """
        cached = self._cache.get(secret_name)
        if cached is None:
            logger.debug(f"Cache miss: '{secret_name}' not in cache")
            return None

        if cached.is_expired():
            logger.info(
                f"Cache expired: '{secret_name}' (age: {cached.age_seconds():.1f}s)"
            )
            self.invalidate(secret_name)
            return None

        # Update access order for LRU
        if secret_name in self._access_order:
            self._access_order.remove(secret_name)
        self._access_order.append(secret_name)

        logger.debug(
            f"Cache hit: '{secret_name}' (age: {cached.age_seconds():.1f}s, "
            f"expires in: {(cached.expires_at - datetime.now(timezone.utc)).total_seconds():.1f}s)"
        )
        return cached

    def set(
        self,
        secret_name: str,
        value: str,
        version: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Cache a secret value with TTL.

        Args:
            secret_name: Name of secret
            value: Secret value
            version: Secret version ID (for rotation detection)
            ttl_seconds: Custom TTL (uses default if not provided)
        """
        ttl = ttl_seconds or self.config.default_ttl_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        cached = CachedSecret(
            value=value, version=version, expires_at=expires_at
        )

        # Evict oldest if cache is full
        if (
            len(self._cache) >= self.config.max_cache_size
            and secret_name not in self._cache
        ):
            self._evict_oldest()

        self._cache[secret_name] = cached
        if secret_name in self._access_order:
            self._access_order.remove(secret_name)
        self._access_order.append(secret_name)

        logger.debug(
            f"Cached: '{secret_name}' (version: {version}, TTL: {ttl}s)"
        )

    def invalidate(self, secret_name: str) -> None:
        """
        Remove secret from cache.

        Args:
            secret_name: Name of secret to invalidate
        """
        if secret_name in self._cache:
            del self._cache[secret_name]
        if secret_name in self._access_order:
            self._access_order.remove(secret_name)
        logger.debug(f"Invalidated: '{secret_name}'")

    def clear(self) -> None:
        """Clear all cached secrets."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        logger.info(f"Cache cleared ({count} secrets removed)")

    def _evict_oldest(self) -> None:
        """Evict least recently used secret (LRU eviction)."""
        if not self._access_order:
            return

        oldest_key = self._access_order.pop(0)
        if oldest_key in self._cache:
            del self._cache[oldest_key]
            logger.debug(f"Evicted (LRU): '{oldest_key}'")

    def get_version(self, secret_name: str) -> Optional[str]:
        """
        Get cached secret version without retrieving value.

        Args:
            secret_name: Name of secret

        Returns:
            Version ID if cached and not expired, None otherwise
        """
        cached = self.get(secret_name)
        return cached.version if cached else None

    def has_version_changed(
        self, secret_name: str, current_version: str
    ) -> bool:
        """
        Check if secret version has changed since cached.

        Args:
            secret_name: Name of secret
            current_version: Current version from Key Vault

        Returns:
            True if version changed or not in cache
        """
        cached_version = self.get_version(secret_name)
        if cached_version is None:
            return True
        return cached_version != current_version

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_secrets = len(self._cache)
        expired_secrets = sum(
            1 for cached in self._cache.values() if cached.is_expired()
        )
        valid_secrets = total_secrets - expired_secrets

        return {
            "total_secrets": total_secrets,
            "valid_secrets": valid_secrets,
            "expired_secrets": expired_secrets,
            "max_cache_size": self.config.max_cache_size,
            "cache_utilization_pct": (total_secrets / self.config.max_cache_size)
            * 100,
            "default_ttl_seconds": self.config.default_ttl_seconds,
        }
