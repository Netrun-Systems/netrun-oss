"""
Netrun RBAC Team Model - Hierarchical team with materialized path.

Following Netrun Systems SDLC v2.3 standards.

Hierarchy is managed using the materialized path pattern for efficient
ancestor/descendant queries without recursive CTEs.

Example path structure:
    /sales                      (depth=0, root team)
    /sales/enterprise           (depth=1, child of sales)
    /sales/enterprise/west      (depth=2, grandchild)

Querying descendants: WHERE path LIKE '/sales/%'
Querying ancestors: Split path and query by IDs
"""

from datetime import datetime, timezone
from uuid import uuid4, UUID as PyUUID

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from .mixins import TenantMixin, AuditMixin, SoftDeleteMixin


class Team(TenantMixin, AuditMixin, SoftDeleteMixin):
    """
    Hierarchical team model with parent/child relationships.

    Uses materialized path pattern for efficient hierarchy queries.

    This is a mixin-style model that should be combined with your Base class:

        from sqlalchemy.orm import declarative_base
        from netrun.rbac.models import Team

        Base = declarative_base()

        class TeamModel(Base, Team):
            __tablename__ = "teams"

    Attributes:
        id: Primary key UUID
        tenant_id: Foreign key to tenant (from TenantMixin)
        name: Team display name
        description: Optional team description
        parent_team_id: Foreign key to parent team (NULL for root teams)
        path: Materialized path string (e.g., "/parent-id/this-id")
        depth: Depth in hierarchy (0 = root)
        settings: Team-specific configuration (JSON)
        is_public: Whether team is visible to all tenant members
        max_members: Maximum members allowed in this team
    """

    __tablename__ = "teams"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Team primary key"
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Team display name"
    )

    description = Column(
        Text,
        nullable=True,
        comment="Team description"
    )

    # Hierarchy columns
    parent_team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Parent team ID (NULL for root teams)"
    )

    path = Column(
        String(1000),
        nullable=False,
        default="/",
        index=True,
        comment="Materialized path for hierarchy queries"
    )

    depth = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Depth in hierarchy (0 = root)"
    )

    # Team settings
    settings = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Team-specific configuration"
    )

    is_public = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Visible to all tenant members"
    )

    max_members = Column(
        Integer,
        default=100,
        nullable=False,
        comment="Maximum members allowed"
    )

    # Relationships (defined when used with actual Base)
    # parent = relationship("Team", remote_side=[id], backref="children")
    # memberships = relationship("TeamMembership", back_populates="team", lazy="dynamic")

    @declared_attr
    def __table_args__(cls):
        return (
            # Index for hierarchy queries (path prefix matching)
            Index('idx_teams_path_prefix', 'path', postgresql_ops={'path': 'text_pattern_ops'}),
            # Composite index for tenant + parent queries
            Index('idx_teams_tenant_parent', 'tenant_id', 'parent_team_id'),
            # Composite index for tenant + depth queries
            Index('idx_teams_tenant_depth', 'tenant_id', 'depth'),
        )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', depth={self.depth})>"

    def build_path(self, parent_path: str = None) -> str:
        """
        Build the materialized path for this team.

        Args:
            parent_path: The path of the parent team (or None for root)

        Returns:
            The new path string
        """
        if parent_path is None or parent_path == "/":
            return f"/{self.id}"
        return f"{parent_path}/{self.id}"

    def get_ancestor_ids(self) -> list[PyUUID]:
        """
        Extract ancestor team IDs from the materialized path.

        Returns:
            List of UUIDs representing ancestors (root first)
        """
        if not self.path or self.path == "/":
            return []

        parts = self.path.strip("/").split("/")
        # Exclude self (last element)
        ancestor_parts = parts[:-1] if len(parts) > 1 else []

        return [PyUUID(part) for part in ancestor_parts if part]

    def is_ancestor_of(self, other_path: str) -> bool:
        """
        Check if this team is an ancestor of another team.

        Args:
            other_path: The path of the potential descendant

        Returns:
            True if this team is an ancestor
        """
        if not other_path:
            return False
        return other_path.startswith(self.path + "/")

    def is_descendant_of(self, ancestor_path: str) -> bool:
        """
        Check if this team is a descendant of another team.

        Args:
            ancestor_path: The path of the potential ancestor

        Returns:
            True if this team is a descendant
        """
        if not ancestor_path or not self.path:
            return False
        return self.path.startswith(ancestor_path + "/")

    @property
    def is_root(self) -> bool:
        """Check if this is a root team (no parent)."""
        return self.parent_team_id is None

    def get_setting(self, key: str, default=None):
        """Get a team setting by key."""
        return (self.settings or {}).get(key, default)
