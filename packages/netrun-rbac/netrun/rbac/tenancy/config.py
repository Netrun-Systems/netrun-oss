"""
Netrun RBAC Tenancy Configuration - Settings for multi-tenant behavior.

Following Netrun Systems SDLC v2.3 standards.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any
from enum import Enum


class IsolationMode(str, Enum):
    """Database isolation strategy."""

    RLS = "rls"  # PostgreSQL Row-Level Security only
    APPLICATION = "app"  # Application-level filtering only
    HYBRID = "hybrid"  # Both RLS and application checks (recommended)


class TenantResolutionStrategy(str, Enum):
    """How to resolve tenant from incoming requests."""

    HEADER = "header"  # X-Tenant-ID or X-Tenant-Slug header
    JWT = "jwt"  # Extract from JWT claims
    SUBDOMAIN = "subdomain"  # tenant.example.com
    PATH = "path"  # /api/v1/tenants/{tenant_id}/...
    QUERY = "query"  # ?tenant_id=xxx
    CUSTOM = "custom"  # Custom resolver function


@dataclass
class TenancyConfig:
    """
    Configuration for the tenancy system.

    This dataclass holds all configuration options for multi-tenant behavior
    including isolation strategy, tenant resolution, and security settings.

    Usage:
        from netrun.rbac.tenancy import TenancyConfig, IsolationMode

        config = TenancyConfig(
            isolation_mode=IsolationMode.HYBRID,
            require_tenant=True,
            tenant_header="X-Tenant-ID",
        )

        setup_tenancy_middleware(app, config)
    """

    # Isolation settings
    isolation_mode: IsolationMode = IsolationMode.HYBRID
    strict_isolation: bool = True  # Fail if isolation check fails vs log warning

    # Tenant resolution
    resolution_strategy: TenantResolutionStrategy = TenantResolutionStrategy.HEADER
    tenant_header: str = "X-Tenant-ID"
    tenant_slug_header: str = "X-Tenant-Slug"
    jwt_tenant_claim: str = "tenant_id"
    jwt_tenant_slug_claim: str = "tenant_slug"
    subdomain_suffix: str = ""  # e.g., ".example.com"

    # Requirement settings
    require_tenant: bool = True  # Require tenant context for all requests
    require_user: bool = False  # Require user context for all requests

    # Paths that don't require tenant context
    exempt_paths: List[str] = field(default_factory=lambda: [
        "/health",
        "/healthz",
        "/ready",
        "/readyz",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    ])

    # Paths that explicitly don't require tenant (broader patterns)
    exempt_path_prefixes: List[str] = field(default_factory=lambda: [
        "/auth/",
        "/public/",
        "/static/",
        "/_next/",
    ])

    # Security settings
    enable_security_middleware: bool = True
    log_cross_tenant_attempts: bool = True
    block_cross_tenant_requests: bool = True
    audit_tenant_access: bool = False  # Log all tenant access for compliance

    # RLS configuration
    rls_tenant_variable: str = "app.current_tenant_id"
    rls_user_variable: str = "app.current_user_id"

    # Performance settings
    cache_tenant_lookups: bool = True
    tenant_cache_ttl_seconds: int = 300  # 5 minutes

    # Custom resolvers (set at runtime)
    custom_tenant_resolver: Optional[Callable] = None
    custom_user_resolver: Optional[Callable] = None

    # Hooks for extensibility
    on_tenant_resolved: Optional[Callable] = None  # Called after tenant is resolved
    on_context_set: Optional[Callable] = None  # Called after context is set
    on_isolation_violation: Optional[Callable] = None  # Called on isolation violation

    def is_path_exempt(self, path: str) -> bool:
        """
        Check if a path is exempt from tenant requirements.

        Args:
            path: The request path to check

        Returns:
            True if the path is exempt from tenant requirements
        """
        # Exact match
        if path in self.exempt_paths:
            return True

        # Prefix match
        for prefix in self.exempt_path_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def validate(self) -> List[str]:
        """
        Validate the configuration and return any errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if self.resolution_strategy == TenantResolutionStrategy.CUSTOM:
            if self.custom_tenant_resolver is None:
                errors.append(
                    "custom_tenant_resolver must be set when using CUSTOM resolution strategy"
                )

        if self.resolution_strategy == TenantResolutionStrategy.SUBDOMAIN:
            if not self.subdomain_suffix:
                errors.append(
                    "subdomain_suffix must be set when using SUBDOMAIN resolution strategy"
                )

        if self.isolation_mode == IsolationMode.RLS:
            if not self.rls_tenant_variable:
                errors.append(
                    "rls_tenant_variable must be set when using RLS isolation mode"
                )

        if self.tenant_cache_ttl_seconds < 0:
            errors.append("tenant_cache_ttl_seconds must be non-negative")

        return errors


# Default configuration instance
DEFAULT_TENANCY_CONFIG = TenancyConfig()
