"""
Netrun RBAC Isolation Base - Abstract base class for isolation strategies.

Following Netrun Systems SDLC v2.3 standards.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Type, Any, Optional
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class IsolationStrategy(ABC):
    """
    Abstract base class for database isolation strategies.

    Isolation strategies control how data is filtered to ensure
    tenant isolation. Implementations can use:
    - PostgreSQL Row-Level Security (RLS)
    - Application-level query filtering
    - A combination of both (hybrid)

    Subclasses must implement:
    - setup_session: Configure database session for isolation
    - apply_query_filters: Add tenant/team filters to queries
    - verify_record_access: Check if a record is accessible

    Usage:
        class MyStrategy(IsolationStrategy):
            async def setup_session(self, session):
                # Configure session for RLS
                pass

            def apply_query_filters(self, query, model_class, **options):
                # Add WHERE clauses for tenant isolation
                return query.where(model_class.tenant_id == ctx.tenant_id)
    """

    @abstractmethod
    async def setup_session(self, session: AsyncSession) -> None:
        """
        Configure the database session for isolation.

        This is called at the beginning of each request/operation to set
        up any session-level variables needed for isolation (e.g., RLS).

        Args:
            session: SQLAlchemy async session to configure

        Raises:
            TenantContextError: If tenant context is not set
            IsolationViolationError: If session setup fails
        """
        pass

    @abstractmethod
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
        Apply tenant/team/share filters to a query.

        This modifies the query to ensure only accessible records are returned.
        The filters applied depend on the model's mixins:
        - TenantMixin: Filter by tenant_id
        - TeamMixin: Filter by user's teams
        - ShareableMixin: Include shared resources

        Args:
            query: SQLAlchemy select query to filter
            model_class: The model class being queried
            include_shared: Include resources shared with the user
            include_team: Include resources from user's teams
            user_id: Override user ID (defaults to context user)

        Returns:
            Modified query with isolation filters applied
        """
        pass

    @abstractmethod
    async def verify_record_access(
        self,
        session: AsyncSession,
        model_class: Type[T],
        record_id: UUID,
        *,
        required_permission: Optional[str] = None,
    ) -> bool:
        """
        Verify that the current user can access a specific record.

        This performs a targeted check for a single record, useful for
        update/delete operations where you need to verify access before
        modifying.

        Args:
            session: Database session
            model_class: The model class of the record
            record_id: UUID of the record to check
            required_permission: Permission level needed (for shares)

        Returns:
            True if access is allowed, False otherwise
        """
        pass

    def has_tenant_column(self, model_class: Type[T]) -> bool:
        """
        Check if a model has a tenant_id column.

        Args:
            model_class: The model class to check

        Returns:
            True if the model has tenant_id column
        """
        return hasattr(model_class, "tenant_id")

    def has_team_column(self, model_class: Type[T]) -> bool:
        """
        Check if a model has a team_id column.

        Args:
            model_class: The model class to check

        Returns:
            True if the model has team_id column
        """
        return hasattr(model_class, "team_id")

    def is_shareable(self, model_class: Type[T]) -> bool:
        """
        Check if a model supports sharing.

        Args:
            model_class: The model class to check

        Returns:
            True if the model has share_level or is_shared columns
        """
        return hasattr(model_class, "share_level") or hasattr(model_class, "is_shared")

    def has_soft_delete(self, model_class: Type[T]) -> bool:
        """
        Check if a model supports soft delete.

        Args:
            model_class: The model class to check

        Returns:
            True if the model has is_deleted column
        """
        return hasattr(model_class, "is_deleted")
