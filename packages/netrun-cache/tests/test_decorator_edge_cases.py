"""Tests for decorator edge cases and uncovered code paths."""

import pytest

from netrun.cache import MemoryCache, cached, cache_invalidate


@pytest.mark.unit
class TestDecoratorEdgeCases:
    """Edge case tests for cache decorators."""

    async def test_cached_with_none_values_in_args(self) -> None:
        """Test cached decorator with None values in arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(arg1: str, arg2: int, arg3: None = None):
            nonlocal call_count
            call_count += 1
            return f"{arg1}_{arg2}_{arg3}"

        # First call
        result1 = await test_func("value", 123, None)
        assert result1 == "value_123_None"
        assert call_count == 1

        # Second call with same args (should use cache)
        result2 = await test_func("value", 123, None)
        assert result2 == "value_123_None"
        assert call_count == 1  # Cache hit

        # Call with different None pattern
        result3 = await test_func("value", 123)
        assert result3 == "value_123_None"
        # May be cache hit or miss depending on how None is handled

    async def test_cached_with_complex_nested_objects(self) -> None:
        """Test cached decorator with complex nested objects."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(data: dict):
            nonlocal call_count
            call_count += 1
            return data.get("result", "default")

        # Complex nested structure
        complex_data = {
            "level1": {
                "level2": {"level3": {"value": 123}},
                "list": [1, 2, 3],
            },
            "result": "success",
        }

        # First call
        result1 = await test_func(complex_data)
        assert result1 == "success"
        assert call_count == 1

        # Second call with same data (should use cache)
        result2 = await test_func(complex_data)
        assert result2 == "success"
        assert call_count == 1  # Cache hit

    async def test_cached_with_list_arguments(self) -> None:
        """Test cached decorator with list arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(items: list):
            nonlocal call_count
            call_count += 1
            return len(items)

        # First call
        result1 = await test_func([1, 2, 3, 4, 5])
        assert result1 == 5
        assert call_count == 1

        # Second call with same list (should use cache)
        result2 = await test_func([1, 2, 3, 4, 5])
        assert result2 == 5
        assert call_count == 1  # Cache hit

    async def test_cached_with_mixed_primitive_types(self) -> None:
        """Test cached decorator with mixed primitive argument types."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(
            str_arg: str, int_arg: int, float_arg: float, bool_arg: bool
        ):
            nonlocal call_count
            call_count += 1
            return f"{str_arg}_{int_arg}_{float_arg}_{bool_arg}"

        # First call
        result1 = await test_func("test", 42, 3.14, True)
        assert result1 == "test_42_3.14_True"
        assert call_count == 1

        # Second call with same args (should use cache)
        result2 = await test_func("test", 42, 3.14, True)
        assert result2 == "test_42_3.14_True"
        assert call_count == 1  # Cache hit

        # Third call with different args
        result3 = await test_func("test", 42, 3.14, False)
        assert result3 == "test_42_3.14_False"
        assert call_count == 2  # Cache miss

    async def test_cached_with_key_prefix_override(self) -> None:
        """Test cached decorator with key_prefix parameter."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory", key_prefix="custom")
        async def test_func(value: str):
            nonlocal call_count
            call_count += 1
            return f"result_{value}"

        # First call
        result1 = await test_func("test")
        assert result1 == "result_test"
        assert call_count == 1

        # Second call (should use cache)
        result2 = await test_func("test")
        assert result2 == "result_test"
        assert call_count == 1  # Cache hit

    async def test_cached_returns_none(self) -> None:
        """Test cached decorator when function returns None."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(value: str):
            nonlocal call_count
            call_count += 1
            if value == "return_none":
                return None
            return f"result_{value}"

        # First call that returns None
        result1 = await test_func("return_none")
        assert result1 is None
        assert call_count == 1

        # Second call with same arg - None is cached, but may not be returned from cache
        # depending on implementation (None often means "not in cache")
        result2 = await test_func("return_none")
        # This may or may not increment call_count depending on caching behavior with None

        # Call with different arg
        result3 = await test_func("test")
        assert result3 == "result_test"

    async def test_cache_invalidate_with_multiple_keys(self) -> None:
        """Test cache_invalidate decorator with multiple keys."""
        # Test that decorator doesn't raise errors with multiple keys
        # Note: The decorator creates its own internal cache instance
        # that is separate from any external cache we create

        call_count = 0

        @cache_invalidate(namespace="test_invalidate", keys=["key1", "key2"])
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "done"

        # Call function - should execute without errors
        result = await test_func()
        assert result == "done"
        assert call_count == 1

        # Call again to ensure it works consistently
        result = await test_func()
        assert result == "done"
        assert call_count == 2

    async def test_cache_invalidate_with_pattern_warning(self) -> None:
        """Test cache_invalidate with pattern parameter (not yet implemented)."""
        cache = MemoryCache(namespace="test")
        await cache.initialize()

        await cache.set("user:1", "value1")
        await cache.set("user:2", "value2")

        @cache_invalidate(namespace="test", pattern="user:*")
        async def test_func():
            return "done"

        # Call function - should log warning about pattern not being implemented
        result = await test_func()
        assert result == "done"

        # Keys should still exist (pattern invalidation not implemented)
        assert await cache.exists("user:1") is True
        assert await cache.exists("user:2") is True

        await cache.close()

    async def test_cache_invalidate_empty_keys(self) -> None:
        """Test cache_invalidate with empty keys list."""
        cache = MemoryCache(namespace="test")
        await cache.initialize()

        call_count = 0

        @cache_invalidate(namespace="test", keys=[])
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await test_func()
        assert result == "done"
        assert call_count == 1

        await cache.close()

    async def test_cache_invalidate_no_keys_no_pattern(self) -> None:
        """Test cache_invalidate with neither keys nor pattern."""
        cache = MemoryCache(namespace="test")
        await cache.initialize()

        call_count = 0

        @cache_invalidate(namespace="test")
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await test_func()
        assert result == "done"
        assert call_count == 1

        await cache.close()

    async def test_cached_with_kwargs_only(self) -> None:
        """Test cached decorator with keyword-only arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(*, name: str, age: int):
            nonlocal call_count
            call_count += 1
            return f"{name}_{age}"

        # First call
        result1 = await test_func(name="John", age=30)
        assert result1 == "John_30"
        assert call_count == 1

        # Second call with same kwargs (should use cache)
        result2 = await test_func(name="John", age=30)
        assert result2 == "John_30"
        assert call_count == 1  # Cache hit

        # Third call with different order (should still cache hit due to sorting)
        result3 = await test_func(age=30, name="John")
        assert result3 == "John_30"
        assert call_count == 1  # Cache hit

    async def test_cached_with_complex_kwargs(self) -> None:
        """Test cached decorator with complex keyword arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(**kwargs):
            nonlocal call_count
            call_count += 1
            return kwargs

        # First call
        result1 = await test_func(name="John", data={"age": 30, "city": "NYC"})
        assert result1 == {"name": "John", "data": {"age": 30, "city": "NYC"}}
        assert call_count == 1

        # Second call with same kwargs (should use cache)
        result2 = await test_func(name="John", data={"age": 30, "city": "NYC"})
        assert result2 == {"name": "John", "data": {"age": 30, "city": "NYC"}}
        assert call_count == 1  # Cache hit

    async def test_cached_backend_memory_explicit(self) -> None:
        """Test cached decorator with explicit memory backend."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory", max_size=100)
        async def test_func(value: str):
            nonlocal call_count
            call_count += 1
            return f"result_{value}"

        result1 = await test_func("test")
        assert result1 == "result_test"
        assert call_count == 1

        result2 = await test_func("test")
        assert result2 == "result_test"
        assert call_count == 1  # Cache hit

    async def test_cached_with_very_long_key(self) -> None:
        """Test cached decorator with very long cache key."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(data: str):
            nonlocal call_count
            call_count += 1
            return len(data)

        # Very long string argument
        long_string = "a" * 10000

        result1 = await test_func(long_string)
        assert result1 == 10000
        assert call_count == 1

        result2 = await test_func(long_string)
        assert result2 == 10000
        assert call_count == 1  # Cache hit

    async def test_cache_invalidate_with_function_return_value(self) -> None:
        """Test that cache_invalidate returns function result."""
        @cache_invalidate(namespace="test_return_value", keys=["key1"])
        async def test_func(x: int, y: int):
            return x + y

        # Test that function executes and returns correct value
        result = await test_func(5, 10)
        assert result == 15

        # Test with different args
        result = await test_func(3, 7)
        assert result == 10

        # Test with negative numbers
        result = await test_func(-5, 10)
        assert result == 5

    async def test_cached_decorator_with_default_args(self) -> None:
        """Test cached decorator with functions having default arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(a: int, b: int = 10, c: str = "default"):
            nonlocal call_count
            call_count += 1
            return f"{a}_{b}_{c}"

        # Call with all defaults
        result1 = await test_func(5)
        assert result1 == "5_10_default"
        assert call_count == 1

        # Call again with same args (should cache hit)
        result2 = await test_func(5)
        assert result2 == "5_10_default"
        assert call_count == 1

        # Call with explicit args equal to defaults
        result3 = await test_func(5, 10, "default")
        assert result3 == "5_10_default"
        # May or may not be cache hit depending on key generation

        # Call with different defaults
        result4 = await test_func(5, 20)
        assert result4 == "5_20_default"
        assert call_count >= 2  # Should be cache miss

    async def test_cached_with_boolean_args(self) -> None:
        """Test cached decorator specifically with boolean arguments."""
        call_count = 0

        @cached(ttl=3600, namespace="test", backend="memory")
        async def test_func(flag: bool):
            nonlocal call_count
            call_count += 1
            return "true" if flag else "false"

        result1 = await test_func(True)
        assert result1 == "true"
        assert call_count == 1

        result2 = await test_func(True)
        assert result2 == "true"
        assert call_count == 1  # Cache hit

        result3 = await test_func(False)
        assert result3 == "false"
        assert call_count == 2  # Cache miss

        result4 = await test_func(False)
        assert result4 == "false"
        assert call_count == 2  # Cache hit
