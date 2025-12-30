"""
Netrun RBAC Share Service - Resource sharing operations.

Following Netrun Systems SDLC v2.3 standards.

Provides operations for sharing resources:
- Share with users, teams, or tenants
- External sharing via email link
- Permission management
- Share expiration and revocation
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Type
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.resource_share import ResourceShare
from ..models.enums import SharePermission
from ..tenancy.context import TenantContext
from ..tenancy.exceptions import ShareAccessDeniedError, CrossTenantViolationError

logger = logging.getLogger(__name__)


class ShareService:
    """
    Service for resource sharing operations.

    Handles creating, querying, and managing resource shares
    with support for users, teams, tenants, and external sharing.

    Attributes:
        session: SQLAlchemy async session
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the share service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def share_with_user(
        self,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
        *,
        permission: SharePermission = SharePermission.VIEW,
        expires_at: Optional[datetime] = None,
        message: Optional[str] = None,
    ) -> ResourceShare:
        """
        Share a resource with a specific user.

        Args:
            resource_type: Type of resource (e.g., "contact", "document")
            resource_id: UUID of the resource
            user_id: UUID of the target user
            permission: Permission level to grant
            expires_at: Optional expiration datetime
            message: Optional message for the recipient

        Returns:
            Created ResourceShare
        """
        ctx = TenantContext.require()

        share = ResourceShare(
            id=uuid4(),
            tenant_id=ctx.tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            shared_with_user_id=user_id,
            permission=permission.value,
            expires_at=expires_at,
            shared_by=ctx.user_id,
            message=message,
        )

        self.session.add(share)
        await self.session.flush()

        logger.info(
            f"Shared {resource_type}:{resource_id} with user {user_id} "
            f"({permission.value})"
        )

        return share

    async def share_with_team(
        self,
        resource_type: str,
        resource_id: UUID,
        team_id: UUID,
        *,
        permission: SharePermission = SharePermission.VIEW,
        expires_at: Optional[datetime] = None,
        message: Optional[str] = None,
    ) -> ResourceShare:
        """
        Share a resource with an entire team.

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource
            team_id: UUID of the target team
            permission: Permission level to grant
            expires_at: Optional expiration datetime
            message: Optional message

        Returns:
            Created ResourceShare
        """
        ctx = TenantContext.require()

        share = ResourceShare(
            id=uuid4(),
            tenant_id=ctx.tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            shared_with_team_id=team_id,
            permission=permission.value,
            expires_at=expires_at,
            shared_by=ctx.user_id,
            message=message,
        )

        self.session.add(share)
        await self.session.flush()

        logger.info(
            f"Shared {resource_type}:{resource_id} with team {team_id} "
            f"({permission.value})"
        )

        return share

    async def share_with_tenant(
        self,
        resource_type: str,
        resource_id: UUID,
        target_tenant_id: UUID,
        *,
        permission: SharePermission = SharePermission.VIEW,
        expires_at: Optional[datetime] = None,
        message: Optional[str] = None,
    ) -> ResourceShare:
        """
        Share a resource with another tenant (cross-tenant sharing).

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource
            target_tenant_id: UUID of the target tenant
            permission: Permission level to grant
            expires_at: Optional expiration datetime
            message: Optional message

        Returns:
            Created ResourceShare
        """
        ctx = TenantContext.require()

        share = ResourceShare(
            id=uuid4(),
            tenant_id=ctx.tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            shared_with_tenant_id=target_tenant_id,
            permission=permission.value,
            expires_at=expires_at,
            shared_by=ctx.user_id,
            message=message,
        )

        self.session.add(share)
        await self.session.flush()

        logger.info(
            f"Shared {resource_type}:{resource_id} with tenant "
            f"{target_tenant_id} ({permission.value})"
        )

        return share

    async def share_externally(
        self,
        resource_type: str,
        resource_id: UUID,
        email: str,
        *,
        permission: SharePermission = SharePermission.VIEW,
        expires_hours: int = 72,
        message: Optional[str] = None,
    ) -> ResourceShare:
        """
        Share a resource externally via email link.

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource
            email: Email address of external recipient
            permission: Permission level to grant
            expires_hours: Hours until share expires
            message: Optional message for recipient

        Returns:
            Created ResourceShare with external_token
        """
        ctx = TenantContext.require()

        share = ResourceShare(
            id=uuid4(),
            tenant_id=ctx.tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            shared_externally=email,
            permission=permission.value,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
            shared_by=ctx.user_id,
            message=message,
            external_token=secrets.token_urlsafe(32),
        )

        self.session.add(share)
        await self.session.flush()

        logger.info(
            f"Shared {resource_type}:{resource_id} externally with {email}"
        )

        return share

    async def get_share_by_token(
        self,
        token: str,
    ) -> Optional[ResourceShare]:
        """
        Get an external share by its token.

        Args:
            token: External share token

        Returns:
            ResourceShare if found and valid, None otherwise
        """
        result = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.external_token == token,
                ResourceShare.is_revoked == False,
            )
        )
        share = result.scalar_one_or_none()

        if share and share.is_expired:
            return None

        return share

    async def get_shares_for_resource(
        self,
        resource_type: str,
        resource_id: UUID,
        *,
        include_revoked: bool = False,
        include_expired: bool = False,
    ) -> List[ResourceShare]:
        """
        Get all shares for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource
            include_revoked: Include revoked shares
            include_expired: Include expired shares

        Returns:
            List of ResourceShare records
        """
        ctx = TenantContext.require()

        query = select(ResourceShare).where(
            ResourceShare.tenant_id == ctx.tenant_id,
            ResourceShare.resource_type == resource_type,
            ResourceShare.resource_id == resource_id,
        )

        if not include_revoked:
            query = query.where(ResourceShare.is_revoked == False)

        if not include_expired:
            query = query.where(
                or_(
                    ResourceShare.expires_at.is_(None),
                    ResourceShare.expires_at > datetime.now(timezone.utc),
                )
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_shares_for_user(
        self,
        user_id: UUID,
        *,
        resource_type: Optional[str] = None,
    ) -> List[ResourceShare]:
        """
        Get all resources shared with a user.

        Args:
            user_id: UUID of the user
            resource_type: Optional filter by resource type

        Returns:
            List of active ResourceShare records
        """
        query = select(ResourceShare).where(
            ResourceShare.shared_with_user_id == user_id,
            ResourceShare.is_revoked == False,
            or_(
                ResourceShare.expires_at.is_(None),
                ResourceShare.expires_at > datetime.now(timezone.utc),
            ),
        )

        if resource_type:
            query = query.where(ResourceShare.resource_type == resource_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_shares_for_team(
        self,
        team_id: UUID,
        *,
        resource_type: Optional[str] = None,
    ) -> List[ResourceShare]:
        """
        Get all resources shared with a team.

        Args:
            team_id: UUID of the team
            resource_type: Optional filter by resource type

        Returns:
            List of active ResourceShare records
        """
        query = select(ResourceShare).where(
            ResourceShare.shared_with_team_id == team_id,
            ResourceShare.is_revoked == False,
            or_(
                ResourceShare.expires_at.is_(None),
                ResourceShare.expires_at > datetime.now(timezone.utc),
            ),
        )

        if resource_type:
            query = query.where(ResourceShare.resource_type == resource_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def check_access(
        self,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
        *,
        required_permission: SharePermission = SharePermission.VIEW,
        team_ids: Optional[List[UUID]] = None,
    ) -> bool:
        """
        Check if a user has access to a resource via sharing.

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource
            user_id: UUID of the user
            required_permission: Minimum permission required
            team_ids: User's team IDs (for team share check)

        Returns:
            True if user has required permission
        """
        # Define permission hierarchy
        permission_levels = {
            SharePermission.VIEW.value: 1,
            SharePermission.COMMENT.value: 2,
            SharePermission.EDIT.value: 3,
            SharePermission.FULL.value: 4,
        }

        required_level = permission_levels.get(required_permission.value, 0)

        # Check user-level share
        user_share = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.resource_type == resource_type,
                ResourceShare.resource_id == resource_id,
                ResourceShare.shared_with_user_id == user_id,
                ResourceShare.is_revoked == False,
                or_(
                    ResourceShare.expires_at.is_(None),
                    ResourceShare.expires_at > datetime.now(timezone.utc),
                ),
            )
        )
        share = user_share.scalar_one_or_none()

        if share:
            share_level = permission_levels.get(share.permission, 0)
            if share_level >= required_level:
                share.record_access()
                await self.session.flush()
                return True

        # Check team-level shares
        if team_ids:
            team_share = await self.session.execute(
                select(ResourceShare).where(
                    ResourceShare.resource_type == resource_type,
                    ResourceShare.resource_id == resource_id,
                    ResourceShare.shared_with_team_id.in_(team_ids),
                    ResourceShare.is_revoked == False,
                    or_(
                        ResourceShare.expires_at.is_(None),
                        ResourceShare.expires_at > datetime.now(timezone.utc),
                    ),
                )
            )
            for share in team_share.scalars():
                share_level = permission_levels.get(share.permission, 0)
                if share_level >= required_level:
                    share.record_access()
                    await self.session.flush()
                    return True

        return False

    async def revoke(
        self,
        share_id: UUID,
    ) -> bool:
        """
        Revoke a share.

        Args:
            share_id: UUID of the share

        Returns:
            True if revoked, False if not found
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.id == share_id,
                ResourceShare.tenant_id == ctx.tenant_id,
            )
        )
        share = result.scalar_one_or_none()

        if not share:
            return False

        share.revoke(ctx.user_id)
        await self.session.flush()

        logger.info(f"Revoked share {share_id}")

        return True

    async def revoke_all_for_resource(
        self,
        resource_type: str,
        resource_id: UUID,
    ) -> int:
        """
        Revoke all shares for a resource.

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource

        Returns:
            Number of shares revoked
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.tenant_id == ctx.tenant_id,
                ResourceShare.resource_type == resource_type,
                ResourceShare.resource_id == resource_id,
                ResourceShare.is_revoked == False,
            )
        )
        shares = result.scalars().all()

        for share in shares:
            share.revoke(ctx.user_id)

        await self.session.flush()

        logger.info(
            f"Revoked {len(shares)} shares for {resource_type}:{resource_id}"
        )

        return len(shares)

    async def update_permission(
        self,
        share_id: UUID,
        new_permission: SharePermission,
    ) -> Optional[ResourceShare]:
        """
        Update the permission level of a share.

        Args:
            share_id: UUID of the share
            new_permission: New permission level

        Returns:
            Updated share or None if not found
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.id == share_id,
                ResourceShare.tenant_id == ctx.tenant_id,
            )
        )
        share = result.scalar_one_or_none()

        if not share:
            return None

        share.permission = new_permission.value
        share.updated_by = ctx.user_id

        await self.session.flush()

        return share

    async def extend_expiration(
        self,
        share_id: UUID,
        new_expires_at: datetime,
    ) -> Optional[ResourceShare]:
        """
        Extend the expiration of a share.

        Args:
            share_id: UUID of the share
            new_expires_at: New expiration datetime

        Returns:
            Updated share or None if not found
        """
        ctx = TenantContext.require()

        result = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.id == share_id,
                ResourceShare.tenant_id == ctx.tenant_id,
            )
        )
        share = result.scalar_one_or_none()

        if not share:
            return None

        share.expires_at = new_expires_at
        share.updated_by = ctx.user_id

        await self.session.flush()

        return share

    async def cleanup_expired(self) -> int:
        """
        Cleanup expired shares (batch operation).

        Returns:
            Number of shares marked as expired
        """
        result = await self.session.execute(
            select(ResourceShare).where(
                ResourceShare.is_revoked == False,
                ResourceShare.expires_at.isnot(None),
                ResourceShare.expires_at < datetime.now(timezone.utc),
            )
        )
        shares = result.scalars().all()

        for share in shares:
            share.is_revoked = True
            share.revoked_at = datetime.now(timezone.utc)

        await self.session.flush()

        if shares:
            logger.info(f"Cleaned up {len(shares)} expired shares")

        return len(shares)
