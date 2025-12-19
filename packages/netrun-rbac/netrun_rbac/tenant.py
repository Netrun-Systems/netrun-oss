"""
Tenant Context Management for Multi-Tenant RBAC

Extracted from: Intirkast middleware/tenant_context.py + app/core/database.py
Provides PostgreSQL Row-Level Security (RLS) session variable management
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import MissingTenantContextError

logger = logging.getLogger(__name__)


class TenantContext:
    """
    Tenant context for database session scoping

    Stores tenant_id and user_id for PostgreSQL RLS enforcement
    """

    def __init__(self, tenant_id: str | UUID, user_id: Optional[str | UUID] = None):
        """
        Initialize tenant context

        Args:
            tenant_id: Tenant UUID (string or UUID object)
            user_id: User UUID for audit logging (optional)
        """
        self.tenant_id = str(tenant_id)
        self.user_id = str(user_id) if user_id else None

    def to_dict(self) -> dict:
        """
        Convert to dictionary for storage

        Returns:
            Dictionary with tenant_id and user_id
        """
        return {"tenant_id": self.tenant_id, "user_id": self.user_id}


async def set_tenant_context(
    session: AsyncSession, tenant_id: str | UUID, user_id: Optional[str | UUID] = None
) -> None:
    """
    Set PostgreSQL session variables for Row-Level Security (RLS)

    Extracted from: Intirkast test_rls_isolation.py (set_rls_context)

    Sets:
    - app.current_tenant_id: Used by RLS policies to filter queries
    - app.current_user_id: Used for audit logging (optional)

    Args:
        session: SQLAlchemy AsyncSession
        tenant_id: Tenant UUID to scope queries to
        user_id: User UUID for audit logging (optional)

    Example RLS Policy:
        CREATE POLICY tenant_isolation_policy ON users
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

    Usage:
        async with AsyncSessionLocal() as session:
            # Set tenant context
            await set_tenant_context(session, tenant_id="550e8400-...", user_id="660e8400-...")

            # All queries now automatically filtered by tenant_id
            result = await session.execute(select(User))
            users = result.scalars().all()  # Only returns users from specified tenant

    PostgreSQL Session Variables:
    - SET LOCAL: Variables persist for current transaction only
    - current_setting('app.current_tenant_id', true): Retrieves variable (true = no error if missing)
    - NULLIF(..., ''): Converts empty string to NULL (handles missing variable)
    - ::UUID: Casts string to UUID type
    """
    if not tenant_id:
        raise MissingTenantContextError("tenant_id is required for RLS enforcement")

    # Set tenant context
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)}
    )

    logger.debug(f"RLS enabled for tenant: {tenant_id}")

    # Set user context for audit logging (optional)
    if user_id:
        await session.execute(
            text("SET LOCAL app.current_user_id = :user_id"), {"user_id": str(user_id)}
        )
        logger.debug(f"Audit context set for user: {user_id}")


async def clear_tenant_context(session: AsyncSession) -> None:
    """
    Clear PostgreSQL RLS session variables

    Extracted from: Intirkast test_rls_isolation.py (clear_rls_context)

    Resets:
    - app.current_tenant_id
    - app.current_user_id

    Usage:
        async with AsyncSessionLocal() as session:
            # Set tenant context
            await set_tenant_context(session, tenant_id="550e8400-...")

            # Query tenant-scoped data
            result = await session.execute(select(User))
            users = result.scalars().all()

            # Clear context (e.g., for admin operations)
            await clear_tenant_context(session)

            # Query all data (no RLS filtering)
            result = await session.execute(select(User))
            all_users = result.scalars().all()
    """
    await session.execute(text("RESET app.current_tenant_id"))
    await session.execute(text("RESET app.current_user_id"))
    logger.debug("Tenant context cleared")


async def get_current_tenant_id(session: AsyncSession) -> Optional[str]:
    """
    Retrieve current tenant_id from PostgreSQL session variable

    Returns:
        Tenant ID if set, None otherwise

    Usage:
        async with AsyncSessionLocal() as session:
            tenant_id = await get_current_tenant_id(session)
            if tenant_id:
                print(f"Current tenant: {tenant_id}")
    """
    result = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
    tenant_id = result.scalar()

    # PostgreSQL returns empty string if variable not set
    return tenant_id if tenant_id and tenant_id != "" else None


async def get_current_user_id(session: AsyncSession) -> Optional[str]:
    """
    Retrieve current user_id from PostgreSQL session variable

    Returns:
        User ID if set, None otherwise

    Usage:
        async with AsyncSessionLocal() as session:
            user_id = await get_current_user_id(session)
            if user_id:
                print(f"Current user: {user_id}")
    """
    result = await session.execute(text("SELECT current_setting('app.current_user_id', true)"))
    user_id = result.scalar()

    # PostgreSQL returns empty string if variable not set
    return user_id if user_id and user_id != "" else None


def get_db_with_rls(tenant_id_getter: callable, user_id_getter: Optional[callable] = None):
    """
    FastAPI dependency factory to get database session with RLS enabled

    Extracted from: Intirkast app/core/database.py (get_db_with_rls)

    Args:
        tenant_id_getter: Function to extract tenant_id from request
        user_id_getter: Function to extract user_id from request (optional)

    Returns:
        FastAPI dependency function

    Usage:
        # Define getter functions
        def get_tenant_id_from_request(request: Request) -> str:
            return request.state.tenant_id

        def get_user_id_from_request(request: Request) -> str:
            return request.state.user_id

        # Create dependency
        get_db_scoped = get_db_with_rls(
            tenant_id_getter=get_tenant_id_from_request,
            user_id_getter=get_user_id_from_request
        )

        # Use in route
        @router.get("/api/users")
        async def list_users(db: AsyncSession = Depends(get_db_scoped)):
            # All queries automatically scoped to tenant
            result = await db.execute(select(User))
            return result.scalars().all()

    PLACEHOLDER Pattern:
        Replace {{AsyncSessionLocal}} with your session factory:

        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        engine = create_async_engine("{{DATABASE_URL}}")
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)
    """

    async def dependency(
        tenant_id: str = tenant_id_getter, user_id: Optional[str] = user_id_getter or None
    ):
        """
        Database session dependency with RLS context

        Args:
            tenant_id: Tenant ID from request
            user_id: User ID from request (optional)

        Yields:
            AsyncSession with RLS context set
        """
        # PLACEHOLDER: Replace with your AsyncSessionLocal
        # from your_app.database import AsyncSessionLocal

        # Temporary placeholder error
        raise NotImplementedError(
            "Replace {{AsyncSessionLocal}} placeholder with your session factory. "
            "See netrun_rbac.tenant.get_db_with_rls docstring for example."
        )

        # Example implementation (uncomment and replace):
        # async with AsyncSessionLocal() as session:
        #     try:
        #         # Set RLS context
        #         await set_tenant_context(session, tenant_id, user_id)
        #
        #         yield session
        #
        #         await session.commit()
        #     except Exception as e:
        #         await session.rollback()
        #         logger.error(f"Database error: {e}")
        #         raise
        #     finally:
        #         await session.close()

    return dependency
