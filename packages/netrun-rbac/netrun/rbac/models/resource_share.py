"""
Netrun RBAC Resource Share Model - Share any resource with users, teams, or tenants.

Following Netrun Systems SDLC v2.3 standards.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from .mixins import TenantMixin, AuditMixin
from .enums import SharePermission


class ResourceShare(TenantMixin, AuditMixin):
    """
    Share any resource with users, teams, or across tenants.

    Supports multiple sharing targets:
    - shared_with_user_id: Share with specific user
    - shared_with_team_id: Share with entire team (includes sub-teams)
    - shared_with_tenant_id: Share with entire tenant (cross-tenant sharing)
    - shared_externally: Share via email link (for external collaborators)

    Only one sharing target should be set per record.

    This is a mixin-style model that should be combined with your Base class:

        from sqlalchemy.orm import declarative_base
        from netrun.rbac.models import ResourceShare

        Base = declarative_base()

        class ResourceShareModel(Base, ResourceShare):
            __tablename__ = "resource_shares"

    Attributes:
        id: Primary key UUID
        tenant_id: Owning tenant (from TenantMixin)
        resource_type: Type of resource being shared (e.g., "contact", "document")
        resource_id: UUID of the shared resource
        shared_with_user_id: Target user UUID (mutually exclusive)
        shared_with_team_id: Target team UUID (mutually exclusive)
        shared_with_tenant_id: Target tenant UUID for cross-tenant (mutually exclusive)
        shared_externally: Email address for external sharing (mutually exclusive)
        permission: Permission level (view, comment, edit, full)
        expires_at: Optional expiration timestamp
        shared_by: UUID of user who created the share
        message: Optional message/note for the share recipient
        access_count: Number of times share was accessed
        last_accessed_at: Last access timestamp
    """

    __tablename__ = "resource_shares"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Share primary key"
    )

    # Resource being shared
    resource_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of resource (e.g., 'contact', 'document')"
    )

    resource_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the shared resource"
    )

    # Sharing targets (mutually exclusive - only one should be set)
    shared_with_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Target user UUID"
    )

    shared_with_team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Target team UUID"
    )

    shared_with_tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Target tenant UUID for cross-tenant sharing"
    )

    shared_externally = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Email address for external sharing"
    )

    # Permission level
    permission = Column(
        String(20),
        default=SharePermission.VIEW.value,
        nullable=False,
        comment="Permission: view, comment, edit, full"
    )

    # Expiration
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Share expiration timestamp"
    )

    # Who created the share
    shared_by = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of user who created share"
    )

    # Optional message
    message = Column(
        String(500),
        nullable=True,
        comment="Message/note for recipient"
    )

    # Access tracking
    access_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times accessed"
    )

    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last access timestamp"
    )

    # External share token (for email link sharing)
    external_token = Column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
        comment="Token for external share links"
    )

    # Metadata
    metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Additional share metadata"
    )

    # Soft delete
    is_revoked = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Share revocation flag"
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Revocation timestamp"
    )

    revoked_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of user who revoked share"
    )

    # Relationships (defined when used with actual Base)
    # team = relationship("Team", foreign_keys=[shared_with_team_id])
    # target_tenant = relationship("Tenant", foreign_keys=[shared_with_tenant_id])

    @declared_attr
    def __table_args__(cls):
        return (
            # Composite index for resource lookup
            Index("idx_resource_share_resource", "resource_type", "resource_id"),
            # Composite index for user shares
            Index("idx_resource_share_user", "shared_with_user_id", "is_revoked"),
            # Composite index for team shares
            Index("idx_resource_share_team", "shared_with_team_id", "is_revoked"),
            # Composite index for tenant shares
            Index("idx_resource_share_tenant_target", "shared_with_tenant_id", "is_revoked"),
            # Index for expiring shares cleanup
            Index("idx_resource_share_expires", "expires_at", postgresql_where="expires_at IS NOT NULL"),
            # Check constraint: at least one sharing target must be set
            CheckConstraint(
                """
                (shared_with_user_id IS NOT NULL)::int +
                (shared_with_team_id IS NOT NULL)::int +
                (shared_with_tenant_id IS NOT NULL)::int +
                (shared_externally IS NOT NULL)::int = 1
                """,
                name="chk_resource_share_one_target"
            ),
        )

    def __repr__(self) -> str:
        target = self._get_target_description()
        return f"<ResourceShare(resource={self.resource_type}:{self.resource_id}, {target}, permission='{self.permission}')>"

    def _get_target_description(self) -> str:
        """Get human-readable description of share target."""
        if self.shared_with_user_id:
            return f"user={self.shared_with_user_id}"
        if self.shared_with_team_id:
            return f"team={self.shared_with_team_id}"
        if self.shared_with_tenant_id:
            return f"tenant={self.shared_with_tenant_id}"
        if self.shared_externally:
            return f"external={self.shared_externally}"
        return "no_target"

    @property
    def is_active(self) -> bool:
        """Check if share is currently active (not revoked and not expired)."""
        if self.is_revoked:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if share has expired."""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return True
        return False

    @property
    def share_type(self) -> str:
        """Get the type of share (user, team, tenant, external)."""
        if self.shared_with_user_id:
            return "user"
        if self.shared_with_team_id:
            return "team"
        if self.shared_with_tenant_id:
            return "tenant"
        if self.shared_externally:
            return "external"
        return "unknown"

    def can_view(self) -> bool:
        """Check if share grants view permission."""
        return self.is_active

    def can_comment(self) -> bool:
        """Check if share grants comment permission."""
        return self.is_active and self.permission in (
            SharePermission.COMMENT.value,
            SharePermission.EDIT.value,
            SharePermission.FULL.value
        )

    def can_edit(self) -> bool:
        """Check if share grants edit permission."""
        return self.is_active and self.permission in (
            SharePermission.EDIT.value,
            SharePermission.FULL.value
        )

    def can_reshare(self) -> bool:
        """Check if share grants full permission (can re-share)."""
        return self.is_active and self.permission == SharePermission.FULL.value

    def record_access(self):
        """Record that the share was accessed."""
        self.access_count = (self.access_count or 0) + 1
        self.last_accessed_at = datetime.now(timezone.utc)

    def revoke(self, revoked_by_user_id):
        """Revoke the share."""
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_by = revoked_by_user_id


