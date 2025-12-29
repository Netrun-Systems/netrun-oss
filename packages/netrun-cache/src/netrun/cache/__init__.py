"""
netrun-cache - Redis and in-memory caching patterns for Netrun Systems portfolio.

Provides:
- RedisCache: Distributed Redis caching
- MemoryCache: In-memory LRU cache with TTL
- CacheManager: Multi-layer cache (L1: memory, L2: Redis)
- @cached: Decorator for function result caching
- CacheConfig: Configuration model
- CacheStats: Statistics model
"""

from .memory_cache import MemoryCache
from .types import CacheBackend, CacheConfig, CacheStats

# Conditionally import Redis-dependent components
try:
    from .redis_cache import RedisCache

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisCache = None  # type: ignore

# Import cache manager (handles Redis fallback internally)
from .cache_manager import CacheManager

# Import decorators
from .decorators import cache_invalidate, cached

__version__ = "1.0.0"

__all__ = [
    # Core classes
    "MemoryCache",
    "RedisCache",
    "CacheManager",
    # Decorators
    "cached",
    "cache_invalidate",
    # Types
    "CacheConfig",
    "CacheStats",
    "CacheBackend",
    # Constants
    "REDIS_AVAILABLE",
]
