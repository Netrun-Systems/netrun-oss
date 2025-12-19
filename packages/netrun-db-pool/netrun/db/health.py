"""Database pool health monitoring utilities."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class PoolHealth:
    """
    Database connection pool health status.

    Contains metrics for monitoring pool utilization and connection health.
    """

    # Overall health status
    healthy: bool
    status: Literal["healthy", "degraded", "unhealthy"]

    # Pool metrics
    pool_size: int
    checked_in: int  # Available connections
    checked_out: int  # In-use connections
    overflow: int  # Overflow connections created
    max_overflow: int  # Maximum allowed overflow

    # Performance metrics
    latency_ms: float

    # Metadata
    database_type: str
    timestamp: datetime

    @property
    def utilization_percent(self) -> float:
        """Calculate pool utilization percentage."""
        total = self.pool_size + self.max_overflow
        if total == 0:
            return 0.0
        return (self.checked_out / total) * 100

    @property
    def available_connections(self) -> int:
        """Calculate available connections (including overflow capacity)."""
        return (self.pool_size + self.max_overflow) - self.checked_out

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "healthy": self.healthy,
            "status": self.status,
            "pool_size": self.pool_size,
            "checked_in_connections": self.checked_in,
            "checked_out_connections": self.checked_out,
            "overflow_connections": self.overflow,
            "max_overflow": self.max_overflow,
            "utilization_percent": round(self.utilization_percent, 2),
            "available_connections": self.available_connections,
            "latency_ms": round(self.latency_ms, 2),
            "database": self.database_type,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_pool(
        cls,
        pool_obj: Any,
        latency_ms: float,
        database_type: str = "postgresql",
        healthy: bool = True,
    ) -> "PoolHealth":
        """
        Create PoolHealth from SQLAlchemy pool object.

        Args:
            pool_obj: SQLAlchemy pool instance
            latency_ms: Query latency in milliseconds
            database_type: Database type (postgresql, sqlite, etc.)
            healthy: Whether the health check query succeeded

        Returns:
            PoolHealth instance with current pool metrics
        """
        # NullPool/StaticPool (SQLite) don't have full pool metrics
        # Provide sensible defaults for these pool types
        has_pool_metrics = hasattr(pool_obj, "checkedout")

        if has_pool_metrics:
            checked_out = pool_obj.checkedout()
            pool_size = pool_obj.size()
            overflow = pool_obj.overflow()
            max_overflow = getattr(pool_obj, "_max_overflow", 0)
            checked_in = pool_obj.checkedin()
        else:
            # Default metrics for NullPool/StaticPool
            checked_out = 0
            pool_size = 1
            overflow = 0
            max_overflow = 0
            checked_in = 1

        # Calculate utilization for status determination
        total = pool_size + max_overflow
        utilization = (checked_out / total * 100) if total > 0 else 0

        # Determine status based on utilization
        if not healthy:
            status = "unhealthy"
        elif utilization >= 90:
            status = "degraded"
        else:
            status = "healthy"

        return cls(
            healthy=healthy,
            status=status,
            pool_size=pool_size,
            checked_in=checked_in,
            checked_out=checked_out,
            overflow=overflow,
            max_overflow=max_overflow,
            latency_ms=latency_ms,
            database_type=database_type,
            timestamp=datetime.now(timezone.utc),
        )
