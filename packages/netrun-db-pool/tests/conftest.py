"""Pytest configuration and fixtures for netrun-db-pool tests."""

import asyncio
import os

import pytest
from sqlalchemy import text

from netrun_db_pool import AsyncDatabasePool, PoolConfig, TenantAwareDatabasePool


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def sqlite_pool():
    """Create SQLite in-memory pool for testing."""
    config = PoolConfig(
        database_url="sqlite+aiosqlite:///:memory:",
        pool_size=5,
        max_overflow=2,
        echo=False,
    )
    pool = AsyncDatabasePool(config=config)
    await pool.initialize()

    # Create test table
    async with pool._engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                )
                """
            )
        )

    yield pool
    await pool.close()


@pytest.fixture
async def postgresql_pool():
    """
    Create PostgreSQL pool for integration tests.

    Requires PostgreSQL running on localhost:5432.
    Set POSTGRES_TEST_URL environment variable to override.
    """
    postgres_url = os.getenv(
        "POSTGRES_TEST_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db",
    )

    config = PoolConfig(
        database_url=postgres_url,
        pool_size=10,
        max_overflow=5,
        pool_recycle=3600,
        echo=False,
    )

    pool = AsyncDatabasePool(config=config)

    try:
        await pool.initialize()

        # Create test table
        async with pool.get_session() as session:
            await session.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            await session.execute(
                text(
                    """
                    CREATE TABLE users (
                        id SERIAL PRIMARY KEY,
                        tenant_id UUID,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL
                    )
                    """
                )
            )
            await session.commit()

        yield pool

    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    finally:
        if pool.is_initialized:
            await pool.close()


@pytest.fixture
async def tenant_pool():
    """
    Create tenant-aware PostgreSQL pool for RLS testing.

    Requires PostgreSQL with RLS support.
    """
    postgres_url = os.getenv(
        "POSTGRES_TEST_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db",
    )

    config = PoolConfig(
        database_url=postgres_url,
        pool_size=10,
        max_overflow=5,
    )

    pool = TenantAwareDatabasePool(config=config)

    try:
        await pool.initialize()

        # Create test table with RLS
        async with pool.get_session() as session:
            await session.execute(text("DROP TABLE IF EXISTS tenant_users CASCADE"))
            await session.execute(
                text(
                    """
                    CREATE TABLE tenant_users (
                        id SERIAL PRIMARY KEY,
                        tenant_id UUID NOT NULL,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL
                    )
                    """
                )
            )

            # Enable RLS
            await session.execute(
                text("ALTER TABLE tenant_users ENABLE ROW LEVEL SECURITY")
            )

            # Create RLS policy
            await session.execute(
                text(
                    """
                    CREATE POLICY tenant_isolation ON tenant_users
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    """
                )
            )

            await session.commit()

        yield pool

    except Exception as e:
        pytest.skip(f"PostgreSQL with RLS not available: {e}")

    finally:
        if pool.is_initialized:
            await pool.close()


@pytest.fixture
def sample_config():
    """Sample PoolConfig for testing."""
    return PoolConfig(
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        app_name="test-service",
    )
