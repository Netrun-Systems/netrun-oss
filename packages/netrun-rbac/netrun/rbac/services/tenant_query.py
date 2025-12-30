"""
Netrun RBAC Tenant Query Service - Generic auto-filtering query service.

Following Netrun Systems SDLC v2.3 standards.

This service provides a generic, type-safe way to query tenant-aware models
with automatic filtering based on the current tenant context.

Usage:
    from netrun.rbac.services import TenantQueryService
    from myapp.models import Contact

    class ContactService(TenantQueryService[Contact]):
        pass

    # Or use directly
    service = TenantQueryService(session, Contact)
    contacts = await service.get_all(limit=50)
    contact = await service.get_by_id(contact_id)
"""

import logging
from typing import TypeVar, Type, Generic, Optional, List, Any, Dict
from uuid import UUID

from sqlalchemy import select, func, or_, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..tenancy.context import TenantContext
from ..tenancy.exceptions import TenantContextError, CrossTenantViolationError
from ..isolation.base import IsolationStrategy
from ..isolation.hybrid import HybridIsolationStrategy

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TenantQueryService(Generic[T]):
    """
    Generic query service with automatic tenant filtering.

    This service provides CRUD operations that automatically apply
    tenant isolation based on the current context. It supports:
    - Tenant filtering (tenant_id = current_tenant)
    - Team filtering (resources owned by user's teams)
    - Share filtering (resources shared with user)
    - Soft delete filtering (exclude deleted records)

    Type Parameters:
        T: The model class this service operates on

    Attributes:
        session: SQLAlchemy async session
        model: The model class
        isolation: Isolation strategy to use

    Usage:
        # Direct usage
        service = TenantQueryService(session, Contact)
        contacts = await service.get_all()

        # Subclass for custom methods
        class ContactService(TenantQueryService[Contact]):
            async def get_by_email(self, email: str) -> Optional[Contact]:
                return await self.get_one_by(email=email)
    """

    def __init__(
        self,
        session: AsyncSession,
        model: Type[T],
        isolation: Optional[IsolationStrategy] = None,
    ):
        """
        Initialize the query service.

        Args:
            session: SQLAlchemy async session
            model: The model class to query
            isolation: Isolation strategy (defaults to HybridIsolationStrategy)
        """
        self.session = session
        self.model = model
        self.isolation = isolation or HybridIsolationStrategy()

    async def setup_isolation(self) -> None:
        """
        Setup database session isolation (RLS variables).

        Call this at the start of operations to ensure RLS is configured.
        """
        await self.isolation.setup_session(self.session)

    async def get_by_id(
        self,
        id: UUID,
        *,
        include_shared: bool = True,
        include_team: bool = True,
        eager_load: Optional[List[str]] = None,
    ) -> Optional[T]:
        """
        Get a single record by ID with tenant filtering.

        Args:
            id: UUID of the record
            include_shared: Include if shared with user
            include_team: Include if from user's team
            eager_load: List of relationship names to eager load

        Returns:
            The record if found and accessible, None otherwise
        """
        await self.setup_isolation()

        query = select(self.model).where(self.model.id == id)

        # Apply eager loading
        if eager_load:
            for rel_name in eager_load:
                if hasattr(self.model, rel_name):
                    query = query.options(selectinload(getattr(self.model, rel_name)))

        # Apply isolation filters
        query = self.isolation.apply_query_filters(
            query,
            self.model,
            include_shared=include_shared,
            include_team=include_team,
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        include_shared: bool = True,
        include_team: bool = True,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        eager_load: Optional[List[str]] = None,
    ) -> List[T]:
        """
        Get all accessible records with tenant filtering.

        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            include_shared: Include resources shared with user
            include_team: Include resources from user's teams
            order_by: Column name to order by
            order_desc: Order descending if True
            eager_load: List of relationship names to eager load

        Returns:
            List of accessible records
        """
        await self.setup_isolation()

        query = select(self.model)

        # Apply eager loading
        if eager_load:
            for rel_name in eager_load:
                if hasattr(self.model, rel_name):
                    query = query.options(selectinload(getattr(self.model, rel_name)))

        # Apply isolation filters
        query = self.isolation.apply_query_filters(
            query,
            self.model,
            include_shared=include_shared,
            include_team=include_team,
        )

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_one_by(self, **filters) -> Optional[T]:
        """
        Get a single record by arbitrary filters.

        Args:
            **filters: Column=value filters to apply

        Returns:
            The first matching record or None
        """
        await self.setup_isolation()

        query = select(self.model)

        # Apply user filters
        for column_name, value in filters.items():
            if hasattr(self.model, column_name):
                query = query.where(getattr(self.model, column_name) == value)

        # Apply isolation filters
        query = self.isolation.apply_query_filters(query, self.model)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_many_by(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """
        Get multiple records by arbitrary filters.

        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            **filters: Column=value filters to apply

        Returns:
            List of matching records
        """
        await self.setup_isolation()

        query = select(self.model)

        # Apply user filters
        for column_name, value in filters.items():
            if hasattr(self.model, column_name):
                if isinstance(value, list):
                    query = query.where(getattr(self.model, column_name).in_(value))
                else:
                    query = query.where(getattr(self.model, column_name) == value)

        # Apply isolation filters
        query = self.isolation.apply_query_filters(query, self.model)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        include_shared: bool = True,
        include_team: bool = True,
        **filters
    ) -> int:
        """
        Count accessible records.

        Args:
            include_shared: Include shared resources in count
            include_team: Include team resources in count
            **filters: Additional filters to apply

        Returns:
            Number of accessible records
        """
        await self.setup_isolation()

        query = select(func.count()).select_from(self.model)

        # Apply user filters
        for column_name, value in filters.items():
            if hasattr(self.model, column_name):
                query = query.where(getattr(self.model, column_name) == value)

        # Apply isolation filters
        query = self.isolation.apply_query_filters(
            query,
            self.model,
            include_shared=include_shared,
            include_team=include_team,
        )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists and is accessible.

        Args:
            id: UUID of the record

        Returns:
            True if record exists and is accessible
        """
        record = await self.get_by_id(id)
        return record is not None

    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new record with automatic tenant assignment.

        The tenant_id is automatically set from the current context.
        If the model has created_by, it's set from context.user_id.

        Args:
            data: Dictionary of column values

        Returns:
            The created record

        Raises:
            TenantContextError: If tenant context is not set
        """
        ctx = TenantContext.require()

        # Auto-inject tenant_id
        if hasattr(self.model, "tenant_id"):
            data["tenant_id"] = ctx.tenant_id

        # Auto-inject created_by
        if hasattr(self.model, "created_by") and ctx.user_id:
            data["created_by"] = ctx.user_id

        # Create instance
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()

        logger.debug(
            f"Created {self.model.__name__} id={instance.id} "
            f"in tenant={ctx.tenant_id}"
        )

        return instance

    async def update(
        self,
        id: UUID,
        data: Dict[str, Any],
    ) -> Optional[T]:
        """
        Update a record by ID with tenant validation.

        Args:
            id: UUID of the record to update
            data: Dictionary of column values to update

        Returns:
            The updated record, or None if not found

        Raises:
            CrossTenantViolationError: If record belongs to different tenant
        """
        ctx = TenantContext.require()

        # First verify access
        existing = await self.get_by_id(id)
        if existing is None:
            return None

        # Verify tenant ownership for update
        if hasattr(existing, "tenant_id") and existing.tenant_id != ctx.tenant_id:
            raise CrossTenantViolationError(
                current_tenant_id=ctx.tenant_id,
                target_tenant_id=existing.tenant_id,
                resource_type=self.model.__name__,
                resource_id=id,
            )

        # Update fields
        for key, value in data.items():
            if hasattr(existing, key) and key not in ("id", "tenant_id", "created_at"):
                setattr(existing, key, value)

        # Update updated_by if applicable
        if hasattr(existing, "updated_by") and ctx.user_id:
            existing.updated_by = ctx.user_id

        await self.session.flush()

        logger.debug(
            f"Updated {self.model.__name__} id={id} in tenant={ctx.tenant_id}"
        )

        return existing

    async def delete(
        self,
        id: UUID,
        *,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete a record by ID with tenant validation.

        Args:
            id: UUID of the record to delete
            soft_delete: If True and model supports it, soft delete

        Returns:
            True if deleted, False if not found

        Raises:
            CrossTenantViolationError: If record belongs to different tenant
        """
        ctx = TenantContext.require()

        # Verify access
        existing = await self.get_by_id(id)
        if existing is None:
            return False

        # Verify tenant ownership
        if hasattr(existing, "tenant_id") and existing.tenant_id != ctx.tenant_id:
            raise CrossTenantViolationError(
                current_tenant_id=ctx.tenant_id,
                target_tenant_id=existing.tenant_id,
                resource_type=self.model.__name__,
                resource_id=id,
            )

        # Soft delete if supported and requested
        if soft_delete and hasattr(existing, "is_deleted"):
            existing.is_deleted = True
            if hasattr(existing, "deleted_at"):
                from datetime import datetime, timezone
                existing.deleted_at = datetime.now(timezone.utc)
            if hasattr(existing, "deleted_by") and ctx.user_id:
                existing.deleted_by = ctx.user_id
            await self.session.flush()
            logger.debug(f"Soft deleted {self.model.__name__} id={id}")
        else:
            # Hard delete
            await self.session.delete(existing)
            await self.session.flush()
            logger.debug(f"Hard deleted {self.model.__name__} id={id}")

        return True

    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple records with automatic tenant assignment.

        Args:
            items: List of dictionaries with column values

        Returns:
            List of created records
        """
        ctx = TenantContext.require()
        created = []

        for data in items:
            # Auto-inject tenant_id
            if hasattr(self.model, "tenant_id"):
                data["tenant_id"] = ctx.tenant_id

            # Auto-inject created_by
            if hasattr(self.model, "created_by") and ctx.user_id:
                data["created_by"] = ctx.user_id

            instance = self.model(**data)
            self.session.add(instance)
            created.append(instance)

        await self.session.flush()

        logger.debug(
            f"Bulk created {len(created)} {self.model.__name__} records "
            f"in tenant={ctx.tenant_id}"
        )

        return created
