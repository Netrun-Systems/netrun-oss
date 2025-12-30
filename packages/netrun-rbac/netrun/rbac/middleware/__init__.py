"""
Netrun RBAC Middleware Module - FastAPI middleware for multi-tenant applications.

Following Netrun Systems SDLC v2.3 standards.

Provides a 3-layer middleware stack:
1. TenantResolutionMiddleware - Resolves tenant from request (header/JWT/subdomain)
2. IsolationEnforcementMiddleware - Sets up database isolation
3. TenantSecurityMiddleware - Security checks and audit logging

Usage:
    from netrun.rbac.middleware import setup_tenancy_middleware
    from netrun.rbac.tenancy import TenancyConfig

    app = FastAPI()
    config = TenancyConfig(require_tenant=True)
    setup_tenancy_middleware(app, config, get_session=get_db_session)

    # Or add individual middleware:
    from netrun.rbac.middleware import TenantResolutionMiddleware
    app.add_middleware(TenantResolutionMiddleware, config=config)
"""

from .tenant import TenantResolutionMiddleware
from .isolation import IsolationEnforcementMiddleware
from .security import TenantSecurityMiddleware
from .stack import setup_tenancy_middleware

__all__ = [
    # Individual middleware
    "TenantResolutionMiddleware",
    "IsolationEnforcementMiddleware",
    "TenantSecurityMiddleware",
    # Setup function
    "setup_tenancy_middleware",
]
