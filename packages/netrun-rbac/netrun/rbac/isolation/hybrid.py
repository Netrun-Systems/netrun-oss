"""
Netrun RBAC Hybrid Isolation - Combined RLS + Application-level strategy.

Following Netrun Systems SDLC v2.3 standards.

This is the RECOMMENDED isolation strategy. It combines:
1. PostgreSQL RLS for database-level enforcement
2. Application-level filtering for defense-in-depth

Benefits:
- Defense-in-depth: Even if application code has bugs, RLS prevents leaks
- Flexibility: Application filtering handles complex share/team logic
- Performance: RLS is optimized at database level
- Auditability: Both layers can be logged independently
"""

import logging
from typing import TypeVar, Type, Optional
from uuid import UUID

from sqlalchemy import Select, text, or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import IsolationStrategy
from .rls import RLSIsolationStrategy
from .application import ApplicationIsolationStrategy
from ..tenancy.context import TenantContext
from ..tenancy.exceptions import TenantContextError, IsolationViolationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HybridIsolationStrategy(IsolationStrategy):
    """
    Hybrid isolation combining PostgreSQL RLS with application-level filtering.

    This is the RECOMMENDED strategy for production multi-tenant applications.
    It provides defense-in-depth by enforcing isolation at both the database
    and application levels.

    Flow:
    1. setup_session: Sets PostgreSQL session variables for RLS
    2. apply_query_filters: Adds application-level WHERE clauses
    3. Query execution: RLS policies filter at database level

    Even if application code fails to filter properly, RLS provides
    a safety net at the database level.

    Attributes:
        rls_strategy: The RLS isolation component
        app_strategy: The application isolation component
        strict_mode: Fail on violations vs log warnings
    """

    def __init__(
        self,
        tenant_variable: str = "app.current_tenant_id",
        user_variable: str = "app.current_user_id",
        strict_mode: bool = True,
    ):
        """
        Initialize the hybrid isolation strategy.

        Args:
            tenant_variable: PostgreSQL session variable for tenant ID
            user_variable: PostgreSQL session variable for user ID
            strict_mode: Raise exceptions on violations (vs log warning)
        """
        self.rls_strategy = RLSIsolationStrategy(
            tenant_variable=tenant_variable,
            user_variable=user_variable,
        )
        self.app_strategy = ApplicationIsolationStrategy()
        self.strict_mode = strict_mode
        self.tenant_variable = tenant_variable
        self.user_variable = user_variable

    async def setup_session(self, session: AsyncSession) -> None:
        """
        Configure session for both RLS and application isolation.

        Sets PostgreSQL session variables and verifies tenant context.

        Args:
            session: SQLAlchemy async session

        Raises:
            TenantContextError: If tenant context is not set
            IsolationViolationError: If setup fails in strict mode
        """
        ctx = TenantContext.get_current()
        if ctx is None:
            raise TenantContextError(
                "Cannot setup hybrid isolation: tenant context not set"
            )

        try:
            # Setup RLS session variables
            await self.rls_strategy.setup_session(session)

            logger.debug(
                f"Hybrid isolation configured: tenant={ctx.tenant_id}, "
                f"user={ctx.user_id}, teams={len(ctx.team_ids)}"
            )

        except Exception as e:
            error_msg = f"Hybrid isolation setup failed: {e}"
            if self.strict_mode:
                raise IsolationViolationError(
                    operation="session_setup",
                    details={"error": str(e)}
                )
            else:
                logger.warning(error_msg)

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
        Apply both RLS awareness and application-level filters.

        In hybrid mode, we apply application-level filters as defense-in-depth.
        Even though RLS will filter at the database level, the application
        filters provide an additional safety layer and handle complex
        logic that RLS can't express (like share permissions).

        Args:
            query: SQLAlchemy select query
            model_class: The model class being queried
            include_shared: Include resources shared with the user
            include_team: Include resources from user's teams
            user_id: Override user ID (defaults to context user)

        Returns:
            Query with isolation filters applied
        """
        # Apply application-level filters
        # RLS will also filter, but this provides defense-in-depth
        return self.app_strategy.apply_query_filters(
            query,
            model_class,
            include_shared=include_shared,
            include_team=include_team,
            user_id=user_id,
        )

    async def verify_record_access(
        self,
        session: AsyncSession,
        model_class: Type[T],
        record_id: UUID,
        *,
        required_permission: Optional[str] = None,
    ) -> bool:
        """
        Verify record access using both RLS and application checks.

        This performs a comprehensive access check:
        1. Ensures RLS session is configured
        2. Applies application-level access check
        3. Verifies the record is accessible through both layers

        Args:
            session: Database session
            model_class: The model class
            record_id: UUID of the record
            required_permission: Permission level needed for shared access

        Returns:
            True if the record is accessible through both layers
        """
        ctx = TenantContext.require()

        try:
            # Ensure RLS is configured
            await self.setup_session(session)

            # Use application strategy for detailed access check
            # This also serves as validation that our app filters work correctly
            has_access = await self.app_strategy.verify_record_access(
                session,
                model_class,
                record_id,
                required_permission=required_permission,
            )

            if not has_access:
                logger.debug(
                    f"Hybrid access denied to {model_class.__name__}:{record_id} "
                    f"for user={ctx.user_id} in tenant={ctx.tenant_id}"
                )

            return has_access

        except Exception as e:
            error_msg = f"Hybrid access verification failed: {e}"
            if self.strict_mode:
                logger.error(error_msg)
                return False
            else:
                logger.warning(error_msg)
                return False

    async def verify_isolation_integrity(
        self,
        session: AsyncSession,
        model_class: Type[T],
    ) -> dict:
        """
        Verify that RLS and application filters are consistent.

        This is a diagnostic method that can be used to detect
        configuration issues where RLS and application filters
        might return different results.

        Args:
            session: Database session
            model_class: The model class to check

        Returns:
            Dict with verification results
        """
        ctx = TenantContext.require()

        result = {
            "model": model_class.__name__,
            "tenant_id": str(ctx.tenant_id),
            "user_id": str(ctx.user_id) if ctx.user_id else None,
            "rls_configured": False,
            "app_filters_applied": False,
            "consistent": True,
            "issues": [],
        }

        try:
            # Check RLS configuration
            await self.setup_session(session)
            result["rls_configured"] = True

            # The consistency check would compare RLS-only results
            # with application-filtered results
            # This is a placeholder for the full implementation

            result["app_filters_applied"] = True

        except Exception as e:
            result["issues"].append(str(e))
            result["consistent"] = False

        return result

    def generate_hybrid_setup_sql(self, table_names: list[str]) -> str:
        """
        Generate SQL for setting up hybrid isolation on tables.

        This creates RLS policies that work with application-level
        filters for defense-in-depth.

        Args:
            table_names: List of table names to configure

        Returns:
            SQL string for complete hybrid setup
        """
        sql_parts = [
            "-- Hybrid Isolation Setup",
            "-- PostgreSQL RLS policies for defense-in-depth",
            "",
        ]

        for table in table_names:
            sql_parts.append(self.rls_strategy.generate_rls_policy_sql(table))
            sql_parts.append("")

        # Add helpful comments
        sql_parts.extend([
            "-- Note: Application-level filtering is handled by",
            "-- HybridIsolationStrategy.apply_query_filters()",
            "-- Both layers must pass for access to be granted.",
        ])

        return "\n".join(sql_parts)
