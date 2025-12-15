"""
Tests for token bucket implementation.
"""

import time
import pytest
from netrun_ratelimit import TokenBucket, MemoryBackend
from netrun_ratelimit.bucket import RateLimitResult


class TestTokenBucket:
    """Test TokenBucket class."""

    def test_init_default(self):
        """Test bucket initialization with defaults."""
        bucket = TokenBucket(rate=100, period=60)
        assert bucket.rate == 100
        assert bucket.period == 60
        assert bucket.burst == 100  # defaults to rate

    def test_init_with_burst(self):
        """Test bucket initialization with custom burst."""
        bucket = TokenBucket(rate=100, period=60, burst=200)
        assert bucket.burst == 200

    def test_init_invalid_rate(self):
        """Test bucket rejects invalid rate."""
        with pytest.raises(ValueError, match="rate must be at least 1"):
            TokenBucket(rate=0, period=60)

    def test_init_invalid_period(self):
        """Test bucket rejects invalid period."""
        with pytest.raises(ValueError, match="period must be at least 1"):
            TokenBucket(rate=100, period=0)

    def test_consume_allowed(self, token_bucket):
        """Test consuming tokens when allowed."""
        result = token_bucket.consume("test-key")
        assert result.allowed is True
        assert result.remaining == 9
        assert result.limit == 10

    def test_consume_multiple(self, token_bucket):
        """Test consuming multiple tokens at once."""
        result = token_bucket.consume("test-key", tokens=5)
        assert result.allowed is True
        assert result.remaining == 5

    def test_consume_exhausted(self, token_bucket):
        """Test consuming when bucket exhausted."""
        # Exhaust all tokens
        for _ in range(10):
            token_bucket.consume("test-key")

        # Next request should be denied
        result = token_bucket.consume("test-key")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after > 0

    def test_consume_refill(self, memory_backend):
        """Test token refill over time."""
        bucket = TokenBucket(
            rate=10,
            period=10,  # 1 token per second
            backend=memory_backend,
        )

        # Exhaust tokens at time 0
        now = 1000.0
        for _ in range(10):
            bucket.consume("test-key", now=now)

        # Should be denied at same time
        result = bucket.consume("test-key", now=now)
        assert result.allowed is False

        # Should be allowed after 1 second (1 token refilled)
        result = bucket.consume("test-key", now=now + 1.0)
        assert result.allowed is True

    def test_get_status(self, token_bucket):
        """Test getting status without consuming."""
        # Consume some tokens
        token_bucket.consume("test-key", tokens=3)

        # Get status
        result = token_bucket.get_status("test-key")
        assert result.remaining == 7
        assert result.allowed is True

    def test_reset(self, token_bucket):
        """Test resetting a key."""
        # Consume all tokens
        for _ in range(10):
            token_bucket.consume("test-key")

        # Verify exhausted
        result = token_bucket.consume("test-key")
        assert result.allowed is False

        # Reset
        token_bucket.reset("test-key")

        # Should be allowed again
        result = token_bucket.consume("test-key")
        assert result.allowed is True
        assert result.remaining == 9

    def test_separate_keys(self, token_bucket):
        """Test that different keys have separate buckets."""
        # Exhaust key1
        for _ in range(10):
            token_bucket.consume("key1")

        # key2 should still have tokens
        result = token_bucket.consume("key2")
        assert result.allowed is True


class TestRateLimitResult:
    """Test RateLimitResult class."""

    def test_headers_allowed(self):
        """Test headers when allowed."""
        result = RateLimitResult(
            allowed=True,
            limit=100,
            remaining=50,
            reset_at=1234567890.0,
        )
        headers = result.headers
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "50"
        assert headers["X-RateLimit-Reset"] == "1234567890"
        assert "Retry-After" not in headers

    def test_headers_denied(self):
        """Test headers when denied."""
        result = RateLimitResult(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=1234567890.0,
            retry_after=30.5,
        )
        headers = result.headers
        assert headers["Retry-After"] == "31"  # rounded up
