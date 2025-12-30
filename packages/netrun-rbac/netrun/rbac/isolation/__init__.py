"""
Netrun RBAC Isolation Module - Database isolation strategies for multi-tenant applications.

Following Netrun Systems SDLC v2.3 standards.

Provides three isolation strategies:
- RLSIsolationStrategy: PostgreSQL Row-Level Security
- ApplicationIsolationStrategy: Application-level query filtering
- HybridIsolationStrategy: Both RLS and application filtering (recommended)

Usage:
    from netrun.rbac.isolation import HybridIsolationStrategy, get_isolation_strategy
    from netrun.rbac.tenancy import TenancyConfig, IsolationMode

    # Direct instantiation
    isolation = HybridIsolationStrategy()

    # Get strategy from config
    config = TenancyConfig(isolation_mode=IsolationMode.HYBRID)
    isolation = get_isolation_strategy(config)

    # Setup session for RLS
    await isolation.setup_session(session)

    # Apply query filters
    query = isolation.apply_query_filters(query, Contact)
"""

from .base import IsolationStrategy
from .rls import RLSIsolationStrategy
from .application import ApplicationIsolationStrategy
from .hybrid import HybridIsolationStrategy
from ..tenancy.config import TenancyConfig, IsolationMode


def get_isolation_strategy(config: TenancyConfig) -> IsolationStrategy:
    """
    Factory function to get the appropriate isolation strategy based on config.

    Args:
        config: Tenancy configuration

    Returns:
        Appropriate IsolationStrategy instance
    """
    if config.isolation_mode == IsolationMode.RLS:
        return RLSIsolationStrategy(
            tenant_variable=config.rls_tenant_variable,
            user_variable=config.rls_user_variable,
        )
    elif config.isolation_mode == IsolationMode.APPLICATION:
        return ApplicationIsolationStrategy()
    else:  # HYBRID (default)
        return HybridIsolationStrategy(
            tenant_variable=config.rls_tenant_variable,
            user_variable=config.rls_user_variable,
            strict_mode=config.strict_isolation,
        )


__all__ = [
    # Base class
    "IsolationStrategy",
    # Implementations
    "RLSIsolationStrategy",
    "ApplicationIsolationStrategy",
    "HybridIsolationStrategy",
    # Factory
    "get_isolation_strategy",
]
