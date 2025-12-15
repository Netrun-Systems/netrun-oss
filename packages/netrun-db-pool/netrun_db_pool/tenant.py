"""Multi-tenant database pool with Row-Level Security (RLS) support."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netrun_db_pool.pool import AsyncDatabasePool

logger = logging.getLogger(__name__)


class TenantAwareDatabasePool(AsyncDatabasePool):
    """
    Multi-tenant database pool with PostgreSQL Row-Level Security (RLS).

    Automatically sets tenant context using PostgreSQL session variables:
    - app.current_tenant_id: Tenant UUID for RLS filtering
    - app.current_user_id: User UUID for audit logging (optional)

    Example PostgreSQL RLS policy:
        CREATE POLICY tenant_isolation ON users
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

    Usage:
        >>> pool = TenantAwareDatabasePool.from_env()
        >>> async with pool.get_tenant_session(tenant_id="550e8400-...") as session:
        ...     # All queries automatically filtered by tenant_id
        ...     users = await session.execute(select(User))
    """

    @asynccontextmanager
    async def get_tenant_session(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Get tenant-scoped database session with RLS context.

        Args:
            tenant_id: Tenant UUID for RLS filtering
            user_id: User UUID for audit logging (optional)

        Yields:
            AsyncSession: Session with tenant context set

        Example:
            >>> async with pool.get_tenant_session("550e8400-...") as session:
            ...     # Only tenant-owned records are accessible
            ...     result = await session.execute(select(User))
        """
        if not self._initialized:
            await self.initialize()

        async with self._session_factory() as session:
            try:
                # Set tenant context for RLS
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id},
                )

                # Set user context for audit logging (optional)
                if user_id:
                    await session.execute(
                        text("SET LOCAL app.current_user_id = :user_id"),
                        {"user_id": user_id},
                    )

                logger.debug(f"Set RLS context: tenant_id={tenant_id}, user_id={user_id}")

                yield session
                await session.commit()

            except Exception as e:
                logger.error(f"Tenant session error: {e}")
                await session.rollback()
                raise

            finally:
                # Context is automatically cleared on transaction end (LOCAL scope)
                await session.close()

    async def verify_rls_enabled(self, table_name: str) -> bool:
        """
        Verify RLS is enabled for a table.

        Args:
            table_name: Table name to check

        Returns:
            bool: True if RLS is enabled, False otherwise

        Example:
            >>> is_protected = await pool.verify_rls_enabled("users")
            >>> if not is_protected:
            ...     logger.warning("RLS not enabled for users table!")
        """
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text(
                        """
                        SELECT relrowsecurity
                        FROM pg_class
                        WHERE relname = :table_name
                        """
                    ),
                    {"table_name": table_name},
                )
                row = result.fetchone()
                return row[0] if row else False
        except Exception as e:
            logger.error(f"Failed to check RLS status for {table_name}: {e}")
            return False

    async def get_current_tenant_context(self, session: AsyncSession) -> Optional[str]:
        """
        Get current tenant context from session.

        Args:
            session: Active database session

        Returns:
            str: Current tenant_id or None if not set

        Example:
            >>> async with pool.get_tenant_session("550e8400-...") as session:
            ...     tenant_id = await pool.get_current_tenant_context(session)
            ...     print(f"Current tenant: {tenant_id}")
        """
        try:
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
            row = result.fetchone()
            return row[0] if row and row[0] else None
        except Exception as e:
            logger.error(f"Failed to get tenant context: {e}")
            return None
