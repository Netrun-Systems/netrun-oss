"""
netrun.ratelimit: Distributed rate limiting with token bucket algorithm.

This package provides:
- Token bucket rate limiting algorithm
- Redis backend for distributed systems
- In-memory backend for single-instance applications
- FastAPI middleware integration
- Route decorators for fine-grained control
- Per-user and per-endpoint rate limits

Example:
    from fastapi import FastAPI
    from netrun.ratelimit import RateLimiter, RedisBackend, RateLimitMiddleware

    app = FastAPI()

    # Create rate limiter with Redis backend
    backend = RedisBackend(redis_url="redis://localhost:6379")
    limiter = RateLimiter(backend=backend, rate=100, period=60)

    # Add middleware
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
"""

from netrun.ratelimit.bucket import TokenBucket, RateLimiter
from netrun.ratelimit.backends import (
    RateLimitBackend,
    MemoryBackend,
    RedisBackend,
)
from netrun.ratelimit.config import RateLimitConfig
from netrun.ratelimit.exceptions import (
    RateLimitError,
    RateLimitExceeded,
    RateLimitBackendError,
)

__version__ = "2.0.0"
__author__ = "Daniel Garza"
__email__ = "daniel@netrunsystems.com"

__all__ = [
    # Core
    "TokenBucket",
    "RateLimiter",
    # Backends
    "RateLimitBackend",
    "MemoryBackend",
    "RedisBackend",
    # Config
    "RateLimitConfig",
    # Exceptions
    "RateLimitError",
    "RateLimitExceeded",
    "RateLimitBackendError",
    # Version
    "__version__",
]

# Lazy imports for optional dependencies
def __getattr__(name: str):
    """Lazy import for optional FastAPI components."""
    if name == "RateLimitMiddleware":
        from netrun.ratelimit.middleware import RateLimitMiddleware
        return RateLimitMiddleware
    if name == "rate_limit":
        from netrun.ratelimit.decorators import rate_limit
        return rate_limit
    if name == "RateLimitRoute":
        from netrun.ratelimit.decorators import RateLimitRoute
        return RateLimitRoute
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
