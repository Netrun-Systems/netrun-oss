"""Database pool configuration management using Pydantic settings."""

from typing import Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PoolConfig(BaseSettings):
    """
    Database connection pool configuration.

    Supports environment variable configuration with DB_ prefix.
    Example: DB_POOL_SIZE=20, DB_MAX_OVERFLOW=10
    """

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Connection settings
    database_url: str = Field(
        ...,
        description="Database connection URL (postgresql+asyncpg://user:pass@host/db)",
        validation_alias=AliasChoices("DATABASE_URL", "DB_DATABASE_URL", "database_url"),
    )

    # Pool size settings
    pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of connections to maintain in pool",
    )

    max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum overflow connections beyond pool_size",
    )

    pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Seconds to wait for connection before timeout",
    )

    pool_recycle: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Seconds before recycling connections (prevents stale connections)",
    )

    # Connection health settings
    pool_pre_ping: bool = Field(
        default=True,
        description="Test connections before using (recommended for production)",
    )

    # Query settings
    command_timeout: Optional[int] = Field(
        default=60,
        ge=1,
        le=600,
        description="Query timeout in seconds (PostgreSQL specific)",
    )

    # PostgreSQL optimization
    enable_jit: bool = Field(
        default=False,
        description="Enable JIT compilation (disable for consistent query planning)",
    )

    # Application identification
    app_name: str = Field(
        default="netrun-service",
        description="Application name for PostgreSQL connection tracking",
    )

    # Logging
    echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging (use in development only)",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure asyncpg driver is specified for PostgreSQL URLs."""
        if v.startswith("postgresql://"):
            # Auto-convert to asyncpg driver
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql+asyncpg://"):
            return v
        elif v.startswith("sqlite"):
            # Allow SQLite for testing (requires aiosqlite)
            if not v.startswith("sqlite+aiosqlite://"):
                return v.replace("sqlite://", "sqlite+aiosqlite://", 1)
            return v
        else:
            raise ValueError(
                f"Unsupported database URL scheme: {v}. "
                "Use postgresql+asyncpg:// or sqlite+aiosqlite://"
            )

    @property
    def connect_args(self) -> dict:
        """Generate PostgreSQL-specific connection arguments."""
        if "postgresql" in self.database_url:
            args = {
                "server_settings": {
                    "application_name": self.app_name,
                    "jit": "on" if self.enable_jit else "off",
                }
            }
            if self.command_timeout:
                args["command_timeout"] = self.command_timeout
            return args
        return {}

    @property
    def total_max_connections(self) -> int:
        """Calculate total maximum connections (pool_size + max_overflow)."""
        return self.pool_size + self.max_overflow
