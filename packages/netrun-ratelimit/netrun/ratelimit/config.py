"""
Configuration for netrun-ratelimit.

Provides Pydantic-based configuration with sensible defaults.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class RateLimitConfig(BaseSettings):
    """
    Rate limiting configuration.

    Attributes:
        rate: Number of requests allowed per period.
        period: Time period in seconds.
        burst: Maximum burst size (defaults to rate).
        key_prefix: Prefix for Redis keys.
        redis_url: Redis connection URL.
        block_duration: How long to block after limit exceeded (seconds).
        include_headers: Whether to include rate limit headers in responses.
    """

    rate: int = Field(
        default=100,
        ge=1,
        description="Number of requests allowed per period"
    )
    period: int = Field(
        default=60,
        ge=1,
        description="Time period in seconds"
    )
    burst: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum burst size (defaults to rate if not set)"
    )
    key_prefix: str = Field(
        default="ratelimit:",
        description="Prefix for rate limit keys"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL (e.g., redis://localhost:6379)"
    )
    block_duration: int = Field(
        default=0,
        ge=0,
        description="Additional block duration after limit exceeded (seconds)"
    )
    include_headers: bool = Field(
        default=True,
        description="Include X-RateLimit-* headers in responses"
    )

    # Header names (customizable)
    header_limit: str = Field(
        default="X-RateLimit-Limit",
        description="Header name for rate limit"
    )
    header_remaining: str = Field(
        default="X-RateLimit-Remaining",
        description="Header name for remaining requests"
    )
    header_reset: str = Field(
        default="X-RateLimit-Reset",
        description="Header name for reset timestamp"
    )
    header_retry_after: str = Field(
        default="Retry-After",
        description="Header name for retry after (seconds)"
    )

    model_config = {
        "env_prefix": "RATELIMIT_",
        "case_sensitive": False,
    }

    @property
    def effective_burst(self) -> int:
        """Get effective burst size (defaults to rate if not set)."""
        return self.burst if self.burst is not None else self.rate

    @property
    def refill_rate(self) -> float:
        """Calculate token refill rate (tokens per second)."""
        return self.rate / self.period
