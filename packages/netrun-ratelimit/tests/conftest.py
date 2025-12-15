"""
Test fixtures for netrun-ratelimit.
"""

import pytest
from netrun_ratelimit import MemoryBackend, RateLimiter, TokenBucket


@pytest.fixture
def memory_backend():
    """Create a fresh memory backend for each test."""
    return MemoryBackend()


@pytest.fixture
def limiter(memory_backend):
    """Create a rate limiter with memory backend."""
    return RateLimiter(
        backend=memory_backend,
        rate=10,
        period=60,
        key_prefix="test:",
    )


@pytest.fixture
def token_bucket(memory_backend):
    """Create a token bucket with memory backend."""
    return TokenBucket(
        rate=10,
        period=60,
        burst=10,
        backend=memory_backend,
    )


@pytest.fixture
def strict_limiter(memory_backend):
    """Create a strict rate limiter (1 req/sec)."""
    return RateLimiter(
        backend=memory_backend,
        rate=1,
        period=1,
        key_prefix="strict:",
    )
