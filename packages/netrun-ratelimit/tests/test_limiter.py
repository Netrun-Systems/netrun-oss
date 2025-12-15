"""
Tests for RateLimiter class.
"""

import pytest
from netrun_ratelimit import RateLimiter, MemoryBackend


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init_default(self):
        """Test limiter initialization with defaults."""
        limiter = RateLimiter()
        assert limiter.rate == 100
        assert limiter.period == 60
        assert limiter.key_prefix == "ratelimit:"

    def test_init_custom(self):
        """Test limiter initialization with custom values."""
        backend = MemoryBackend()
        limiter = RateLimiter(
            backend=backend,
            rate=50,
            period=30,
            burst=100,
            key_prefix="api:",
        )
        assert limiter.rate == 50
        assert limiter.period == 30
        assert limiter.burst == 100
        assert limiter.key_prefix == "api:"

    def test_check_allowed(self, limiter):
        """Test check when allowed."""
        result = limiter.check("user123")
        assert result.allowed is True
        assert result.remaining == 9

    def test_check_denied(self, limiter):
        """Test check when denied."""
        # Exhaust limit
        for _ in range(10):
            limiter.check("user123")

        result = limiter.check("user123")
        assert result.allowed is False
        assert result.retry_after > 0

    def test_is_allowed(self, limiter):
        """Test is_allowed convenience method."""
        assert limiter.is_allowed("user123") is True

        # Exhaust
        for _ in range(9):
            limiter.check("user123")

        assert limiter.is_allowed("user123") is False

    def test_get_status(self, limiter):
        """Test get_status without consuming."""
        # Consume some
        for _ in range(3):
            limiter.check("user123")

        # Get status (shouldn't consume)
        result = limiter.get_status("user123")
        assert result.remaining == 7

        # Get status again (should be same)
        result = limiter.get_status("user123")
        assert result.remaining == 7

    def test_reset(self, limiter):
        """Test resetting a key."""
        # Exhaust
        for _ in range(10):
            limiter.check("user123")

        # Verify exhausted
        assert limiter.is_allowed("user123") is False

        # Reset
        limiter.reset("user123")

        # Should be allowed
        assert limiter.is_allowed("user123") is True

    def test_key_prefix(self, memory_backend):
        """Test that key prefix is applied."""
        limiter = RateLimiter(
            backend=memory_backend,
            rate=10,
            period=60,
            key_prefix="custom:",
        )

        limiter.check("user123")

        # Check the actual key in backend
        assert "custom:user123" in memory_backend._buckets

    def test_check_with_custom_limits(self, limiter):
        """Test check with per-request limit overrides."""
        # Use stricter limit
        result = limiter.check("user123", rate=5, period=60)
        assert result.limit == 5

        # Exhaust stricter limit
        for _ in range(4):
            limiter.check("user123", rate=5, period=60)

        result = limiter.check("user123", rate=5, period=60)
        assert result.allowed is False

    def test_separate_users(self, limiter):
        """Test that users have separate limits."""
        # Exhaust user1
        for _ in range(10):
            limiter.check("user1")

        # user2 should still be allowed
        result = limiter.check("user2")
        assert result.allowed is True


@pytest.mark.asyncio
class TestRateLimiterAsync:
    """Test async methods of RateLimiter."""

    async def test_acheck(self, limiter):
        """Test async check."""
        result = await limiter.acheck("user123")
        assert result.allowed is True

    async def test_ais_allowed(self, limiter):
        """Test async is_allowed."""
        assert await limiter.ais_allowed("user123") is True

        # Exhaust
        for _ in range(9):
            await limiter.acheck("user123")

        assert await limiter.ais_allowed("user123") is False
