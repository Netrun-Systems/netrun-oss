"""
Redis-based distributed caching implementation.

Provides async Redis caching with namespace isolation, TTL management,
batch operations, and statistics tracking.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union

from .types import CacheConfig, CacheStats

logger = logging.getLogger(__name__)

# Import Redis with fallback for optional dependency
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = Any  # type: ignore


class RedisCache:
    """
    Redis-based distributed cache with namespace isolation and statistics.

    Features:
    - Async Redis operations
    - Namespace-based key prefixing
    - Configurable TTL
    - Batch operations (pipeline)
    - Atomic counters
    - Hit/miss tracking
    - JSON serialization
    - Key hashing for complex keys

    Example:
        >>> cache = RedisCache(namespace="users", default_ttl=3600)
        >>> await cache.initialize()
        >>> await cache.set("user:123", {"name": "John"})
        >>> user = await cache.get("user:123")
    """

    def __init__(
        self,
        redis_client: Optional["Redis"] = None,
        config: Optional[CacheConfig] = None,
        namespace: str = "cache",
        default_ttl: int = 3600,
    ):
        """
        Initialize Redis cache.

        Args:
            redis_client: Optional existing Redis connection
            config: Optional cache configuration
            namespace: Cache namespace prefix (for isolation)
            default_ttl: Default TTL in seconds
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis support requires 'redis[asyncio]>=5.0.0'. "
                "Install with: pip install netrun-cache[redis]"
            )

        self.config = config or CacheConfig(namespace=namespace, default_ttl=default_ttl)
        self.redis_client = redis_client
        self.namespace = self.config.namespace
        self.default_ttl = self.config.default_ttl
        self._initialized = False

        # Hit/miss tracking keys
        self._hits_key = f"{self.namespace}:stats:hits"
        self._misses_key = f"{self.namespace}:stats:misses"

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return

        try:
            if not self.redis_client:
                # Build Redis URL from config
                if self.config.redis_url:
                    redis_url = self.config.redis_url
                else:
                    password_part = (
                        f":{self.config.redis_password}@"
                        if self.config.redis_password
                        else ""
                    )
                    redis_url = (
                        f"redis://{password_part}{self.config.redis_host}:"
                        f"{self.config.redis_port}/{self.config.redis_db}"
                    )

                self.redis_client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    socket_timeout=self.config.socket_timeout,
                )

            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info(f"Redis cache initialized (namespace={self.namespace})")

        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self._initialized = False
            raise

    def _make_key(self, key: str) -> str:
        """
        Generate namespaced cache key.

        Args:
            key: Cache key

        Returns:
            Namespaced key
        """
        return f"{self.namespace}:{key}"

    def _hash_key(self, data: Union[str, Dict[str, Any], List[Any]]) -> str:
        """
        Generate hash for complex keys (e.g., LLM prompts).

        Args:
            data: Data to hash

        Returns:
            SHA256 hash
        """
        if isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True)

        return hashlib.sha256(str(data).encode()).hexdigest()

    async def get(self, key: str, track_stats: bool = True) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            track_stats: Whether to track hit/miss statistics

        Returns:
            Cached value or None if not found
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            value = await self.redis_client.get(cache_key)

            if value is not None:
                if track_stats:
                    await self.redis_client.incr(self._hits_key)

                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                if track_stats:
                    await self.redis_client.incr(self._misses_key)
                return None

        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, nx: bool = False
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not specified)
            nx: Only set if key doesn't exist (SET NX)

        Returns:
            True if set, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            ttl = ttl if ttl is not None else self.default_ttl

            # Serialize complex objects
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            if nx:
                # SET NX - only set if not exists
                result = await self.redis_client.set(cache_key, value, ex=ttl, nx=True)
                return result is not None
            else:
                await self.redis_client.setex(cache_key, ttl, value)
                return True

        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            result = await self.redis_client.delete(cache_key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            result = await self.redis_client.exists(cache_key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to check cache key existence {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set/update TTL for a key.

        Args:
            key: Cache key
            ttl: TTL in seconds

        Returns:
            True if updated, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            result = await self.redis_client.expire(cache_key, ttl)
            return result

        except Exception as e:
            logger.error(f"Failed to set expiration for cache key {key}: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple keys in a single operation (pipeline).

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs (only found keys)
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_keys = [self._make_key(k) for k in keys]

            # Use pipeline for efficiency
            pipe = self.redis_client.pipeline()
            for cache_key in cache_keys:
                pipe.get(cache_key)

            values = await pipe.execute()

            result: Dict[str, Any] = {}
            for i, key in enumerate(keys):
                if values[i] is not None:
                    try:
                        result[key] = json.loads(values[i])
                    except (json.JSONDecodeError, TypeError):
                        result[key] = values[i]

                    # Track hit
                    await self.redis_client.incr(self._hits_key)
                else:
                    # Track miss
                    await self.redis_client.incr(self._misses_key)

            return result

        except Exception as e:
            logger.error(f"Failed to get many cache keys: {e}")
            return {}

    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """
        Set multiple keys in a single operation (pipeline).

        Args:
            items: Dictionary of key-value pairs
            ttl: TTL in seconds (uses default if not specified)

        Returns:
            Number of keys set
        """
        if not self._initialized:
            await self.initialize()

        try:
            ttl = ttl if ttl is not None else self.default_ttl

            # Use pipeline for efficiency
            pipe = self.redis_client.pipeline()
            for key, value in items.items():
                cache_key = self._make_key(key)

                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                elif not isinstance(value, str):
                    value = str(value)

                pipe.setex(cache_key, ttl, value)

            await pipe.execute()
            return len(items)

        except Exception as e:
            logger.error(f"Failed to set many cache keys: {e}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter (atomic operation).

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New value or None if failed
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            new_value = await self.redis_client.incrby(cache_key, amount)
            return new_value

        except Exception as e:
            logger.error(f"Failed to increment cache key {key}: {e}")
            return None

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement counter (atomic operation).

        Args:
            key: Counter key
            amount: Amount to decrement

        Returns:
            New value or None if failed
        """
        if not self._initialized:
            await self.initialize()

        try:
            cache_key = self._make_key(key)
            new_value = await self.redis_client.decrby(cache_key, amount)
            return new_value

        except Exception as e:
            logger.error(f"Failed to decrement cache key {key}: {e}")
            return None

    async def clear_namespace(self) -> int:
        """
        Clear all keys in this namespace.

        Returns:
            Number of keys deleted
        """
        if not self._initialized:
            await self.initialize()

        try:
            pattern = f"{self.namespace}:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)

                if keys:
                    deleted_count += await self.redis_client.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted_count} keys from namespace {self.namespace}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to clear namespace {self.namespace}: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            Cache statistics model
        """
        if not self._initialized:
            await self.initialize()

        try:
            hits = await self.redis_client.get(self._hits_key)
            misses = await self.redis_client.get(self._misses_key)

            hits = int(hits) if hits else 0
            misses = int(misses) if misses else 0
            total = hits + misses

            hit_rate = (hits / total * 100) if total > 0 else 0.0

            # Count keys in namespace
            pattern = f"{self.namespace}:*"
            cursor = 0
            key_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                # Exclude stats keys
                keys = [
                    k
                    for k in keys
                    if not k.endswith(":stats:hits") and not k.endswith(":stats:misses")
                ]
                key_count += len(keys)

                if cursor == 0:
                    break

            return CacheStats(
                namespace=self.namespace,
                hits=hits,
                misses=misses,
                total_requests=total,
                hit_rate_percent=round(hit_rate, 2),
                cached_keys=key_count,
                backend="redis",
                connected=self._initialized,
            )

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return CacheStats(
                namespace=self.namespace,
                hits=0,
                misses=0,
                total_requests=0,
                hit_rate_percent=0.0,
                cached_keys=0,
                backend="redis",
                connected=False,
            )

    async def reset_stats(self) -> bool:
        """
        Reset cache statistics.

        Returns:
            True if reset, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.redis_client.delete(self._hits_key, self._misses_key)
            logger.info(f"Reset cache stats for namespace {self.namespace}")
            return True

        except Exception as e:
            logger.error(f"Failed to reset cache stats: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False
            logger.info(f"Redis cache closed (namespace={self.namespace})")
