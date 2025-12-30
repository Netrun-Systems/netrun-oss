"""
Netrun RBAC Mixins - Reusable SQLAlchemy mixins for tenant isolation and auditing.

Usage:
    from netrun.rbac.models import TenantMixin, TeamMixin, ShareableMixin, AuditMixin

    class Contact(Base, TenantMixin, TeamMixin, ShareableMixin, AuditMixin):
        __tablename__ = "contacts"
        id = Column(UUID, primary_key=True, default=uuid4)
        name = Column(String(200), nullable=False)
        email = Column(String(255))
"""

from datetime import datetime, timezone
from uuid import UUID as PyUUID

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr


class TenantMixin:
    """
    Mixin for multi-tenant models with data isolation.

    Adds:
    - tenant_id: UUID foreign key to tenants table (NOT NULL, indexed)
    - Composite index on tenant_id for query performance

    All queries should include tenant_id filter (enforced by TenantQueryService).
    """

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="Tenant ID for data isolation"
        )

    @declared_attr
    def __table_args__(cls):
        # Check if parent class already has __table_args__
        existing_args = getattr(super(), '__table_args__', ())
        if isinstance(existing_args, dict):
            return existing_args

        # Add tenant index if not present
        new_args = list(existing_args) if existing_args else []
        return tuple(new_args)


class TeamMixin:
    """
    Mixin for team-scoped resources.

    Adds:
    - team_id: Optional UUID foreign key to teams table (indexed)

    Resources with team_id are visible to team members.
    Resources without team_id are private to creator or tenant-wide based on share_level.
    """

    @declared_attr
    def team_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Team ID for group access (NULL = private or tenant-wide)"
        )


class ShareableMixin:
    """
    Mixin for resources that can be shared.

    Adds:
    - is_shared: Boolean flag for optimization
    - share_level: Default visibility level (private, team, tenant)

    Actual shares are stored in ResourceShare table.
    """

    @declared_attr
    def is_shared(cls):
        return Column(
            Boolean,
            default=False,
            nullable=False,
            comment="Quick flag for shared resources"
        )

    @declared_attr
    def share_level(cls):
        return Column(
            String(20),
            default="private",
            nullable=False,
            comment="Default visibility: private, team, tenant"
        )


class AuditMixin:
    """
    Mixin for audit trail.

    Adds:
    - created_at: Timestamp of creation (auto-set)
    - updated_at: Timestamp of last update (auto-update)
    - created_by: UUID of creating user
    - updated_by: UUID of last updating user
    """

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
            comment="Creation timestamp"
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
            comment="Last update timestamp"
        )

    @declared_attr
    def created_by(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            comment="UUID of creating user"
        )

    @declared_attr
    def updated_by(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            comment="UUID of last updating user"
        )


class SoftDeleteMixin:
    """
    Mixin for soft delete support.

    Adds:
    - is_deleted: Soft delete flag
    - deleted_at: Deletion timestamp
    - deleted_by: UUID of deleting user

    Queries should filter by is_deleted=False (handled by TenantQueryService).
    """

    @declared_attr
    def is_deleted(cls):
        return Column(
            Boolean,
            default=False,
            nullable=False,
            index=True,
            comment="Soft delete flag"
        )

    @declared_attr
    def deleted_at(cls):
        return Column(
            DateTime(timezone=True),
            nullable=True,
            comment="Soft delete timestamp"
        )

    @declared_attr
    def deleted_by(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            comment="UUID of deleting user"
        )
