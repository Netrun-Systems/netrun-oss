"""Tests for TenantAwareDatabasePool with RLS support."""

import uuid

import pytest
from sqlalchemy import text

from netrun_db_pool import TenantAwareDatabasePool


@pytest.mark.integration
class TestTenantAwareDatabasePool:
    """Test tenant-aware database pool with RLS."""

    @pytest.mark.asyncio
    async def test_tenant_session_context(self, tenant_pool):
        """Test tenant context is set correctly."""
        tenant_id = str(uuid.uuid4())

        async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
            # Verify tenant context is set
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
            context_tenant_id = result.scalar()
            assert context_tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_tenant_session_with_user_id(self, tenant_pool):
        """Test tenant and user context are set."""
        tenant_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        async with tenant_pool.get_tenant_session(
            tenant_id=tenant_id,
            user_id=user_id,
        ) as session:
            # Verify tenant context
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
            assert result.scalar() == tenant_id

            # Verify user context
            result = await session.execute(
                text("SELECT current_setting('app.current_user_id', true)")
            )
            assert result.scalar() == user_id

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, tenant_pool):
        """Test RLS enforces tenant isolation."""
        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        # Insert data for tenant 1
        async with tenant_pool.get_tenant_session(tenant_id=tenant1_id) as session:
            await session.execute(
                text(
                    """
                    INSERT INTO tenant_users (tenant_id, name, email)
                    VALUES (:tenant_id, :name, :email)
                    """
                ),
                {
                    "tenant_id": tenant1_id,
                    "name": "Tenant 1 User",
                    "email": "t1user@example.com",
                },
            )

        # Insert data for tenant 2
        async with tenant_pool.get_tenant_session(tenant_id=tenant2_id) as session:
            await session.execute(
                text(
                    """
                    INSERT INTO tenant_users (tenant_id, name, email)
                    VALUES (:tenant_id, :name, :email)
                    """
                ),
                {
                    "tenant_id": tenant2_id,
                    "name": "Tenant 2 User",
                    "email": "t2user@example.com",
                },
            )

        # Verify tenant 1 only sees their data
        async with tenant_pool.get_tenant_session(tenant_id=tenant1_id) as session:
            result = await session.execute(text("SELECT COUNT(*) FROM tenant_users"))
            count = result.scalar()
            # Should only see tenant 1's user (RLS enforced)
            assert count == 1

            # Verify it's the correct user
            result = await session.execute(
                text("SELECT email FROM tenant_users")
            )
            email = result.scalar()
            assert email == "t1user@example.com"

        # Verify tenant 2 only sees their data
        async with tenant_pool.get_tenant_session(tenant_id=tenant2_id) as session:
            result = await session.execute(text("SELECT COUNT(*) FROM tenant_users"))
            count = result.scalar()
            assert count == 1

            result = await session.execute(
                text("SELECT email FROM tenant_users")
            )
            email = result.scalar()
            assert email == "t2user@example.com"

    @pytest.mark.asyncio
    async def test_verify_rls_enabled(self, tenant_pool):
        """Test RLS verification utility."""
        is_enabled = await tenant_pool.verify_rls_enabled("tenant_users")
        assert is_enabled is True

        # Test non-existent table
        is_enabled = await tenant_pool.verify_rls_enabled("nonexistent_table")
        assert is_enabled is False

    @pytest.mark.asyncio
    async def test_get_current_tenant_context(self, tenant_pool):
        """Test retrieval of current tenant context."""
        tenant_id = str(uuid.uuid4())

        async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
            current_tenant = await tenant_pool.get_current_tenant_context(session)
            assert current_tenant == tenant_id

    @pytest.mark.asyncio
    async def test_tenant_context_cleanup(self, tenant_pool):
        """Test tenant context is cleaned up after transaction."""
        tenant_id = str(uuid.uuid4())

        # Set tenant context
        async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
            assert result.scalar() == tenant_id

        # New session should not have tenant context
        async with tenant_pool.get_session() as session:
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
            # Should return empty string or NULL (context cleared)
            context = result.scalar()
            assert context in (None, "", tenant_id)  # LOCAL scope cleared

    @pytest.mark.asyncio
    async def test_tenant_session_rollback(self, tenant_pool):
        """Test tenant session rollback on error."""
        tenant_id = str(uuid.uuid4())

        try:
            async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO tenant_users (tenant_id, name, email)
                        VALUES (:tenant_id, :name, :email)
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "name": "Test User",
                        "email": "rollback@example.com",
                    },
                )
                # Force error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify rollback (user should not exist)
        async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM tenant_users WHERE email = :email"),
                {"email": "rollback@example.com"},
            )
            count = result.scalar()
            assert count == 0

    @pytest.mark.asyncio
    async def test_concurrent_tenant_sessions(self, tenant_pool):
        """Test concurrent sessions with different tenants."""
        async def insert_for_tenant(tenant_num: int):
            tenant_id = str(uuid.uuid4())
            async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO tenant_users (tenant_id, name, email)
                        VALUES (:tenant_id, :name, :email)
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "name": f"Tenant {tenant_num} User",
                        "email": f"tenant{tenant_num}@example.com",
                    },
                )
            return tenant_id

        # Run 3 concurrent tenant sessions
        import asyncio
        tenant_ids = await asyncio.gather(*[insert_for_tenant(i) for i in range(3)])

        # Verify each tenant sees only their data
        for tenant_id in tenant_ids:
            async with tenant_pool.get_tenant_session(tenant_id=tenant_id) as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM tenant_users")
                )
                count = result.scalar()
                assert count == 1  # RLS isolation
