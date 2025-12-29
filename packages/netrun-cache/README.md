# netrun-cache

Redis and in-memory caching patterns for Netrun Systems portfolio.

## Features

- **RedisCache**: Distributed Redis caching with namespace isolation, TTL management, and statistics
- **MemoryCache**: In-memory LRU cache with TTL support (fallback when Redis unavailable)
- **CacheManager**: Multi-layer cache with L1 (memory) and L2 (Redis) tiers
- **Decorators**: `@cached` for automatic function result caching
- **Type Safety**: Pydantic v2 models for configuration and statistics
- **Optional Dependencies**: Redis support is optional, works with memory cache only

## Installation

### Basic (memory cache only)
```bash
pip install netrun-cache
```

### With Redis support
```bash
pip install netrun-cache[redis]
```

### All features
```bash
pip install netrun-cache[all]
```

## Quick Start

### Memory Cache (No Redis Required)

```python
from netrun.cache import MemoryCache

# Create cache instance
cache = MemoryCache(namespace="users", default_ttl=3600, max_size=1000)
await cache.initialize()

# Basic operations
await cache.set("user:123", {"name": "John", "email": "john@example.com"})
user = await cache.get("user:123")
await cache.delete("user:123")

# Batch operations
users = {"user:1": {"name": "Alice"}, "user:2": {"name": "Bob"}}
await cache.set_many(users, ttl=1800)
cached_users = await cache.get_many(["user:1", "user:2"])

# Atomic counters
await cache.increment("page_views")
await cache.decrement("inventory:item_123")

# Statistics
stats = await cache.get_stats()
print(f"Hit rate: {stats.hit_rate_percent}%")
print(f"Cached keys: {stats.cached_keys}")
```

### Redis Cache

```python
from netrun.cache import RedisCache, CacheConfig

# Using configuration object
config = CacheConfig(
    namespace="api",
    default_ttl=3600,
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    redis_password="your_password"
)

cache = RedisCache(config=config)
await cache.initialize()

# Or simple initialization
cache = RedisCache(namespace="api", default_ttl=3600)
await cache.initialize()

# Same interface as MemoryCache
await cache.set("product:456", {"name": "Widget", "price": 29.99})
product = await cache.get("product:456")

# Complex key hashing
prompt = "What is the capital of France?"
key = cache._hash_key(prompt)
await cache.set(key, "Paris")

# Clear namespace
await cache.clear_namespace()
```

### Multi-Layer Cache

```python
from netrun.cache import CacheManager, CacheConfig

# L1 (memory) + L2 (Redis) caching
config = CacheConfig(
    namespace="api",
    default_ttl=3600,      # L2 (Redis) TTL
    l1_max_size=100,       # L1 cache size
    l1_ttl=300,            # L1 TTL (5 minutes)
    redis_host="localhost"
)

cache = CacheManager(config)
await cache.initialize()

# Automatically checks L1, then L2
user = await cache.get("user:789")

# Write-through to both layers
await cache.set("user:789", {"name": "Charlie"})

# Get statistics for both layers
stats = await cache.get_stats()
print(f"L1 hit rate: {stats['l1'].hit_rate_percent}%")
print(f"L2 hit rate: {stats['l2'].hit_rate_percent}%")
```

### Decorator Pattern

```python
from netrun.cache import cached

# Cache function results (memory backend)
@cached(ttl=3600, namespace="api", backend="memory")
async def get_user(user_id: str):
    # Expensive database operation
    return await db.fetch_user(user_id)

# Cache with Redis backend
@cached(ttl=1800, namespace="products", backend="redis", redis_host="localhost")
async def get_product(product_id: str):
    return await db.fetch_product(product_id)

# Multi-layer caching
@cached(ttl=3600, namespace="search", backend="multi_layer")
async def search_items(query: str, limit: int = 10):
    return await search_engine.query(query, limit)

# Use decorated functions normally
user = await get_user("123")  # Cache miss, fetches from DB
user = await get_user("123")  # Cache hit, returns cached value
```

## Configuration

### CacheConfig Model

```python
from netrun.cache import CacheConfig, CacheBackend

config = CacheConfig(
    backend=CacheBackend.MULTI_LAYER,
    namespace="cache",
    default_ttl=3600,
    max_size=1000,

    # Redis configuration
    redis_url="redis://:password@localhost:6379/0",  # Or individual params
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    redis_password="secret",
    socket_timeout=5,
    socket_connect_timeout=5,

    # Multi-layer configuration
    l1_max_size=100,
    l1_ttl=300,
)
```

### CacheStats Model

```python
stats = await cache.get_stats()

print(f"Namespace: {stats.namespace}")
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Total requests: {stats.total_requests}")
print(f"Hit rate: {stats.hit_rate_percent}%")
print(f"Cached keys: {stats.cached_keys}")
print(f"Backend: {stats.backend}")
print(f"Connected: {stats.connected}")
```

## Advanced Usage

### Namespace Isolation

```python
# Create isolated cache namespaces
user_cache = MemoryCache(namespace="users")
product_cache = MemoryCache(namespace="products")

# Keys don't conflict
await user_cache.set("123", {"name": "Alice"})
await product_cache.set("123", {"name": "Widget"})

# Clear specific namespace
await user_cache.clear_namespace()  # Only clears user_cache
```

### Key Hashing for Complex Data

```python
from netrun.cache import RedisCache

cache = RedisCache(namespace="llm")

# Hash complex prompts for consistent keys
prompt = {
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7
}

key = cache._hash_key(prompt)  # SHA256 hash
await cache.set(key, "AI response here")
```

### SET NX (Set if Not Exists)

```python
# Distributed locking pattern
acquired = await cache.set("lock:resource_123", "locked", ttl=30, nx=True)

if acquired:
    try:
        # Critical section
        await process_resource()
    finally:
        await cache.delete("lock:resource_123")
```

### Graceful Shutdown

```python
# Close connections properly
await cache.close()
```

## API Reference

### MemoryCache

- `initialize()` - Initialize cache
- `get(key, track_stats=True)` - Get value
- `set(key, value, ttl=None, nx=False)` - Set value
- `delete(key)` - Delete key
- `exists(key)` - Check if key exists
- `expire(key, ttl)` - Update TTL
- `get_many(keys)` - Batch get
- `set_many(items, ttl=None)` - Batch set
- `increment(key, amount=1)` - Atomic increment
- `decrement(key, amount=1)` - Atomic decrement
- `clear_namespace()` - Clear all keys in namespace
- `get_stats()` - Get statistics
- `reset_stats()` - Reset statistics
- `close()` - Close cache

### RedisCache

Same API as MemoryCache, plus:
- `_hash_key(data)` - Generate SHA256 hash for complex keys

### CacheManager

Same API as MemoryCache/RedisCache with multi-layer behavior.

## Performance Characteristics

### MemoryCache
- **Get**: O(1) - OrderedDict lookup
- **Set**: O(1) - OrderedDict insert with LRU eviction
- **Memory**: Up to `max_size` items in RAM
- **Concurrency**: Thread-safe with asyncio locks

### RedisCache
- **Get**: O(1) - Redis GET
- **Set**: O(1) - Redis SETEX
- **Network**: Single round-trip per operation
- **Batch**: Pipeline reduces network overhead
- **Scalability**: Distributed across Redis cluster

### CacheManager
- **Get**: L1 hit = O(1), L1 miss + L2 hit = O(1) + network
- **Set**: Write-through to both layers
- **Hit Rate**: Typically 80-95% L1, 99%+ combined

## Development

### Running Tests

```bash
cd /data/workspace/github/Netrun_Service_Library_v2/packages/netrun-cache

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=netrun.cache --cov-report=term-missing
```

### Test Requirements

- Unit tests work without Redis (use MemoryCache or fakeredis)
- Integration tests require Redis server running
- Use `@pytest.mark.integration` for Redis-dependent tests

## License

MIT License - Copyright (c) 2025 Netrun Systems

## Links

- **Homepage**: https://netrunsystems.com
- **Documentation**: https://docs.netrunsystems.com/cache
- **Repository**: https://github.com/netrunsystems/netrun-cache
- **Issues**: https://github.com/netrunsystems/netrun-cache/issues
