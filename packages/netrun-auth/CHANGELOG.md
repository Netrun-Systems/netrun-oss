# Changelog

All notable changes to netrun-auth will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-12-05

### Added - netrun-logging Integration

- **Graceful Import Pattern** - Optional netrun-logging dependency
  - Falls back to standard Python logging if netrun-logging not installed
  - No breaking changes for existing users
  - Install with: `pip install netrun-auth[logging]`

- **Structured Logging** - Enhanced observability across all modules
  - **JWT Operations** (`jwt.py`)
    - `token_pair_generated` - Token creation with context (user_id, org_id, session_id)
    - `token_verified` - Successful token validation
    - `token_expired` - Token expiration events
    - `token_invalid` - Token validation failures
    - `token_blacklisted` - Revoked token access attempts
    - `tokens_refreshed` - Token refresh operations
    - `token_revoked` - Individual token revocation
    - `user_tokens_revoked` - Bulk token revocation (logout all sessions)

  - **RBAC Operations** (`rbac.py`)
    - `permission_denied` - Permission check failures with user context
    - Includes user_id, permission, roles for audit trails

  - **Authentication Middleware** (`middleware.py`)
    - `authenticated_request` - Successful authentication with full context
    - `authentication_failed` - Authentication failures with error details
    - Request context binding (method, path, user_id, tenant_id)

  - **Password Operations** (`password.py`)
    - `password_hashed` - Password hashing operations
    - `password_verified` - Password verification results
    - `password_validation_failed` - Password policy violations
    - `password_verification_error` - Hash verification errors

- **Context Binding** - Automatic context propagation
  - `bind_request_context()` - HTTP request context (method, path, user_id, tenant_id)
  - `bind_context()` - Custom context fields
  - Automatic correlation ID generation for request tracking

### Changed

- **Version**: Updated from 1.1.0 to 1.2.0
- **Dependencies**: Added optional `netrun-logging>=1.2.0` dependency
- **Logging**: All modules now support both standard logging and netrun-logging

### Documentation

- Updated docstrings with v1.2.0 changelog notes
- Added integration examples for netrun-logging
- Updated pyproject.toml with new optional dependency

### Security

- No security changes (logging integration only)
- All existing security features remain unchanged

### Migration Guide

**From 1.1.0 to 1.2.0:**

1. **No Breaking Changes** - Fully backward compatible
2. **Optional Integration** - Install netrun-logging for enhanced observability:
   ```bash
   pip install netrun-auth[logging]
   ```
3. **Automatic Detection** - netrun-logging used if available, standard logging otherwise
4. **Structured Logs** - Event-based logging replaces formatted strings when netrun-logging available

**Example with netrun-logging:**
```python
from netrun_auth import JWTManager
from netrun_logging import configure_logging

# Configure structured logging
configure_logging(app_name="my-auth-service", environment="production")

# JWTManager automatically uses netrun-logging
jwt_manager = JWTManager(config)
token_pair = await jwt_manager.generate_token_pair(user_id="user123")
# Logs: token_pair_generated user_id=user123 session_id=... roles_count=2
```

**Example without netrun-logging:**
```python
from netrun_auth import JWTManager

# Standard logging (no changes required)
jwt_manager = JWTManager(config)
token_pair = await jwt_manager.generate_token_pair(user_id="user123")
# Logs: Generated token pair for user user123
```

---

## [1.0.0] - 2025-11-25

### Added - Core Authentication

- **JWT Manager** (`jwt.py`) - Production-ready JWT token management
  - RS256 asymmetric signing with RSA key pair support
  - Token pair generation (access + refresh tokens)
  - Token validation with comprehensive error handling
  - Token refresh with automatic rotation
  - Token revocation with Redis blacklisting
  - Token introspection for debugging
  - Key rotation support for security compliance

- **Role-Based Access Control** (`rbac.py`) - Enterprise RBAC system
  - Default roles: viewer, user, admin, super_admin
  - Permission model with `resource:action` format
  - Wildcard permissions (e.g., `admin:*`)
  - Role inheritance and aggregation
  - Dynamic role registration
  - Permission checking with has_permission/has_any_permission
  - Role hierarchy with implicit permission propagation

- **Password Manager** (`password.py`) - Secure password handling
  - Argon2id hashing algorithm (OWASP recommended)
  - Configurable time, memory, and parallelism costs
  - Password strength validation
  - Automatic rehashing detection for algorithm updates
  - Timing-attack resistant verification

- **Authentication Middleware** (`middleware.py`) - FastAPI integration
  - Automatic JWT extraction from Authorization header
  - Token validation and user context injection
  - Rate limiting per user/organization
  - Security headers (OWASP Secure Headers Project)
  - Audit logging for authentication events
  - Session tracking with Redis
  - IP address and user agent tracking

- **FastAPI Dependencies** (`dependencies.py`) - Dependency injection
  - `get_current_user()` - Extract authenticated user
  - `get_optional_user()` - Optional authentication
  - `require_roles(*roles)` - Role-based protection
  - `require_permissions(*permissions)` - Permission-based protection
  - `require_organization(org_id)` - Organization scoping

### Added - Data Models

- **Pydantic Models** (`types.py`) - Type-safe data structures
  - `TokenClaims` - JWT payload structure
  - `TokenPair` - Access + refresh token pair
  - `User` - Authenticated user with roles/permissions
  - `AuthContext` - Request authentication context
  - `SessionInfo` - Session metadata
  - `AuditLog` - Authentication event logging

### Added - Configuration

- **Configuration Management** (`config.py`) - Environment-based config
  - `AuthConfig` - Main configuration class using Pydantic Settings
  - Environment variable support with `NETRUN_AUTH_` prefix
  - JWT configuration (algorithm, issuer, audience, expiry)
  - Redis connection settings
  - Password policy settings
  - Rate limiting configuration
  - Security header configuration
  - Validation of required settings on startup

### Added - Error Handling

- **Exception Hierarchy** (`exceptions.py`) - Comprehensive error types
  - `AuthenticationError` - Base authentication exception
  - `TokenExpiredError` - Token expiration handling
  - `TokenInvalidError` - Malformed/invalid tokens
  - `TokenRevokedError` - Blacklisted tokens
  - `InsufficientPermissionsError` - Permission denial
  - `RateLimitExceededError` - Rate limit enforcement
  - `PasswordValidationError` - Password policy violations

### Added - Azure Integration

- **Azure AD Client** (`integrations/azure_ad.py`) - Microsoft Entra ID
  - MSAL-based authentication flow
  - Token acquisition with client credentials
  - Token validation with Azure AD public keys
  - Azure Key Vault integration for secret storage
  - Configurable tenant, client ID, and scopes
  - Automatic token refresh
  - Optional: Install with `pip install netrun-auth[azure]`

### Added - OAuth 2.0 Integration

- **OAuth Client** (`integrations/oauth.py`) - Generic OAuth 2.0
  - Authorization code flow with PKCE
  - Support for Google, GitHub, Okta, Auth0
  - State parameter for CSRF protection
  - Token exchange and refresh
  - User info endpoint integration
  - Configurable provider endpoints
  - Optional: Install with `pip install netrun-auth[oauth]`

### Security

- **NIST SP 800-63B** compliance for token handling
- **OWASP Authentication Cheat Sheet** compliance
- **SOC2** audit trail support with comprehensive logging
- **Argon2id** password hashing (OWASP recommended)
- **RS256** JWT signing (asymmetric, production-ready)
- **Token blacklisting** for secure logout and revocation
- **Rate limiting** for brute-force protection
- **Security headers** (CSP, HSTS, X-Frame-Options, etc.)
- **PKCE** (Proof Key for Code Exchange) for OAuth flows
- **Timing-attack resistant** password verification
- **IP address tracking** for session validation
- **User agent tracking** for device fingerprinting

### Testing

- **Comprehensive Test Suite** - 98% code coverage
  - Unit tests for all core modules
  - Integration tests for FastAPI middleware
  - Mock-based tests for external dependencies
  - Async/await test support with pytest-asyncio
  - Coverage reporting with pytest-cov

### Documentation

- **README.md** - Complete usage guide with examples
- **INTEGRATIONS_GUIDE.md** - Azure and OAuth integration docs
- **SECURITY_GUIDELINES.md** - Security best practices
- **AUTHENTICATION_BEST_PRACTICES_RESEARCH.md** - Research documentation
- **TEST_SUITE_SUMMARY.md** - Test coverage and quality metrics

### Dependencies

**Core Dependencies:**
- `pydantic>=2.5.0` - Data validation and settings management
- `pydantic-settings>=2.1.0` - Environment-based configuration
- `pyjwt[crypto]>=2.8.0` - JWT encoding/decoding with RSA support
- `cryptography>=41.0.0` - Cryptographic operations
- `redis>=5.0.0` - Token blacklisting and session storage
- `pwdlib[argon2]>=0.2.0` - Password hashing with Argon2id

**Optional Dependencies:**
- Azure: `msal>=1.26.0`, `azure-identity>=1.15.0`, `azure-keyvault-secrets>=4.8.0`
- OAuth: `authlib>=1.3.0`, `httpx>=0.26.0`
- FastAPI: `fastapi>=0.109.0`, `starlette>=0.36.0`

### Platform Support

- Python 3.10, 3.11, 3.12
- Linux, macOS, Windows
- Redis 5.0+

---

## Future Roadmap

### [1.1.0] - Planned Features

- **Multi-Factor Authentication (MFA)**
  - TOTP (Time-based One-Time Password) support
  - SMS/email verification codes
  - Backup codes for account recovery
  - MFA enforcement per organization

- **Adaptive Authentication**
  - Risk-based authentication with scoring
  - Device fingerprinting
  - Geolocation-based policies
  - Login anomaly detection

- **Advanced Session Management**
  - Concurrent session limits
  - Device management dashboard
  - Session revocation by device
  - Remember me functionality

### [1.2.0] - Enterprise Features

- **SAML 2.0 Integration**
  - SAML IdP support
  - SP-initiated and IdP-initiated flows
  - Attribute mapping

- **LDAP/Active Directory Integration**
  - User synchronization
  - Group mapping to roles
  - Password policy integration

- **Advanced Audit Logging**
  - Structured logging with ELK/Splunk support
  - Compliance reports (SOC2, HIPAA, GDPR)
  - Real-time alerting for suspicious activity

### [2.0.0] - Next Generation

- **Passwordless Authentication**
  - WebAuthn/FIDO2 support
  - Passkey integration
  - Biometric authentication

- **Zero Trust Architecture**
  - Continuous authentication
  - Context-aware access control
  - Micro-segmentation support

- **GraphQL Integration**
  - GraphQL middleware
  - Field-level permissions
  - Subscription authentication

---

## Migration Guides

### Migrating from Proprietary to MIT License

Version 1.0.0 changes the license from Proprietary to MIT License. If you previously acquired this software under a proprietary license:

1. Review the MIT License terms in the LICENSE file
2. Update your internal documentation to reflect the new license
3. No code changes required - API remains unchanged

### Upgrading to 1.0.0

This is the initial stable release. For users upgrading from pre-1.0 versions:

1. **Breaking Changes**: None (initial stable release)
2. **Deprecations**: None
3. **New Features**: All features listed above

---

## Contributing

We welcome contributions! Please see our contributing guidelines (coming soon).

## Support

- **Issues**: https://github.com/netrunsystems/netrun-auth/issues
- **Documentation**: https://docs.netrunsystems.com/auth
- **Email**: daniel@netrunsystems.com

---

[1.0.0]: https://github.com/netrunsystems/netrun-auth/releases/tag/v1.0.0
