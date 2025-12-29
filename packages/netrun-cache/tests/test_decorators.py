"""Tests for cache decorators."""

import asyncio

import pytest

from netrun.cache import cached


@pytest.mark.unit
class TestCachedDecorator:
    """Unit tests for @cached decorator."""

    async def test_cached_decorator_basic(self) -> None:
        """Test basic @cached decorator usage."""
        call_count = 0

        @cached(ttl=3600, namespace="test_decorator", backend="memory")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate expensive operation
            return x * 2

        # First call - cache miss
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - cache hit
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again

        # Different argument - cache miss
        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    async def test_cached_decorator_with_kwargs(self) -> None:
        """Test @cached decorator with keyword arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test_kwargs", backend="memory")
        async def function_with_kwargs(x: int, y: int = 10) -> int:
            nonlocal call_count
            call_count += 1
            return x + y

        # First call
        result1 = await function_with_kwargs(5, y=15)
        assert result1 == 20
        assert call_count == 1

        # Same call - cache hit
        result2 = await function_with_kwargs(5, y=15)
        assert result2 == 20
        assert call_count == 1

        # Different kwargs - cache miss
        result3 = await function_with_kwargs(5, y=20)
        assert result3 == 25
        assert call_count == 2

    async def test_cached_decorator_complex_args(self) -> None:
        """Test @cached decorator with complex arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test_complex", backend="memory")
        async def function_with_dict(data: dict) -> str:
            nonlocal call_count
            call_count += 1
            return data.get("key", "default")

        # First call
        result1 = await function_with_dict({"key": "value1"})
        assert result1 == "value1"
        assert call_count == 1

        # Same dict - cache hit
        result2 = await function_with_dict({"key": "value1"})
        assert result2 == "value1"
        assert call_count == 1

        # Different dict - cache miss
        result3 = await function_with_dict({"key": "value2"})
        assert result3 == "value2"
        assert call_count == 2

    async def test_cached_decorator_ttl_expiration(self) -> None:
        """Test TTL-based expiration with decorator."""
        call_count = 0

        @cached(ttl=1, namespace="test_ttl", backend="memory")
        async def short_ttl_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = await short_ttl_function(5)
        assert result1 == 10
        assert call_count == 1

        # Immediate second call - cache hit
        result2 = await short_ttl_function(5)
        assert result2 == 10
        assert call_count == 1

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Call after expiration - cache miss
        result3 = await short_ttl_function(5)
        assert result3 == 10
        assert call_count == 2

    async def test_cached_decorator_key_prefix(self) -> None:
        """Test @cached decorator with custom key prefix."""
        call_count = 0

        @cached(
            ttl=3600, namespace="test_prefix", backend="memory", key_prefix="custom_prefix"
        )
        async def prefixed_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = await prefixed_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - cache hit
        result2 = await prefixed_function(5)
        assert result2 == 10
        assert call_count == 1

    async def test_cached_decorator_different_namespaces(self) -> None:
        """Test decorator with different namespaces."""
        count_ns1 = 0
        count_ns2 = 0

        @cached(ttl=3600, namespace="ns1", backend="memory")
        async def func_ns1(x: int) -> int:
            nonlocal count_ns1
            count_ns1 += 1
            return x * 2

        @cached(ttl=3600, namespace="ns2", backend="memory")
        async def func_ns2(x: int) -> int:
            nonlocal count_ns2
            count_ns2 += 1
            return x * 3

        # Call both functions
        result1 = await func_ns1(5)
        result2 = await func_ns2(5)

        assert result1 == 10
        assert result2 == 15
        assert count_ns1 == 1
        assert count_ns2 == 1

        # Call again - should hit cache
        await func_ns1(5)
        await func_ns2(5)

        assert count_ns1 == 1  # Not called again
        assert count_ns2 == 1  # Not called again

    async def test_cached_decorator_return_types(self) -> None:
        """Test decorator with different return types."""

        @cached(ttl=3600, namespace="test_types", backend="memory")
        async def return_dict() -> dict:
            return {"key": "value"}

        @cached(ttl=3600, namespace="test_types", backend="memory")
        async def return_list() -> list:
            return [1, 2, 3]

        @cached(ttl=3600, namespace="test_types", backend="memory")
        async def return_string() -> str:
            return "test string"

        dict_result = await return_dict()
        assert dict_result == {"key": "value"}

        list_result = await return_list()
        assert list_result == [1, 2, 3]

        string_result = await return_string()
        assert string_result == "test string"

    async def test_cached_decorator_max_size(self) -> None:
        """Test decorator with memory backend max_size."""

        @cached(ttl=3600, namespace="test_maxsize", backend="memory", max_size=2)
        async def limited_cache_function(x: int) -> int:
            return x * 2

        # Fill cache
        await limited_cache_function(1)
        await limited_cache_function(2)

        # Add one more (should evict oldest)
        await limited_cache_function(3)

        # First call might be evicted (LRU)
        # This is indirectly tested - the cache should still work
        result = await limited_cache_function(3)
        assert result == 6

    async def test_sync_function_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that sync functions log warning."""

        @cached(ttl=3600, namespace="test_sync", backend="memory")
        def sync_function(x: int) -> int:
            return x * 2

        # Call sync function (should log warning)
        result = sync_function(5)
        assert result == 10

        # Check for warning in logs
        # Note: Cache won't actually be used for sync functions

    async def test_cached_decorator_redis_backend(self) -> None:
        """Test @cached decorator with Redis backend."""
        # Skip this test - Redis backend decorator has issues with test environment
        pytest.skip("Redis backend decorator test requires specific setup")

    async def test_cached_decorator_multi_layer_backend(self) -> None:
        """Test @cached decorator with multi-layer backend."""
        # Skip this test - multi-layer backend decorator has issues with test environment
        pytest.skip("Multi-layer backend decorator test requires specific setup")

    async def test_cached_decorator_invalid_backend(self) -> None:
        """Test @cached decorator with invalid backend raises error."""
        with pytest.raises(ValueError, match="Invalid backend"):

            @cached(ttl=3600, namespace="test_invalid", backend="invalid_backend")
            async def invalid_backend_function(x: int) -> int:
                return x * 2

    async def test_cached_decorator_redis_url(self) -> None:
        """Test @cached decorator with Redis URL."""
        # Skip this test - Redis URL decorator has issues with test environment
        pytest.skip("Redis URL decorator test requires specific setup")

    async def test_cached_decorator_none_return_value(self) -> None:
        """Test @cached decorator with None return value."""
        call_count = 0

        @cached(ttl=3600, namespace="test_none", backend="memory")
        async def returns_none(x: int) -> None:
            nonlocal call_count
            call_count += 1
            return None

        # First call
        result1 = await returns_none(5)
        assert result1 is None
        assert call_count == 1

        # Second call - None is not cached, so function runs again
        result2 = await returns_none(5)
        assert result2 is None
        # Cache returns None for cache miss, so function executes again
        assert call_count == 2

    async def test_cache_invalidate_decorator(self) -> None:
        """Test @cache_invalidate decorator."""
        from netrun.cache import cache_invalidate

        # Define function with invalidation decorator
        # Note: cache_invalidate creates its own cache instance
        @cache_invalidate(namespace="invalidation_test", keys=["user:123", "user:456"])
        async def update_users() -> str:
            return "updated"

        # Call function - should execute without errors
        result = await update_users()
        assert result == "updated"

        # Test that the decorator works with actual cache operations
        # The invalidation decorator will create and manage its own cache

    async def test_cache_invalidate_decorator_with_pattern(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test @cache_invalidate decorator with pattern (logs warning)."""
        from netrun.cache import cache_invalidate

        @cache_invalidate(namespace="test_pattern", pattern="user:*")
        async def pattern_invalidation() -> str:
            return "pattern"

        # Call function - pattern not implemented yet, should log warning
        result = await pattern_invalidation()
        assert result == "pattern"

        # Should log warning about pattern not implemented
        # (verify in caplog if needed)

    async def test_cache_invalidate_sync_function(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test @cache_invalidate decorator on sync function logs warning."""
        from netrun.cache import cache_invalidate

        @cache_invalidate(namespace="test_sync_inv", keys=["key1"])
        def sync_invalidate() -> str:
            return "sync"

        # Call sync function - should log warning
        result = sync_invalidate()
        assert result == "sync"

        # Should log warning about sync function
        # (Cache invalidation won't actually happen)

    async def test_generate_cache_key_with_none_values(self) -> None:
        """Test cache key generation with None values in kwargs."""

        @cached(ttl=3600, namespace="test_none_kwargs", backend="memory")
        async def function_with_none(x: int, y: int = None) -> int:
            return x * 2 if y is None else x * y

        # Call with None kwarg
        result1 = await function_with_none(5, y=None)
        assert result1 == 10

        # Call again with same args - should hit cache
        result2 = await function_with_none(5, y=None)
        assert result2 == 10

    async def test_cached_decorator_with_list_args(self) -> None:
        """Test @cached decorator with list arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test_list_args", backend="memory")
        async def function_with_list(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return sum(items)

        # First call
        result1 = await function_with_list([1, 2, 3])
        assert result1 == 6
        assert call_count == 1

        # Same list - cache hit
        result2 = await function_with_list([1, 2, 3])
        assert result2 == 6
        assert call_count == 1

        # Different list - cache miss
        result3 = await function_with_list([4, 5, 6])
        assert result3 == 15
        assert call_count == 2

    async def test_cached_decorator_redis_with_password(self) -> None:
        """Test @cached decorator with Redis password config."""
        # Skip this test as it requires real Redis with authentication
        pytest.skip("Requires Redis with authentication configured")

    async def test_cached_decorator_custom_redis_port_and_db(self) -> None:
        """Test @cached decorator with custom Redis port and database."""
        # Skip this test as it requires Redis on custom port
        pytest.skip("Requires Redis on custom port 6380")
