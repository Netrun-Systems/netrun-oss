"""
Netrun RBAC Enums - Role, permission, and status enumerations.

Following Netrun Systems SDLC v2.3 standards.
"""

from enum import Enum


class TenantRole(str, Enum):
    """Role within a tenant organization."""

    OWNER = "owner"      # Full control, billing, can delete tenant
    ADMIN = "admin"      # Manage members, settings, full CRUD
    MEMBER = "member"    # Standard access, can create/edit own resources
    GUEST = "guest"      # Read-only access, limited visibility


class TeamRole(str, Enum):
    """Role within a team/group."""

    OWNER = "owner"      # Full control over team, can delete
    ADMIN = "admin"      # Can add/remove members, manage settings
    MEMBER = "member"    # Standard team member, can access team resources
    GUEST = "guest"      # View-only access to team resources


class SharePermission(str, Enum):
    """Permission level for shared resources."""

    VIEW = "view"        # Read-only access
    COMMENT = "comment"  # Can add comments/annotations
    EDIT = "edit"        # Can modify the resource
    FULL = "full"        # Full control including re-sharing


class TenantStatus(str, Enum):
    """Tenant account status."""

    TRIAL = "trial"          # Trial period, limited features
    ACTIVE = "active"        # Active subscription
    SUSPENDED = "suspended"  # Suspended for non-payment or policy violation
    CANCELLED = "cancelled"  # Subscription cancelled, data retained
    ARCHIVED = "archived"    # Archived, minimal data access


class IsolationMode(str, Enum):
    """Database isolation strategy."""

    RLS = "rls"              # PostgreSQL Row-Level Security only
    APPLICATION = "app"      # Application-level filtering only
    HYBRID = "hybrid"        # Both RLS and application checks (recommended)


class InvitationStatus(str, Enum):
    """Status of tenant/team invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"
