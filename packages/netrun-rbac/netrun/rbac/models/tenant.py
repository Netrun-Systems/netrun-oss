"""
Netrun RBAC Tenant Model - Organization container with subscription and limits.

Following Netrun Systems SDLC v2.3 standards.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .enums import TenantStatus


class Tenant:
    """
    Tenant model representing an organization in the multi-tenant system.

    This is a mixin-style model that should be combined with your Base class:

        from sqlalchemy.orm import declarative_base
        from netrun.rbac.models import Tenant

        Base = declarative_base()

        class TenantModel(Base, Tenant):
            __tablename__ = "tenants"

    Attributes:
        id: Primary key UUID
        name: Organization display name
        slug: URL-safe unique identifier (e.g., "acme-corp")
        domain: Optional custom domain for SSO/routing
        subscription_tier: Plan level (basic, pro, enterprise)
        status: Account status (trial, active, suspended, etc.)
        max_users: User limit for this tenant
        max_teams: Team limit for this tenant
        settings: Tenant-specific configuration (JSON)
        security_settings: Security policies (JSON)
        enabled_features: Feature flags (JSON array)
        billing_email: Email for billing notifications
        technical_contact: Email for technical notifications
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Tenant primary key"
    )

    name = Column(
        String(255),
        nullable=False,
        comment="Organization display name"
    )

    slug = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="URL-safe unique identifier"
    )

    domain = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Custom domain for SSO/routing"
    )

    # Subscription management
    subscription_tier = Column(
        String(50),
        default="basic",
        nullable=False,
        comment="Plan level: basic, pro, enterprise"
    )

    status = Column(
        String(20),
        default=TenantStatus.TRIAL.value,
        nullable=False,
        index=True,
        comment="Account status"
    )

    # Resource limits
    max_users = Column(
        Integer,
        default=10,
        nullable=False,
        comment="Maximum users allowed"
    )

    max_teams = Column(
        Integer,
        default=20,
        nullable=False,
        comment="Maximum teams allowed"
    )

    max_storage_gb = Column(
        Integer,
        default=10,
        nullable=False,
        comment="Maximum storage in GB"
    )

    # Configuration (JSON columns)
    settings = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Tenant-specific configuration"
    )

    security_settings = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Security policies (MFA, IP allowlist, etc.)"
    )

    enabled_features = Column(
        JSONB,
        default=list,
        nullable=False,
        comment="Feature flags array"
    )

    # Contact information
    billing_email = Column(
        String(255),
        nullable=True,
        comment="Email for billing notifications"
    )

    technical_contact = Column(
        String(255),
        nullable=True,
        comment="Email for technical notifications"
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

    # Soft delete
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Soft delete flag"
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp"
    )

    # Relationships (defined when used with actual Base)
    # teams = relationship("Team", back_populates="tenant", lazy="dynamic")
    # memberships = relationship("TenantMembership", back_populates="tenant", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, slug='{self.slug}', status='{self.status}')>"

    @property
    def is_active(self) -> bool:
        """Check if tenant is in active status."""
        return self.status == TenantStatus.ACTIVE.value and not self.is_deleted

    @property
    def can_add_users(self) -> bool:
        """Check if tenant can add more users (requires membership count check)."""
        return self.is_active

    @property
    def can_add_teams(self) -> bool:
        """Check if tenant can add more teams (requires team count check)."""
        return self.is_active

    def has_feature(self, feature_name: str) -> bool:
        """Check if a feature is enabled for this tenant."""
        return feature_name in (self.enabled_features or [])

    def get_setting(self, key: str, default=None):
        """Get a tenant setting by key."""
        return (self.settings or {}).get(key, default)

    def get_security_setting(self, key: str, default=None):
        """Get a security setting by key."""
        return (self.security_settings or {}).get(key, default)
