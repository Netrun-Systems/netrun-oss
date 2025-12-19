"""
netrun-db-pool: Production-grade database connection pooling for Netrun Systems services.

Provides async PostgreSQL connection pools with multi-tenant RLS support,
health monitoring, and FastAPI integration.

v2.0.0: Migrated to netrun.db namespace structure
v1.1.0: Added netrun-logging integration for structured database operation logging
"""

from netrun.db.config import PoolConfig
from netrun.db.health import PoolHealth
from netrun.db.pool import AsyncDatabasePool
from netrun.db.tenant import TenantAwareDatabasePool

__version__ = "2.0.0"
__all__ = [
    "AsyncDatabasePool",
    "TenantAwareDatabasePool",
    "PoolConfig",
    "PoolHealth",
]
