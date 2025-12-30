"""
Netrun RBAC RLS Isolation - PostgreSQL Row-Level Security strategy.

Following Netrun Systems SDLC v2.3 standards.

This strategy relies on PostgreSQL RLS policies to enforce tenant isolation
at the database level. Application-level filtering is minimal as RLS
handles the heavy lifting.

Prerequisites:
- RLS must be enabled on tenant-aware tables
- RLS policies must be created using the provided SQL generators
- Session variables (app.current_tenant_id) must be set before queries

Example RLS Policy:
    CREATE POLICY tenant_isolation ON contacts
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
"""

import logging
from typing import TypeVar, Type, Optional
from uuid import UUID

from sqlalchemy import Select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import IsolationStrategy
from ..tenancy.context import TenantContext
from ..tenancy.exceptions import TenantContextError, IsolationViolationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RLSIsolationStrategy(IsolationStrategy):
    """
    PostgreSQL Row-Level Security isolation strategy.

    This strategy sets PostgreSQL session variables that RLS policies use
    to filter data. The actual filtering happens at the database level,
    providing strong security guarantees.

    Note: This strategy does minimal application-level filtering since
    RLS handles isolation. Use HybridIsolationStrategy for defense-in-depth.

    Attributes:
        tenant_variable: PostgreSQL variable name for tenant ID
        user_variable: PostgreSQL variable name for user ID
    """

    def __init__(
        self,
        tenant_variable: str = "app.current_tenant_id",
        user_variable: str = "app.current_user_id",
    ):
        """
        Initialize the RLS isolation strategy.

        Args:
            tenant_variable: PostgreSQL session variable for tenant ID
            user_variable: PostgreSQL session variable for user ID
        """
        self.tenant_variable = tenant_variable
        self.user_variable = user_variable

    async def setup_session(self, session: AsyncSession) -> None:
        """
        Set PostgreSQL session variables for RLS policies.

        This must be called at the start of each request/transaction
        to set the tenant and user context for RLS policies.

        Args:
            session: SQLAlchemy async session

        Raises:
            TenantContextError: If tenant context is not set
        """
        ctx = TenantContext.get_current()
        if ctx is None:
            raise TenantContextError(
                "Cannot setup RLS session: tenant context not set"
            )

        try:
            # Set tenant ID for RLS policies
            await session.execute(
                text(f"SET LOCAL {self.tenant_variable} = :tenant_id"),
                {"tenant_id": str(ctx.tenant_id)}
            )

            # Set user ID if available
            if ctx.user_id:
                await session.execute(
                    text(f"SET LOCAL {self.user_variable} = :user_id"),
                    {"user_id": str(ctx.user_id)}
                )

            logger.debug(
                f"RLS session configured: tenant={ctx.tenant_id}, user={ctx.user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to setup RLS session: {e}")
            raise IsolationViolationError(
                operation="session_setup",
                details={"error": str(e)}
            )

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
        Apply minimal query filters (RLS handles most isolation).

        Since RLS policies handle tenant isolation at the database level,
        this method only adds application-level filters for features RLS
        can't handle (like soft delete exclusion).

        Args:
            query: SQLAlchemy select query
            model_class: The model class being queried
            include_shared: Include shared resources (RLS handles this)
            include_team: Include team resources (RLS handles this)
            user_id: Override user ID (not used in RLS mode)

        Returns:
            Query with soft delete filter if applicable
        """
        # RLS handles tenant/team/share isolation
        # We only add soft delete filter at application level
        if self.has_soft_delete(model_class):
            query = query.where(model_class.is_deleted == False)

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
        Verify access to a specific record using RLS.

        In RLS mode, we attempt to select the record. If RLS policies
        block access, the query will return no results.

        Args:
            session: Database session (must have RLS configured)
            model_class: The model class
            record_id: UUID of the record
            required_permission: Not used in RLS-only mode

        Returns:
            True if the record is accessible
        """
        try:
            # Ensure RLS is configured for this session
            await self.setup_session(session)

            # Try to select the record - RLS will filter if no access
            from sqlalchemy import select

            query = select(model_class).where(model_class.id == record_id)

            if self.has_soft_delete(model_class):
                query = query.where(model_class.is_deleted == False)

            result = await session.execute(query)
            record = result.scalar_one_or_none()

            return record is not None

        except Exception as e:
            logger.warning(f"Record access verification failed: {e}")
            return False

    def generate_rls_policy_sql(
        self,
        table_name: str,
        policy_name: Optional[str] = None,
        include_user_check: bool = False,
    ) -> str:
        """
        Generate SQL for creating an RLS policy.

        Args:
            table_name: Name of the table
            policy_name: Optional policy name (defaults to {table}_tenant_isolation)
            include_user_check: Add user-level check in addition to tenant

        Returns:
            SQL string for CREATE POLICY statement
        """
        policy_name = policy_name or f"{table_name}_tenant_isolation"

        if include_user_check:
            using_clause = f"""
                tenant_id = current_setting('{self.tenant_variable}')::uuid
                AND (
                    created_by = current_setting('{self.user_variable}')::uuid
                    OR share_level IN ('team', 'tenant')
                )
            """
        else:
            using_clause = f"tenant_id = current_setting('{self.tenant_variable}')::uuid"

        return f"""
-- Enable RLS on table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create isolation policy
CREATE POLICY {policy_name} ON {table_name}
FOR ALL
USING ({using_clause.strip()});

-- Force RLS for table owner (security best practice)
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;
"""

    def generate_enable_rls_sql(self, table_names: list[str]) -> str:
        """
        Generate SQL to enable RLS on multiple tables.

        Args:
            table_names: List of table names

        Returns:
            SQL string for enabling RLS and creating policies
        """
        statements = []
        for table in table_names:
            statements.append(self.generate_rls_policy_sql(table))
        return "\n".join(statements)
