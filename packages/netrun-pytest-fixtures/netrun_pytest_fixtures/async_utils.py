"""
Async Utilities for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides session-scoped event loop fixtures for async testing.
Addresses 71% duplication across Service_* test suites.

Usage:
    Simply install the package and pytest-asyncio will use these fixtures automatically.

    @pytest.mark.asyncio
    async def test_async_operation(event_loop):
        result = await some_async_function()
        assert result == expected

Fixtures:
    - event_loop: Session-scoped asyncio event loop for all async tests
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


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create session-scoped event loop for async tests.

    This fixture addresses the 71% duplication of event_loop fixtures
    across Service_* test suites. Using session scope prevents creating
    multiple event loops during a test session, improving test performance
    and preventing event loop management issues.

    Yields:
        asyncio.AbstractEventLoop: Event loop for async test execution

    Example:
        @pytest.mark.asyncio
        async def test_database_query(event_loop, async_db_session):
            result = await async_db_session.execute(query)
            assert result is not None
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
