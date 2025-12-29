"""Tests for Redis cache edge cases using fakeredis."""

import json
from unittest.mock import AsyncMock, patch

import pytest

try:
    import fakeredis.aioredis

    from netrun.cache import CacheConfig, RedisCache

    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False


@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, reason="fakeredis not available")
@pytest.mark.unit
class TestRedisCacheEdgeCases:
    """Edge case tests for RedisCache."""

    @pytest.fixture
    async def redis_cache(self):
        """Create Redis cache with fakeredis."""
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache = RedisCache(redis_client=fake_redis, namespace="test", default_ttl=3600)
        await cache.initialize()
        yield cache
        await cache.close()

    async def test_redis_cache_double_initialization(self, redis_cache: "RedisCache") -> None:
        """Test that double initialization is a no-op."""
        assert redis_cache._initialized is True

        # Initialize again - should return immediately
        await redis_cache.initialize()
        assert redis_cache._initialized is True

    async def test_redis_cache_set_with_dict_value(self, redis_cache: "RedisCache") -> None:
        """Test set operation with dictionary value."""
        data = {"name": "John", "age": 30, "city": "NYC"}

        result = await redis_cache.set("user:1", data)
        assert result is True

        # Get and verify JSON deserialization
        value = await redis_cache.get("user:1")
        assert value == data

    async def test_redis_cache_set_with_list_value(self, redis_cache: "RedisCache") -> None:
        """Test set operation with list value."""
        data = [1, 2, 3, 4, 5]

        result = await redis_cache.set("numbers", data)
        assert result is True

        value = await redis_cache.get("numbers")
        assert value == data

    async def test_redis_cache_set_with_non_string_value(self, redis_cache: "RedisCache") -> None:
        """Test set operation with non-string primitive value."""
        # Integer value - gets converted to string for storage
        result = await redis_cache.set("count", 42)
        assert result is True

        value = await redis_cache.get("count")
        # Value is converted to string, but not JSON serialized
        assert value == 42 or value == "42"  # May vary by implementation

    async def test_redis_cache_get_non_json_value(self, redis_cache: "RedisCache") -> None:
        """Test get operation with non-JSON value."""
        # Set plain string directly
        await redis_cache.redis_client.set(
            redis_cache._make_key("plain"), "plain_text"
        )

        value = await redis_cache.get("plain")
        assert value == "plain_text"

    async def test_redis_cache_set_nx_success(self, redis_cache: "RedisCache") -> None:
        """Test SET NX operation when key doesn't exist."""
        result = await redis_cache.set("new_key", "value", nx=True)
        assert result is True

        value = await redis_cache.get("new_key")
        assert value == "value"

    async def test_redis_cache_set_nx_failure(self, redis_cache: "RedisCache") -> None:
        """Test SET NX operation when key exists."""
        # Set key first
        await redis_cache.set("existing_key", "original")

        # Try to set with NX (should fail)
        result = await redis_cache.set("existing_key", "new_value", nx=True)
        assert result is False

        # Value should remain unchanged
        value = await redis_cache.get("existing_key")
        assert value == "original"

    async def test_redis_cache_delete_existing_key(self, redis_cache: "RedisCache") -> None:
        """Test delete operation on existing key."""
        await redis_cache.set("key1", "value1")

        result = await redis_cache.delete("key1")
        assert result is True

        value = await redis_cache.get("key1")
        assert value is None

    async def test_redis_cache_delete_nonexistent_key(self, redis_cache: "RedisCache") -> None:
        """Test delete operation on nonexistent key."""
        result = await redis_cache.delete("nonexistent")
        assert result is False

    async def test_redis_cache_exists_nonexistent_key(self, redis_cache: "RedisCache") -> None:
        """Test exists operation on nonexistent key."""
        result = await redis_cache.exists("nonexistent")
        assert result is False

    async def test_redis_cache_expire_existing_key(self, redis_cache: "RedisCache") -> None:
        """Test expire operation on existing key."""
        await redis_cache.set("key1", "value1")

        result = await redis_cache.expire("key1", 100)
        assert result is True

    async def test_redis_cache_expire_nonexistent_key(self, redis_cache: "RedisCache") -> None:
        """Test expire operation on nonexistent key."""
        result = await redis_cache.expire("nonexistent", 100)
        assert result is False

    async def test_redis_cache_get_many_all_hits(self, redis_cache: "RedisCache") -> None:
        """Test get_many when all keys exist."""
        await redis_cache.set("key1", "value1")
        await redis_cache.set("key2", {"data": "value2"})
        await redis_cache.set("key3", [1, 2, 3])

        result = await redis_cache.get_many(["key1", "key2", "key3"])

        assert result == {
            "key1": "value1",
            "key2": {"data": "value2"},
            "key3": [1, 2, 3],
        }

    async def test_redis_cache_get_many_partial_hits(self, redis_cache: "RedisCache") -> None:
        """Test get_many with some missing keys."""
        await redis_cache.set("key1", "value1")
        await redis_cache.set("key3", "value3")

        result = await redis_cache.get_many(["key1", "key2", "key3", "key4"])

        assert result == {"key1": "value1", "key3": "value3"}
        assert "key2" not in result
        assert "key4" not in result

    async def test_redis_cache_get_many_all_misses(self, redis_cache: "RedisCache") -> None:
        """Test get_many when no keys exist."""
        result = await redis_cache.get_many(["key1", "key2", "key3"])

        assert result == {}

    async def test_redis_cache_get_many_empty_list(self, redis_cache: "RedisCache") -> None:
        """Test get_many with empty key list."""
        result = await redis_cache.get_many([])

        assert result == {}

    async def test_redis_cache_set_many_success(self, redis_cache: "RedisCache") -> None:
        """Test set_many operation."""
        items = {
            "key1": "value1",
            "key2": {"data": "value2"},
            "key3": [1, 2, 3],
        }

        count = await redis_cache.set_many(items, ttl=100)
        assert count == 3

        # Verify all keys set
        for key, expected_value in items.items():
            value = await redis_cache.get(key)
            assert value == expected_value

    async def test_redis_cache_set_many_empty_dict(self, redis_cache: "RedisCache") -> None:
        """Test set_many with empty dictionary."""
        count = await redis_cache.set_many({})
        assert count == 0

    async def test_redis_cache_set_many_with_custom_ttl(self, redis_cache: "RedisCache") -> None:
        """Test set_many with custom TTL."""
        items = {"key1": "value1", "key2": "value2"}

        count = await redis_cache.set_many(items, ttl=200)
        assert count == 2

    async def test_redis_cache_increment_new_key(self, redis_cache: "RedisCache") -> None:
        """Test increment operation on new key."""
        result = await redis_cache.increment("counter")
        assert result == 1

        result = await redis_cache.increment("counter")
        assert result == 2

    async def test_redis_cache_increment_existing_key(self, redis_cache: "RedisCache") -> None:
        """Test increment operation on existing counter."""
        await redis_cache.redis_client.set(redis_cache._make_key("counter"), "10")

        result = await redis_cache.increment("counter")
        assert result == 11

        result = await redis_cache.increment("counter", 5)
        assert result == 16

    async def test_redis_cache_decrement_new_key(self, redis_cache: "RedisCache") -> None:
        """Test decrement operation on new key."""
        result = await redis_cache.decrement("counter")
        assert result == -1

        result = await redis_cache.decrement("counter")
        assert result == -2

    async def test_redis_cache_decrement_existing_key(self, redis_cache: "RedisCache") -> None:
        """Test decrement operation on existing counter."""
        await redis_cache.redis_client.set(redis_cache._make_key("counter"), "10")

        result = await redis_cache.decrement("counter")
        assert result == 9

        result = await redis_cache.decrement("counter", 5)
        assert result == 4

    async def test_redis_cache_clear_namespace(self, redis_cache: "RedisCache") -> None:
        """Test clearing all keys in namespace."""
        # Set keys in test namespace
        await redis_cache.set("key1", "value1")
        await redis_cache.set("key2", "value2")
        await redis_cache.set("key3", "value3")

        # Create cache in different namespace
        other_cache = RedisCache(
            redis_client=redis_cache.redis_client,
            namespace="other",
            default_ttl=3600,
        )
        await other_cache.initialize()
        await other_cache.set("key1", "other_value")

        # Clear test namespace
        count = await redis_cache.clear_namespace()
        assert count >= 3  # At least 3 keys (may include stats keys)

        # Test namespace keys should be gone
        assert await redis_cache.get("key1") is None
        assert await redis_cache.get("key2") is None
        assert await redis_cache.get("key3") is None

        # Other namespace key should remain
        assert await other_cache.get("key1") == "other_value"

        await other_cache.close()

    async def test_redis_cache_clear_empty_namespace(self, redis_cache: "RedisCache") -> None:
        """Test clearing empty namespace."""
        count = await redis_cache.clear_namespace()
        assert count >= 0

    async def test_redis_cache_get_stats_with_data(self, redis_cache: "RedisCache") -> None:
        """Test get_stats with actual cache usage."""
        await redis_cache.reset_stats()

        # Perform operations
        await redis_cache.set("key1", "value1")
        await redis_cache.set("key2", "value2")

        await redis_cache.get("key1")  # Hit
        await redis_cache.get("key2")  # Hit
        await redis_cache.get("nonexistent")  # Miss

        stats = await redis_cache.get_stats()

        assert stats.namespace == "test"
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.total_requests == 3
        assert stats.hit_rate_percent == pytest.approx(66.67, rel=0.01)
        assert stats.cached_keys >= 2  # At least key1 and key2
        assert stats.backend == "redis"
        assert stats.connected is True

    async def test_redis_cache_get_stats_empty_cache(self, redis_cache: "RedisCache") -> None:
        """Test get_stats on empty cache."""
        await redis_cache.reset_stats()

        stats = await redis_cache.get_stats()

        assert stats.namespace == "test"
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total_requests == 0
        assert stats.hit_rate_percent == 0.0
        assert stats.cached_keys >= 0
        assert stats.backend == "redis"
        assert stats.connected is True

    async def test_redis_cache_reset_stats(self, redis_cache: "RedisCache") -> None:
        """Test reset_stats operation."""
        # Generate some stats
        await redis_cache.set("key1", "value1")
        await redis_cache.get("key1")
        await redis_cache.get("nonexistent")

        stats = await redis_cache.get_stats()
        assert stats.hits > 0
        assert stats.misses > 0

        # Reset
        result = await redis_cache.reset_stats()
        assert result is True

        stats = await redis_cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

    async def test_redis_cache_hash_key_string(self, redis_cache: "RedisCache") -> None:
        """Test _hash_key with string input."""
        hash1 = redis_cache._hash_key("test_string")
        hash2 = redis_cache._hash_key("test_string")
        hash3 = redis_cache._hash_key("different_string")

        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different input = different hash
        assert len(hash1) == 64  # SHA256 hash length

    async def test_redis_cache_hash_key_dict(self, redis_cache: "RedisCache") -> None:
        """Test _hash_key with dictionary input."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 2, "a": 1}  # Same data, different order
        dict3 = {"a": 1, "b": 3}

        hash1 = redis_cache._hash_key(dict1)
        hash2 = redis_cache._hash_key(dict2)
        hash3 = redis_cache._hash_key(dict3)

        assert hash1 == hash2  # Same data = same hash (order independent)
        assert hash1 != hash3  # Different data = different hash

    async def test_redis_cache_hash_key_list(self, redis_cache: "RedisCache") -> None:
        """Test _hash_key with list input."""
        list1 = [1, 2, 3]
        list2 = [1, 2, 3]
        list3 = [1, 2, 4]

        hash1 = redis_cache._hash_key(list1)
        hash2 = redis_cache._hash_key(list2)
        hash3 = redis_cache._hash_key(list3)

        assert hash1 == hash2  # Same list = same hash
        assert hash1 != hash3  # Different list = different hash

    async def test_redis_cache_get_with_track_stats_disabled(self, redis_cache: "RedisCache") -> None:
        """Test get operation with track_stats=False."""
        await redis_cache.reset_stats()
        await redis_cache.set("key1", "value1")

        # Get with stats disabled
        value = await redis_cache.get("key1", track_stats=False)
        assert value == "value1"

        stats = await redis_cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

        # Get nonexistent with stats disabled
        value = await redis_cache.get("nonexistent", track_stats=False)
        assert value is None

        stats = await redis_cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

    async def test_redis_cache_close_connection(self, redis_cache: "RedisCache") -> None:
        """Test close operation."""
        assert redis_cache._initialized is True

        await redis_cache.close()

        assert redis_cache._initialized is False

    async def test_redis_cache_namespace_isolation(self) -> None:
        """Test that different namespaces are isolated."""
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

        cache1 = RedisCache(redis_client=fake_redis, namespace="ns1", default_ttl=3600)
        cache2 = RedisCache(redis_client=fake_redis, namespace="ns2", default_ttl=3600)

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

    async def test_redis_cache_set_many_with_non_string_values(self, redis_cache: "RedisCache") -> None:
        """Test set_many with various non-string value types."""
        items = {
            "int_key": 42,
            "float_key": 3.14,
            "bool_key": True,
            "dict_key": {"nested": "value"},
            "list_key": [1, 2, 3],
        }

        count = await redis_cache.set_many(items)
        assert count == 5

        # Verify dict and list are properly stored/retrieved
        assert await redis_cache.get("dict_key") == {"nested": "value"}
        assert await redis_cache.get("list_key") == [1, 2, 3]

        # Primitives are converted to strings
        int_val = await redis_cache.get("int_key")
        assert int_val == 42 or int_val == "42"
