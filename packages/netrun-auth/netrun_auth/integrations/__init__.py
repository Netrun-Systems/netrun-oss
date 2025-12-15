"""
Authentication integrations for external providers.

Provides production-ready integrations with:
- Azure AD / Entra ID (azure_ad.py) - Standard Azure AD for enterprise
- Azure AD B2C (azure_ad_b2c.py) - Consumer identity with social logins
- Generic OAuth 2.0 providers (oauth.py)

All integrations include:
- Comprehensive security features (PKCE, token validation)
- Claims mapping to netrun-auth format
- Multi-tenant support
- FastAPI integration helpers

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-07
"""

from netrun_auth.integrations.azure_ad import (
    AzureADConfig,
    AzureADClient,
    AzureADMultiTenantClient,
    get_azure_ad_client,
    initialize_azure_ad,
    get_current_user_azure,
)
from netrun_auth.integrations.azure_ad_b2c import (
    AzureADB2CConfig,
    AzureADB2CClient,
    B2CUserFlow,
    B2CUserFlowConfig,
    B2CTokenClaims,
    initialize_b2c,
    get_b2c_client,
    get_current_user_b2c,
    extract_bearer_token,
    is_b2c_configured,
)
from netrun_auth.integrations.oauth import (
    OAuthProvider,
    OAuthConfig,
    OAuthClient,
    OAuthManager,
    get_oauth_manager,
    create_oauth_router,
)

__all__ = [
    # Azure AD (Standard/Entra ID)
    "AzureADConfig",
    "AzureADClient",
    "AzureADMultiTenantClient",
    "get_azure_ad_client",
    "initialize_azure_ad",
    "get_current_user_azure",
    # Azure AD B2C (Consumer Identity)
    "AzureADB2CConfig",
    "AzureADB2CClient",
    "B2CUserFlow",
    "B2CUserFlowConfig",
    "B2CTokenClaims",
    "initialize_b2c",
    "get_b2c_client",
    "get_current_user_b2c",
    "extract_bearer_token",
    "is_b2c_configured",
    # OAuth
    "OAuthProvider",
    "OAuthConfig",
    "OAuthClient",
    "OAuthManager",
    "get_oauth_manager",
    "create_oauth_router",
]
