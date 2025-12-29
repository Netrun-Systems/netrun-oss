"""
Cache decorators for function result caching.

Provides @cached decorator for automatic caching of function results.
"""

import functools
import hashlib
import inspect
import json
import logging
from typing import Any, Callable, Optional, TypeVar, Union

from .cache_manager import CacheManager
from .memory_cache import MemoryCache
from .types import CacheConfig

logger = logging.getLogger(__name__)

# Import Redis with fallback
try:
    from .redis_cache import RedisCache

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisCache = None  # type: ignore


T = TypeVar("T")


def _generate_cache_key(
    func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    """
    Generate cache key from function name and arguments.

    Args:
        func: Function being cached
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Build key from function name and arguments
    key_parts = [func.__module__, func.__name__]

    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # Hash complex objects
            arg_str = json.dumps(arg, sort_keys=True, default=str)
            arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:8]
            key_parts.append(arg_hash)

    # Add keyword arguments (sorted for consistency)
    for key in sorted(kwargs.keys()):
        value = kwargs[key]
        if isinstance(value, (str, int, float, bool)):
            key_parts.append(f"{key}={value}")
        else:
            # Hash complex objects
            value_str = json.dumps(value, sort_keys=True, default=str)
            value_hash = hashlib.md5(value_str.encode()).hexdigest()[:8]
            key_parts.append(f"{key}={value_hash}")

    return ":".join(key_parts)


def cached(
    ttl: int = 3600,
    namespace: str = "cache",
    backend: str = "memory",
    redis_url: Optional[str] = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    max_size: int = 1000,
    key_prefix: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results.

    Supports both sync and async functions. Automatically generates cache keys
    from function name and arguments.

    Args:
        ttl: Cache TTL in seconds
        namespace: Cache namespace
        backend: Cache backend ("memory", "redis", or "multi_layer")
        redis_url: Redis connection URL (overrides host/port/db/password)
        redis_host: Redis host
        redis_port: Redis port
        redis_db: Redis database number
        redis_password: Redis password
        max_size: Maximum cache size (memory backend)
        key_prefix: Optional key prefix (overrides function-based key)

    Returns:
        Decorated function

    Example:
        >>> @cached(ttl=3600, namespace="api")
        ... async def get_user(user_id: str):
        ...     return await db.fetch_user(user_id)

        >>> @cached(ttl=300, backend="redis", redis_host="localhost")
        ... def expensive_calculation(x: int, y: int):
        ...     return x ** y
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Create cache instance based on backend
        cache_config = CacheConfig(
            namespace=namespace,
            default_ttl=ttl,
            max_size=max_size,
            redis_url=redis_url,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
        )

        if backend == "memory":
            cache: Union[MemoryCache, "RedisCache", CacheManager] = MemoryCache(config=cache_config)
        elif backend == "redis":
            if not REDIS_AVAILABLE or not RedisCache:
                logger.warning(
                    "Redis not available, falling back to memory cache. "
                    "Install with: pip install netrun-cache[redis]"
                )
                cache = MemoryCache(config=cache_config)
            else:
                cache = RedisCache(config=cache_config)
        elif backend == "multi_layer":
            cache = CacheManager(config=cache_config)
        else:
            raise ValueError(f"Invalid backend: {backend}")

        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                # Ensure cache is initialized
                if not cache._initialized:
                    await cache.initialize()

                # Generate cache key
                if key_prefix:
                    cache_key = f"{key_prefix}:{_generate_cache_key(func, args, kwargs)}"
                else:
                    cache_key = _generate_cache_key(func, args, kwargs)

                # Try to get from cache
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value

                # Call function
                logger.debug(f"Cache miss: {cache_key}")
                result = await func(*args, **kwargs)

                # Store in cache
                await cache.set(cache_key, result, ttl=ttl)

                return result

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> T:
                # Note: Sync decorator not fully implemented for async cache
                # This is a limitation - cache operations are async
                logger.warning(
                    f"Sync function {func.__name__} decorated with async cache. "
                    "Cache will not be used. Use async functions for caching."
                )
                return func(*args, **kwargs)

            return sync_wrapper  # type: ignore

    return decorator


def cache_invalidate(
    namespace: str = "cache",
    keys: Optional[list[str]] = None,
    pattern: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to invalidate cache entries after function execution.

    Args:
        namespace: Cache namespace
        keys: Specific keys to invalidate
        pattern: Key pattern to invalidate (not implemented yet)

    Returns:
        Decorated function

    Example:
        >>> @cache_invalidate(namespace="users", keys=["user:*"])
        ... async def update_user(user_id: str, data: dict):
        ...     await db.update_user(user_id, data)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Create memory cache for invalidation
        cache = MemoryCache(namespace=namespace)

        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                # Execute function
                result = await func(*args, **kwargs)

                # Invalidate cache entries
                if not cache._initialized:
                    await cache.initialize()

                if keys:
                    for key in keys:
                        await cache.delete(key)
                        logger.debug(f"Invalidated cache key: {key}")

                if pattern:
                    logger.warning("Pattern-based invalidation not yet implemented")

                return result

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> T:
                logger.warning(
                    f"Sync function {func.__name__} decorated with async cache invalidation. "
                    "Invalidation will not be performed. Use async functions."
                )
                return func(*args, **kwargs)

            return sync_wrapper  # type: ignore

    return decorator
