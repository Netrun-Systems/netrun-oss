"""Tests for edge cases and uncovered code paths."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netrun.cache import CacheConfig, CacheManager, MemoryCache


@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests to improve coverage."""

    async def test_memory_cache_increment_non_integer(self) -> None:
        """Test increment on non-integer value."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()

        # Set non-integer value
        await cache.set("key1", "string_value")

        # Try to increment - should return None
        result = await cache.increment("key1")
        assert result is None

        await cache.close()

    async def test_memory_cache_double_initialization(self) -> None:
        """Test that double initialization is a no-op."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()
        assert cache._initialized is True

        # Initialize again - should be no-op
        await cache.initialize()
        assert cache._initialized is True

        await cache.close()

    async def test_memory_cache_expire_nonexistent_key(self) -> None:
        """Test expire on nonexistent key."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()

        # Expire nonexistent key
        result = await cache.expire("nonexistent", 100)
        assert result is False

        await cache.close()

    async def test_memory_cache_close_clears_data(self) -> None:
        """Test that close clears all cached data."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Close cache
        await cache.close()

        assert cache._initialized is False
        assert len(cache._cache) == 0

    async def test_memory_cache_get_stats_with_expired_keys(self) -> None:
        """Test get_stats correctly counts non-expired keys."""
        cache = MemoryCache(namespace="test", default_ttl=1)
        await cache.initialize()

        # Set keys with short TTL
        await cache.set("key1", "value1", ttl=1)
        await cache.set("key2", "value2", ttl=10)

        # Wait for key1 to expire
        await asyncio.sleep(1.1)

        stats = await cache.get_stats()
        # Only key2 should be counted (key1 expired)
        assert stats.cached_keys == 1

        await cache.close()

    async def test_cache_manager_lazy_init_on_expire(self) -> None:
        """Test lazy initialization on expire operation."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)

        # expire should trigger initialization
        await manager.set("key1", "value1")
        result = await manager.expire("key1", 100)

        assert manager._initialized is True
        assert result is True

        await manager.close()

    async def test_cache_manager_get_with_no_redis(self) -> None:
        """Test cache manager get operation when Redis is unavailable."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        # Set value in L1
        await manager.set("key1", "value1")

        # Get value (should come from L1)
        value = await manager.get("key1")
        assert value == "value1"

        await manager.close()

    async def test_cache_manager_exists_with_redis_unavailable(self) -> None:
        """Test exists operation when Redis is unavailable."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        # Set in L1 only
        await manager.l1_cache.set("key1", "value1")

        # exists should find it in L1
        result = await manager.exists("key1")
        assert result is True

        # Non-existent key
        result = await manager.exists("nonexistent")
        assert result is False

        await manager.close()

    async def test_cache_manager_get_many_empty_list(self) -> None:
        """Test get_many with empty key list."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        result = await manager.get_many([])
        assert result == {}

        await manager.close()

    async def test_cache_manager_set_many_empty_dict(self) -> None:
        """Test set_many with empty dictionary."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        count = await manager.set_many({})
        assert count == 0

        await manager.close()

    async def test_cache_manager_close_with_no_l2(self) -> None:
        """Test close operation when L2 cache is None."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        # Don't initialize - this ensures L2 is None

        # Set initialized flag manually to test close
        manager._initialized = True

        # Close should not raise error
        await manager.close()
        assert manager._initialized is False

    async def test_memory_cache_set_with_expired_entry_cleanup(self) -> None:
        """Test that set operation cleans up expired entries."""
        cache = MemoryCache(namespace="test", default_ttl=1, max_size=10)
        await cache.initialize()

        # Set keys with short TTL
        await cache.set("key1", "value1", ttl=1)
        await cache.set("key2", "value2", ttl=1)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Set new key - should trigger cleanup of expired entries
        await cache.set("key3", "value3", ttl=10)

        # Expired keys should be cleaned up
        stats = await cache.get_stats()
        assert stats.cached_keys == 1  # Only key3

        await cache.close()

    async def test_memory_cache_lru_eviction_with_existing_key_update(self) -> None:
        """Test LRU eviction when updating existing key doesn't trigger eviction."""
        cache = MemoryCache(namespace="test", max_size=3)
        await cache.initialize()

        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Update existing key - should not trigger eviction
        await cache.set("key2", "updated_value2")

        # All keys should still exist
        assert await cache.exists("key1") is True
        assert await cache.exists("key2") is True
        assert await cache.exists("key3") is True
        assert await cache.get("key2") == "updated_value2"

        await cache.close()

    async def test_memory_cache_get_with_track_stats_disabled(self) -> None:
        """Test get operation with track_stats=False."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()

        await cache.reset_stats()
        await cache.set("key1", "value1")

        # Get with stats tracking disabled
        value = await cache.get("key1", track_stats=False)
        assert value == "value1"

        # Stats should not be updated
        stats = await cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

        # Get nonexistent key with stats disabled
        value = await cache.get("nonexistent", track_stats=False)
        assert value is None

        stats = await cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

        await cache.close()

    async def test_cache_manager_get_with_track_stats(self) -> None:
        """Test cache manager get with track_stats parameter."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        await manager.set("key1", "value1")

        # Get with stats tracking
        value = await manager.get("key1", track_stats=True)
        assert value == "value1"

        # Get with stats disabled
        value = await manager.get("key1", track_stats=False)
        assert value == "value1"

        await manager.close()

    async def test_cache_manager_custom_ttl_on_set(self) -> None:
        """Test cache manager set with custom TTL."""
        config = CacheConfig(namespace="test", default_ttl=3600, l1_ttl=100)
        manager = CacheManager(config)
        await manager.initialize()

        # Set with custom TTL shorter than l1_ttl
        await manager.set("key1", "value1", ttl=50)

        # Value should be set
        value = await manager.get("key1")
        assert value == "value1"

        await manager.close()

    async def test_cache_manager_custom_ttl_on_set_many(self) -> None:
        """Test cache manager set_many with custom TTL."""
        config = CacheConfig(namespace="test", default_ttl=3600, l1_ttl=100)
        manager = CacheManager(config)
        await manager.initialize()

        items = {"key1": "value1", "key2": "value2"}

        # Set with custom TTL shorter than l1_ttl
        count = await manager.set_many(items, ttl=50)
        assert count == 2

        # Values should be set
        result = await manager.get_many(["key1", "key2"])
        assert result == items

        await manager.close()

    async def test_cache_manager_expire_with_custom_ttl(self) -> None:
        """Test cache manager expire with TTL longer than l1_ttl."""
        config = CacheConfig(namespace="test", default_ttl=3600, l1_ttl=100)
        manager = CacheManager(config)
        await manager.initialize()

        await manager.set("key1", "value1")

        # Expire with TTL longer than l1_ttl - L1 should use min(ttl, l1_ttl)
        result = await manager.expire("key1", 200)
        assert result is True

        await manager.close()

    async def test_memory_cache_get_many_track_stats(self) -> None:
        """Test that get_many properly tracks stats."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()
        await cache.reset_stats()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Get many should track hits and misses
        result = await cache.get_many(["key1", "key2", "nonexistent"])

        assert result == {"key1": "value1", "key2": "value2"}

        stats = await cache.get_stats()
        assert stats.hits == 2  # key1 and key2
        assert stats.misses == 1  # nonexistent

        await cache.close()

    async def test_cache_manager_set_with_nx_flag(self) -> None:
        """Test cache manager set with nx flag."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        # First set with nx should succeed
        result = await manager.set("key1", "value1", nx=True)
        assert result is True

        # Second set with nx should fail
        result = await manager.set("key1", "value2", nx=True)
        assert result is False

        # Value should remain unchanged
        value = await manager.get("key1")
        assert value == "value1"

        await manager.close()

    async def test_cache_manager_get_many_no_l1_misses(self) -> None:
        """Test get_many when all keys are in L1."""
        config = CacheConfig(namespace="test", default_ttl=3600)
        manager = CacheManager(config)
        await manager.initialize()

        # Set values directly in L1
        await manager.l1_cache.set("key1", "value1")
        await manager.l1_cache.set("key2", "value2")

        # Get many should find all in L1
        result = await manager.get_many(["key1", "key2"])
        assert result == {"key1": "value1", "key2": "value2"}

        await manager.close()

    async def test_memory_cache_set_many_with_ttl(self) -> None:
        """Test set_many with custom TTL."""
        cache = MemoryCache(namespace="test", default_ttl=3600)
        await cache.initialize()

        items = {"key1": "value1", "key2": "value2"}
        count = await cache.set_many(items, ttl=1)
        assert count == 2

        # Values should exist
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Values should be expired
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

        await cache.close()

    async def test_cache_config_default_values(self) -> None:
        """Test CacheConfig with default values."""
        config = CacheConfig()

        assert config.namespace == "cache"
        assert config.default_ttl == 3600
        assert config.max_size == 1000
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_db == 0
        assert config.redis_password is None
        assert config.redis_url is None
        assert config.l1_ttl == 300
        assert config.l1_max_size == 100  # Default is 100, not 1000

    async def test_cache_config_custom_values(self) -> None:
        """Test CacheConfig with custom values."""
        config = CacheConfig(
            namespace="custom",
            default_ttl=7200,
            max_size=500,
            redis_host="redis.example.com",
            redis_port=6380,
            redis_db=2,
            redis_password="secret",
            redis_url="redis://custom-url:6379/0",
            l1_ttl=600,
            l1_max_size=2000,
        )

        assert config.namespace == "custom"
        assert config.default_ttl == 7200
        assert config.max_size == 500
        assert config.redis_host == "redis.example.com"
        assert config.redis_port == 6380
        assert config.redis_db == 2
        assert config.redis_password == "secret"
        assert config.redis_url == "redis://custom-url:6379/0"
        assert config.l1_ttl == 600
        assert config.l1_max_size == 2000
