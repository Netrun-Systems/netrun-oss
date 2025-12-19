"""
Backwards compatibility shim for netrun-db-pool middleware.

DEPRECATED: Please use netrun.db.middleware instead:

    # Old (deprecated)
    from netrun_db_pool.middleware import get_db_dependency

    # New (recommended)
    from netrun.db.middleware import get_db_dependency

This shim will be removed in version 3.0.0 (estimated: Q2 2026).
"""

import warnings

warnings.warn(
    "The 'netrun_db_pool.middleware' module is deprecated. "
    "Please update your imports to use 'netrun.db.middleware' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from netrun.db.middleware import (
    TenantContextMiddleware,
    get_db_dependency,
    get_tenant_db_dependency,
)

__all__ = [
    "get_db_dependency",
    "get_tenant_db_dependency",
    "TenantContextMiddleware",
]
