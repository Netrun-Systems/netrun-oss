"""Tests for MemoryCache."""

import asyncio

import pytest

from netrun.cache import CacheConfig, MemoryCache


@pytest.mark.unit
class TestMemoryCache:
    """Unit tests for MemoryCache."""

    @pytest.fixture
    async def cache(self) -> MemoryCache:
        """Create cache instance for testing."""
        cache = MemoryCache(namespace="test", default_ttl=3600, max_size=100)
        await cache.initialize()
        yield cache
        await cache.close()

    async def test_initialize(self, cache: MemoryCache) -> None:
        """Test cache initialization."""
        assert cache._initialized is True
        assert cache.namespace == "test"
        assert cache.default_ttl == 3600
        assert cache.max_size == 100

    async def test_set_and_get(self, cache: MemoryCache) -> None:
        """Test basic set and get operations."""
        # Set string value
        assert await cache.set("key1", "value1") is True
        assert await cache.get("key1") == "value1"

        # Set dict value
        data = {"name": "John", "age": 30}
        assert await cache.set("key2", data) is True
        assert await cache.get("key2") == data

        # Set list value
        items = [1, 2, 3, 4, 5]
        assert await cache.set("key3", items) is True
        assert await cache.get("key3") == items

    async def test_get_nonexistent(self, cache: MemoryCache) -> None:
        """Test getting nonexistent key."""
        assert await cache.get("nonexistent") is None

    async def test_delete(self, cache: MemoryCache) -> None:
        """Test delete operation."""
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True

        assert await cache.delete("key1") is True
        assert await cache.exists("key1") is False
        assert await cache.get("key1") is None

        # Delete nonexistent key
        assert await cache.delete("nonexistent") is False

    async def test_exists(self, cache: MemoryCache) -> None:
        """Test exists operation."""
        assert await cache.exists("key1") is False

        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True

        await cache.delete("key1")
        assert await cache.exists("key1") is False

    async def test_expire(self, cache: MemoryCache) -> None:
        """Test expire operation."""
        await cache.set("key1", "value1", ttl=3600)
        assert await cache.exists("key1") is True

        # Update TTL to 1 second
        assert await cache.expire("key1", 1) is True

        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await cache.exists("key1") is False

    async def test_ttl_expiration(self, cache: MemoryCache) -> None:
        """Test TTL-based expiration."""
        # Set with 1 second TTL
        await cache.set("key1", "value1", ttl=1)
        assert await cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await cache.get("key1") is None

    async def test_set_nx(self, cache: MemoryCache) -> None:
        """Test SET NX (set if not exists)."""
        # First set should succeed
        assert await cache.set("key1", "value1", nx=True) is True
        assert await cache.get("key1") == "value1"

        # Second set should fail (key exists)
        assert await cache.set("key1", "value2", nx=True) is False
        assert await cache.get("key1") == "value1"  # Value unchanged

        # After delete, set should succeed
        await cache.delete("key1")
        assert await cache.set("key1", "value2", nx=True) is True
        assert await cache.get("key1") == "value2"

    async def test_get_many(self, cache: MemoryCache) -> None:
        """Test batch get operation."""
        # Set multiple keys
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Get multiple keys
        result = await cache.get_many(["key1", "key2", "key3", "nonexistent"])

        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}
        assert "nonexistent" not in result

    async def test_set_many(self, cache: MemoryCache) -> None:
        """Test batch set operation."""
        items = {"key1": "value1", "key2": "value2", "key3": "value3"}

        count = await cache.set_many(items, ttl=3600)
        assert count == 3

        # Verify all keys set
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

    async def test_increment(self, cache: MemoryCache) -> None:
        """Test atomic increment operation."""
        # Increment nonexistent key (initializes to amount)
        assert await cache.increment("counter") == 1
        assert await cache.increment("counter") == 2
        assert await cache.increment("counter", 5) == 7

    async def test_decrement(self, cache: MemoryCache) -> None:
        """Test atomic decrement operation."""
        await cache.set("counter", 10)

        assert await cache.decrement("counter") == 9
        assert await cache.decrement("counter", 5) == 4

    async def test_lru_eviction(self, cache: MemoryCache) -> None:
        """Test LRU eviction when cache is full."""
        # Create cache with max_size=3
        small_cache = MemoryCache(namespace="test_lru", max_size=3)
        await small_cache.initialize()

        # Fill cache
        await small_cache.set("key1", "value1")
        await small_cache.set("key2", "value2")
        await small_cache.set("key3", "value3")

        # All keys should exist
        assert await small_cache.exists("key1") is True
        assert await small_cache.exists("key2") is True
        assert await small_cache.exists("key3") is True

        # Add one more key (should evict key1)
        await small_cache.set("key4", "value4")

        # key1 should be evicted
        assert await small_cache.exists("key1") is False
        assert await small_cache.exists("key2") is True
        assert await small_cache.exists("key3") is True
        assert await small_cache.exists("key4") is True

        await small_cache.close()

    async def test_namespace_isolation(self) -> None:
        """Test namespace isolation."""
        cache1 = MemoryCache(namespace="ns1")
        cache2 = MemoryCache(namespace="ns2")

        await cache1.initialize()
        await cache2.initialize()

        # Set same key in different namespaces
        await cache1.set("key1", "value1")
        await cache2.set("key1", "value2")

        # Values should be isolated
        assert await cache1.get("key1") == "value1"
        assert await cache2.get("key1") == "value2"

        await cache1.close()
        await cache2.close()

    async def test_clear_namespace(self, cache: MemoryCache) -> None:
        """Test clearing all keys in namespace."""
        # Set multiple keys
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Clear namespace
        count = await cache.clear_namespace()
        assert count == 3

        # All keys should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    async def test_get_stats(self, cache: MemoryCache) -> None:
        """Test statistics tracking."""
        # Reset stats
        await cache.reset_stats()

        # Perform operations
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.get("key1")  # Hit
        await cache.get("key2")  # Hit
        await cache.get("nonexistent")  # Miss

        stats = await cache.get_stats()

        assert stats.namespace == "test"
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.total_requests == 3
        assert stats.hit_rate_percent == pytest.approx(66.67, rel=0.01)
        assert stats.cached_keys == 2
        assert stats.backend == "memory"
        assert stats.connected is True

    async def test_reset_stats(self, cache: MemoryCache) -> None:
        """Test resetting statistics."""
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("nonexistent")  # Miss

        stats = await cache.get_stats()
        assert stats.hits > 0
        assert stats.misses > 0

        # Reset
        assert await cache.reset_stats() is True

        stats = await cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

    async def test_config_model(self) -> None:
        """Test CacheConfig integration."""
        config = CacheConfig(namespace="test_config", default_ttl=1800, max_size=500)

        cache = MemoryCache(config=config)
        await cache.initialize()

        assert cache.namespace == "test_config"
        assert cache.default_ttl == 1800
        assert cache.max_size == 500

        await cache.close()
