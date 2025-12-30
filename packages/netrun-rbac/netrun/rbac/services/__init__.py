"""
Netrun RBAC Services Module - Query and business logic services.

Following Netrun Systems SDLC v2.3 standards.

Provides tenant-aware services:
- TenantQueryService: Generic query service with auto-filtering
- TenantService: CRUD operations for tenants
- TeamService: Team management with hierarchy
- MembershipService: User membership management
- ShareService: Resource sharing operations

Usage:
    from netrun.rbac.services import TenantQueryService
    from myapp.models import Contact

    # In route handler
    async def list_contacts(session = Depends(get_session)):
        service = TenantQueryService(session, Contact)
        return await service.get_all()
"""

from .tenant_query import TenantQueryService
from .tenant_service import TenantService
from .team_service import TeamService
from .membership_service import MembershipService
from .share_service import ShareService

__all__ = [
    "TenantQueryService",
    "TenantService",
    "TeamService",
    "MembershipService",
    "ShareService",
]
