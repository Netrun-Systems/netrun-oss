"""
In-memory LRU cache implementation with TTL support.

Provides thread-safe in-memory caching as fallback when Redis is unavailable
or for L1 cache in multi-layer setups.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from .types import CacheConfig, CacheStats

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    In-memory LRU cache with TTL support.

    Features:
    - LRU eviction policy
    - Per-key TTL
    - Thread-safe operations
    - Automatic expiration
    - Same interface as RedisCache
    - Hit/miss tracking

    Example:
        >>> cache = MemoryCache(namespace="users", default_ttl=3600, max_size=1000)
        >>> await cache.initialize()
        >>> await cache.set("user:123", {"name": "John"})
        >>> user = await cache.get("user:123")
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        namespace: str = "cache",
        default_ttl: int = 3600,
        max_size: int = 1000,
    ):
        """
        Initialize memory cache.

        Args:
            config: Optional cache configuration
            namespace: Cache namespace (for statistics)
            default_ttl: Default TTL in seconds
            max_size: Maximum number of cached items
        """
        self.config = config or CacheConfig(
            namespace=namespace, default_ttl=default_ttl, max_size=max_size
        )
        self.namespace = self.config.namespace
        self.default_ttl = self.config.default_ttl
        self.max_size = self.config.max_size or 1000
        self._initialized = False

        # Cache storage: key -> (value, expiry_time)
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0

    async def initialize(self) -> None:
        """Initialize memory cache."""
        if self._initialized:
            return

        self._initialized = True
        logger.info(
            f"Memory cache initialized (namespace={self.namespace}, max_size={self.max_size})"
        )

    def _make_key(self, key: str) -> str:
        """
        Generate namespaced cache key.

        Args:
            key: Cache key

        Returns:
            Namespaced key
        """
        return f"{self.namespace}:{key}"

    def _is_expired(self, expiry_time: float) -> bool:
        """
        Check if entry is expired.

        Args:
            expiry_time: Expiry timestamp

        Returns:
            True if expired, False otherwise
        """
        return time.time() > expiry_time

    def _evict_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() if current_time > expiry
        ]

        for key in expired_keys:
            del self._cache[key]

    def _evict_lru(self) -> None:
        """Evict least recently used item if cache is full."""
        if len(self._cache) >= self.max_size:
            # Remove oldest item (first in OrderedDict)
            self._cache.popitem(last=False)

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

        cache_key = self._make_key(key)

        async with self._lock:
            if cache_key in self._cache:
                value, expiry = self._cache[cache_key]

                if self._is_expired(expiry):
                    # Expired - remove and count as miss
                    del self._cache[cache_key]
                    if track_stats:
                        self._misses += 1
                    return None

                # Move to end (mark as recently used)
                self._cache.move_to_end(cache_key)

                if track_stats:
                    self._hits += 1

                return value
            else:
                if track_stats:
                    self._misses += 1
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

        cache_key = self._make_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl

        async with self._lock:
            if nx and cache_key in self._cache:
                # Key exists and nx=True, don't set
                return False

            # Evict expired entries
            self._evict_expired()

            # Evict LRU if necessary
            if cache_key not in self._cache:
                self._evict_lru()

            # Set value
            self._cache[cache_key] = (value, expiry)
            self._cache.move_to_end(cache_key)

            return True

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

        cache_key = self._make_key(key)

        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists and not expired, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        cache_key = self._make_key(key)

        async with self._lock:
            if cache_key in self._cache:
                _, expiry = self._cache[cache_key]
                if self._is_expired(expiry):
                    del self._cache[cache_key]
                    return False
                return True
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

        cache_key = self._make_key(key)
        new_expiry = time.time() + ttl

        async with self._lock:
            if cache_key in self._cache:
                value, _ = self._cache[cache_key]
                self._cache[cache_key] = (value, new_expiry)
                return True
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple keys.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs (only found keys)
        """
        result: Dict[str, Any] = {}

        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value

        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """
        Set multiple keys.

        Args:
            items: Dictionary of key-value pairs
            ttl: TTL in seconds (uses default if not specified)

        Returns:
            Number of keys set
        """
        count = 0

        for key, value in items.items():
            if await self.set(key, value, ttl=ttl):
                count += 1

        return count

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

        cache_key = self._make_key(key)

        async with self._lock:
            if cache_key in self._cache:
                value, expiry = self._cache[cache_key]
                if isinstance(value, int):
                    new_value = value + amount
                    self._cache[cache_key] = (new_value, expiry)
                    return new_value
                else:
                    logger.error(f"Cannot increment non-integer value for key {key}")
                    return None
            else:
                # Initialize counter
                expiry = time.time() + self.default_ttl
                self._cache[cache_key] = (amount, expiry)
                return amount

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement counter (atomic operation).

        Args:
            key: Counter key
            amount: Amount to decrement

        Returns:
            New value or None if failed
        """
        return await self.increment(key, -amount)

    async def clear_namespace(self) -> int:
        """
        Clear all keys in this namespace.

        Returns:
            Number of keys deleted
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            prefix = f"{self.namespace}:"
            keys_to_delete = [key for key in self._cache.keys() if key.startswith(prefix)]

            for key in keys_to_delete:
                del self._cache[key]

            logger.info(f"Cleared {len(keys_to_delete)} keys from namespace {self.namespace}")
            return len(keys_to_delete)

    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            Cache statistics model
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            # Count non-expired keys
            current_time = time.time()
            cached_keys = sum(
                1
                for key, (_, expiry) in self._cache.items()
                if not self._is_expired(expiry) and key.startswith(f"{self.namespace}:")
            )

            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0

            return CacheStats(
                namespace=self.namespace,
                hits=self._hits,
                misses=self._misses,
                total_requests=total,
                hit_rate_percent=round(hit_rate, 2),
                cached_keys=cached_keys,
                backend="memory",
                connected=self._initialized,
            )

    async def reset_stats(self) -> bool:
        """
        Reset cache statistics.

        Returns:
            True if reset, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            self._hits = 0
            self._misses = 0
            logger.info(f"Reset cache stats for namespace {self.namespace}")
            return True

    async def close(self) -> None:
        """Close memory cache (cleanup)."""
        if self._initialized:
            async with self._lock:
                self._cache.clear()
                self._initialized = False
                logger.info(f"Memory cache closed (namespace={self.namespace})")
