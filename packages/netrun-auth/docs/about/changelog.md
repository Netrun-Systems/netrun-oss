# Changelog

All notable changes to netrun-auth will be documented in this file.

## Version 1.0.0 - 2025-11-25

### Initial Release

#### Core Features
- **JWT Authentication**: RS256 asymmetric signing with rotating key pairs
- **Role-Based Access Control (RBAC)**: Permission model with role hierarchy
- **Password Security**: Argon2id hashing (OWASP/NIST compliant)
- **FastAPI Integration**: Middleware and dependency injection
- **Token Blacklisting**: Redis-backed token revocation
- **Rate Limiting**: Configurable per-user/IP limits
- **Azure AD Integration**: Full Entra ID support
- **OAuth 2.0**: Pre-configured providers (Google, GitHub, Okta, Auth0)
- **Session Management**: Multi-device tracking
- **Audit Logging**: Comprehensive authentication events

#### Components
- `JWTManager`: Token generation, validation, refresh
- `RBACManager`: Role and permission management
- `PasswordManager`: Argon2id hashing and validation
- `AuthenticationMiddleware`: FastAPI middleware
- `AzureADClient`: Azure AD/Entra ID integration
- `OAuth2Client`: OAuth 2.0 provider support

#### Security
- NIST SP 800-63B compliant
- OWASP Authentication Cheat Sheet implementation
- SOC2 control support
- GDPR privacy controls
- HIPAA technical safeguards
- FedRAMP-aligned security controls

#### Documentation
- Complete API reference
- Installation and setup guides
- Security best practices
- Compliance and standards guide
- Multi-tenant setup guide
- Complete FastAPI example application
- Azure AD integration guide
- OAuth 2.0 provider guide

### Testing
- Comprehensive test suite (95%+ coverage)
- Unit tests for all components
- Integration tests for FastAPI
- Security-focused test cases

### Performance
- Token validation: ~1-2ms
- Password hashing: 1-2 seconds (intentionally slow)
- Blacklist lookup: ~1-5ms (Redis)
- Rate limiting: <5ms per check

---

## Planned Features (Future Releases)

### v1.1.0
- [ ] OIDC (OpenID Connect) support
- [ ] Hardware security key support (FIDO2/WebAuthn)
- [ ] Passwordless authentication
- [ ] Event-based notifications
- [ ] Token binding
- [ ] Device fingerprinting

### v1.2.0
- [ ] GraphQL security directives
- [ ] WebSocket authentication
- [ ] gRPC authentication
- [ ] Multi-factor authentication (built-in)
- [ ] Contextual risk assessment
- [ ] Geo-blocking

### v2.0.0
- [ ] Decentralized identity support
- [ ] Zero-trust architecture
- [ ] Biometric authentication
- [ ] Blockchain-backed credentials
- [ ] AI-powered anomaly detection

---

## Known Issues

None reported in v1.0.0

## Security Advisories

No security advisories for v1.0.0

## Migration Guides

### From Manual JWT Implementation
1. Install netrun-auth
2. Initialize JWTManager with existing keys
3. Replace custom JWT validation with netrun-auth
4. Migrate RBAC to RBACManager
5. Update password handling to use PasswordManager

### From Third-Party Auth Provider
1. Install netrun-auth
2. Configure OAuth/OIDC integration
3. Map provider claims to netrun-auth User model
4. Gradual migration of user base
5. Complete after all users migrated

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
