"""
Netrun RBAC Tenant Context - Thread-safe tenant context using contextvars.

Following Netrun Systems SDLC v2.3 standards.

The TenantContext provides thread-safe, async-safe context management for
multi-tenant applications. It uses Python's contextvars module to maintain
tenant state across async boundaries.

Usage:
    # As context manager
    with TenantContext(tenant_id=uuid, tenant_slug="acme"):
        # All code here sees the tenant context
        ctx = TenantContext.get_current()

    # Manual management
    ctx = TenantContext(tenant_id=uuid, tenant_slug="acme")
    token = ctx.set()
    try:
        # Do work
    finally:
        ctx.reset(token)
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Optional, Tuple, Any
from uuid import UUID

from .exceptions import TenantContextError


@dataclass(frozen=True)
class TenantContextData:
    """
    Immutable data container for tenant context.

    Using frozen=True ensures the context data cannot be modified after creation,
    preventing accidental mutations across async boundaries.

    Attributes:
        tenant_id: UUID of the current tenant
        tenant_slug: URL-safe identifier for the tenant
        user_id: UUID of the current user (optional)
        user_roles: Tuple of role strings for the user
        team_ids: Tuple of team UUIDs the user belongs to
        team_paths: Tuple of team materialized paths for hierarchy queries
        custom_permissions: Tuple of additional permission strings
        session_metadata: Additional session data (request ID, IP, etc.)
    """

    tenant_id: UUID
    tenant_slug: str = ""
    user_id: Optional[UUID] = None
    user_roles: Tuple[str, ...] = ()
    team_ids: Tuple[UUID, ...] = ()
    team_paths: Tuple[str, ...] = ()
    custom_permissions: Tuple[str, ...] = ()
    session_metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate context data after creation."""
        if not self.tenant_id:
            raise TenantContextError("tenant_id is required")

    @property
    def has_user(self) -> bool:
        """Check if user context is available."""
        return self.user_id is not None

    @property
    def is_admin(self) -> bool:
        """Check if user has admin or owner role."""
        admin_roles = {"owner", "admin"}
        return bool(admin_roles & set(self.user_roles))

    @property
    def is_owner(self) -> bool:
        """Check if user has owner role."""
        return "owner" in self.user_roles

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.user_roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has a custom permission."""
        return permission in self.custom_permissions

    def is_in_team(self, team_id: UUID) -> bool:
        """Check if user is a member of a specific team."""
        return team_id in self.team_ids

    def has_team_path_access(self, path: str) -> bool:
        """
        Check if user has access to a team based on materialized path.

        User has access if any of their team paths is a prefix of the target path
        (meaning they're in an ancestor team) or matches exactly.
        """
        for user_path in self.team_paths:
            if path == user_path or path.startswith(user_path + "/"):
                return True
        return False


# Module-level context variable
_tenant_context: ContextVar[Optional[TenantContextData]] = ContextVar(
    "tenant_context", default=None
)


class TenantContext:
    """
    Thread-safe tenant context manager using contextvars.

    Provides both context manager and manual APIs for setting tenant context.
    The context is automatically propagated across async boundaries.

    Usage as context manager:
        with TenantContext(tenant_id=uuid, tenant_slug="acme"):
            # Context is active here
            ctx = TenantContext.get_current()

    Usage with manual management:
        ctx = TenantContext(tenant_id=uuid, tenant_slug="acme")
        token = ctx.set()
        try:
            # Context is active here
        finally:
            ctx.reset(token)

    Class methods for accessing context:
        TenantContext.get_current() -> Optional[TenantContextData]
        TenantContext.require() -> TenantContextData (raises if not set)
        TenantContext.get_tenant_id() -> Optional[UUID]
        TenantContext.get_user_id() -> Optional[UUID]
    """

    def __init__(
        self,
        tenant_id: UUID,
        tenant_slug: str = "",
        user_id: Optional[UUID] = None,
        user_roles: Optional[list[str]] = None,
        team_ids: Optional[list[UUID]] = None,
        team_paths: Optional[list[str]] = None,
        custom_permissions: Optional[list[str]] = None,
        session_metadata: Optional[dict] = None,
    ):
        """
        Initialize a new tenant context.

        Args:
            tenant_id: UUID of the tenant
            tenant_slug: URL-safe tenant identifier
            user_id: UUID of the current user (optional)
            user_roles: List of role strings for the user
            team_ids: List of team UUIDs the user belongs to
            team_paths: List of team materialized paths
            custom_permissions: List of additional permission strings
            session_metadata: Additional session data
        """
        self.data = TenantContextData(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            user_id=user_id,
            user_roles=tuple(user_roles or []),
            team_ids=tuple(team_ids or []),
            team_paths=tuple(team_paths or []),
            custom_permissions=tuple(custom_permissions or []),
            session_metadata=session_metadata or {},
        )
        self._token: Optional[Token] = None

    def __enter__(self) -> TenantContextData:
        """Enter context manager and set the tenant context."""
        self._token = _tenant_context.set(self.data)
        return self.data

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and reset the tenant context."""
        if self._token is not None:
            _tenant_context.reset(self._token)
            self._token = None

    def set(self) -> Token:
        """
        Manually set the context and return a token for reset.

        Returns:
            Token that can be used to reset the context
        """
        self._token = _tenant_context.set(self.data)
        return self._token

    def reset(self, token: Optional[Token] = None) -> None:
        """
        Reset the context using the provided or stored token.

        Args:
            token: Token from set() call, or uses stored token if None
        """
        reset_token = token or self._token
        if reset_token is not None:
            _tenant_context.reset(reset_token)
            self._token = None

    # Class methods for accessing context

    @classmethod
    def get_current(cls) -> Optional[TenantContextData]:
        """
        Get the current tenant context if set.

        Returns:
            TenantContextData if context is set, None otherwise
        """
        return _tenant_context.get()

    @classmethod
    def require(cls) -> TenantContextData:
        """
        Get the current tenant context, raising if not set.

        Returns:
            TenantContextData

        Raises:
            TenantContextError: If no tenant context is set
        """
        ctx = _tenant_context.get()
        if ctx is None:
            raise TenantContextError(
                "Tenant context not set. Ensure TenantResolutionMiddleware is configured "
                "or use TenantContext context manager."
            )
        return ctx

    @classmethod
    def get_tenant_id(cls) -> Optional[UUID]:
        """Get the current tenant ID if context is set."""
        ctx = _tenant_context.get()
        return ctx.tenant_id if ctx else None

    @classmethod
    def get_user_id(cls) -> Optional[UUID]:
        """Get the current user ID if context is set."""
        ctx = _tenant_context.get()
        return ctx.user_id if ctx else None

    @classmethod
    def get_tenant_slug(cls) -> Optional[str]:
        """Get the current tenant slug if context is set."""
        ctx = _tenant_context.get()
        return ctx.tenant_slug if ctx else None

    @classmethod
    def is_set(cls) -> bool:
        """Check if tenant context is currently set."""
        return _tenant_context.get() is not None

    @classmethod
    def clear(cls) -> None:
        """
        Clear the current context.

        WARNING: This should only be used in testing or cleanup scenarios.
        Normal code should use the context manager or reset() method.
        """
        _tenant_context.set(None)


# Convenience alias
get_tenant_context = TenantContext.get_current
require_tenant_context = TenantContext.require
