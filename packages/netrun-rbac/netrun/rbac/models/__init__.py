"""
Netrun RBAC Models - SQLAlchemy models for multi-tenant RBAC with hierarchical teams.

Models:
- Tenant: Organization container with subscription and limits
- Team: Hierarchical team with materialized path
- TenantMembership: User membership in a tenant
- TeamMembership: User membership in a team
- ResourceShare: Resource sharing across users/teams/tenants

Mixins:
- TenantMixin: Add tenant_id FK to any model
- TeamMixin: Add optional team_id FK
- ShareableMixin: Mark resource as shareable
- AuditMixin: Add created_at, updated_at, created_by, updated_by
"""

from .enums import (
    TenantRole,
    TeamRole,
    SharePermission,
    TenantStatus,
    IsolationMode,
    InvitationStatus,
)
from .mixins import (
    TenantMixin,
    TeamMixin,
    ShareableMixin,
    AuditMixin,
    SoftDeleteMixin,
)
from .tenant import Tenant
from .team import Team
from .membership import TenantMembership, TeamMembership, TenantInvitation
from .resource_share import ResourceShare

__all__ = [
    # Enums
    "TenantRole",
    "TeamRole",
    "SharePermission",
    "TenantStatus",
    "IsolationMode",
    "InvitationStatus",
    # Mixins
    "TenantMixin",
    "TeamMixin",
    "ShareableMixin",
    "AuditMixin",
    "SoftDeleteMixin",
    # Models
    "Tenant",
    "Team",
    "TenantMembership",
    "TeamMembership",
    "TenantInvitation",
    "ResourceShare",
]
