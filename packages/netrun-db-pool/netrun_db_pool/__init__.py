"""
netrun-db-pool: Production-grade database connection pooling for Netrun Systems services.

Provides async PostgreSQL connection pools with multi-tenant RLS support,
health monitoring, and FastAPI integration.

v1.1.0: Added netrun-logging integration for structured database operation logging
"""

from netrun_db_pool.config import PoolConfig
from netrun_db_pool.health import PoolHealth
from netrun_db_pool.pool import AsyncDatabasePool
from netrun_db_pool.tenant import TenantAwareDatabasePool

__version__ = "1.1.0"
__all__ = [
    "AsyncDatabasePool",
    "TenantAwareDatabasePool",
    "PoolConfig",
    "PoolHealth",
]
