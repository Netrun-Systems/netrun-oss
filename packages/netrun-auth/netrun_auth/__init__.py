"""
Netrun Authentication (netrun-auth)
====================================

Unified authentication library for Netrun Systems portfolio.

Features:
- JWT authentication with RS256 asymmetric signing
- Role-Based Access Control (RBAC) with permission model
- Password hashing with Argon2id
- FastAPI middleware and dependencies
- Token blacklisting with Redis
- Rate limiting and brute-force protection
- Azure AD / OAuth 2.0 integrations
- Azure AD B2C for consumer identity (social logins)

Changelog:
- v1.3.0 (2025-12-07): Azure AD B2C integration
  - Full B2C support with user flows (sign-up, password reset, profile edit)
  - Social identity provider support (Google, Facebook, etc.)
  - B2C-specific claims mapping (emails array, tfp, idp)
  - PKCE support for SPA applications
- v1.2.0 (2025-12-05): Deep netrun-logging integration
  - Graceful import pattern for optional netrun-logging dependency
  - Structured logging for authentication attempts and token operations
  - Context binding for user_id, tenant_id, session_id tracking
  - Enhanced audit logging for security events
- v1.1.0 (2025-11-26): Casbin RBAC integration
- v1.0.0 (2025-11-25): Initial release

Author: Netrun Systems
Version: 1.3.0
Date: 2025-12-07

Quick Start:
    from netrun_auth import JWTManager, AuthConfig
    from netrun_auth.middleware import AuthenticationMiddleware
    from netrun_auth.dependencies import get_current_user

    # Initialize
    config = AuthConfig()
    jwt_manager = JWTManager(config)

    # Add to FastAPI
    app.add_middleware(AuthenticationMiddleware, jwt_manager=jwt_manager)

    # Use in routes
    @app.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        return {"user_id": user.user_id}
"""

__version__ = "1.3.0"
__author__ = "Netrun Systems"

# Core authentication
from .jwt import JWTManager, KeyPair, get_jwt_manager
from .password import PasswordManager, get_password_manager
from .rbac import RBACManager, get_rbac_manager, require_permission, require_role
from .config import AuthConfig

# Casbin integration (optional)
try:
    from .rbac_casbin import CasbinRBACManager
    _HAS_CASBIN = True
except ImportError:
    _HAS_CASBIN = False
    CasbinRBACManager = None  # type: ignore

# Type definitions
from .types import (
    TokenType,
    TokenClaims,
    TokenPair,
    User,
    AuthContext,
    APIKey,
    Permission,
    Role
)

# Exceptions
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError,
    APIKeyInvalidError,
    RoleNotFoundError,
    PermissionDeniedError,
    SessionExpiredError,
    RateLimitExceededError
)

# FastAPI integration (optional)
try:
    from .middleware import AuthenticationMiddleware
    from .dependencies import (
        get_auth_context,
        get_current_user,
        get_current_user_optional,
        require_roles,
        require_all_roles,
        require_permissions,
        require_all_permissions,
        require_organization,
        require_self_or_permission
    )
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    # Create placeholder None values for imports when FastAPI not installed
    AuthenticationMiddleware = None  # type: ignore
    get_auth_context = None  # type: ignore
    get_current_user = None  # type: ignore
    get_current_user_optional = None  # type: ignore
    require_roles = None  # type: ignore
    require_all_roles = None  # type: ignore
    require_permissions = None  # type: ignore
    require_all_permissions = None  # type: ignore
    require_organization = None  # type: ignore
    require_self_or_permission = None  # type: ignore

# Casbin FastAPI middleware (optional)
try:
    from .middleware_casbin import (
        CasbinAuthMiddleware,
        path_prefix_mapper,
        regex_resource_mapper
    )
    _HAS_CASBIN_MIDDLEWARE = True
except ImportError:
    _HAS_CASBIN_MIDDLEWARE = False
    CasbinAuthMiddleware = None  # type: ignore
    path_prefix_mapper = None  # type: ignore
    regex_resource_mapper = None  # type: ignore

# Azure AD B2C integration (optional - requires msal, httpx)
try:
    from .integrations.azure_ad_b2c import (
        AzureADB2CConfig,
        AzureADB2CClient,
        B2CUserFlow,
        B2CUserFlowConfig,
        B2CTokenClaims,
        initialize_b2c,
        get_b2c_client,
        get_current_user_b2c,
        is_b2c_configured,
    )
    _HAS_B2C = True
except ImportError:
    _HAS_B2C = False
    AzureADB2CConfig = None  # type: ignore
    AzureADB2CClient = None  # type: ignore
    B2CUserFlow = None  # type: ignore
    B2CUserFlowConfig = None  # type: ignore
    B2CTokenClaims = None  # type: ignore
    initialize_b2c = None  # type: ignore
    get_b2c_client = None  # type: ignore
    get_current_user_b2c = None  # type: ignore
    is_b2c_configured = None  # type: ignore

__all__ = [
    # Version
    "__version__",
    "__author__",

    # Core managers
    "JWTManager",
    "KeyPair",
    "get_jwt_manager",
    "PasswordManager",
    "get_password_manager",
    "RBACManager",
    "get_rbac_manager",
    "require_permission",
    "require_role",
    "AuthConfig",

    # Casbin integration
    "CasbinRBACManager",

    # Types
    "TokenType",
    "TokenClaims",
    "TokenPair",
    "User",
    "AuthContext",
    "APIKey",
    "Permission",
    "Role",

    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenBlacklistedError",
    "APIKeyInvalidError",
    "RoleNotFoundError",
    "PermissionDeniedError",
    "SessionExpiredError",
    "RateLimitExceededError",

    # FastAPI integration
    "AuthenticationMiddleware",
    "get_auth_context",
    "get_current_user",
    "get_current_user_optional",
    "require_roles",
    "require_all_roles",
    "require_permissions",
    "require_all_permissions",
    "require_organization",
    "require_self_or_permission",

    # Casbin FastAPI middleware
    "CasbinAuthMiddleware",
    "path_prefix_mapper",
    "regex_resource_mapper",

    # Azure AD B2C integration
    "AzureADB2CConfig",
    "AzureADB2CClient",
    "B2CUserFlow",
    "B2CUserFlowConfig",
    "B2CTokenClaims",
    "initialize_b2c",
    "get_b2c_client",
    "get_current_user_b2c",
    "is_b2c_configured",
]
