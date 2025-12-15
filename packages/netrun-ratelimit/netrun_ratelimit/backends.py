"""
Rate limit storage backends.

Provides memory and Redis backends for storing rate limit state.
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

from netrun_ratelimit.bucket import RateLimitResult
from netrun_ratelimit.exceptions import RateLimitBackendError


@dataclass
class BucketState:
    """Internal state of a token bucket."""
    tokens: float
    last_update: float


class RateLimitBackend(ABC):
    """
    Abstract base class for rate limit backends.

    Backends are responsible for storing and updating token bucket state.
    They must handle concurrent access safely.
    """

    @abstractmethod
    def consume(
        self,
        key: str,
        tokens: int,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """
        Consume tokens from the bucket.

        Args:
            key: Unique identifier for the rate limit.
            tokens: Number of tokens to consume.
            rate: Requests allowed per period.
            period: Time period in seconds.
            burst: Maximum bucket capacity.
            now: Current timestamp.

        Returns:
            RateLimitResult with allowed status.
        """
        pass

    @abstractmethod
    def get_status(
        self,
        key: str,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """
        Get current status without consuming tokens.

        Args:
            key: Unique identifier for the rate limit.
            rate: Requests allowed per period.
            period: Time period in seconds.
            burst: Maximum bucket capacity.
            now: Current timestamp.

        Returns:
            RateLimitResult with current status.
        """
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """
        Reset the rate limit for a key.

        Args:
            key: Unique identifier to reset.
        """
        pass

    async def aconsume(
        self,
        key: str,
        tokens: int,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """
        Async version of consume (default implementation calls sync version).

        Override in async-native backends like Redis.
        """
        return self.consume(key, tokens, rate, period, burst, now)

    async def aget_status(
        self,
        key: str,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """Async version of get_status."""
        return self.get_status(key, rate, period, burst, now)

    async def areset(self, key: str) -> None:
        """Async version of reset."""
        self.reset(key)


class MemoryBackend(RateLimitBackend):
    """
    In-memory rate limit backend.

    Suitable for single-instance applications. Not shared across processes.
    Uses threading lock for thread safety.

    Example:
        backend = MemoryBackend()
        limiter = RateLimiter(backend=backend, rate=100, period=60)
    """

    def __init__(self) -> None:
        self._buckets: Dict[str, BucketState] = {}
        self._lock = threading.Lock()

    def _get_bucket(
        self,
        key: str,
        burst: int,
        now: float,
    ) -> BucketState:
        """Get or create bucket state."""
        if key not in self._buckets:
            self._buckets[key] = BucketState(tokens=float(burst), last_update=now)
        return self._buckets[key]

    def _refill(
        self,
        bucket: BucketState,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> None:
        """Refill tokens based on elapsed time."""
        elapsed = now - bucket.last_update
        refill_rate = rate / period
        new_tokens = bucket.tokens + (elapsed * refill_rate)
        bucket.tokens = min(new_tokens, float(burst))
        bucket.last_update = now

    def consume(
        self,
        key: str,
        tokens: int,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """Consume tokens from the bucket."""
        with self._lock:
            bucket = self._get_bucket(key, burst, now)
            self._refill(bucket, rate, period, burst, now)

            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                return RateLimitResult(
                    allowed=True,
                    limit=rate,
                    remaining=int(bucket.tokens),
                    reset_at=now + period,
                )
            else:
                # Calculate when tokens will be available
                tokens_needed = tokens - bucket.tokens
                refill_rate = rate / period
                retry_after = tokens_needed / refill_rate if refill_rate > 0 else period

                return RateLimitResult(
                    allowed=False,
                    limit=rate,
                    remaining=0,
                    reset_at=now + period,
                    retry_after=retry_after,
                )

    def get_status(
        self,
        key: str,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """Get current status without consuming."""
        with self._lock:
            bucket = self._get_bucket(key, burst, now)
            self._refill(bucket, rate, period, burst, now)

            return RateLimitResult(
                allowed=bucket.tokens >= 1,
                limit=rate,
                remaining=int(bucket.tokens),
                reset_at=now + period,
            )

    def reset(self, key: str) -> None:
        """Reset a key by removing it."""
        with self._lock:
            self._buckets.pop(key, None)

    def clear(self) -> None:
        """Clear all rate limit state."""
        with self._lock:
            self._buckets.clear()


class RedisBackend(RateLimitBackend):
    """
    Redis-based rate limit backend.

    Uses Lua scripting for atomic operations. Suitable for distributed
    applications where rate limits must be shared across instances.

    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379").
        redis_client: Existing Redis client (alternative to redis_url).
        key_prefix: Prefix for Redis keys (default: "ratelimit:").

    Example:
        backend = RedisBackend(redis_url="redis://localhost:6379")
        limiter = RateLimiter(backend=backend, rate=100, period=60)

        # Or with existing client
        import redis
        client = redis.Redis.from_url("redis://localhost:6379")
        backend = RedisBackend(redis_client=client)
    """

    # Lua script for atomic token bucket operations
    LUA_CONSUME = """
    local key = KEYS[1]
    local tokens_requested = tonumber(ARGV[1])
    local rate = tonumber(ARGV[2])
    local period = tonumber(ARGV[3])
    local burst = tonumber(ARGV[4])
    local now = tonumber(ARGV[5])

    -- Get current state
    local data = redis.call('HMGET', key, 'tokens', 'last_update')
    local current_tokens = tonumber(data[1])
    local last_update = tonumber(data[2])

    -- Initialize if new
    if current_tokens == nil then
        current_tokens = burst
        last_update = now
    end

    -- Calculate refill
    local elapsed = now - last_update
    local refill_rate = rate / period
    local new_tokens = math.min(current_tokens + (elapsed * refill_rate), burst)

    local allowed = 0
    local remaining = 0
    local retry_after = 0

    if new_tokens >= tokens_requested then
        -- Allow and consume
        new_tokens = new_tokens - tokens_requested
        allowed = 1
        remaining = math.floor(new_tokens)
    else
        -- Deny and calculate retry
        remaining = 0
        local tokens_needed = tokens_requested - new_tokens
        retry_after = tokens_needed / refill_rate
    end

    -- Update state with TTL
    redis.call('HMSET', key, 'tokens', new_tokens, 'last_update', now)
    redis.call('EXPIRE', key, period * 2)

    return {allowed, remaining, retry_after}
    """

    LUA_STATUS = """
    local key = KEYS[1]
    local rate = tonumber(ARGV[1])
    local period = tonumber(ARGV[2])
    local burst = tonumber(ARGV[3])
    local now = tonumber(ARGV[4])

    local data = redis.call('HMGET', key, 'tokens', 'last_update')
    local current_tokens = tonumber(data[1])
    local last_update = tonumber(data[2])

    if current_tokens == nil then
        return {burst, 1}
    end

    local elapsed = now - last_update
    local refill_rate = rate / period
    local new_tokens = math.min(current_tokens + (elapsed * refill_rate), burst)

    return {math.floor(new_tokens), new_tokens >= 1 and 1 or 0}
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[Any] = None,
        key_prefix: str = "ratelimit:",
    ) -> None:
        if redis_client is None and redis_url is None:
            raise ValueError("Either redis_url or redis_client must be provided")

        self.key_prefix = key_prefix
        self._client = redis_client
        self._redis_url = redis_url
        self._consume_script: Optional[Any] = None
        self._status_script: Optional[Any] = None

    @property
    def client(self) -> Any:
        """Lazy load Redis client."""
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis.from_url(self._redis_url)
            except ImportError:
                raise ImportError(
                    "redis package is required for RedisBackend. "
                    "Install with: pip install netrun-ratelimit[redis]"
                )
        return self._client

    def _get_scripts(self) -> tuple[Any, Any]:
        """Get or register Lua scripts."""
        if self._consume_script is None:
            self._consume_script = self.client.register_script(self.LUA_CONSUME)
            self._status_script = self.client.register_script(self.LUA_STATUS)
        return self._consume_script, self._status_script

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    def consume(
        self,
        key: str,
        tokens: int,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """Consume tokens using Redis Lua script."""
        try:
            consume_script, _ = self._get_scripts()
            redis_key = self._make_key(key)

            result = consume_script(
                keys=[redis_key],
                args=[tokens, rate, period, burst, now],
            )

            allowed = bool(result[0])
            remaining = int(result[1])
            retry_after = float(result[2])

            return RateLimitResult(
                allowed=allowed,
                limit=rate,
                remaining=remaining,
                reset_at=now + period,
                retry_after=retry_after,
            )
        except Exception as e:
            raise RateLimitBackendError(
                f"Redis error during consume: {e}",
                original_error=e,
            )

    def get_status(
        self,
        key: str,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """Get status using Redis Lua script."""
        try:
            _, status_script = self._get_scripts()
            redis_key = self._make_key(key)

            result = status_script(
                keys=[redis_key],
                args=[rate, period, burst, now],
            )

            remaining = int(result[0])
            allowed = bool(result[1])

            return RateLimitResult(
                allowed=allowed,
                limit=rate,
                remaining=remaining,
                reset_at=now + period,
            )
        except Exception as e:
            raise RateLimitBackendError(
                f"Redis error during status check: {e}",
                original_error=e,
            )

    def reset(self, key: str) -> None:
        """Delete the rate limit key."""
        try:
            redis_key = self._make_key(key)
            self.client.delete(redis_key)
        except Exception as e:
            raise RateLimitBackendError(
                f"Redis error during reset: {e}",
                original_error=e,
            )

    async def aconsume(
        self,
        key: str,
        tokens: int,
        rate: int,
        period: int,
        burst: int,
        now: float,
    ) -> RateLimitResult:
        """Async consume using aioredis-compatible client."""
        try:
            redis_key = self._make_key(key)

            # Check if we have an async client
            if hasattr(self.client, 'evalsha'):
                # Use async Redis client
                result = await self.client.evalsha(
                    self._consume_script.sha if self._consume_script else "",
                    1,
                    redis_key,
                    tokens, rate, period, burst, now,
                )
            else:
                # Fall back to sync
                return self.consume(key, tokens, rate, period, burst, now)

            allowed = bool(result[0])
            remaining = int(result[1])
            retry_after = float(result[2])

            return RateLimitResult(
                allowed=allowed,
                limit=rate,
                remaining=remaining,
                reset_at=now + period,
                retry_after=retry_after,
            )
        except Exception as e:
            raise RateLimitBackendError(
                f"Redis async error during consume: {e}",
                original_error=e,
            )

    def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            self._client.close()
