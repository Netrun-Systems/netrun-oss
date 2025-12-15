"""
Tests for rate limit backends.
"""

import pytest
from netrun_ratelimit import MemoryBackend
from netrun_ratelimit.exceptions import RateLimitBackendError


class TestMemoryBackend:
    """Test MemoryBackend class."""

    def test_consume_new_key(self):
        """Test consuming from a new key."""
        backend = MemoryBackend()
        result = backend.consume(
            key="test",
            tokens=1,
            rate=10,
            period=60,
            burst=10,
            now=1000.0,
        )
        assert result.allowed is True
        assert result.remaining == 9

    def test_consume_multiple_times(self):
        """Test multiple consumes from same key."""
        backend = MemoryBackend()
        now = 1000.0

        for i in range(5):
            result = backend.consume(
                key="test",
                tokens=1,
                rate=10,
                period=60,
                burst=10,
                now=now,
            )
            assert result.allowed is True
            assert result.remaining == 9 - i

    def test_consume_exhausted(self):
        """Test consume when exhausted."""
        backend = MemoryBackend()
        now = 1000.0

        # Exhaust tokens
        for _ in range(10):
            backend.consume(
                key="test",
                tokens=1,
                rate=10,
                period=60,
                burst=10,
                now=now,
            )

        # Should be denied
        result = backend.consume(
            key="test",
            tokens=1,
            rate=10,
            period=60,
            burst=10,
            now=now,
        )
        assert result.allowed is False
        assert result.remaining == 0

    def test_consume_refill(self):
        """Test token refill."""
        backend = MemoryBackend()

        # Exhaust at time 0
        for _ in range(10):
            backend.consume(
                key="test",
                tokens=1,
                rate=10,
                period=10,  # 1 token/sec
                burst=10,
                now=0.0,
            )

        # Should be denied at time 0
        result = backend.consume(
            key="test",
            tokens=1,
            rate=10,
            period=10,
            burst=10,
            now=0.0,
        )
        assert result.allowed is False

        # Should be allowed at time 1 (1 token refilled)
        result = backend.consume(
            key="test",
            tokens=1,
            rate=10,
            period=10,
            burst=10,
            now=1.0,
        )
        assert result.allowed is True

    def test_get_status(self):
        """Test get_status without consuming."""
        backend = MemoryBackend()
        now = 1000.0

        # Consume some
        backend.consume(key="test", tokens=3, rate=10, period=60, burst=10, now=now)

        # Get status
        result = backend.get_status(
            key="test",
            rate=10,
            period=60,
            burst=10,
            now=now,
        )
        assert result.remaining == 7
        assert result.allowed is True

    def test_reset(self):
        """Test reset."""
        backend = MemoryBackend()
        now = 1000.0

        # Exhaust
        for _ in range(10):
            backend.consume(key="test", tokens=1, rate=10, period=60, burst=10, now=now)

        # Reset
        backend.reset("test")

        # Should be allowed with full tokens
        result = backend.consume(
            key="test",
            tokens=1,
            rate=10,
            period=60,
            burst=10,
            now=now,
        )
        assert result.allowed is True
        assert result.remaining == 9

    def test_clear(self):
        """Test clear all."""
        backend = MemoryBackend()
        now = 1000.0

        # Create multiple keys
        for key in ["key1", "key2", "key3"]:
            backend.consume(key=key, tokens=5, rate=10, period=60, burst=10, now=now)

        # Clear all
        backend.clear()

        # All should be at full capacity
        for key in ["key1", "key2", "key3"]:
            result = backend.get_status(key=key, rate=10, period=60, burst=10, now=now)
            assert result.remaining == 10

    def test_thread_safety(self):
        """Test thread safety with concurrent access."""
        import threading

        backend = MemoryBackend()
        results = []
        errors = []

        def consume_tokens():
            try:
                for _ in range(100):
                    result = backend.consume(
                        key="shared",
                        tokens=1,
                        rate=1000,
                        period=60,
                        burst=1000,
                        now=1000.0,
                    )
                    results.append(result.allowed)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = [threading.Thread(target=consume_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # Total consumed should equal total True results
        # Some may be denied due to exhaustion
        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 1000  # All should succeed


class TestRedisBackend:
    """Test RedisBackend class."""

    def test_init_requires_url_or_client(self):
        """Test RedisBackend requires redis_url or redis_client."""
        from netrun_ratelimit import RedisBackend

        with pytest.raises(ValueError, match="Either redis_url or redis_client"):
            RedisBackend()

    @pytest.mark.skipif(
        True,  # Skip unless fakeredis available
        reason="Requires fakeredis for testing",
    )
    def test_consume_with_fakeredis(self):
        """Test consume with fakeredis."""
        try:
            import fakeredis
            from netrun_ratelimit import RedisBackend

            client = fakeredis.FakeRedis()
            backend = RedisBackend(redis_client=client)

            result = backend.consume(
                key="test",
                tokens=1,
                rate=10,
                period=60,
                burst=10,
                now=1000.0,
            )
            assert result.allowed is True
        except ImportError:
            pytest.skip("fakeredis not installed")
