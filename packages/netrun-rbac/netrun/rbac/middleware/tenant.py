"""
Netrun RBAC Tenant Resolution Middleware - Resolve tenant from incoming requests.

Following Netrun Systems SDLC v2.3 standards.

This middleware is the outermost layer of the tenancy stack. It:
1. Extracts tenant identifier from request (header/JWT/subdomain/path)
2. Looks up tenant in database (with caching)
3. Loads user's tenant membership and teams
4. Sets TenantContext for downstream middleware and handlers
"""

import logging
from typing import Callable, Optional, Awaitable, Any
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from ..tenancy.context import TenantContext
from ..tenancy.config import TenancyConfig, TenantResolutionStrategy
from ..tenancy.exceptions import (
    TenantNotFoundError,
    TenantAccessDeniedError,
    TenantSuspendedError,
)

logger = logging.getLogger(__name__)


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to resolve tenant from incoming requests.

    Supports multiple resolution strategies:
    - HEADER: X-Tenant-ID or X-Tenant-Slug header
    - JWT: Extract from JWT claims
    - SUBDOMAIN: tenant.example.com
    - PATH: /api/v1/tenants/{tenant_id}/...
    - CUSTOM: User-provided resolver function

    The resolved tenant context is set using TenantContext and is
    available to all downstream middleware and route handlers.

    Attributes:
        config: Tenancy configuration
        get_session: Factory function to get database session
        get_tenant_lookup: Async function to lookup tenant by ID/slug
        get_user_membership: Async function to get user's membership details
    """

    def __init__(
        self,
        app: ASGIApp,
        config: TenancyConfig,
        get_session: Optional[Callable] = None,
        get_tenant_lookup: Optional[Callable] = None,
        get_user_membership: Optional[Callable] = None,
    ):
        """
        Initialize the tenant resolution middleware.

        Args:
            app: ASGI application
            config: Tenancy configuration
            get_session: Factory to get database session
            get_tenant_lookup: Async function(session, id_or_slug) -> Tenant
            get_user_membership: Async function(session, user_id, tenant_id) -> membership dict
        """
        super().__init__(app)
        self.config = config
        self.get_session = get_session
        self.get_tenant_lookup = get_tenant_lookup
        self.get_user_membership = get_user_membership

        # Simple in-memory cache for tenant lookups
        self._tenant_cache: dict[str, tuple[Any, float]] = {}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Process the request and resolve tenant context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Check if path is exempt from tenant requirements
        if self.config.is_path_exempt(request.url.path):
            return await call_next(request)

        try:
            # Resolve tenant identifier from request
            tenant_id, tenant_slug = await self._resolve_tenant_identifier(request)

            if tenant_id is None and tenant_slug is None:
                if self.config.require_tenant:
                    return self._error_response(
                        "Tenant identification required",
                        status_code=400,
                        code="TENANT_REQUIRED"
                    )
                # No tenant required, continue without context
                return await call_next(request)

            # Lookup tenant (with caching)
            tenant = await self._lookup_tenant(tenant_id, tenant_slug)

            if tenant is None:
                raise TenantNotFoundError(
                    tenant_identifier=tenant_id or tenant_slug,
                    identifier_type="id" if tenant_id else "slug"
                )

            # Check tenant status
            if hasattr(tenant, 'status') and tenant.status == "suspended":
                raise TenantSuspendedError(
                    tenant_id=tenant.id,
                    tenant_slug=getattr(tenant, 'slug', None)
                )

            # Get user context if available
            user_id, user_roles, team_ids, team_paths = await self._resolve_user_context(
                request, tenant.id
            )

            # Set tenant context
            ctx = TenantContext(
                tenant_id=tenant.id,
                tenant_slug=getattr(tenant, 'slug', ''),
                user_id=user_id,
                user_roles=user_roles,
                team_ids=team_ids,
                team_paths=team_paths,
            )

            # Execute request within context
            with ctx:
                # Store tenant in request state for easy access
                request.state.tenant = tenant
                request.state.tenant_context = ctx.data

                # Call hook if configured
                if self.config.on_tenant_resolved:
                    await self._safe_call_hook(
                        self.config.on_tenant_resolved, request, tenant
                    )

                response = await call_next(request)

                return response

        except TenantNotFoundError as e:
            logger.warning(f"Tenant not found: {e}")
            return self._error_response(str(e), status_code=404, code=e.code)

        except TenantAccessDeniedError as e:
            logger.warning(f"Tenant access denied: {e}")
            return self._error_response(str(e), status_code=403, code=e.code)

        except TenantSuspendedError as e:
            logger.warning(f"Tenant suspended: {e}")
            return self._error_response(str(e), status_code=403, code=e.code)

        except Exception as e:
            logger.error(f"Tenant resolution error: {e}", exc_info=True)
            return self._error_response(
                "Internal server error during tenant resolution",
                status_code=500,
                code="TENANT_RESOLUTION_ERROR"
            )

    async def _resolve_tenant_identifier(
        self, request: Request
    ) -> tuple[Optional[UUID], Optional[str]]:
        """
        Extract tenant identifier from the request.

        Returns:
            Tuple of (tenant_id, tenant_slug) - one may be None
        """
        strategy = self.config.resolution_strategy

        if strategy == TenantResolutionStrategy.HEADER:
            return self._resolve_from_header(request)

        elif strategy == TenantResolutionStrategy.JWT:
            return await self._resolve_from_jwt(request)

        elif strategy == TenantResolutionStrategy.SUBDOMAIN:
            return self._resolve_from_subdomain(request)

        elif strategy == TenantResolutionStrategy.PATH:
            return self._resolve_from_path(request)

        elif strategy == TenantResolutionStrategy.CUSTOM:
            if self.config.custom_tenant_resolver:
                return await self.config.custom_tenant_resolver(request)

        return None, None

    def _resolve_from_header(
        self, request: Request
    ) -> tuple[Optional[UUID], Optional[str]]:
        """Resolve tenant from X-Tenant-ID or X-Tenant-Slug header."""
        tenant_id_str = request.headers.get(self.config.tenant_header)
        tenant_slug = request.headers.get(self.config.tenant_slug_header)

        tenant_id = None
        if tenant_id_str:
            try:
                tenant_id = UUID(tenant_id_str)
            except ValueError:
                # If not a valid UUID, treat as slug
                tenant_slug = tenant_id_str

        return tenant_id, tenant_slug

    async def _resolve_from_jwt(
        self, request: Request
    ) -> tuple[Optional[UUID], Optional[str]]:
        """Resolve tenant from JWT claims."""
        # JWT should be decoded by auth middleware and stored in request state
        if not hasattr(request.state, 'jwt_claims'):
            return None, None

        claims = request.state.jwt_claims
        tenant_id_str = claims.get(self.config.jwt_tenant_claim)
        tenant_slug = claims.get(self.config.jwt_tenant_slug_claim)

        tenant_id = None
        if tenant_id_str:
            try:
                tenant_id = UUID(tenant_id_str)
            except ValueError:
                pass

        return tenant_id, tenant_slug

    def _resolve_from_subdomain(
        self, request: Request
    ) -> tuple[Optional[UUID], Optional[str]]:
        """Resolve tenant from subdomain (tenant.example.com)."""
        host = request.headers.get("host", "")

        if not self.config.subdomain_suffix:
            return None, None

        if host.endswith(self.config.subdomain_suffix):
            slug = host[: -len(self.config.subdomain_suffix)]
            if slug and "." not in slug:  # Single subdomain level
                return None, slug

        return None, None

    def _resolve_from_path(
        self, request: Request
    ) -> tuple[Optional[UUID], Optional[str]]:
        """Resolve tenant from URL path (/api/v1/tenants/{tenant_id}/...)."""
        path_parts = request.url.path.strip("/").split("/")

        # Look for 'tenants' in path and get the next segment
        try:
            tenant_idx = path_parts.index("tenants")
            if tenant_idx + 1 < len(path_parts):
                identifier = path_parts[tenant_idx + 1]
                try:
                    return UUID(identifier), None
                except ValueError:
                    return None, identifier
        except ValueError:
            pass

        return None, None

    async def _lookup_tenant(
        self,
        tenant_id: Optional[UUID],
        tenant_slug: Optional[str],
    ) -> Optional[Any]:
        """
        Lookup tenant by ID or slug (with caching).

        Args:
            tenant_id: Tenant UUID
            tenant_slug: Tenant slug

        Returns:
            Tenant object or None
        """
        if self.get_tenant_lookup is None:
            logger.warning("No tenant lookup function configured")
            return None

        cache_key = str(tenant_id or tenant_slug)

        # Check cache
        if self.config.cache_tenant_lookups and cache_key in self._tenant_cache:
            import time
            tenant, cached_at = self._tenant_cache[cache_key]
            if time.time() - cached_at < self.config.tenant_cache_ttl_seconds:
                return tenant

        # Lookup from database
        if self.get_session is None:
            return None

        async with self.get_session() as session:
            tenant = await self.get_tenant_lookup(
                session,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug
            )

            # Cache result
            if tenant and self.config.cache_tenant_lookups:
                import time
                self._tenant_cache[cache_key] = (tenant, time.time())

            return tenant

    async def _resolve_user_context(
        self,
        request: Request,
        tenant_id: UUID,
    ) -> tuple[Optional[UUID], list[str], list[UUID], list[str]]:
        """
        Resolve user context (roles, teams) from request.

        Returns:
            Tuple of (user_id, roles, team_ids, team_paths)
        """
        user_id = None
        user_roles = []
        team_ids = []
        team_paths = []

        # Get user ID from request state (set by auth middleware)
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        elif hasattr(request.state, 'jwt_claims'):
            user_id_str = request.state.jwt_claims.get('sub')
            if user_id_str:
                try:
                    user_id = UUID(user_id_str)
                except ValueError:
                    pass

        # Get membership details
        if user_id and self.get_user_membership and self.get_session:
            async with self.get_session() as session:
                membership = await self.get_user_membership(
                    session, user_id, tenant_id
                )
                if membership:
                    user_roles = membership.get('roles', [])
                    team_ids = membership.get('team_ids', [])
                    team_paths = membership.get('team_paths', [])

        return user_id, user_roles, team_ids, team_paths

    async def _safe_call_hook(
        self, hook: Callable, *args, **kwargs
    ) -> None:
        """Safely call a hook function, catching any errors."""
        try:
            result = hook(*args, **kwargs)
            if hasattr(result, '__await__'):
                await result
        except Exception as e:
            logger.warning(f"Hook execution failed: {e}")

    def _error_response(
        self,
        message: str,
        status_code: int = 400,
        code: str = "TENANT_ERROR",
    ) -> JSONResponse:
        """Create an error JSON response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": code,
                "message": message,
            }
        )
