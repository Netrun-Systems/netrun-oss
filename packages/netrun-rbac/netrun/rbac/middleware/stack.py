"""
Netrun RBAC Middleware Stack - Setup complete tenancy middleware stack.

Following Netrun Systems SDLC v2.3 standards.

This module provides a single function to setup all tenancy middleware
in the correct order with proper configuration.

Middleware order (outermost to innermost):
1. TenantResolutionMiddleware - Resolves tenant from request
2. IsolationEnforcementMiddleware - Sets up database isolation
3. TenantSecurityMiddleware - Security checks and audit logging

Usage:
    from fastapi import FastAPI
    from netrun.rbac.middleware import setup_tenancy_middleware
    from netrun.rbac.tenancy import TenancyConfig

    app = FastAPI()

    setup_tenancy_middleware(
        app,
        config=TenancyConfig(require_tenant=True),
        get_session=get_db_session,
        get_tenant_lookup=lookup_tenant_by_id_or_slug,
        get_user_membership=get_user_tenant_membership,
    )
"""

import logging
from typing import Callable, Optional, Any

from fastapi import FastAPI

from .tenant import TenantResolutionMiddleware
from .isolation import IsolationEnforcementMiddleware
from .security import TenantSecurityMiddleware
from ..tenancy.config import TenancyConfig

logger = logging.getLogger(__name__)


def setup_tenancy_middleware(
    app: FastAPI,
    config: Optional[TenancyConfig] = None,
    get_session: Optional[Callable] = None,
    get_tenant_lookup: Optional[Callable] = None,
    get_user_membership: Optional[Callable] = None,
    audit_logger: Optional[logging.Logger] = None,
    rate_limiter: Optional[Any] = None,
) -> None:
    """
    Setup the complete tenancy middleware stack on a FastAPI application.

    This adds three middleware layers in the correct order:
    1. TenantResolutionMiddleware (outermost) - Resolves tenant from request
    2. IsolationEnforcementMiddleware - Sets up database isolation
    3. TenantSecurityMiddleware (innermost) - Security and audit

    Note: FastAPI middleware is added in reverse order (last added = outermost),
    so we add them in reverse order here.

    Args:
        app: FastAPI application instance
        config: Tenancy configuration (uses defaults if None)
        get_session: Async context manager to get database session
        get_tenant_lookup: Async function to lookup tenant by ID/slug
        get_user_membership: Async function to get user's membership details
        audit_logger: Custom logger for audit events
        rate_limiter: Optional rate limiter instance

    Example:
        async def get_db_session():
            async with AsyncSessionLocal() as session:
                yield session

        async def lookup_tenant(session, tenant_id=None, tenant_slug=None):
            if tenant_id:
                return await session.get(Tenant, tenant_id)
            if tenant_slug:
                result = await session.execute(
                    select(Tenant).where(Tenant.slug == tenant_slug)
                )
                return result.scalar_one_or_none()

        async def get_membership(session, user_id, tenant_id):
            # Return dict with roles, team_ids, team_paths
            return {
                "roles": ["member"],
                "team_ids": [...],
                "team_paths": [...],
            }

        setup_tenancy_middleware(
            app,
            config=TenancyConfig(require_tenant=True),
            get_session=get_db_session,
            get_tenant_lookup=lookup_tenant,
            get_user_membership=get_membership,
        )
    """
    config = config or TenancyConfig()

    # Validate configuration
    validation_errors = config.validate()
    if validation_errors:
        for error in validation_errors:
            logger.warning(f"Tenancy config validation warning: {error}")

    # Add middleware in REVERSE order (FastAPI adds outermost last)

    # 3. Security middleware (innermost - runs last before handler)
    if config.enable_security_middleware:
        app.add_middleware(
            TenantSecurityMiddleware,
            config=config,
            audit_logger=audit_logger,
            rate_limiter=rate_limiter,
        )
        logger.debug("Added TenantSecurityMiddleware")

    # 2. Isolation enforcement middleware (middle)
    app.add_middleware(
        IsolationEnforcementMiddleware,
        config=config,
        get_session=get_session,
        strict_mode=config.strict_isolation,
    )
    logger.debug("Added IsolationEnforcementMiddleware")

    # 1. Tenant resolution middleware (outermost - runs first)
    app.add_middleware(
        TenantResolutionMiddleware,
        config=config,
        get_session=get_session,
        get_tenant_lookup=get_tenant_lookup,
        get_user_membership=get_user_membership,
    )
    logger.debug("Added TenantResolutionMiddleware")

    logger.info(
        f"Tenancy middleware stack configured: "
        f"mode={config.isolation_mode.value}, "
        f"require_tenant={config.require_tenant}, "
        f"security={config.enable_security_middleware}"
    )


def setup_minimal_tenancy(
    app: FastAPI,
    get_session: Optional[Callable] = None,
    get_tenant_lookup: Optional[Callable] = None,
) -> None:
    """
    Setup minimal tenancy with just resolution middleware.

    Use this for simpler applications that don't need the full
    security and isolation stack.

    Args:
        app: FastAPI application instance
        get_session: Async context manager to get database session
        get_tenant_lookup: Async function to lookup tenant
    """
    config = TenancyConfig(
        require_tenant=True,
        enable_security_middleware=False,
    )

    app.add_middleware(
        TenantResolutionMiddleware,
        config=config,
        get_session=get_session,
        get_tenant_lookup=get_tenant_lookup,
    )

    logger.info("Minimal tenancy middleware configured (resolution only)")


def create_tenancy_config_from_env() -> TenancyConfig:
    """
    Create TenancyConfig from environment variables.

    Environment variables:
        TENANCY_REQUIRE_TENANT: "true" or "false"
        TENANCY_REQUIRE_USER: "true" or "false"
        TENANCY_ISOLATION_MODE: "rls", "app", or "hybrid"
        TENANCY_TENANT_HEADER: Header name for tenant ID
        TENANCY_STRICT_ISOLATION: "true" or "false"
        TENANCY_ENABLE_SECURITY: "true" or "false"
        TENANCY_CACHE_TTL: Cache TTL in seconds

    Returns:
        TenancyConfig populated from environment
    """
    import os
    from ..tenancy.config import IsolationMode

    def str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes")

    isolation_mode_map = {
        "rls": IsolationMode.RLS,
        "app": IsolationMode.APPLICATION,
        "hybrid": IsolationMode.HYBRID,
    }

    return TenancyConfig(
        require_tenant=str_to_bool(
            os.getenv("TENANCY_REQUIRE_TENANT", "true")
        ),
        require_user=str_to_bool(
            os.getenv("TENANCY_REQUIRE_USER", "false")
        ),
        isolation_mode=isolation_mode_map.get(
            os.getenv("TENANCY_ISOLATION_MODE", "hybrid").lower(),
            IsolationMode.HYBRID
        ),
        tenant_header=os.getenv("TENANCY_TENANT_HEADER", "X-Tenant-ID"),
        strict_isolation=str_to_bool(
            os.getenv("TENANCY_STRICT_ISOLATION", "true")
        ),
        enable_security_middleware=str_to_bool(
            os.getenv("TENANCY_ENABLE_SECURITY", "true")
        ),
        tenant_cache_ttl_seconds=int(
            os.getenv("TENANCY_CACHE_TTL", "300")
        ),
    )
