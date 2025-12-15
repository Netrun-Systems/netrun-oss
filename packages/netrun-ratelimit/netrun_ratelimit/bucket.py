"""
Token bucket rate limiting algorithm.

Implements a token bucket that refills at a constant rate,
allowing bursts up to the bucket capacity while maintaining
an average rate limit.
"""

import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netrun_ratelimit.backends import RateLimitBackend


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float
    retry_after: float = 0.0

    @property
    def headers(self) -> dict[str, str]:
        """Return rate limit headers for HTTP response."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if not self.allowed:
            headers["Retry-After"] = str(int(self.retry_after) + 1)
        return headers


class TokenBucket:
    """
    Token bucket rate limiter.

    The bucket starts full and tokens are consumed with each request.
    Tokens refill at a constant rate up to the bucket capacity (burst).

    Args:
        rate: Number of requests allowed per period.
        period: Time period in seconds.
        burst: Maximum bucket capacity (defaults to rate).

    Example:
        # 100 requests per minute with burst of 150
        bucket = TokenBucket(rate=100, period=60, burst=150)

        # Check if request is allowed
        result = bucket.consume("user:123", tokens=1)
        if result.allowed:
            # Process request
            pass
        else:
            # Rate limited, retry after result.retry_after seconds
            pass
    """

    def __init__(
        self,
        rate: int,
        period: int = 60,
        burst: Optional[int] = None,
        backend: Optional["RateLimitBackend"] = None,
    ):
        if rate < 1:
            raise ValueError("rate must be at least 1")
        if period < 1:
            raise ValueError("period must be at least 1")

        self.rate = rate
        self.period = period
        self.burst = burst if burst is not None else rate
        self._backend = backend

        # Calculate refill rate (tokens per second)
        self.refill_rate = rate / period

    @property
    def backend(self) -> "RateLimitBackend":
        """Get the backend, creating a default memory backend if needed."""
        if self._backend is None:
            from netrun_ratelimit.backends import MemoryBackend
            self._backend = MemoryBackend()
        return self._backend

    def consume(
        self,
        key: str,
        tokens: int = 1,
        now: Optional[float] = None,
    ) -> RateLimitResult:
        """
        Attempt to consume tokens from the bucket.

        Args:
            key: Unique identifier for the rate limit (e.g., user ID, IP).
            tokens: Number of tokens to consume.
            now: Current timestamp (defaults to time.time()).

        Returns:
            RateLimitResult with allowed status and rate limit info.
        """
        if now is None:
            now = time.time()

        return self.backend.consume(
            key=key,
            tokens=tokens,
            rate=self.rate,
            period=self.period,
            burst=self.burst,
            now=now,
        )

    def get_status(
        self,
        key: str,
        now: Optional[float] = None,
    ) -> RateLimitResult:
        """
        Get current rate limit status without consuming tokens.

        Args:
            key: Unique identifier for the rate limit.
            now: Current timestamp (defaults to time.time()).

        Returns:
            RateLimitResult with current status.
        """
        if now is None:
            now = time.time()

        return self.backend.get_status(
            key=key,
            rate=self.rate,
            period=self.period,
            burst=self.burst,
            now=now,
        )

    def reset(self, key: str) -> None:
        """
        Reset the rate limit for a key.

        Args:
            key: Unique identifier to reset.
        """
        self.backend.reset(key)


class RateLimiter:
    """
    High-level rate limiter with multiple limit tiers.

    Provides a convenient interface for rate limiting with support
    for per-user, per-endpoint, and global limits.

    Args:
        backend: Storage backend for rate limit state.
        rate: Default requests per period.
        period: Default time period in seconds.
        burst: Default burst capacity.
        key_prefix: Prefix for all rate limit keys.

    Example:
        from netrun_ratelimit import RateLimiter, RedisBackend

        # Create limiter with Redis backend
        backend = RedisBackend(redis_url="redis://localhost:6379")
        limiter = RateLimiter(backend=backend, rate=100, period=60)

        # Check rate limit
        result = limiter.check("user:123")
        if not result.allowed:
            raise HTTPException(429, headers=result.headers)
    """

    def __init__(
        self,
        backend: Optional["RateLimitBackend"] = None,
        rate: int = 100,
        period: int = 60,
        burst: Optional[int] = None,
        key_prefix: str = "ratelimit:",
    ):
        self.rate = rate
        self.period = period
        self.burst = burst if burst is not None else rate
        self.key_prefix = key_prefix
        self._backend = backend

        # Default bucket using configured settings
        self._default_bucket = TokenBucket(
            rate=rate,
            period=period,
            burst=self.burst,
            backend=self._backend,
        )

    @property
    def backend(self) -> "RateLimitBackend":
        """Get the backend, creating a default memory backend if needed."""
        if self._backend is None:
            from netrun_ratelimit.backends import MemoryBackend
            self._backend = MemoryBackend()
            self._default_bucket._backend = self._backend
        return self._backend

    def _make_key(self, key: str) -> str:
        """Create a prefixed key."""
        return f"{self.key_prefix}{key}"

    def check(
        self,
        key: str,
        tokens: int = 1,
        rate: Optional[int] = None,
        period: Optional[int] = None,
        burst: Optional[int] = None,
    ) -> RateLimitResult:
        """
        Check and consume rate limit tokens.

        Args:
            key: Unique identifier (user ID, IP, etc.).
            tokens: Number of tokens to consume.
            rate: Override default rate for this check.
            period: Override default period for this check.
            burst: Override default burst for this check.

        Returns:
            RateLimitResult with allowed status and headers.
        """
        full_key = self._make_key(key)

        # Use custom limits if provided
        if rate is not None or period is not None or burst is not None:
            bucket = TokenBucket(
                rate=rate or self.rate,
                period=period or self.period,
                burst=burst or self.burst,
                backend=self.backend,
            )
            return bucket.consume(full_key, tokens=tokens)

        return self._default_bucket.consume(full_key, tokens=tokens)

    def is_allowed(self, key: str, tokens: int = 1) -> bool:
        """
        Simple check if request is allowed.

        Args:
            key: Unique identifier.
            tokens: Number of tokens to consume.

        Returns:
            True if allowed, False if rate limited.
        """
        return self.check(key, tokens=tokens).allowed

    def get_status(self, key: str) -> RateLimitResult:
        """
        Get current rate limit status without consuming tokens.

        Args:
            key: Unique identifier.

        Returns:
            RateLimitResult with current status.
        """
        full_key = self._make_key(key)
        return self._default_bucket.get_status(full_key)

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Unique identifier to reset.
        """
        full_key = self._make_key(key)
        self._default_bucket.reset(full_key)

    async def acheck(
        self,
        key: str,
        tokens: int = 1,
        rate: Optional[int] = None,
        period: Optional[int] = None,
        burst: Optional[int] = None,
    ) -> RateLimitResult:
        """
        Async version of check for use with async backends.

        Args:
            key: Unique identifier.
            tokens: Number of tokens to consume.
            rate: Override default rate.
            period: Override default period.
            burst: Override default burst.

        Returns:
            RateLimitResult with allowed status.
        """
        full_key = self._make_key(key)

        effective_rate = rate or self.rate
        effective_period = period or self.period
        effective_burst = burst or self.burst

        return await self.backend.aconsume(
            key=full_key,
            tokens=tokens,
            rate=effective_rate,
            period=effective_period,
            burst=effective_burst,
            now=time.time(),
        )

    async def ais_allowed(self, key: str, tokens: int = 1) -> bool:
        """Async version of is_allowed."""
        result = await self.acheck(key, tokens=tokens)
        return result.allowed
