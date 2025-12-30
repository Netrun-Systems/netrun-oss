"""
Netrun RBAC Membership Models - User membership in tenants and teams.

Following Netrun Systems SDLC v2.3 standards.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from .enums import TenantRole, TeamRole, InvitationStatus


class TenantMembership:
    """
    User membership in a tenant organization.

    This is a mixin-style model that should be combined with your Base class:

        from sqlalchemy.orm import declarative_base
        from netrun.rbac.models import TenantMembership

        Base = declarative_base()

        class TenantMembershipModel(Base, TenantMembership):
            __tablename__ = "tenant_memberships"

    Attributes:
        id: Primary key UUID
        tenant_id: Foreign key to tenant
        user_id: UUID of the user (from auth system)
        role: Role within the tenant (owner, admin, member, guest)
        is_active: Whether membership is active
        custom_permissions: Additional permissions beyond role (JSON array)
        invited_by: UUID of user who invited this member
        invited_at: When invitation was sent
        joined_at: When user accepted invitation
    """

    __tablename__ = "tenant_memberships"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Membership primary key"
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant foreign key"
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User UUID from auth system"
    )

    role = Column(
        String(20),
        default=TenantRole.MEMBER.value,
        nullable=False,
        comment="Role: owner, admin, member, guest"
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active membership flag"
    )

    # Custom permissions beyond the role
    custom_permissions = Column(
        JSONB,
        default=list,
        nullable=False,
        comment="Additional permissions array"
    )

    # Invitation tracking
    invited_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of inviting user"
    )

    invited_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Invitation timestamp"
    )

    joined_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Join/acceptance timestamp"
    )

    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Creation timestamp"
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="Last update timestamp"
    )

    # Relationships (defined when used with actual Base)
    # tenant = relationship("Tenant", back_populates="memberships")

    @declared_attr
    def __table_args__(cls):
        return (
            UniqueConstraint("tenant_id", "user_id", name="uq_tenant_membership_tenant_user"),
            Index("idx_tenant_membership_user_active", "user_id", "is_active"),
        )

    def __repr__(self) -> str:
        return f"<TenantMembership(tenant_id={self.tenant_id}, user_id={self.user_id}, role='{self.role}')>"

    @property
    def is_owner(self) -> bool:
        """Check if this membership has owner role."""
        return self.role == TenantRole.OWNER.value

    @property
    def is_admin(self) -> bool:
        """Check if this membership has admin or owner role."""
        return self.role in (TenantRole.OWNER.value, TenantRole.ADMIN.value)

    def has_permission(self, permission: str) -> bool:
        """Check if this membership has a custom permission."""
        return permission in (self.custom_permissions or [])


class TeamMembership:
    """
    User membership in a team.

    Supports both direct membership and inherited membership from parent teams.

    This is a mixin-style model that should be combined with your Base class:

        from sqlalchemy.orm import declarative_base
        from netrun.rbac.models import TeamMembership

        Base = declarative_base()

        class TeamMembershipModel(Base, TeamMembership):
            __tablename__ = "team_memberships"

    Attributes:
        id: Primary key UUID
        team_id: Foreign key to team
        user_id: UUID of the user (from auth system)
        role: Role within the team (owner, admin, member, guest)
        inherited_from: Team ID if membership is inherited from parent
        is_active: Whether membership is active
        custom_permissions: Additional permissions beyond role (JSON array)
    """

    __tablename__ = "team_memberships"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Membership primary key"
    )

    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Team foreign key"
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User UUID from auth system"
    )

    role = Column(
        String(20),
        default=TeamRole.MEMBER.value,
        nullable=False,
        comment="Role: owner, admin, member, guest"
    )

    # Inheritance tracking
    inherited_from = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Source team ID if inherited membership"
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active membership flag"
    )

    # Custom permissions beyond the role
    custom_permissions = Column(
        JSONB,
        default=list,
        nullable=False,
        comment="Additional permissions array"
    )

    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Creation timestamp"
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="Last update timestamp"
    )

    # Relationships (defined when used with actual Base)
    # team = relationship("Team", foreign_keys=[team_id], back_populates="memberships")
    # inherited_from_team = relationship("Team", foreign_keys=[inherited_from])

    @declared_attr
    def __table_args__(cls):
        return (
            UniqueConstraint("team_id", "user_id", name="uq_team_membership_team_user"),
            Index("idx_team_membership_user_active", "user_id", "is_active"),
            Index("idx_team_membership_inherited", "inherited_from"),
        )

    def __repr__(self) -> str:
        inherited = " (inherited)" if self.inherited_from else ""
        return f"<TeamMembership(team_id={self.team_id}, user_id={self.user_id}, role='{self.role}'{inherited})>"

    @property
    def is_direct(self) -> bool:
        """Check if this is a direct (not inherited) membership."""
        return self.inherited_from is None

    @property
    def is_inherited(self) -> bool:
        """Check if this membership is inherited from a parent team."""
        return self.inherited_from is not None

    @property
    def is_owner(self) -> bool:
        """Check if this membership has owner role."""
        return self.role == TeamRole.OWNER.value

    @property
    def is_admin(self) -> bool:
        """Check if this membership has admin or owner role."""
        return self.role in (TeamRole.OWNER.value, TeamRole.ADMIN.value)

    def has_permission(self, permission: str) -> bool:
        """Check if this membership has a custom permission."""
        return permission in (self.custom_permissions or [])


class TenantInvitation:
    """
    Invitation to join a tenant organization.

    This is a mixin-style model that should be combined with your Base class.

    Attributes:
        id: Primary key UUID
        tenant_id: Foreign key to tenant
        email: Email address of invitee
        role: Role to assign upon acceptance
        status: Invitation status (pending, accepted, declined, expired, revoked)
        token: Unique token for invitation link
        expires_at: When invitation expires
        invited_by: UUID of inviting user
    """

    __tablename__ = "tenant_invitations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Invitation primary key"
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant foreign key"
    )

    email = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Invitee email address"
    )

    role = Column(
        String(20),
        default=TenantRole.MEMBER.value,
        nullable=False,
        comment="Role to assign upon acceptance"
    )

    status = Column(
        String(20),
        default=InvitationStatus.PENDING.value,
        nullable=False,
        index=True,
        comment="Invitation status"
    )

    token = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique invitation token"
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Invitation expiration timestamp"
    )

    invited_by = Column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID of inviting user"
    )

    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Creation timestamp"
    )

    accepted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Acceptance timestamp"
    )

    # Relationships (defined when used with actual Base)
    # tenant = relationship("Tenant")

    @declared_attr
    def __table_args__(cls):
        return (
            Index("idx_tenant_invitation_tenant_email", "tenant_id", "email"),
            Index("idx_tenant_invitation_status_expires", "status", "expires_at"),
        )

    def __repr__(self) -> str:
        return f"<TenantInvitation(tenant_id={self.tenant_id}, email='{self.email}', status='{self.status}')>"

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending."""
        return self.status == InvitationStatus.PENDING.value

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        if self.status == InvitationStatus.EXPIRED.value:
            return True
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return True
        return False
