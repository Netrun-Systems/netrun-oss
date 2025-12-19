"""
Database Fixtures for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides SQLAlchemy async session fixtures for database testing.
Supports both PostgreSQL and SQLite in-memory databases.

Usage:
    @pytest.mark.asyncio
    async def test_user_creation(async_db_session):
        user = User(name="Test")
        async_db_session.add(user)
        await async_db_session.commit()
        assert user.id is not None

Fixtures:
    - test_database_url: Test database URL (SQLite in-memory by default)
    - async_engine: Async SQLAlchemy engine
    - async_session_factory: Session factory for creating sessions
    - async_db_session: Async database session with automatic cleanup
    - init_test_database: Initialize database schema for testing
"""

import pytest
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase

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
def test_database_url() -> str:
    """
    Test database URL for SQLAlchemy testing.

    Defaults to SQLite in-memory database for fast, isolated tests.
    Override with environment variable for PostgreSQL integration tests.

    Returns:
        str: Database URL

    Environment Variables:
        TEST_DATABASE_URL: Override with PostgreSQL URL for integration tests

    Example:
        def test_database_connection(test_database_url):
            assert "sqlite" in test_database_url or "postgresql" in test_database_url
    """
    import os
    # Default to SQLite in-memory for fast tests
    # Override with TEST_DATABASE_URL env var for PostgreSQL integration tests
    return os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture(scope="session")
async def async_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create async SQLAlchemy engine for testing.

    Session-scoped to reuse engine across tests for performance.
    Automatically disposes of engine after test session.

    Args:
        test_database_url: Test database URL fixture

    Yields:
        AsyncEngine: SQLAlchemy async engine

    Example:
        @pytest.mark.asyncio
        async def test_engine_connection(async_engine):
            async with async_engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result is not None
    """
    engine = create_async_engine(
        test_database_url,
        echo=False,  # Set to True for SQL debugging
        future=True,
        pool_pre_ping=True  # Verify connections before use
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def async_session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create async session factory for test database sessions.

    Session-scoped factory that creates new sessions for each test.
    Configure with expire_on_commit=False for testing convenience.

    Args:
        async_engine: Async engine fixture

    Returns:
        async_sessionmaker: Session factory

    Example:
        @pytest.mark.asyncio
        async def test_multiple_sessions(async_session_factory):
            async with async_session_factory() as session1:
                async with async_session_factory() as session2:
                    # Independent sessions for concurrent testing
                    pass
    """
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects accessible after commit
        autoflush=False,  # Manual flush control for testing
        autocommit=False
    )


@pytest.fixture
async def async_db_session(
    async_session_factory: async_sessionmaker[AsyncSession]
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session for testing with automatic cleanup.

    Each test gets a fresh session that automatically rolls back changes.
    Ensures test isolation and prevents database pollution.

    Args:
        async_session_factory: Session factory fixture

    Yields:
        AsyncSession: Async database session

    Cleanup:
        Automatically rolls back all changes and closes session

    Example:
        @pytest.mark.asyncio
        async def test_user_crud(async_db_session):
            user = User(name="Test User")
            async_db_session.add(user)
            await async_db_session.commit()

            # Changes rolled back automatically after test
            assert user.id is not None
    """
    async with async_session_factory() as session:
        async with session.begin():
            yield session
            # Automatic rollback on test completion
            await session.rollback()


@pytest.fixture(scope="function")
async def init_test_database(async_engine: AsyncEngine, base_model: DeclarativeBase):
    """
    Initialize test database schema before tests.

    Creates all tables defined in SQLAlchemy models before each test.
    Drops all tables after test completion for clean state.

    Args:
        async_engine: Async engine fixture
        base_model: SQLAlchemy DeclarativeBase with model definitions

    Note:
        Requires base_model fixture to be defined in your test suite:

        @pytest.fixture(scope="session")
        def base_model():
            return Base  # Your SQLAlchemy Base

    Example:
        @pytest.mark.asyncio
        async def test_with_schema(init_test_database, async_db_session):
            # Database schema already initialized
            user = User(name="Test")
            async_db_session.add(user)
            await async_db_session.commit()
    """
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(base_model.metadata.create_all)

    yield

    # Drop all tables after test
    async with async_engine.begin() as conn:
        await conn.run_sync(base_model.metadata.drop_all)


@pytest.fixture
def mock_db_session():
    """
    Mock database session for unit testing without database.

    Use for testing business logic that depends on database sessions
    without requiring actual database connection.

    Returns:
        MagicMock: Mock async session

    Example:
        def test_service_logic(mock_db_session):
            from unittest.mock import AsyncMock
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            service = UserService(mock_db_session)
            result = await service.get_user(user_id)
            assert result is not None
    """
    from unittest.mock import MagicMock, AsyncMock

    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    session.refresh = AsyncMock()

    return session


@pytest.fixture
async def transaction_rollback_session(
    async_session_factory: async_sessionmaker[AsyncSession]
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session with nested transaction rollback.

    Use for testing transaction handling and rollback scenarios.
    All changes are rolled back, including explicit commits in tests.

    Args:
        async_session_factory: Session factory fixture

    Yields:
        AsyncSession: Session with savepoint for rollback

    Example:
        @pytest.mark.asyncio
        async def test_transaction_rollback(transaction_rollback_session):
            user = User(name="Test")
            transaction_rollback_session.add(user)
            await transaction_rollback_session.commit()

            # Even after commit, changes rolled back at test end
            # Test isolation maintained
    """
    async with async_session_factory() as session:
        async with session.begin():
            # Create savepoint for nested transaction
            savepoint = await session.begin_nested()
            yield session
            # Rollback to savepoint
            await savepoint.rollback()
