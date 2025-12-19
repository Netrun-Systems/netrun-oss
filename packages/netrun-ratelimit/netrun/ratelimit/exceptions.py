"""
Exceptions for netrun-ratelimit.

Provides a hierarchy of rate limiting exceptions with useful metadata.
"""

from typing import Optional


class RateLimitError(Exception):
    """Base exception for rate limiting errors."""

    def __init__(self, message: str = "Rate limit error"):
        self.message = message
        super().__init__(self.message)


class RateLimitExceeded(RateLimitError):
    """
    Raised when rate limit is exceeded.

    Attributes:
        limit: The configured rate limit.
        remaining: Remaining requests (always 0 when exceeded).
        reset_at: Unix timestamp when the limit resets.
        retry_after: Seconds until the client can retry.
        key: The rate limit key that was exceeded.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        limit: int = 0,
        remaining: int = 0,
        reset_at: float = 0.0,
        retry_after: float = 0.0,
        key: Optional[str] = None,
    ):
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after
        self.key = key
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"RateLimitExceeded(limit={self.limit}, "
            f"retry_after={self.retry_after:.1f}s, key={self.key!r})"
        )

    @property
    def headers(self) -> dict[str, str]:
        """Return rate limit headers for HTTP response."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at)),
            "Retry-After": str(int(self.retry_after) + 1),
        }


class RateLimitBackendError(RateLimitError):
    """
    Raised when the rate limit backend fails.

    This can happen when Redis is unavailable or returns an error.
    Applications may choose to allow requests through when this occurs
    (fail-open) or deny all requests (fail-closed).
    """

    def __init__(
        self,
        message: str = "Rate limit backend error",
        *,
        original_error: Optional[Exception] = None,
    ):
        self.original_error = original_error
        super().__init__(message)

    def __repr__(self) -> str:
        return f"RateLimitBackendError({self.message!r}, original={self.original_error!r})"
