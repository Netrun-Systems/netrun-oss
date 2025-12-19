"""
Tests for TTL-based secret caching.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from netrun.config.cache import CachedSecret, SecretCache, SecretCacheConfig


class TestCachedSecret:
    """Test CachedSecret dataclass."""

    def test_cached_secret_creation(self):
        """Test creating a CachedSecret."""
        secret = CachedSecret(value="test-value", version="v1")
        assert secret.value == "test-value"
        assert secret.version == "v1"
        assert isinstance(secret.fetched_at, datetime)
        assert secret.expires_at is None

    def test_cached_secret_expiration(self):
        """Test secret expiration logic."""
        # Not expired (no expiration set)
        secret = CachedSecret(value="test")
        assert not secret.is_expired()

        # Not expired (future expiration)
        secret = CachedSecret(
            value="test",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert not secret.is_expired()

        # Expired (past expiration)
        secret = CachedSecret(
            value="test",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert secret.is_expired()

    def test_cached_secret_age(self):
        """Test age calculation."""
        secret = CachedSecret(value="test")
        time.sleep(0.1)
        age = secret.age_seconds()
        assert age >= 0.1


class TestSecretCacheConfig:
    """Test SecretCacheConfig dataclass."""

    def test_default_config(self):
        """Test default cache configuration."""
        config = SecretCacheConfig()
        assert config.default_ttl_seconds == 28800  # 8 hours
        assert config.max_cache_size == 500
        assert config.enable_version_tracking is True

    def test_custom_config(self):
        """Test custom cache configuration."""
        config = SecretCacheConfig(
            default_ttl_seconds=3600, max_cache_size=100, enable_version_tracking=False
        )
        assert config.default_ttl_seconds == 3600
        assert config.max_cache_size == 100
        assert config.enable_version_tracking is False


class TestSecretCache:
    """Test SecretCache functionality."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = SecretCache()
        assert cache.config.default_ttl_seconds == 28800
        assert len(cache._cache) == 0

    def test_cache_set_and_get(self):
        """Test setting and getting cached secrets."""
        cache = SecretCache()
        cache.set("test-secret", "test-value", version="v1")

        cached = cache.get("test-secret")
        assert cached is not None
        assert cached.value == "test-value"
        assert cached.version == "v1"
        assert not cached.is_expired()

    def test_cache_miss(self):
        """Test cache miss behavior."""
        cache = SecretCache()
        cached = cache.get("nonexistent")
        assert cached is None

    def test_cache_expiration(self):
        """Test TTL expiration."""
        config = SecretCacheConfig(default_ttl_seconds=1)  # 1 second TTL
        cache = SecretCache(config)

        cache.set("test-secret", "test-value")
        cached = cache.get("test-secret")
        assert cached is not None

        # Wait for expiration
        time.sleep(1.1)
        cached = cache.get("test-secret")
        assert cached is None  # Should be expired and invalidated

    def test_cache_custom_ttl(self):
        """Test custom TTL per secret."""
        cache = SecretCache()
        cache.set("short-lived", "value", ttl_seconds=1)
        cache.set("long-lived", "value", ttl_seconds=10)

        # Short-lived should expire
        time.sleep(1.1)
        assert cache.get("short-lived") is None
        assert cache.get("long-lived") is not None

    def test_cache_invalidate(self):
        """Test manual cache invalidation."""
        cache = SecretCache()
        cache.set("test-secret", "test-value")
        assert cache.get("test-secret") is not None

        cache.invalidate("test-secret")
        assert cache.get("test-secret") is None

    def test_cache_clear(self):
        """Test clearing entire cache."""
        cache = SecretCache()
        cache.set("secret1", "value1")
        cache.set("secret2", "value2")
        cache.set("secret3", "value3")

        assert len(cache._cache) == 3
        cache.clear()
        assert len(cache._cache) == 0

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        config = SecretCacheConfig(max_cache_size=3)
        cache = SecretCache(config)

        # Fill cache
        cache.set("secret1", "value1")
        cache.set("secret2", "value2")
        cache.set("secret3", "value3")

        # Add one more (should evict oldest)
        cache.set("secret4", "value4")

        assert cache.get("secret1") is None  # Evicted
        assert cache.get("secret2") is not None
        assert cache.get("secret3") is not None
        assert cache.get("secret4") is not None

    def test_cache_lru_access_order(self):
        """Test LRU access order updates."""
        config = SecretCacheConfig(max_cache_size=3)
        cache = SecretCache(config)

        cache.set("secret1", "value1")
        cache.set("secret2", "value2")
        cache.set("secret3", "value3")

        # Access secret1 (should move to end of LRU)
        cache.get("secret1")

        # Add secret4 (should evict secret2, not secret1)
        cache.set("secret4", "value4")

        assert cache.get("secret1") is not None  # Accessed recently
        assert cache.get("secret2") is None  # Evicted
        assert cache.get("secret3") is not None
        assert cache.get("secret4") is not None

    def test_get_version(self):
        """Test getting cached secret version."""
        cache = SecretCache()
        cache.set("test-secret", "value", version="v123")

        version = cache.get_version("test-secret")
        assert version == "v123"

    def test_has_version_changed(self):
        """Test version change detection."""
        cache = SecretCache()
        cache.set("test-secret", "value", version="v1")

        # Same version
        assert not cache.has_version_changed("test-secret", "v1")

        # Different version
        assert cache.has_version_changed("test-secret", "v2")

        # Not in cache
        assert cache.has_version_changed("nonexistent", "v1")

    def test_cache_stats(self):
        """Test cache statistics."""
        config = SecretCacheConfig(default_ttl_seconds=10, max_cache_size=100)
        cache = SecretCache(config)

        cache.set("secret1", "value1")
        cache.set("secret2", "value2")

        stats = cache.get_stats()
        assert stats["total_secrets"] == 2
        assert stats["valid_secrets"] == 2
        assert stats["expired_secrets"] == 0
        assert stats["max_cache_size"] == 100
        assert stats["default_ttl_seconds"] == 10

    def test_cache_stats_with_expired(self):
        """Test cache statistics with expired secrets."""
        config = SecretCacheConfig(default_ttl_seconds=1)
        cache = SecretCache(config)

        cache.set("secret1", "value1")
        cache.set("secret2", "value2")

        # Wait for expiration
        time.sleep(1.1)

        stats = cache.get_stats()
        assert stats["total_secrets"] == 2
        assert stats["expired_secrets"] == 2
        assert stats["valid_secrets"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
