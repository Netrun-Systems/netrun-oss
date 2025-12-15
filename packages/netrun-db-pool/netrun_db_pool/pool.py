"""
Core async database pool implementation using SQLAlchemy.

v1.1.0: Added netrun-logging and netrun-errors integration for structured
logging and standardized exception handling.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, StaticPool

from netrun_db_pool.config import PoolConfig
from netrun_db_pool.health import PoolHealth

# Optional netrun-logging integration
_use_netrun_logging = False
_logger = None

try:
    from netrun_logging import get_logger, log_operation_timing
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    log_operation_timing = None  # type: ignore
    _logger = logging.getLogger(__name__)


def _log(level: str, message: str, **kwargs) -> None:
    """Log using netrun-logging if available, otherwise standard logging."""
    if _use_netrun_logging:
        log_method = getattr(_logger, level, _logger.info)
        log_method(message, **kwargs)
    else:
        log_method = getattr(_logger, level, _logger.info)
        log_method(f"{message} {kwargs}" if kwargs else message)


# Alias for backward compatibility
logger = _logger


class AsyncDatabasePool:
    """
    Production-grade async database connection pool.

    Features:
    - SQLAlchemy 2.0+ with asyncpg driver
    - Configurable pool sizing and overflow
    - Health monitoring with detailed metrics
    - Connection pre-ping for reliability
    - Automatic connection recycling
    - PostgreSQL-specific optimizations (JIT control, query timeout)

    Example:
        >>> from netrun_db_pool import AsyncDatabasePool, PoolConfig
        >>> config = PoolConfig(database_url="postgresql+asyncpg://user:pass@localhost/db")
        >>> pool = AsyncDatabasePool(config=config)
        >>> await pool.initialize()
        >>> async with pool.get_session() as session:
        ...     result = await session.execute(text("SELECT 1"))
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        config: Optional[PoolConfig] = None,
    ):
        """
        Initialize database pool.

        Args:
            database_url: Database connection URL (overrides config.database_url)
            config: PoolConfig instance (loads from environment if not provided)
        """
        # Load configuration
        if config is None:
            config = PoolConfig()

        # Override database_url if provided
        if database_url:
            config.database_url = database_url

        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._initialized = False

        # Create engine immediately (lazy initialization on first query)
        self._create_engine()

    def _create_engine(self) -> None:
        """Create SQLAlchemy async engine with pool configuration."""
        # Choose pool class:
        # - StaticPool for in-memory SQLite (maintains single connection)
        # - NullPool for file-based SQLite (no pooling needed)
        # - AsyncAdaptedQueuePool for PostgreSQL (standard pooling)
        is_sqlite = "sqlite" in self.config.database_url
        is_memory_db = is_sqlite and ":memory:" in self.config.database_url

        if is_memory_db:
            poolclass = StaticPool
        elif is_sqlite:
            poolclass = NullPool
        else:
            poolclass = AsyncAdaptedQueuePool

        _log(
            "info",
            "db_engine_creating",
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_recycle=self.config.pool_recycle,
            pool_class=poolclass.__name__,
            using_netrun_logging=_use_netrun_logging,
        )

        # Build engine kwargs - NullPool/StaticPool don't accept pool sizing args
        engine_kwargs = {
            "echo": self.config.echo,
            "poolclass": poolclass,
            "connect_args": self.config.connect_args,
        }

        # Only add pool sizing args for AsyncAdaptedQueuePool (PostgreSQL)
        if not is_sqlite:
            engine_kwargs.update({
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping,
            })

        self._engine = create_async_engine(
            self.config.database_url,
            **engine_kwargs,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def initialize(self) -> None:
        """
        Initialize pool and verify database connectivity.

        Raises:
            Exception: If database connection fails
        """
        if self._initialized:
            _log("warning", "db_pool_already_initialized")
            return

        _log("info", "db_pool_initializing")

        # Test connectivity
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            self._initialized = True
            _log("info", "db_pool_initialized", success=True)
        except Exception as e:
            _log("error", "db_pool_initialization_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def close(self) -> None:
        """Close all connections and dispose of engine."""
        if self._engine:
            _log("info", "db_pool_closing")
            await self._engine.dispose()
            self._initialized = False
            _log("info", "db_pool_closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session (context manager).

        Yields:
            AsyncSession: Database session with automatic commit/rollback

        Example:
            >>> async with pool.get_session() as session:
            ...     result = await session.execute(select(User))
            ...     users = result.scalars().all()
        """
        if not self._initialized:
            await self.initialize()

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Simple health check (returns boolean).

        Returns:
            bool: True if database is reachable, False otherwise
        """
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            _log("error", "db_health_check_failed", error=str(e))
            return False

    async def health_check_detailed(self) -> PoolHealth:
        """
        Detailed health check with pool metrics.

        Returns:
            PoolHealth: Comprehensive pool health status

        Example:
            >>> health = await pool.health_check_detailed()
            >>> print(f"Pool utilization: {health.utilization_percent}%")
            >>> print(f"Available connections: {health.available_connections}")
        """
        start_time = time.perf_counter()
        healthy = False

        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as healthy"))
                row = result.fetchone()
                healthy = row[0] == 1 if row else False
        except Exception as e:
            _log("error", "db_health_check_query_failed", error=str(e))

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Determine database type
        database_type = "sqlite" if "sqlite" in self.config.database_url else "postgresql"

        # Create health status from pool metrics
        return PoolHealth.from_pool(
            pool_obj=self._engine.pool,
            latency_ms=latency_ms,
            database_type=database_type,
            healthy=healthy,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Get SQLAlchemy async engine (for advanced use cases)."""
        return self._engine

    @property
    def is_initialized(self) -> bool:
        """Check if pool has been initialized."""
        return self._initialized

    @classmethod
    def from_env(cls) -> "AsyncDatabasePool":
        """
        Create pool from environment variables.

        Loads configuration from DB_* environment variables.

        Returns:
            AsyncDatabasePool: Configured pool instance

        Example:
            >>> # Requires: DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, etc.
            >>> pool = AsyncDatabasePool.from_env()
        """
        config = PoolConfig()
        return cls(config=config)
