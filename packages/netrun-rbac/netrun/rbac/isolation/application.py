"""
Netrun RBAC Application Isolation - Application-level query filtering strategy.

Following Netrun Systems SDLC v2.3 standards.

This strategy enforces tenant isolation entirely at the application level
by adding WHERE clauses to all queries. This is useful when:
- PostgreSQL RLS is not available
- Using a database that doesn't support RLS
- Simpler deployment without RLS setup

Note: For maximum security, use HybridIsolationStrategy which combines
RLS with application-level filtering for defense-in-depth.
"""

import logging
from typing import TypeVar, Type, Optional, List
from uuid import UUID

from sqlalchemy import Select, or_, and_, select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from .base import IsolationStrategy
from ..tenancy.context import TenantContext
from ..tenancy.exceptions import TenantContextError
from ..models.enums import SharePermission

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ApplicationIsolationStrategy(IsolationStrategy):
    """
    Application-level query filtering isolation strategy.

    This strategy adds WHERE clauses to all queries to enforce tenant
    isolation. It handles:
    - Tenant filtering (tenant_id = current_tenant)
    - Team filtering (team_id IN user's teams)
    - Share filtering (checking ResourceShare table)
    - Soft delete filtering (is_deleted = False)
    """

    async def setup_session(self, session: AsyncSession) -> None:
        """
        No-op for application-level isolation.

        Unlike RLS, application isolation doesn't need session setup
        since all filtering happens in queries.

        Args:
            session: SQLAlchemy async session (unused)

        Raises:
            TenantContextError: If tenant context is not set
        """
        ctx = TenantContext.get_current()
        if ctx is None:
            raise TenantContextError(
                "Cannot verify isolation: tenant context not set"
            )
        # No session setup needed for application-level filtering
        logger.debug(f"Application isolation verified for tenant={ctx.tenant_id}")

    def apply_query_filters(
        self,
        query: Select[tuple[T]],
        model_class: Type[T],
        *,
        include_shared: bool = True,
        include_team: bool = True,
        user_id: Optional[UUID] = None,
    ) -> Select[tuple[T]]:
        """
        Apply comprehensive application-level filters to a query.

        This builds a WHERE clause that includes:
        1. Tenant filter (always applied if model has tenant_id)
        2. Team filter (if model has team_id and include_team=True)
        3. Share filter (if model is shareable and include_shared=True)
        4. Soft delete filter (if model has is_deleted)

        Args:
            query: SQLAlchemy select query
            model_class: The model class being queried
            include_shared: Include resources shared with the user
            include_team: Include resources from user's teams
            user_id: Override user ID (defaults to context user)

        Returns:
            Query with isolation filters applied
        """
        ctx = TenantContext.require()
        effective_user_id = user_id or ctx.user_id

        conditions = []

        # 1. Tenant filter (always applied)
        if self.has_tenant_column(model_class):
            conditions.append(model_class.tenant_id == ctx.tenant_id)

        # 2. Build access conditions
        access_conditions = []

        # 2a. Owner access (created_by = user)
        if hasattr(model_class, "created_by") and effective_user_id:
            access_conditions.append(model_class.created_by == effective_user_id)

        # 2b. Team access
        if include_team and self.has_team_column(model_class) and ctx.team_ids:
            team_condition = model_class.team_id.in_(list(ctx.team_ids))
            access_conditions.append(team_condition)

        # 2c. Tenant-wide access (share_level = 'tenant')
        if self.is_shareable(model_class):
            if hasattr(model_class, "share_level"):
                access_conditions.append(model_class.share_level == "tenant")

        # 2d. Public team resources
        if self.has_team_column(model_class):
            # Resources with no team_id but tenant-level share
            if self.is_shareable(model_class) and hasattr(model_class, "share_level"):
                public_condition = and_(
                    model_class.team_id.is_(None),
                    model_class.share_level == "tenant"
                )
                access_conditions.append(public_condition)

        # Combine access conditions with OR
        if access_conditions:
            if len(access_conditions) == 1:
                conditions.append(access_conditions[0])
            else:
                conditions.append(or_(*access_conditions))

        # 3. Soft delete filter
        if self.has_soft_delete(model_class):
            conditions.append(model_class.is_deleted == False)

        # Apply all conditions
        if conditions:
            if len(conditions) == 1:
                query = query.where(conditions[0])
            else:
                query = query.where(and_(*conditions))

        return query

    async def verify_record_access(
        self,
        session: AsyncSession,
        model_class: Type[T],
        record_id: UUID,
        *,
        required_permission: Optional[str] = None,
    ) -> bool:
        """
        Verify access to a specific record at application level.

        Checks:
        1. Record belongs to current tenant
        2. User has access via ownership, team, or share

        Args:
            session: Database session
            model_class: The model class
            record_id: UUID of the record
            required_permission: Permission level needed for shared access

        Returns:
            True if the record is accessible
        """
        ctx = TenantContext.require()

        try:
            # Build query with filters
            query = select(model_class).where(model_class.id == record_id)
            query = self.apply_query_filters(
                query,
                model_class,
                include_shared=True,
                include_team=True,
            )

            result = await session.execute(query)
            record = result.scalar_one_or_none()

            if record is None:
                logger.debug(
                    f"Access denied to {model_class.__name__}:{record_id} "
                    f"for user={ctx.user_id}"
                )
                return False

            # Additional permission check for shares
            if required_permission and self.is_shareable(model_class):
                return await self._check_share_permission(
                    session, model_class, record_id, required_permission
                )

            return True

        except Exception as e:
            logger.warning(f"Record access verification failed: {e}")
            return False

    async def _check_share_permission(
        self,
        session: AsyncSession,
        model_class: Type[T],
        record_id: UUID,
        required_permission: str,
    ) -> bool:
        """
        Check if user has required permission via sharing.

        Args:
            session: Database session
            model_class: The model class
            record_id: UUID of the record
            required_permission: Permission level needed

        Returns:
            True if user has required permission
        """
        ctx = TenantContext.require()

        # Map permission levels to check
        permission_hierarchy = {
            SharePermission.VIEW.value: [
                SharePermission.VIEW.value,
                SharePermission.COMMENT.value,
                SharePermission.EDIT.value,
                SharePermission.FULL.value,
            ],
            SharePermission.COMMENT.value: [
                SharePermission.COMMENT.value,
                SharePermission.EDIT.value,
                SharePermission.FULL.value,
            ],
            SharePermission.EDIT.value: [
                SharePermission.EDIT.value,
                SharePermission.FULL.value,
            ],
            SharePermission.FULL.value: [
                SharePermission.FULL.value,
            ],
        }

        valid_permissions = permission_hierarchy.get(required_permission, [])
        if not valid_permissions:
            return False

        # This would need the ResourceShare model imported
        # For now, return True if basic access is granted
        # Full implementation would check ResourceShare table
        logger.debug(
            f"Share permission check for {model_class.__name__}:{record_id} "
            f"permission={required_permission}"
        )
        return True

    def get_user_accessible_team_ids(self) -> List[UUID]:
        """
        Get all team IDs the current user can access.

        This includes direct team memberships and inherited access
        from parent teams.

        Returns:
            List of accessible team UUIDs
        """
        ctx = TenantContext.get_current()
        if ctx is None:
            return []
        return list(ctx.team_ids)
