"""
Netrun RBAC Membership Service - User membership management.

Following Netrun Systems SDLC v2.3 standards.

Provides operations for managing user memberships in tenants and teams:
- Adding/removing users from tenants
- Managing roles and permissions
- Invitation management
- Membership queries
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.membership import TenantMembership, TenantInvitation
from ..models.enums import TenantRole, InvitationStatus
from ..tenancy.context import TenantContext
from ..tenancy.exceptions import TenantAccessDeniedError

logger = logging.getLogger(__name__)


class MembershipService:
    """
    Service for tenant and team membership management.

    Handles user membership operations including invitations,
    role management, and permission queries.

    Attributes:
        session: SQLAlchemy async session
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the membership service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_user_membership(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Optional[TenantMembership]:
        """
        Get a user's membership in a tenant.

        Args:
            user_id: UUID of the user
            tenant_id: UUID of the tenant

        Returns:
            TenantMembership if found, None otherwise
        """
        result = await self.session.execute(
            select(TenantMembership).where(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_tenants(
        self,
        user_id: UUID,
        *,
        active_only: bool = True,
    ) -> List[TenantMembership]:
        """
        Get all tenant memberships for a user.

        Args:
            user_id: UUID of the user
            active_only: Only return active memberships

        Returns:
            List of TenantMembership records
        """
        query = select(TenantMembership).where(
            TenantMembership.user_id == user_id
        )

        if active_only:
            query = query.where(TenantMembership.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tenant_members(
        self,
        tenant_id: UUID,
        *,
        active_only: bool = True,
        role: Optional[TenantRole] = None,
    ) -> List[TenantMembership]:
        """
        Get all members of a tenant.

        Args:
            tenant_id: UUID of the tenant
            active_only: Only return active members
            role: Filter by specific role

        Returns:
            List of TenantMembership records
        """
        query = select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id
        )

        if active_only:
            query = query.where(TenantMembership.is_active == True)

        if role:
            query = query.where(TenantMembership.role == role.value)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_member(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        role: TenantRole = TenantRole.MEMBER,
        invited_by: Optional[UUID] = None,
        custom_permissions: Optional[List[str]] = None,
    ) -> TenantMembership:
        """
        Add a user to a tenant.

        Args:
            tenant_id: UUID of the tenant
            user_id: UUID of the user
            role: Role to assign
            invited_by: UUID of inviting user
            custom_permissions: Additional permissions

        Returns:
            Created TenantMembership
        """
        # Check if already a member
        existing = await self.get_user_membership(user_id, tenant_id)

        if existing:
            # Reactivate if inactive
            existing.is_active = True
            existing.role = role.value
            if custom_permissions:
                existing.custom_permissions = custom_permissions
            await self.session.flush()
            return existing

        membership = TenantMembership(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role.value,
            custom_permissions=custom_permissions or [],
            invited_by=invited_by,
            invited_at=datetime.now(timezone.utc) if invited_by else None,
            joined_at=datetime.now(timezone.utc),
        )

        self.session.add(membership)
        await self.session.flush()

        logger.info(
            f"Added user {user_id} to tenant {tenant_id} as {role.value}"
        )

        return membership

    async def remove_member(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Remove a user from a tenant (soft delete).

        Args:
            tenant_id: UUID of the tenant
            user_id: UUID of the user

        Returns:
            True if removed, False if not a member
        """
        membership = await self.get_user_membership(user_id, tenant_id)

        if not membership:
            return False

        # Don't allow removing the last owner
        if membership.role == TenantRole.OWNER.value:
            owners = await self.get_tenant_members(
                tenant_id, role=TenantRole.OWNER
            )
            if len(owners) <= 1:
                raise TenantAccessDeniedError(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    reason="Cannot remove the last owner"
                )

        membership.is_active = False
        await self.session.flush()

        logger.info(f"Removed user {user_id} from tenant {tenant_id}")

        return True

    async def update_role(
        self,
        tenant_id: UUID,
        user_id: UUID,
        new_role: TenantRole,
    ) -> Optional[TenantMembership]:
        """
        Update a user's role in a tenant.

        Args:
            tenant_id: UUID of the tenant
            user_id: UUID of the user
            new_role: New role to assign

        Returns:
            Updated membership or None if not found
        """
        membership = await self.get_user_membership(user_id, tenant_id)

        if not membership:
            return None

        # Don't allow demoting the last owner
        if membership.role == TenantRole.OWNER.value and new_role != TenantRole.OWNER:
            owners = await self.get_tenant_members(
                tenant_id, role=TenantRole.OWNER
            )
            if len(owners) <= 1:
                raise TenantAccessDeniedError(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    reason="Cannot demote the last owner"
                )

        membership.role = new_role.value
        await self.session.flush()

        logger.info(
            f"Updated user {user_id} role to {new_role.value} "
            f"in tenant {tenant_id}"
        )

        return membership

    async def add_permission(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permission: str,
    ) -> Optional[TenantMembership]:
        """
        Add a custom permission to a user's membership.

        Args:
            tenant_id: UUID of the tenant
            user_id: UUID of the user
            permission: Permission string to add

        Returns:
            Updated membership or None if not found
        """
        membership = await self.get_user_membership(user_id, tenant_id)

        if not membership:
            return None

        permissions = list(membership.custom_permissions or [])
        if permission not in permissions:
            permissions.append(permission)
            membership.custom_permissions = permissions
            await self.session.flush()

        return membership

    async def remove_permission(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permission: str,
    ) -> Optional[TenantMembership]:
        """
        Remove a custom permission from a user's membership.

        Args:
            tenant_id: UUID of the tenant
            user_id: UUID of the user
            permission: Permission string to remove

        Returns:
            Updated membership or None if not found
        """
        membership = await self.get_user_membership(user_id, tenant_id)

        if not membership:
            return None

        permissions = list(membership.custom_permissions or [])
        if permission in permissions:
            permissions.remove(permission)
            membership.custom_permissions = permissions
            await self.session.flush()

        return membership

    # Invitation methods

    async def create_invitation(
        self,
        tenant_id: UUID,
        email: str,
        *,
        role: TenantRole = TenantRole.MEMBER,
        invited_by: UUID,
        expires_hours: int = 72,
    ) -> TenantInvitation:
        """
        Create an invitation to join a tenant.

        Args:
            tenant_id: UUID of the tenant
            email: Email address to invite
            role: Role to assign upon acceptance
            invited_by: UUID of inviting user
            expires_hours: Hours until invitation expires

        Returns:
            Created TenantInvitation
        """
        # Check for existing pending invitation
        existing = await self.session.execute(
            select(TenantInvitation).where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.email == email,
                TenantInvitation.status == InvitationStatus.PENDING.value,
            )
        )
        if existing.scalar_one_or_none():
            # Revoke old invitation
            await self.revoke_invitation_by_email(tenant_id, email)

        invitation = TenantInvitation(
            id=uuid4(),
            tenant_id=tenant_id,
            email=email,
            role=role.value,
            status=InvitationStatus.PENDING.value,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
            invited_by=invited_by,
        )

        self.session.add(invitation)
        await self.session.flush()

        logger.info(f"Created invitation for {email} to tenant {tenant_id}")

        return invitation

    async def get_invitation_by_token(
        self,
        token: str,
    ) -> Optional[TenantInvitation]:
        """
        Get an invitation by its token.

        Args:
            token: Invitation token

        Returns:
            TenantInvitation if found, None otherwise
        """
        result = await self.session.execute(
            select(TenantInvitation).where(
                TenantInvitation.token == token
            )
        )
        return result.scalar_one_or_none()

    async def accept_invitation(
        self,
        token: str,
        user_id: UUID,
    ) -> Optional[TenantMembership]:
        """
        Accept an invitation and create membership.

        Args:
            token: Invitation token
            user_id: UUID of accepting user

        Returns:
            Created TenantMembership or None if invalid invitation
        """
        invitation = await self.get_invitation_by_token(token)

        if not invitation:
            return None

        # Check if expired
        if invitation.is_expired:
            invitation.status = InvitationStatus.EXPIRED.value
            await self.session.flush()
            return None

        # Check if still pending
        if invitation.status != InvitationStatus.PENDING.value:
            return None

        # Create membership
        membership = await self.add_member(
            tenant_id=invitation.tenant_id,
            user_id=user_id,
            role=TenantRole(invitation.role),
            invited_by=invitation.invited_by,
        )

        # Update invitation status
        invitation.status = InvitationStatus.ACCEPTED.value
        invitation.accepted_at = datetime.now(timezone.utc)

        await self.session.flush()

        logger.info(
            f"Invitation accepted: user {user_id} joined tenant "
            f"{invitation.tenant_id}"
        )

        return membership

    async def decline_invitation(self, token: str) -> bool:
        """
        Decline an invitation.

        Args:
            token: Invitation token

        Returns:
            True if declined, False if invalid
        """
        invitation = await self.get_invitation_by_token(token)

        if not invitation or invitation.status != InvitationStatus.PENDING.value:
            return False

        invitation.status = InvitationStatus.DECLINED.value
        await self.session.flush()

        return True

    async def revoke_invitation(self, invitation_id: UUID) -> bool:
        """
        Revoke an invitation by ID.

        Args:
            invitation_id: UUID of the invitation

        Returns:
            True if revoked, False if not found
        """
        result = await self.session.execute(
            select(TenantInvitation).where(
                TenantInvitation.id == invitation_id
            )
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            return False

        invitation.status = InvitationStatus.REVOKED.value
        await self.session.flush()

        return True

    async def revoke_invitation_by_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> bool:
        """
        Revoke all pending invitations for an email in a tenant.

        Args:
            tenant_id: UUID of the tenant
            email: Email address

        Returns:
            True if any revoked
        """
        result = await self.session.execute(
            select(TenantInvitation).where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.email == email,
                TenantInvitation.status == InvitationStatus.PENDING.value,
            )
        )
        invitations = result.scalars().all()

        for inv in invitations:
            inv.status = InvitationStatus.REVOKED.value

        await self.session.flush()

        return len(invitations) > 0

    async def get_pending_invitations(
        self,
        tenant_id: UUID,
    ) -> List[TenantInvitation]:
        """
        Get all pending invitations for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            List of pending invitations
        """
        result = await self.session.execute(
            select(TenantInvitation).where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.status == InvitationStatus.PENDING.value,
            ).order_by(TenantInvitation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_membership_details(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive membership details for context resolution.

        Returns dict with roles, team_ids, and team_paths for use
        in TenantContext.

        Args:
            user_id: UUID of the user
            tenant_id: UUID of the tenant

        Returns:
            Dict with membership details or None if not a member
        """
        membership = await self.get_user_membership(user_id, tenant_id)

        if not membership or not membership.is_active:
            return None

        # Get team details (would integrate with TeamService)
        # Placeholder for now
        return {
            "roles": [membership.role],
            "custom_permissions": membership.custom_permissions or [],
            "team_ids": [],
            "team_paths": [],
        }
