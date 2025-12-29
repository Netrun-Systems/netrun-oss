"""Tests for retry decorator."""

import asyncio
import pytest
from netrun.resilience import retry, RetryExhausted


class TestRetry:
    """Test retry decorator with sync and async functions."""

    def test_retry_sync_success(self):
        """Test successful execution without retries."""
        call_count = [0]

        @retry(max_attempts=3)
        def successful_func():
            call_count[0] += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count[0] == 1

    async def test_retry_async_success(self):
        """Test successful async execution without retries."""
        call_count = [0]

        @retry(max_attempts=3)
        async def successful_func():
            call_count[0] += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_sync_with_retries(self):
        """Test retry on failure then success."""
        call_count = [0]

        @retry(max_attempts=3, base_delay_ms=10)
        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count[0] == 3

    async def test_retry_async_with_retries(self):
        """Test async retry on failure then success."""
        call_count = [0]

        @retry(max_attempts=3, base_delay_ms=10)
        async def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count[0] == 3

    def test_retry_exhausted_sync(self):
        """Test retry exhaustion for sync function."""
        call_count = [0]

        @retry(max_attempts=3, base_delay_ms=10)
        def always_fails():
            call_count[0] += 1
            raise ConnectionError("Permanent failure")

        with pytest.raises(RetryExhausted) as exc_info:
            always_fails()

        assert call_count[0] == 3
        assert "Failed after 3 attempts" in str(exc_info.value)

    async def test_retry_exhausted_async(self):
        """Test retry exhaustion for async function."""
        call_count = [0]

        @retry(max_attempts=3, base_delay_ms=10)
        async def always_fails():
            call_count[0] += 1
            raise ConnectionError("Permanent failure")

        with pytest.raises(RetryExhausted) as exc_info:
            await always_fails()

        assert call_count[0] == 3
        assert "Failed after 3 attempts" in str(exc_info.value)

    def test_retry_exception_filtering(self):
        """Test that only specified exceptions are retried."""
        call_count = [0]

        @retry(max_attempts=3, base_delay_ms=10, exceptions=(ConnectionError,))
        def selective_retry():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Retry this")
            raise ValueError("Don't retry this")

        with pytest.raises(ValueError):
            selective_retry()

        assert call_count[0] == 2  # Initial + 1 retry, then ValueError

    def test_retry_backoff_timing(self):
        """Test exponential backoff timing."""
        import time
        call_times = []

        @retry(max_attempts=3, base_delay_ms=100, backoff_multiplier=2.0, jitter=False)
        def timed_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Retry")
            return "success"

        result = timed_func()
        assert result == "success"
        assert len(call_times) == 3

        # Check delays: ~100ms, ~200ms
        delay1 = (call_times[1] - call_times[0]) * 1000
        delay2 = (call_times[2] - call_times[1]) * 1000

        assert 80 < delay1 < 150  # ~100ms ± tolerance
        assert 180 < delay2 < 250  # ~200ms ± tolerance

    def test_retry_max_delay(self):
        """Test max delay cap."""
        call_count = [0]

        @retry(
            max_attempts=5,
            base_delay_ms=1000,
            max_delay_ms=2000,
            backoff_multiplier=10.0,
            jitter=False
        )
        def capped_delay():
            call_count[0] += 1
            if call_count[0] < 5:
                raise ConnectionError("Retry")
            return "success"

        result = capped_delay()
        assert result == "success"
        # All delays should be capped at 2000ms

    def test_retry_callback(self):
        """Test retry callback."""
        callback_calls = []

        def on_retry(exception, attempt):
            callback_calls.append((str(exception), attempt))

        @retry(max_attempts=3, base_delay_ms=10, on_retry=on_retry)
        def func_with_callback():
            if len(callback_calls) < 2:
                raise ConnectionError("Retry me")
            return "success"

        result = func_with_callback()
        assert result == "success"
        assert len(callback_calls) == 2
        assert callback_calls[0][1] == 1
        assert callback_calls[1][1] == 2

    async def test_retry_async_callback(self):
        """Test async retry callback."""
        callback_calls = []

        def on_retry(exception, attempt):
            callback_calls.append((str(exception), attempt))

        @retry(max_attempts=3, base_delay_ms=10, on_retry=on_retry)
        async def func_with_callback():
            if len(callback_calls) < 2:
                raise ConnectionError("Retry me")
            return "success"

        result = await func_with_callback()
        assert result == "success"
        assert len(callback_calls) == 2
