"""
Multi-layer cache manager with L1 (memory) and L2 (Redis) tiers.

Provides automatic fallback and write-through/write-behind modes.
"""

import logging
from typing import Any, Dict, List, Optional

from .memory_cache import MemoryCache
from .types import CacheConfig, CacheStats

logger = logging.getLogger(__name__)

# Import Redis with fallback
try:
    from .redis_cache import RedisCache

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisCache = None  # type: ignore


class CacheManager:
    """
    Multi-layer cache manager with L1 (memory) and L2 (Redis).

    Features:
    - Two-tier caching (L1: fast memory, L2: distributed Redis)
    - Automatic fallback to memory-only if Redis unavailable
    - Write-through mode (write to both layers)
    - Invalidation propagation
    - Combined statistics

    Example:
        >>> config = CacheConfig(
        ...     namespace="api",
        ...     default_ttl=3600,
        ...     l1_max_size=100,
        ...     l1_ttl=300
        ... )
        >>> cache = CacheManager(config)
        >>> await cache.initialize()
        >>> await cache.set("key", "value")
        >>> value = await cache.get("key")  # Checks L1, then L2
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._initialized = False

        # L1 cache (memory) - always available
        l1_config = CacheConfig(
            namespace=self.config.namespace,
            default_ttl=self.config.l1_ttl,
            max_size=self.config.l1_max_size,
        )
        self.l1_cache = MemoryCache(config=l1_config)

        # L2 cache (Redis) - optional
        self.l2_cache: Optional["RedisCache"] = None
        self._redis_available = False

    async def initialize(self) -> None:
        """Initialize cache layers."""
        if self._initialized:
            return

        # Initialize L1 (memory) cache
        await self.l1_cache.initialize()

        # Try to initialize L2 (Redis) cache
        if REDIS_AVAILABLE and RedisCache:
            try:
                self.l2_cache = RedisCache(config=self.config)
                await self.l2_cache.initialize()
                self._redis_available = True
                logger.info(
                    f"Multi-layer cache initialized: L1 (memory) + L2 (Redis) "
                    f"(namespace={self.config.namespace})"
                )
            except Exception as e:
                logger.warning(
                    f"Redis unavailable, using memory-only cache: {e}"
                )
                self.l2_cache = None
                self._redis_available = False
        else:
            logger.info(
                f"Redis not available, using memory-only cache "
                f"(namespace={self.config.namespace})"
            )

        self._initialized = True

    async def get(self, key: str, track_stats: bool = True) -> Optional[Any]:
        """
        Get value from cache (L1 then L2).

        Args:
            key: Cache key
            track_stats: Whether to track hit/miss statistics

        Returns:
            Cached value or None if not found
        """
        if not self._initialized:
            await self.initialize()

        # Try L1 (memory) first
        value = await self.l1_cache.get(key, track_stats=track_stats)
        if value is not None:
            return value

        # Try L2 (Redis) if available
        if self._redis_available and self.l2_cache:
            value = await self.l2_cache.get(key, track_stats=track_stats)
            if value is not None:
                # Populate L1 cache (read-through)
                await self.l1_cache.set(key, value, ttl=self.config.l1_ttl)
                return value

        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, nx: bool = False
    ) -> bool:
        """
        Set value in cache (write-through to both layers).

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not specified)
            nx: Only set if key doesn't exist (SET NX)

        Returns:
            True if set in at least one layer, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        l1_success = False
        l2_success = False

        # Write to L1 (memory)
        l1_success = await self.l1_cache.set(
            key, value, ttl=self.config.l1_ttl if ttl is None else min(ttl, self.config.l1_ttl), nx=nx
        )

        # Write to L2 (Redis) if available
        if self._redis_available and self.l2_cache:
            l2_success = await self.l2_cache.set(key, value, ttl=ttl, nx=nx)

        return l1_success or l2_success

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache (both layers).

        Args:
            key: Cache key

        Returns:
            True if deleted from at least one layer, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        l1_success = await self.l1_cache.delete(key)

        l2_success = False
        if self._redis_available and self.l2_cache:
            l2_success = await self.l2_cache.delete(key)

        return l1_success or l2_success

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache (either layer).

        Args:
            key: Cache key

        Returns:
            True if exists in L1 or L2, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        # Check L1 first
        if await self.l1_cache.exists(key):
            return True

        # Check L2 if available
        if self._redis_available and self.l2_cache:
            return await self.l2_cache.exists(key)

        return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set/update TTL for a key (both layers).

        Args:
            key: Cache key
            ttl: TTL in seconds

        Returns:
            True if updated in at least one layer, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        l1_success = await self.l1_cache.expire(key, min(ttl, self.config.l1_ttl))

        l2_success = False
        if self._redis_available and self.l2_cache:
            l2_success = await self.l2_cache.expire(key, ttl)

        return l1_success or l2_success

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple keys (L1 then L2 for misses).

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs (only found keys)
        """
        if not self._initialized:
            await self.initialize()

        # Get from L1
        result = await self.l1_cache.get_many(keys)

        # Find L1 misses
        l1_misses = [key for key in keys if key not in result]

        # Get L1 misses from L2 if available
        if l1_misses and self._redis_available and self.l2_cache:
            l2_results = await self.l2_cache.get_many(l1_misses)

            # Populate L1 with L2 results
            if l2_results:
                await self.l1_cache.set_many(l2_results, ttl=self.config.l1_ttl)

            # Merge results
            result.update(l2_results)

        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """
        Set multiple keys (write-through to both layers).

        Args:
            items: Dictionary of key-value pairs
            ttl: TTL in seconds (uses default if not specified)

        Returns:
            Number of keys set
        """
        if not self._initialized:
            await self.initialize()

        # Write to L1
        l1_count = await self.l1_cache.set_many(
            items,
            ttl=self.config.l1_ttl if ttl is None else min(ttl, self.config.l1_ttl)
        )

        # Write to L2 if available
        if self._redis_available and self.l2_cache:
            await self.l2_cache.set_many(items, ttl=ttl)

        return l1_count

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter (L2 primary, L1 invalidated).

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New value or None if failed
        """
        if not self._initialized:
            await self.initialize()

        # Invalidate L1
        await self.l1_cache.delete(key)

        # Increment in L2 if available
        if self._redis_available and self.l2_cache:
            return await self.l2_cache.increment(key, amount)
        else:
            # Fallback to L1
            return await self.l1_cache.increment(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement counter (L2 primary, L1 invalidated).

        Args:
            key: Counter key
            amount: Amount to decrement

        Returns:
            New value or None if failed
        """
        return await self.increment(key, -amount)

    async def clear_namespace(self) -> int:
        """
        Clear all keys in namespace (both layers).

        Returns:
            Total number of keys deleted
        """
        if not self._initialized:
            await self.initialize()

        l1_count = await self.l1_cache.clear_namespace()

        l2_count = 0
        if self._redis_available and self.l2_cache:
            l2_count = await self.l2_cache.clear_namespace()

        total = l1_count + l2_count
        logger.info(
            f"Cleared {total} keys from namespace {self.config.namespace} "
            f"(L1: {l1_count}, L2: {l2_count})"
        )
        return total

    async def get_stats(self) -> Dict[str, CacheStats]:
        """
        Get cache statistics for both layers.

        Returns:
            Dictionary with L1 and L2 stats
        """
        if not self._initialized:
            await self.initialize()

        stats = {
            "l1": await self.l1_cache.get_stats(),
        }

        if self._redis_available and self.l2_cache:
            stats["l2"] = await self.l2_cache.get_stats()

        return stats

    async def reset_stats(self) -> bool:
        """
        Reset cache statistics for both layers.

        Returns:
            True if reset in at least one layer, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        l1_success = await self.l1_cache.reset_stats()

        l2_success = False
        if self._redis_available and self.l2_cache:
            l2_success = await self.l2_cache.reset_stats()

        return l1_success or l2_success

    async def close(self) -> None:
        """Close cache connections for both layers."""
        if self.l1_cache:
            await self.l1_cache.close()

        if self.l2_cache:
            await self.l2_cache.close()

        self._initialized = False
        logger.info(f"Cache manager closed (namespace={self.config.namespace})")
