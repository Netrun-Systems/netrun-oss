"""
Async Utilities for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides async testing utilities compatible with pytest-asyncio 0.23+.

Usage:
    Simply install the package and pytest-asyncio will use these fixtures automatically.

    @pytest.mark.asyncio
    async def test_async_operation():
        result = await some_async_function()
        assert result == expected

Fixtures:
    - new_event_loop: Fresh event loop for isolated tests

Note (v2.1.1): The custom session-scoped event_loop fixture was removed because
it conflicts with pytest-asyncio >= 0.23 which deprecated event_loop overrides.
Use @pytest.mark.asyncio(loop_scope="session") for session-scoped async tests instead.
"""

import asyncio
from typing import Generator
import pytest

# Graceful netrun-logging integration (optional)
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


@pytest.fixture
def new_event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create a fresh event loop for tests requiring loop isolation.

    Use this fixture when you need a new event loop for specific test cases
    that require complete isolation from other tests (e.g., testing event
    loop lifecycle, custom loop policies, or loop-specific state).

    Yields:
        asyncio.AbstractEventLoop: Fresh event loop for isolated testing

    Example:
        def test_event_loop_lifecycle(new_event_loop):
            assert not new_event_loop.is_closed()
            new_event_loop.run_until_complete(async_task())
            # Loop is cleaned up automatically
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)
