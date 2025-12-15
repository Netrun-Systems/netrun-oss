"""
Redis Fixtures for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides mock Redis client fixtures for testing without Redis server.
Supports common Redis operations with AsyncMock implementations.

Usage:
    @pytest.mark.asyncio
    async def test_cache_operation(mock_redis):
        await mock_redis.set("key", "value")
        result = await mock_redis.get("key")
        assert result == "value"

Fixtures:
    - mock_redis: Mock async Redis client with common operations
    - mock_redis_client: Alias for mock_redis
    - redis_url: Test Redis URL configuration
    - mock_redis_pool: Mock Redis connection pool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Any

# Graceful netrun-logging integration (optional)
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


@pytest.fixture
def redis_url() -> str:
    """
    Test Redis URL configuration.

    Returns:
        str: Redis connection URL for testing

    Example:
        def test_redis_config(redis_url):
            assert "redis://localhost" in redis_url
    """
    return "redis://localhost:6379/0"


@pytest.fixture
def mock_redis():
    """
    Mock Redis client for testing without Redis server.

    Provides AsyncMock implementations of common Redis operations:
    - get, set, delete, exists
    - setex, expire, ttl for expiration
    - hget, hset, hgetall for hashes
    - lpush, rpush, lpop, rpop for lists
    - sadd, smembers for sets
    - zadd, zrange for sorted sets

    All methods return success values by default.
    Configure return values as needed in tests.

    Returns:
        AsyncMock: Mock Redis client

    Example:
        @pytest.mark.asyncio
        async def test_cache_set(mock_redis):
            await mock_redis.set("user:123", "data")
            mock_redis.set.assert_called_once_with("user:123", "data")

        @pytest.mark.asyncio
        async def test_cache_get(mock_redis):
            mock_redis.get.return_value = "cached_data"
            result = await mock_redis.get("key")
            assert result == "cached_data"
    """
    redis = AsyncMock()

    # String operations
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.setnx = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.incr = AsyncMock(return_value=1)
    redis.decr = AsyncMock(return_value=0)

    # Expiration operations
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=-1)
    redis.persist = AsyncMock(return_value=True)

    # Hash operations
    redis.hget = AsyncMock(return_value=None)
    redis.hset = AsyncMock(return_value=1)
    redis.hgetall = AsyncMock(return_value={})
    redis.hdel = AsyncMock(return_value=1)
    redis.hexists = AsyncMock(return_value=0)
    redis.hkeys = AsyncMock(return_value=[])
    redis.hvals = AsyncMock(return_value=[])

    # List operations
    redis.lpush = AsyncMock(return_value=1)
    redis.rpush = AsyncMock(return_value=1)
    redis.lpop = AsyncMock(return_value=None)
    redis.rpop = AsyncMock(return_value=None)
    redis.lrange = AsyncMock(return_value=[])
    redis.llen = AsyncMock(return_value=0)

    # Set operations
    redis.sadd = AsyncMock(return_value=1)
    redis.smembers = AsyncMock(return_value=set())
    redis.sismember = AsyncMock(return_value=False)
    redis.srem = AsyncMock(return_value=1)
    redis.scard = AsyncMock(return_value=0)

    # Sorted set operations
    redis.zadd = AsyncMock(return_value=1)
    redis.zrange = AsyncMock(return_value=[])
    redis.zrem = AsyncMock(return_value=1)
    redis.zcard = AsyncMock(return_value=0)
    redis.zscore = AsyncMock(return_value=None)

    # Key operations
    redis.keys = AsyncMock(return_value=[])
    redis.scan = AsyncMock(return_value=(0, []))
    redis.rename = AsyncMock(return_value=True)

    # Pipeline operations
    redis.pipeline = MagicMock(return_value=AsyncMock())

    # Pub/Sub operations
    redis.publish = AsyncMock(return_value=0)
    redis.subscribe = AsyncMock()
    redis.unsubscribe = AsyncMock()

    # Connection operations
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()

    return redis


@pytest.fixture
def mock_redis_client(mock_redis):
    """
    Alias for mock_redis fixture.

    Provides consistent naming with actual Redis client usage.

    Args:
        mock_redis: Mock Redis fixture

    Returns:
        AsyncMock: Mock Redis client

    Example:
        @pytest.mark.asyncio
        async def test_with_client_name(mock_redis_client):
            await mock_redis_client.set("key", "value")
            assert await mock_redis_client.get("key") is None
    """
    return mock_redis


@pytest.fixture
def mock_redis_pool():
    """
    Mock Redis connection pool for testing pool management.

    Returns:
        MagicMock: Mock Redis connection pool

    Example:
        def test_pool_configuration(mock_redis_pool):
            mock_redis_pool.max_connections = 10
            assert mock_redis_pool.max_connections == 10
    """
    pool = MagicMock()
    pool.max_connections = 10
    pool.connection_kwargs = {"host": "localhost", "port": 6379}
    pool.get_connection = AsyncMock()
    pool.release = AsyncMock()
    pool.disconnect = AsyncMock()
    return pool


@pytest.fixture
def mock_redis_with_data():
    """
    Mock Redis client pre-populated with test data.

    Provides Redis mock with in-memory data store for stateful testing.
    Simulates actual Redis behavior with get/set operations.

    Returns:
        AsyncMock: Mock Redis client with data store

    Example:
        @pytest.mark.asyncio
        async def test_cache_persistence(mock_redis_with_data):
            await mock_redis_with_data.set("user:1", "John")
            result = await mock_redis_with_data.get("user:1")
            assert result == "John"
    """
    redis = AsyncMock()
    data_store = {}
    hash_store = {}
    ttl_store = {}

    async def mock_set(key: str, value: Any, ex: Optional[int] = None):
        data_store[key] = value
        if ex:
            ttl_store[key] = ex
        return True

    async def mock_get(key: str):
        return data_store.get(key)

    async def mock_delete(*keys):
        count = 0
        for key in keys:
            if key in data_store:
                del data_store[key]
                count += 1
        return count

    async def mock_exists(*keys):
        return sum(1 for key in keys if key in data_store)

    async def mock_hset(name: str, key: str, value: Any):
        if name not in hash_store:
            hash_store[name] = {}
        hash_store[name][key] = value
        return 1

    async def mock_hget(name: str, key: str):
        return hash_store.get(name, {}).get(key)

    async def mock_hgetall(name: str):
        return hash_store.get(name, {})

    redis.set = AsyncMock(side_effect=mock_set)
    redis.get = AsyncMock(side_effect=mock_get)
    redis.delete = AsyncMock(side_effect=mock_delete)
    redis.exists = AsyncMock(side_effect=mock_exists)
    redis.hset = AsyncMock(side_effect=mock_hset)
    redis.hget = AsyncMock(side_effect=mock_hget)
    redis.hgetall = AsyncMock(side_effect=mock_hgetall)
    redis.keys = AsyncMock(return_value=list(data_store.keys()))

    return redis


@pytest.fixture
def mock_redis_error():
    """
    Mock Redis client that raises connection errors.

    Use for testing error handling and fallback behavior
    when Redis is unavailable.

    Returns:
        AsyncMock: Mock Redis client that raises errors

    Example:
        @pytest.mark.asyncio
        async def test_redis_connection_error(mock_redis_error):
            from redis.exceptions import ConnectionError

            with pytest.raises(ConnectionError):
                await mock_redis_error.get("key")
    """
    from unittest.mock import AsyncMock

    try:
        from redis.exceptions import ConnectionError as RedisConnectionError
    except ImportError:
        # Fallback if redis package not installed
        class RedisConnectionError(Exception):
            pass

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=RedisConnectionError("Connection failed"))
    redis.set = AsyncMock(side_effect=RedisConnectionError("Connection failed"))
    redis.ping = AsyncMock(side_effect=RedisConnectionError("Connection failed"))

    return redis


@pytest.fixture
async def cleanup_redis_keys(mock_redis):
    """
    Fixture to clean up Redis keys after test.

    Use as autouse or explicit cleanup for tests that modify Redis state.

    Args:
        mock_redis: Mock Redis fixture

    Example:
        @pytest.mark.asyncio
        async def test_with_cleanup(mock_redis, cleanup_redis_keys):
            await mock_redis.set("temp:key", "value")
            # Keys cleaned up automatically
    """
    yield
    # Cleanup logic (no-op for mock, but pattern for real Redis)
    await mock_redis.delete("*")
