"""
Backwards compatibility shim for netrun-db-pool.

DEPRECATED: This module provides backwards compatibility for code using the old
netrun_db_pool import path. New code should use the netrun.db namespace:

    # Old (deprecated, but still works)
    from netrun_db_pool import AsyncDatabasePool

    # New (recommended)
    from netrun.db import AsyncDatabasePool

This shim will be removed in version 3.0.0 (estimated: Q2 2026).
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "The 'netrun_db_pool' module is deprecated and will be removed in version 3.0.0. "
    "Please update your imports to use 'netrun.db' instead:\n"
    "  from netrun.db import AsyncDatabasePool, TenantAwareDatabasePool, PoolConfig, PoolHealth\n"
    "See https://github.com/netrunsystems/netrun-db-pool for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from netrun.db import (
    AsyncDatabasePool,
    PoolConfig,
    PoolHealth,
    TenantAwareDatabasePool,
)

__version__ = "2.0.0"
__all__ = [
    "AsyncDatabasePool",
    "TenantAwareDatabasePool",
    "PoolConfig",
    "PoolHealth",
]
