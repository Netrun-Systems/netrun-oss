"""
Netrun RBAC Tenant Service - CRUD operations for tenants.

Following Netrun Systems SDLC v2.3 standards.

Provides operations for tenant management including:
- Creating new tenants
- Looking up tenants by ID or slug
- Updating tenant settings
- Managing tenant status (suspend, activate, archive)
"""

import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tenant import Tenant
from ..models.enums import TenantStatus

logger = logging.getLogger(__name__)


class TenantService:
    """
    Service for tenant CRUD operations.

    Note: This service operates at a higher level than TenantQueryService
    and doesn't apply tenant filtering (since it manages tenants themselves).

    Attributes:
        session: SQLAlchemy async session
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the tenant service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Get a tenant by ID.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Tenant if found, None otherwise
        """
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Get a tenant by slug.

        Args:
            slug: URL-safe tenant identifier

        Returns:
            Tenant if found, None otherwise
        """
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.slug == slug,
                Tenant.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """
        Get a tenant by custom domain.

        Args:
            domain: Custom domain (e.g., "app.acme.com")

        Returns:
            Tenant if found, None otherwise
        """
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.domain == domain,
                Tenant.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def lookup(
        self,
        tenant_id: Optional[UUID] = None,
        tenant_slug: Optional[str] = None,
    ) -> Optional[Tenant]:
        """
        Lookup tenant by ID or slug.

        Args:
            tenant_id: UUID of the tenant
            tenant_slug: URL-safe tenant identifier

        Returns:
            Tenant if found, None otherwise
        """
        if tenant_id:
            return await self.get_by_id(tenant_id)
        if tenant_slug:
            return await self.get_by_slug(tenant_slug)
        return None

    async def create(
        self,
        name: str,
        slug: Optional[str] = None,
        *,
        domain: Optional[str] = None,
        subscription_tier: str = "basic",
        max_users: int = 10,
        max_teams: int = 20,
        settings: Optional[Dict[str, Any]] = None,
        security_settings: Optional[Dict[str, Any]] = None,
        enabled_features: Optional[List[str]] = None,
        billing_email: Optional[str] = None,
        technical_contact: Optional[str] = None,
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            name: Display name for the tenant
            slug: URL-safe identifier (auto-generated if not provided)
            domain: Custom domain for SSO
            subscription_tier: Plan level
            max_users: User limit
            max_teams: Team limit
            settings: Tenant configuration
            security_settings: Security policies
            enabled_features: Feature flags
            billing_email: Billing contact
            technical_contact: Technical contact

        Returns:
            Created Tenant

        Raises:
            ValueError: If slug is already taken
        """
        # Generate slug if not provided
        if not slug:
            slug = self._generate_slug(name)

        # Check slug uniqueness
        existing = await self.get_by_slug(slug)
        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists")

        # Check domain uniqueness if provided
        if domain:
            existing_domain = await self.get_by_domain(domain)
            if existing_domain:
                raise ValueError(f"Tenant with domain '{domain}' already exists")

        tenant = Tenant(
            id=uuid4(),
            name=name,
            slug=slug,
            domain=domain,
            subscription_tier=subscription_tier,
            status=TenantStatus.TRIAL.value,
            max_users=max_users,
            max_teams=max_teams,
            settings=settings or {},
            security_settings=security_settings or {},
            enabled_features=enabled_features or [],
            billing_email=billing_email,
            technical_contact=technical_contact,
        )

        self.session.add(tenant)
        await self.session.flush()

        logger.info(f"Created tenant: {tenant.slug} (id={tenant.id})")

        return tenant

    async def update(
        self,
        tenant_id: UUID,
        **updates
    ) -> Optional[Tenant]:
        """
        Update tenant fields.

        Args:
            tenant_id: UUID of the tenant
            **updates: Fields to update

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        # Protected fields that can't be updated
        protected = {"id", "slug", "created_at"}

        for key, value in updates.items():
            if key not in protected and hasattr(tenant, key):
                setattr(tenant, key, value)

        await self.session.flush()

        logger.info(f"Updated tenant {tenant.slug}: {list(updates.keys())}")

        return tenant

    async def update_settings(
        self,
        tenant_id: UUID,
        settings: Dict[str, Any],
        *,
        merge: bool = True,
    ) -> Optional[Tenant]:
        """
        Update tenant settings.

        Args:
            tenant_id: UUID of the tenant
            settings: Settings to update
            merge: If True, merge with existing settings

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        if merge:
            current = tenant.settings or {}
            current.update(settings)
            tenant.settings = current
        else:
            tenant.settings = settings

        await self.session.flush()

        return tenant

    async def update_security_settings(
        self,
        tenant_id: UUID,
        security_settings: Dict[str, Any],
        *,
        merge: bool = True,
    ) -> Optional[Tenant]:
        """
        Update tenant security settings.

        Args:
            tenant_id: UUID of the tenant
            security_settings: Security settings to update
            merge: If True, merge with existing settings

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        if merge:
            current = tenant.security_settings or {}
            current.update(security_settings)
            tenant.security_settings = current
        else:
            tenant.security_settings = security_settings

        await self.session.flush()

        return tenant

    async def activate(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Activate a tenant (trial -> active or reactivate from suspended).

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        tenant.status = TenantStatus.ACTIVE.value
        await self.session.flush()

        logger.info(f"Activated tenant: {tenant.slug}")

        return tenant

    async def suspend(
        self,
        tenant_id: UUID,
        reason: Optional[str] = None,
    ) -> Optional[Tenant]:
        """
        Suspend a tenant.

        Args:
            tenant_id: UUID of the tenant
            reason: Suspension reason (stored in settings)

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        tenant.status = TenantStatus.SUSPENDED.value

        if reason:
            settings = tenant.settings or {}
            settings["suspension_reason"] = reason
            tenant.settings = settings

        await self.session.flush()

        logger.warning(f"Suspended tenant: {tenant.slug}, reason: {reason}")

        return tenant

    async def archive(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Archive a tenant (soft delete).

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        tenant.status = TenantStatus.ARCHIVED.value
        tenant.is_deleted = True

        from datetime import datetime, timezone
        tenant.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()

        logger.warning(f"Archived tenant: {tenant.slug}")

        return tenant

    async def enable_feature(
        self,
        tenant_id: UUID,
        feature: str,
    ) -> Optional[Tenant]:
        """
        Enable a feature for a tenant.

        Args:
            tenant_id: UUID of the tenant
            feature: Feature name to enable

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        features = list(tenant.enabled_features or [])
        if feature not in features:
            features.append(feature)
            tenant.enabled_features = features
            await self.session.flush()

        return tenant

    async def disable_feature(
        self,
        tenant_id: UUID,
        feature: str,
    ) -> Optional[Tenant]:
        """
        Disable a feature for a tenant.

        Args:
            tenant_id: UUID of the tenant
            feature: Feature name to disable

        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        features = list(tenant.enabled_features or [])
        if feature in features:
            features.remove(feature)
            tenant.enabled_features = features
            await self.session.flush()

        return tenant

    async def get_user_count(self, tenant_id: UUID) -> int:
        """
        Get count of users in a tenant.

        Note: Requires TenantMembership model to be configured.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Number of active users
        """
        # This would use TenantMembership model
        # Placeholder for now
        return 0

    async def get_team_count(self, tenant_id: UUID) -> int:
        """
        Get count of teams in a tenant.

        Note: Requires Team model to be configured.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Number of teams
        """
        # This would use Team model
        # Placeholder for now
        return 0

    def _generate_slug(self, name: str) -> str:
        """
        Generate a URL-safe slug from a name.

        Args:
            name: Tenant name

        Returns:
            URL-safe slug
        """
        # Convert to lowercase and replace spaces with hyphens
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')

        # Ensure it's not empty
        if not slug:
            slug = f"tenant-{uuid4().hex[:8]}"

        return slug
