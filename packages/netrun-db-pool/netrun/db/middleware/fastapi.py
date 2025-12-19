"""FastAPI dependency injection for database sessions."""

from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from netrun.db.pool import AsyncDatabasePool
from netrun.db.tenant import TenantAwareDatabasePool


def get_db_dependency(
    pool: AsyncDatabasePool,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """
    Create FastAPI dependency for database sessions.

    Args:
        pool: AsyncDatabasePool instance

    Returns:
        Dependency function for FastAPI routes

    Example:
        >>> from fastapi import FastAPI, Depends
        >>> from netrun_db_pool import AsyncDatabasePool
        >>> from netrun_db_pool.middleware import get_db_dependency
        >>>
        >>> app = FastAPI()
        >>> pool = AsyncDatabasePool.from_env()
        >>> get_db = get_db_dependency(pool)
        >>>
        >>> @app.get("/users")
        >>> async def list_users(db: AsyncSession = Depends(get_db)):
        ...     result = await db.execute(select(User))
        ...     return result.scalars().all()
    """

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async for session in pool.get_session():
            yield session

    return _get_db


def get_tenant_db_dependency(
    pool: TenantAwareDatabasePool,
    tenant_id_extractor: Callable,
    user_id_extractor: Callable = None,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """
    Create FastAPI dependency for tenant-scoped database sessions.

    Args:
        pool: TenantAwareDatabasePool instance
        tenant_id_extractor: Function to extract tenant_id from request
        user_id_extractor: Function to extract user_id from request (optional)

    Returns:
        Dependency function for FastAPI routes with RLS context

    Example:
        >>> from fastapi import Request, Depends
        >>> from netrun_db_pool import TenantAwareDatabasePool
        >>> from netrun_db_pool.middleware import get_tenant_db_dependency
        >>>
        >>> pool = TenantAwareDatabasePool.from_env()
        >>>
        >>> def get_tenant_id(request: Request) -> str:
        ...     return request.state.tenant_id
        >>>
        >>> def get_user_id(request: Request) -> str:
        ...     return request.state.user_id
        >>>
        >>> get_tenant_db = get_tenant_db_dependency(
        ...     pool=pool,
        ...     tenant_id_extractor=get_tenant_id,
        ...     user_id_extractor=get_user_id,
        ... )
        >>>
        >>> @app.get("/users")
        >>> async def list_users(db: AsyncSession = Depends(get_tenant_db)):
        ...     # Only current tenant's users are accessible
        ...     result = await db.execute(select(User))
        ...     return result.scalars().all()
    """

    async def _get_tenant_db(
        tenant_id: str = Depends(tenant_id_extractor),
        user_id: str = Depends(user_id_extractor) if user_id_extractor else None,
    ) -> AsyncGenerator[AsyncSession, None]:
        async for session in pool.get_tenant_session(
            tenant_id=tenant_id,
            user_id=user_id,
        ):
            yield session

    return _get_tenant_db
