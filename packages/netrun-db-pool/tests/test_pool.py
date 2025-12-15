"""Tests for AsyncDatabasePool core functionality."""

import pytest
from sqlalchemy import select, text

from netrun_db_pool import AsyncDatabasePool, PoolConfig


class TestPoolConfig:
    """Test PoolConfig configuration management."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PoolConfig(database_url="postgresql+asyncpg://localhost/db")

        assert config.pool_size == 20
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
        assert config.pool_pre_ping is True
        assert config.command_timeout == 60
        assert config.enable_jit is False
        assert config.app_name == "netrun-service"
        assert config.echo is False

    def test_total_max_connections(self):
        """Test total max connections calculation."""
        config = PoolConfig(
            database_url="postgresql+asyncpg://localhost/db",
            pool_size=20,
            max_overflow=10,
        )

        assert config.total_max_connections == 30

    def test_postgresql_url_conversion(self):
        """Test automatic conversion to asyncpg driver."""
        config = PoolConfig(database_url="postgresql://user:pass@localhost/db")

        assert config.database_url.startswith("postgresql+asyncpg://")

    def test_sqlite_url_conversion(self):
        """Test SQLite URL conversion to aiosqlite."""
        config = PoolConfig(database_url="sqlite:///test.db")

        assert config.database_url.startswith("sqlite+aiosqlite://")

    def test_connect_args_postgresql(self, sample_config):
        """Test PostgreSQL connect_args generation."""
        connect_args = sample_config.connect_args

        assert "server_settings" in connect_args
        assert connect_args["server_settings"]["application_name"] == "test-service"
        assert connect_args["server_settings"]["jit"] == "off"
        assert connect_args["command_timeout"] == 60

    def test_connect_args_sqlite(self):
        """Test SQLite connect_args (should be empty)."""
        config = PoolConfig(database_url="sqlite+aiosqlite:///:memory:")
        connect_args = config.connect_args

        assert connect_args == {}

    def test_validation_min_values(self):
        """Test minimum value validation."""
        with pytest.raises(ValueError):
            PoolConfig(
                database_url="postgresql+asyncpg://localhost/db",
                pool_size=0,  # Must be >= 1
            )

    def test_validation_max_values(self):
        """Test maximum value validation."""
        with pytest.raises(ValueError):
            PoolConfig(
                database_url="postgresql+asyncpg://localhost/db",
                pool_size=200,  # Must be <= 100
            )


class TestAsyncDatabasePool:
    """Test AsyncDatabasePool functionality."""

    @pytest.mark.asyncio
    async def test_pool_initialization(self, sqlite_pool):
        """Test pool initialization."""
        assert sqlite_pool.is_initialized is True
        assert sqlite_pool.engine is not None

    @pytest.mark.asyncio
    async def test_pool_double_initialization(self, sqlite_pool):
        """Test that double initialization is handled gracefully."""
        # Should not raise error
        await sqlite_pool.initialize()
        assert sqlite_pool.is_initialized is True

    @pytest.mark.asyncio
    async def test_get_session(self, sqlite_pool):
        """Test session acquisition."""
        async with sqlite_pool.get_session() as session:
            result = await session.execute(text("SELECT 1 as value"))
            row = result.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_session_autocommit(self, sqlite_pool):
        """Test automatic session commit."""
        # Insert data
        async with sqlite_pool.get_session() as session:
            await session.execute(
                text("INSERT INTO users (name, email) VALUES (:name, :email)"),
                {"name": "Test User", "email": "test@example.com"},
            )

        # Verify data persists (auto-committed)
        async with sqlite_pool.get_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            assert count == 1

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, sqlite_pool):
        """Test automatic rollback on exception."""
        # First, insert a baseline user that will persist
        async with sqlite_pool.get_session() as session:
            await session.execute(
                text("INSERT INTO users (name, email) VALUES (:name, :email)"),
                {"name": "Baseline User", "email": "baseline@example.com"},
            )

        # Now try to insert with a duplicate email (should rollback)
        try:
            async with sqlite_pool.get_session() as session:
                await session.execute(
                    text("INSERT INTO users (name, email) VALUES (:name, :email)"),
                    {"name": "Test User 2", "email": "test2@example.com"},
                )
                # Force error (duplicate email)
                await session.execute(
                    text("INSERT INTO users (name, email) VALUES (:name, :email)"),
                    {"name": "Test User 3", "email": "test2@example.com"},
                )
        except Exception:
            pass

        # Verify rollback (only baseline user persists)
        async with sqlite_pool.get_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            assert count == 1  # Only baseline user

    @pytest.mark.asyncio
    async def test_health_check_simple(self, sqlite_pool):
        """Test simple health check."""
        is_healthy = await sqlite_pool.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_detailed(self, sqlite_pool):
        """Test detailed health check with metrics."""
        health = await sqlite_pool.health_check_detailed()

        assert health.healthy is True
        assert health.status == "healthy"
        assert health.pool_size > 0
        assert health.latency_ms >= 0
        assert health.database_type == "sqlite"
        assert health.timestamp is not None

    @pytest.mark.asyncio
    async def test_health_check_dict_conversion(self, sqlite_pool):
        """Test health check dict conversion."""
        health = await sqlite_pool.health_check_detailed()
        health_dict = health.to_dict()

        assert "healthy" in health_dict
        assert "status" in health_dict
        assert "pool_size" in health_dict
        assert "utilization_percent" in health_dict
        assert "available_connections" in health_dict
        assert "latency_ms" in health_dict

    @pytest.mark.asyncio
    async def test_pool_utilization_metrics(self, sqlite_pool):
        """Test pool utilization calculations."""
        health = await sqlite_pool.health_check_detailed()

        # Utilization should be low (no active queries)
        assert health.utilization_percent < 50
        assert health.available_connections > 0

    @pytest.mark.asyncio
    async def test_pool_close(self):
        """Test pool cleanup."""
        config = PoolConfig(database_url="sqlite+aiosqlite:///:memory:")
        pool = AsyncDatabasePool(config=config)
        await pool.initialize()

        assert pool.is_initialized is True

        await pool.close()
        assert pool.is_initialized is False

    @pytest.mark.asyncio
    async def test_from_env_constructor(self, monkeypatch):
        """Test pool creation from environment variables."""
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        monkeypatch.setenv("DB_POOL_SIZE", "15")
        monkeypatch.setenv("DB_MAX_OVERFLOW", "5")

        pool = AsyncDatabasePool.from_env()

        assert pool.config.pool_size == 15
        assert pool.config.max_overflow == 5
        assert pool.config.database_url == "sqlite+aiosqlite:///:memory:"

        await pool.close()


@pytest.mark.integration
class TestAsyncDatabasePoolPostgreSQL:
    """Integration tests with real PostgreSQL database."""

    @pytest.mark.asyncio
    async def test_postgresql_connection(self, postgresql_pool):
        """Test PostgreSQL connection and query."""
        async with postgresql_pool.get_session() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version

    @pytest.mark.asyncio
    async def test_postgresql_pool_metrics(self, postgresql_pool):
        """Test PostgreSQL pool metrics."""
        health = await postgresql_pool.health_check_detailed()

        assert health.healthy is True
        assert health.database_type == "postgresql"
        assert health.pool_size == 10
        assert health.max_overflow == 5

    @pytest.mark.asyncio
    async def test_postgresql_transaction_handling(self, postgresql_pool):
        """Test PostgreSQL transaction commit/rollback."""
        # Insert data
        async with postgresql_pool.get_session() as session:
            await session.execute(
                text(
                    "INSERT INTO users (name, email) VALUES (:name, :email)"
                ),
                {"name": "PG User", "email": "pguser@example.com"},
            )

        # Verify commit
        async with postgresql_pool.get_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"),
                {"email": "pguser@example.com"},
            )
            count = result.scalar()
            assert count == 1

    @pytest.mark.asyncio
    async def test_postgresql_concurrent_sessions(self, postgresql_pool):
        """Test concurrent session acquisition."""
        async def insert_user(user_id: int):
            async with postgresql_pool.get_session() as session:
                await session.execute(
                    text("INSERT INTO users (name, email) VALUES (:name, :email)"),
                    {"name": f"User {user_id}", "email": f"user{user_id}@example.com"},
                )

        # Run 5 concurrent inserts
        import asyncio
        await asyncio.gather(*[insert_user(i) for i in range(5)])

        # Verify all inserts
        async with postgresql_pool.get_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            assert count >= 5
