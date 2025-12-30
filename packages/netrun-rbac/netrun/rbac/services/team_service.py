"""
Netrun RBAC Team Service - Team management with hierarchy support.

Following Netrun Systems SDLC v2.3 standards.

Provides operations for hierarchical team management including:
- Creating teams with parent/child relationships
- Managing team memberships
- Querying team hierarchies
- Inheritance of permissions through hierarchy
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.team import Team
from ..models.membership import TeamMembership
from ..models.enums import TeamRole
from ..tenancy.context import TenantContext
from ..tenancy.exceptions import TenantContextError, TeamAccessDeniedError

logger = logging.getLogger(__name__)


class TeamService:
    """
    Service for hierarchical team management.

    Handles team CRUD operations with hierarchy support using
    the materialized path pattern.

    Attributes:
        session: SQLAlchemy async session
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the team service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, team_id: UUID) -> Optional[Team]:
        """
        Get a team by ID within current tenant.

        Args:
            team_id: UUID of the team

        Returns:
            Team if found and in current tenant, None otherwise
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(Team).where(
                Team.id == team_id,
                Team.tenant_id == ctx.tenant_id,
                Team.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        parent_team_id: Optional[UUID] = None,
        settings: Optional[Dict[str, Any]] = None,
        is_public: bool = False,
        max_members: int = 100,
    ) -> Team:
        """
        Create a new team with optional parent.

        Args:
            name: Team display name
            description: Team description
            parent_team_id: UUID of parent team (None for root team)
            settings: Team configuration
            is_public: Whether team is visible to all tenant members
            max_members: Maximum members allowed

        Returns:
            Created Team

        Raises:
            TenantContextError: If tenant context is not set
            TeamAccessDeniedError: If parent team doesn't exist or not accessible
        """
        ctx = TenantContext.require()

        # Calculate path and depth from parent
        path = "/"
        depth = 0

        if parent_team_id:
            parent = await self.get_by_id(parent_team_id)
            if not parent:
                raise TeamAccessDeniedError(
                    team_id=parent_team_id,
                    reason="Parent team not found"
                )
            depth = parent.depth + 1

        # Create team first to get ID for path
        team = Team(
            id=uuid4(),
            tenant_id=ctx.tenant_id,
            name=name,
            description=description,
            parent_team_id=parent_team_id,
            path="/",  # Placeholder
            depth=depth,
            settings=settings or {},
            is_public=is_public,
            max_members=max_members,
            created_by=ctx.user_id,
        )

        self.session.add(team)
        await self.session.flush()

        # Update path with actual ID
        if parent_team_id:
            parent = await self.get_by_id(parent_team_id)
            team.path = f"{parent.path}/{team.id}"
        else:
            team.path = f"/{team.id}"

        await self.session.flush()

        logger.info(
            f"Created team '{name}' (id={team.id}) at depth {depth} "
            f"in tenant {ctx.tenant_id}"
        )

        return team

    async def update(
        self,
        team_id: UUID,
        **updates
    ) -> Optional[Team]:
        """
        Update team fields.

        Args:
            team_id: UUID of the team
            **updates: Fields to update

        Returns:
            Updated team or None if not found
        """
        team = await self.get_by_id(team_id)
        if not team:
            return None

        # Protected fields
        protected = {"id", "tenant_id", "path", "depth", "parent_team_id", "created_at"}

        ctx = TenantContext.get_current()

        for key, value in updates.items():
            if key not in protected and hasattr(team, key):
                setattr(team, key, value)

        if ctx and ctx.user_id:
            team.updated_by = ctx.user_id

        await self.session.flush()

        return team

    async def delete(
        self,
        team_id: UUID,
        *,
        cascade_children: bool = False,
    ) -> bool:
        """
        Soft delete a team.

        Args:
            team_id: UUID of the team
            cascade_children: If True, also delete child teams

        Returns:
            True if deleted, False if not found
        """
        team = await self.get_by_id(team_id)
        if not team:
            return False

        ctx = TenantContext.require()

        if cascade_children:
            # Delete all descendants
            children = await self.get_descendants(team_id)
            for child in children:
                child.is_deleted = True
                if ctx.user_id:
                    child.deleted_by = ctx.user_id

        # Delete the team itself
        team.is_deleted = True
        if ctx.user_id:
            team.deleted_by = ctx.user_id

        from datetime import datetime, timezone
        team.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()

        logger.info(f"Deleted team {team_id} (cascade={cascade_children})")

        return True

    async def get_root_teams(self) -> List[Team]:
        """
        Get all root teams (no parent) in current tenant.

        Returns:
            List of root teams
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(Team).where(
                Team.tenant_id == ctx.tenant_id,
                Team.parent_team_id.is_(None),
                Team.is_deleted == False
            ).order_by(Team.name)
        )
        return list(result.scalars().all())

    async def get_children(self, team_id: UUID) -> List[Team]:
        """
        Get direct children of a team.

        Args:
            team_id: UUID of the parent team

        Returns:
            List of child teams
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(Team).where(
                Team.tenant_id == ctx.tenant_id,
                Team.parent_team_id == team_id,
                Team.is_deleted == False
            ).order_by(Team.name)
        )
        return list(result.scalars().all())

    async def get_descendants(self, team_id: UUID) -> List[Team]:
        """
        Get all descendants of a team using materialized path.

        Args:
            team_id: UUID of the ancestor team

        Returns:
            List of descendant teams
        """
        ctx = TenantContext.require()

        # Get the team's path first
        team = await self.get_by_id(team_id)
        if not team:
            return []

        # Find all teams whose path starts with this team's path
        result = await self.session.execute(
            select(Team).where(
                Team.tenant_id == ctx.tenant_id,
                Team.path.like(f"{team.path}/%"),
                Team.is_deleted == False
            ).order_by(Team.depth, Team.name)
        )
        return list(result.scalars().all())

    async def get_ancestors(self, team_id: UUID) -> List[Team]:
        """
        Get all ancestors of a team.

        Args:
            team_id: UUID of the descendant team

        Returns:
            List of ancestor teams (root first)
        """
        ctx = TenantContext.require()

        team = await self.get_by_id(team_id)
        if not team:
            return []

        # Get ancestor IDs from path
        ancestor_ids = team.get_ancestor_ids()
        if not ancestor_ids:
            return []

        result = await self.session.execute(
            select(Team).where(
                Team.tenant_id == ctx.tenant_id,
                Team.id.in_(ancestor_ids),
                Team.is_deleted == False
            ).order_by(Team.depth)
        )
        return list(result.scalars().all())

    async def get_user_teams(
        self,
        user_id: UUID,
        *,
        include_inherited: bool = True,
    ) -> List[Team]:
        """
        Get all teams a user belongs to.

        Args:
            user_id: UUID of the user
            include_inherited: Include teams accessible via parent membership

        Returns:
            List of teams user can access
        """
        ctx = TenantContext.require()

        # Get direct memberships
        result = await self.session.execute(
            select(Team)
            .join(TeamMembership, TeamMembership.team_id == Team.id)
            .where(
                Team.tenant_id == ctx.tenant_id,
                TeamMembership.user_id == user_id,
                TeamMembership.is_active == True,
                Team.is_deleted == False
            )
        )
        teams = list(result.scalars().all())

        if include_inherited:
            # For each team, include its descendants (user inherits access)
            all_team_ids = set(t.id for t in teams)
            for team in teams:
                descendants = await self.get_descendants(team.id)
                for desc in descendants:
                    if desc.id not in all_team_ids:
                        all_team_ids.add(desc.id)
                        teams.append(desc)

        return teams

    async def get_user_team_ids(
        self,
        user_id: UUID,
        *,
        include_inherited: bool = True,
    ) -> List[UUID]:
        """
        Get all team IDs a user can access.

        Args:
            user_id: UUID of the user
            include_inherited: Include teams accessible via parent membership

        Returns:
            List of accessible team UUIDs
        """
        teams = await self.get_user_teams(user_id, include_inherited=include_inherited)
        return [t.id for t in teams]

    async def get_user_team_paths(
        self,
        user_id: UUID,
    ) -> List[str]:
        """
        Get materialized paths for user's teams.

        Useful for hierarchy-based access checks.

        Args:
            user_id: UUID of the user

        Returns:
            List of team paths
        """
        teams = await self.get_user_teams(user_id, include_inherited=False)
        return [t.path for t in teams]

    async def add_member(
        self,
        team_id: UUID,
        user_id: UUID,
        *,
        role: TeamRole = TeamRole.MEMBER,
    ) -> TeamMembership:
        """
        Add a user to a team.

        Args:
            team_id: UUID of the team
            user_id: UUID of the user
            role: Role in the team

        Returns:
            Created TeamMembership

        Raises:
            TeamAccessDeniedError: If team doesn't exist
        """
        team = await self.get_by_id(team_id)
        if not team:
            raise TeamAccessDeniedError(
                team_id=team_id,
                reason="Team not found"
            )

        # Check if already a member
        existing = await self.session.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
            )
        )
        membership = existing.scalar_one_or_none()

        if membership:
            # Reactivate if inactive
            membership.is_active = True
            membership.role = role.value
        else:
            membership = TeamMembership(
                id=uuid4(),
                team_id=team_id,
                user_id=user_id,
                role=role.value,
            )
            self.session.add(membership)

        await self.session.flush()

        logger.info(f"Added user {user_id} to team {team_id} as {role.value}")

        return membership

    async def remove_member(
        self,
        team_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Remove a user from a team.

        Args:
            team_id: UUID of the team
            user_id: UUID of the user

        Returns:
            True if removed, False if not a member
        """
        result = await self.session.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            return False

        membership.is_active = False
        await self.session.flush()

        logger.info(f"Removed user {user_id} from team {team_id}")

        return True

    async def is_member(
        self,
        team_id: UUID,
        user_id: UUID,
        *,
        include_inherited: bool = True,
    ) -> bool:
        """
        Check if user is a member of a team.

        Args:
            team_id: UUID of the team
            user_id: UUID of the user
            include_inherited: Check parent team memberships

        Returns:
            True if user is a member
        """
        team_ids = await self.get_user_team_ids(
            user_id, include_inherited=include_inherited
        )
        return team_id in team_ids

    async def get_team_tree(self) -> List[Dict[str, Any]]:
        """
        Get full team hierarchy as a tree structure.

        Returns:
            List of root teams with nested children
        """
        root_teams = await self.get_root_teams()

        async def build_tree(team: Team) -> Dict[str, Any]:
            children = await self.get_children(team.id)
            return {
                "id": str(team.id),
                "name": team.name,
                "path": team.path,
                "depth": team.depth,
                "children": [await build_tree(c) for c in children]
            }

        return [await build_tree(t) for t in root_teams]
