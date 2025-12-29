"""Tests for timeout decorator."""

import asyncio
import pytest
import time
from netrun.resilience import timeout
from netrun.resilience.timeout import TimeoutError


class TestTimeout:
    """Test timeout decorator with sync and async functions."""

    async def test_timeout_async_within_limit(self):
        """Test async function completes within timeout."""
        @timeout(seconds=1.0)
        async def fast_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await fast_func()
        assert result == "success"

    async def test_timeout_async_exceeds_limit(self):
        """Test async function timeout."""
        @timeout(seconds=0.1)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "should not reach"

        with pytest.raises(TimeoutError) as exc_info:
            await slow_func()

        assert "Operation timed out" in str(exc_info.value)

    async def test_timeout_async_custom_message(self):
        """Test custom timeout message."""
        @timeout(seconds=0.1, message="Custom timeout message")
        async def slow_func():
            await asyncio.sleep(1.0)

        with pytest.raises(TimeoutError) as exc_info:
            await slow_func()

        assert "Custom timeout message" in str(exc_info.value)

    def test_timeout_sync_within_limit(self):
        """Test sync function completes within timeout."""
        @timeout(seconds=1.0)
        def fast_func():
            time.sleep(0.1)
            return "success"

        result = fast_func()
        assert result == "success"

    def test_timeout_sync_exceeds_limit(self):
        """Test sync function timeout."""
        @timeout(seconds=0.2)
        def slow_func():
            time.sleep(1.0)
            return "should not reach"

        with pytest.raises(TimeoutError) as exc_info:
            slow_func()

        assert "Operation timed out" in str(exc_info.value)

    def test_timeout_sync_custom_message(self):
        """Test custom timeout message for sync."""
        @timeout(seconds=0.2, message="Sync timeout")
        def slow_func():
            time.sleep(1.0)

        with pytest.raises(TimeoutError) as exc_info:
            slow_func()

        assert "Sync timeout" in str(exc_info.value)

    async def test_timeout_async_with_return_value(self):
        """Test timeout preserves return values."""
        @timeout(seconds=1.0)
        async def func_with_return():
            await asyncio.sleep(0.1)
            return {"key": "value", "number": 42}

        result = await func_with_return()
        assert result == {"key": "value", "number": 42}

    def test_timeout_sync_with_return_value(self):
        """Test timeout preserves return values for sync."""
        @timeout(seconds=1.0)
        def func_with_return():
            time.sleep(0.1)
            return [1, 2, 3, 4, 5]

        result = func_with_return()
        assert result == [1, 2, 3, 4, 5]

    async def test_timeout_async_exception_propagation(self):
        """Test that non-timeout exceptions propagate."""
        @timeout(seconds=1.0)
        async def func_with_error():
            await asyncio.sleep(0.1)
            raise ValueError("Custom error")

        with pytest.raises(ValueError) as exc_info:
            await func_with_error()

        assert "Custom error" in str(exc_info.value)

    def test_timeout_sync_exception_propagation(self):
        """Test that non-timeout exceptions propagate for sync."""
        @timeout(seconds=1.0)
        def func_with_error():
            time.sleep(0.1)
            raise ValueError("Custom error")

        with pytest.raises(ValueError) as exc_info:
            func_with_error()

        assert "Custom error" in str(exc_info.value)

    async def test_timeout_async_precise_timing(self):
        """Test timeout precision for async."""
        @timeout(seconds=0.5)
        async def func():
            await asyncio.sleep(0.6)

        start = time.time()
        with pytest.raises(TimeoutError):
            await func()
        elapsed = time.time() - start

        # Should timeout around 0.5s (allow some tolerance)
        assert 0.4 < elapsed < 0.7
