# Security Guidelines for netrun-auth v1.0.0

**Service**: #59 Unified Authentication
**Version**: 1.0.0
**Classification**: INTERNAL - ENGINEERING REFERENCE
**Created**: November 25, 2025
**Author**: Security Engineer (SDLC v2.1 Compliance)
**Correlation ID**: SEC-20251125-AUTH-GUIDELINES

---

## Document Purpose

This document establishes mandatory security requirements, cryptographic standards, and implementation guidelines for the netrun-auth v1.0.0 unified authentication library. All implementations MUST adhere to these guidelines to achieve SOC2, ISO27001, and NIST compliance.

**Compliance Frameworks**:
- NIST SP 800-63B (Digital Identity Guidelines)
- OWASP API Security Top 10 (2023)
- SOC2 Type II Trust Services Criteria
- ISO 27001:2022 Information Security Controls

---

## Table of Contents

1. [Cryptographic Standards](#1-cryptographic-standards)
2. [Token Security](#2-token-security)
3. [Attack Mitigations](#3-attack-mitigations)
4. [Secure Defaults Configuration](#4-secure-defaults-configuration)
5. [Security Audit Logging](#5-security-audit-logging)
6. [Security Code Review Checklist](#6-security-code-review-checklist)
7. [Critical Issues from Portfolio Audit](#7-critical-issues-from-portfolio-audit)
8. [Multi-Tenant Security](#8-multi-tenant-security)
9. [Azure AD Integration Security](#9-azure-ad-integration-security)
10. [API Security Requirements](#10-api-security-requirements)
11. [Password Security](#11-password-security)
12. [Key Management](#12-key-management)
13. [Incident Response](#13-incident-response)

---

## 1. Cryptographic Standards

### 1.1 JWT Signing Algorithm

| Requirement | Specification | Rationale |
|-------------|--------------|-----------|
| **Algorithm** | RS256 (RSA-SHA256) asymmetric signing | Prevents algorithm confusion attacks |
| **Forbidden** | HS256 in production environments | Shared secret vulnerability; single point of compromise |
| **Key Size** | Minimum 2048-bit RSA (4096-bit recommended) | NIST SP 800-57 compliant |
| **Key Rotation** | 90-day rotation schedule minimum | Limits exposure window if key is compromised |

**Implementation Reference** (from GhostGrid):
```python
class JWTConfig(BaseModel):
    """JWT configuration with security defaults."""
    algorithm: str = Field(default="RS256")  # NEVER change to HS256
    key_rotation_interval: timedelta = Field(default=timedelta(days=90))
    access_token_expiry: timedelta = Field(default=timedelta(minutes=15))
    refresh_token_expiry: timedelta = Field(default=timedelta(days=30))
```

**Algorithm Security Comparison**:
| Feature | HS256 (Symmetric) | RS256 (Asymmetric) |
|---------|-------------------|-------------------|
| Security | Shared secret (single point of failure) | Public/private key pair |
| Verification | Requires secret key | Only public key needed |
| Key Distribution | Must remain secret | Public key can be shared |
| Attack Resistance | Vulnerable to confusion attacks | Resistant to confusion attacks |

**CRITICAL**: Hard-code the algorithm in decode operations. NEVER read algorithm from token header.

```python
# CORRECT - Algorithm hard-coded
payload = jwt.decode(token, public_key, algorithms=["RS256"])

# WRONG - Vulnerable to algorithm confusion
header = jwt.get_unverified_header(token)
payload = jwt.decode(token, key, algorithms=[header["alg"]])  # VULNERABLE!
```

### 1.2 Key Storage

| Environment | Storage Method | Access Control |
|-------------|----------------|----------------|
| **Production** | Azure Key Vault with managed identities | Service Principal or Managed Identity only |
| **Staging** | Azure Key Vault (separate instance) | Developer Service Principals |
| **Development** | Local PEM files | Restricted permissions (chmod 600) |
| **Testing** | Ephemeral keys generated at runtime | Test isolation |

**NEVER**:
- Hardcode keys in source code
- Store keys in environment variables (use Key Vault references)
- Commit keys to version control
- Share keys between environments

**Azure Key Vault Integration Pattern**:
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

class KeyVaultKeyManager:
    """Secure key management via Azure Key Vault."""

    def __init__(self, vault_url: str):
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=credential)

    async def get_private_key(self) -> bytes:
        """Retrieve private key from Key Vault."""
        secret = self.client.get_secret("jwt-private-key")
        return secret.value.encode()

    async def get_public_key(self) -> bytes:
        """Retrieve public key from Key Vault."""
        secret = self.client.get_secret("jwt-public-key")
        return secret.value.encode()
```

### 1.3 Password Hashing

| Requirement | Specification | Rationale |
|-------------|--------------|-----------|
| **Algorithm** | Argon2id (Password Hashing Competition winner) | Memory-hard, GPU-resistant |
| **Memory** | 65536 KB (64 MB) minimum | Prevents GPU-based attacks |
| **Iterations** | 3 minimum | Balances security and performance |
| **Parallelism** | 4 threads | Utilizes multi-core CPUs |
| **Salt** | Unique per-password, cryptographically secure | Prevents rainbow table attacks |
| **Pepper** | Optional application-level secret (stored in Key Vault) | Defense in depth |

**Implementation**:
```python
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

password_hasher = PasswordHash((
    Argon2Hasher(
        time_cost=3,        # iterations
        memory_cost=65536,  # 64 MB
        parallelism=4,      # threads
    ),
))

def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return password_hasher.hash(password)

def verify_password(password: str, hash: str) -> bool:
    """Verify password against stored hash."""
    return password_hasher.verify(password, hash)
```

**Alternative (bcrypt) - Acceptable for migration**:
```python
import bcrypt

# If using bcrypt, use cost factor 12 minimum (not default 10)
def hash_password_bcrypt(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()
```

---

## 2. Token Security

### 2.1 Token Lifetime

| Token Type | Lifetime | Refresh Strategy | Rationale |
|------------|----------|------------------|-----------|
| **Access Token** | 15 minutes | Automatic via refresh token | Limits exposure window |
| **Refresh Token** | 30 days | Single-use with rotation | Balance security and UX |
| **API Key** | 1 year | Manual rotation, revocable | Service account persistence |
| **Session Token** | 1 hour (sliding) | Extend on activity | Web session management |

**Token Lifetime Configuration**:
```python
from datetime import timedelta

TOKEN_CONFIG = {
    "access_token_expiry": timedelta(minutes=15),
    "refresh_token_expiry": timedelta(days=30),
    "api_key_expiry": timedelta(days=365),
    "session_expiry": timedelta(hours=1),
    "clock_skew_tolerance": timedelta(seconds=30),
}
```

### 2.2 Token Claims Security

**Required Claims**:
| Claim | Purpose | Validation |
|-------|---------|------------|
| `jti` (JWT ID) | Unique per-token identifier | Used for blacklisting |
| `sub` (Subject) | User identifier | Must exist and be valid |
| `aud` (Audience) | Intended recipient | MUST match configured audience |
| `iss` (Issuer) | Token issuer | MUST match configured issuer |
| `exp` (Expiration) | Token expiry time | Always validated, 30s clock skew |
| `iat` (Issued At) | Token creation time | Reject tokens from future |
| `type` | Token type (access/refresh) | Prevent token type confusion |

**Additional Claims for netrun-auth**:
| Claim | Purpose | Required |
|-------|---------|----------|
| `user_id` | User identifier | Yes |
| `organization_id` | Tenant identifier | Yes (multi-tenant) |
| `roles` | User roles | Yes |
| `permissions` | Fine-grained permissions | Yes |
| `session_id` | Session tracking | Yes |
| `ip_address` | Originating IP | Optional (fraud detection) |
| `user_agent` | Browser/client info | Optional (fraud detection) |

**Token Claims Structure**:
```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class TokenClaims(BaseModel):
    """Standard JWT claims with Netrun extensions."""
    # Standard claims
    jti: str                    # Unique token ID
    sub: str                    # Subject (user_id)
    iss: str                    # Issuer
    aud: str                    # Audience
    exp: int                    # Expiration (Unix timestamp)
    iat: int                    # Issued at (Unix timestamp)
    type: TokenType             # Token type

    # Netrun extensions
    user_id: str
    organization_id: str
    roles: List[str]
    permissions: List[str]
    session_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
```

### 2.3 Token Blacklisting

**Implementation Requirements**:
- **Storage**: Redis SET with TTL matching token expiry
- **Check Order**: Blacklist BEFORE token validation (prevents timing attacks)
- **Trigger Events**: Logout, password change, security event, admin revocation

**Blacklist Implementation**:
```python
from redis.asyncio import Redis
from datetime import datetime, timezone

class TokenBlacklist:
    """Redis-backed token blacklist."""

    def __init__(self, redis: Redis, prefix: str = "blacklist:"):
        self.redis = redis
        self.prefix = prefix

    async def blacklist_token(self, jti: str, exp: datetime) -> None:
        """Add token to blacklist with TTL."""
        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await self.redis.setex(f"{self.prefix}{jti}", ttl, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        return await self.redis.exists(f"{self.prefix}{jti}") > 0

    async def blacklist_user_tokens(self, user_id: str) -> None:
        """Blacklist all tokens for a user (logout all devices)."""
        # Store user_id with timestamp to invalidate all tokens before this time
        await self.redis.set(
            f"{self.prefix}user:{user_id}",
            int(datetime.now(timezone.utc).timestamp())
        )
```

**Validation Order (CRITICAL)**:
```python
async def validate_token(self, token: str) -> TokenClaims:
    """Validate token with blacklist check FIRST."""

    # 1. Decode without verification to get JTI
    unverified = jwt.decode(token, options={"verify_signature": False})
    jti = unverified.get("jti")

    # 2. CHECK BLACKLIST FIRST (prevents timing attacks)
    if await self.blacklist.is_blacklisted(jti):
        raise TokenRevokedError("Token has been revoked")

    # 3. Full validation with signature verification
    claims = jwt.decode(
        token,
        self.public_key,
        algorithms=["RS256"],
        audience=self.audience,
        issuer=self.issuer,
    )

    return TokenClaims(**claims)
```

### 2.4 Refresh Token Rotation

**Single-Use Refresh Tokens**:
```python
async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
    """
    Exchange refresh token for new token pair.

    Security features:
    - Old refresh token is immediately revoked
    - New refresh token issued with each refresh
    - Prevents refresh token reuse attacks
    """
    # Validate refresh token
    claims = await self.validate_token(refresh_token, expected_type="refresh")

    # CRITICAL: Revoke old refresh token IMMEDIATELY
    await self.blacklist.blacklist_token(claims.jti, claims.exp)

    # Generate new token pair
    new_access = await self.generate_access_token(claims.user_id, ...)
    new_refresh = await self.generate_refresh_token(claims.user_id)

    return new_access, new_refresh
```

---

## 3. Attack Mitigations

### 3.1 Brute Force Protection

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Threshold** | 5 failed attempts | Balance security and usability |
| **Lockout Duration** | 15 minutes (exponential backoff) | Deters automated attacks |
| **Tracking** | Per IP + Per username | Prevents distributed attacks |
| **Storage** | Redis with TTL | Scalable, auto-expiring |

**Implementation**:
```python
from redis.asyncio import Redis
import hashlib

class BruteForceProtection:
    """Redis-backed brute force protection."""

    def __init__(
        self,
        redis: Redis,
        max_attempts: int = 5,
        lockout_duration: int = 900,  # 15 minutes
        prefix: str = "bruteforce:"
    ):
        self.redis = redis
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.prefix = prefix

    def _hash_identifier(self, identifier: str) -> str:
        """Hash username/email for privacy."""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]

    async def check_and_increment(
        self,
        ip_address: str,
        username: str
    ) -> tuple[bool, int]:
        """
        Check if login attempt is allowed and increment counter.

        Returns:
            tuple: (is_allowed, remaining_attempts)
        """
        # Check both IP and username
        ip_key = f"{self.prefix}ip:{ip_address}"
        user_key = f"{self.prefix}user:{self._hash_identifier(username)}"

        ip_attempts = int(await self.redis.get(ip_key) or 0)
        user_attempts = int(await self.redis.get(user_key) or 0)

        # Block if either threshold exceeded
        if ip_attempts >= self.max_attempts or user_attempts >= self.max_attempts:
            return False, 0

        # Increment counters
        pipe = self.redis.pipeline()
        pipe.incr(ip_key)
        pipe.expire(ip_key, self.lockout_duration)
        pipe.incr(user_key)
        pipe.expire(user_key, self.lockout_duration)
        await pipe.execute()

        remaining = self.max_attempts - max(ip_attempts, user_attempts) - 1
        return True, remaining

    async def reset(self, ip_address: str, username: str) -> None:
        """Reset counters on successful login."""
        ip_key = f"{self.prefix}ip:{ip_address}"
        user_key = f"{self.prefix}user:{self._hash_identifier(username)}"
        await self.redis.delete(ip_key, user_key)
```

### 3.2 Token Replay Protection

| Attack Vector | Mitigation | Implementation |
|---------------|------------|----------------|
| Access Token Replay | Short lifetime (15 min) | Limits replay window |
| Refresh Token Replay | Single-use with rotation | Blacklist on use |
| JTI Tracking | Store used JTIs | Redis SET with TTL |
| IP Binding | Optional IP claim | Validate IP matches |

### 3.3 Session Fixation Prevention

```python
async def authenticate_user(
    self,
    username: str,
    password: str,
    request: Request
) -> TokenPair:
    """
    Authenticate user with session fixation prevention.
    """
    # Validate credentials
    user = await self.validate_credentials(username, password)

    # CRITICAL: Generate NEW session ID on authentication
    # Never reuse session IDs from before authentication
    session_id = secrets.token_urlsafe(32)

    # Generate tokens with new session ID
    access_token = await self.generate_access_token(
        user_id=user.id,
        session_id=session_id,  # Always new
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )

    refresh_token = await self.generate_refresh_token(
        user_id=user.id,
        session_id=session_id,
    )

    return TokenPair(access_token=access_token, refresh_token=refresh_token)
```

### 3.4 CSRF Protection

| Scenario | Required | Implementation |
|----------|----------|----------------|
| Cookie-based sessions | Yes | Double-submit cookie pattern |
| Bearer token (API) | No | CSRF not applicable |
| Hybrid (cookie + API) | Yes (for cookie paths) | Selective protection |

**Double-Submit Cookie Pattern**:
```python
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = "[CSRF_SECRET_KEY]"  # From Key Vault
    cookie_samesite: str = "lax"
    cookie_secure: bool = True
    cookie_httponly: bool = True

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

# Apply to cookie-based endpoints only
@router.post("/api/protected")
async def protected_route(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    """Protected route requiring CSRF token."""
    await csrf_protect.validate_csrf(request)
    # Process request...
```

### 3.5 Algorithm Confusion Attack Prevention

**CRITICAL - From Security Audit Finding P0**:
```python
# VULNERABLE - Algorithm from token header
header = jwt.get_unverified_header(token)
payload = jwt.decode(token, key, algorithms=[header["alg"]])  # ATTACK VECTOR!

# SECURE - Hard-coded algorithm list
payload = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],  # ONLY RS256 allowed
    options={
        "require": ["exp", "iat", "sub", "iss", "aud", "jti"],
    }
)
```

---

## 4. Secure Defaults Configuration

### 4.1 AuthConfig Secure Defaults

```python
from pydantic import BaseModel, Field, SecretStr
from datetime import timedelta
from typing import List, Optional

class AuthConfig(BaseModel):
    """
    Authentication configuration with secure defaults.

    All security-sensitive settings default to the secure option.
    Insecure options require explicit configuration.
    """

    # Algorithm Configuration
    jwt_algorithm: str = Field(
        default="RS256",
        description="JWT signing algorithm. NEVER change to HS256 in production."
    )

    # Token Lifetimes
    access_token_expiry_minutes: int = Field(
        default=15,
        ge=5,
        le=60,
        description="Access token expiry in minutes (5-60)"
    )
    refresh_token_expiry_days: int = Field(
        default=30,
        ge=1,
        le=90,
        description="Refresh token expiry in days (1-90)"
    )

    # Security Features - ALL enabled by default
    enable_token_blacklisting: bool = Field(
        default=True,
        description="Enable token blacklist for logout support"
    )
    enable_brute_force_protection: bool = Field(
        default=True,
        description="Enable brute force protection on auth endpoints"
    )
    enable_audit_logging: bool = Field(
        default=True,
        description="Enable comprehensive security audit logging"
    )
    require_https: bool = Field(
        default=True,
        description="Require HTTPS for all requests (disable only in development)"
    )
    enable_refresh_token_rotation: bool = Field(
        default=True,
        description="Enable single-use refresh tokens with rotation"
    )

    # Password Requirements (NIST SP 800-63B compliant)
    password_min_length: int = Field(
        default=12,
        ge=8,
        description="Minimum password length"
    )
    password_max_length: int = Field(
        default=128,
        description="Maximum password length"
    )
    password_require_uppercase: bool = Field(
        default=True,
        description="Require at least one uppercase letter"
    )
    password_require_lowercase: bool = Field(
        default=True,
        description="Require at least one lowercase letter"
    )
    password_require_digit: bool = Field(
        default=True,
        description="Require at least one digit"
    )
    password_require_special: bool = Field(
        default=False,
        description="Require special character (NIST no longer recommends)"
    )
    password_check_common: bool = Field(
        default=True,
        description="Check against common password list"
    )

    # Rate Limiting
    max_login_attempts: int = Field(
        default=5,
        description="Maximum login attempts before lockout"
    )
    lockout_duration_minutes: int = Field(
        default=15,
        description="Account lockout duration in minutes"
    )
    rate_limit_requests_per_minute: int = Field(
        default=100,
        description="Rate limit for authenticated requests"
    )
    rate_limit_auth_per_minute: int = Field(
        default=5,
        description="Rate limit for authentication endpoints"
    )

    # Session Configuration
    session_cookie_secure: bool = Field(
        default=True,
        description="Set Secure flag on session cookies"
    )
    session_cookie_httponly: bool = Field(
        default=True,
        description="Set HttpOnly flag on session cookies"
    )
    session_cookie_samesite: str = Field(
        default="lax",
        description="SameSite cookie attribute (lax or strict)"
    )

    # Clock skew tolerance
    clock_skew_seconds: int = Field(
        default=30,
        description="Allowed clock skew for token validation"
    )
```

### 4.2 Exempt Paths (Minimal)

Only these paths should be exempt from authentication:

```python
EXEMPT_PATHS = [
    # Health checks (required for load balancers)
    "/health",
    "/health/ready",
    "/health/live",

    # Metrics (protect in production with separate auth)
    "/metrics",

    # Authentication endpoints (must be public)
    "/auth/login",
    "/auth/register",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/verify-email",

    # OAuth callbacks
    "/auth/oauth/azure/callback",
    "/auth/oauth/google/callback",

    # JWKS endpoint (public keys for external verification)
    "/.well-known/jwks.json",

    # OpenAPI documentation (disable in production if needed)
    "/docs",
    "/redoc",
    "/openapi.json",
]
```

**Path Matching**:
```python
def is_exempt_path(path: str, exempt_paths: List[str]) -> bool:
    """
    Check if path is exempt from authentication.

    Supports:
    - Exact match: "/health"
    - Prefix match: "/auth/oauth/*"
    """
    for exempt in exempt_paths:
        if exempt.endswith("*"):
            if path.startswith(exempt[:-1]):
                return True
        elif path == exempt:
            return True
    return False
```

---

## 5. Security Audit Logging

### 5.1 Events to Log (ALWAYS)

| Event | Log Level | Required Fields |
|-------|-----------|-----------------|
| `login_success` | INFO | user_id, ip_address, user_agent, session_id, auth_method |
| `login_failure` | WARNING | username_hash, ip_address, failure_reason, attempt_count |
| `logout` | INFO | user_id, session_id, logout_type (manual/timeout/forced) |
| `token_refresh` | INFO | user_id, old_session_id, new_session_id |
| `token_revoke` | INFO | user_id, jti, revoke_reason |
| `permission_denied` | WARNING | user_id, requested_resource, missing_permission |
| `password_change` | INFO | user_id, changed_by (self/admin), ip_address |
| `password_reset_request` | INFO | email_hash, ip_address |
| `password_reset_complete` | INFO | user_id, ip_address |
| `account_lockout` | WARNING | username_hash, ip_address, attempt_count |
| `mfa_enable` | INFO | user_id, mfa_type |
| `mfa_disable` | WARNING | user_id, disabled_by |
| `api_key_create` | INFO | user_id, key_id, permissions, expiry |
| `api_key_revoke` | INFO | user_id, key_id, revoke_reason |
| `suspicious_activity` | WARNING | user_id, activity_type, details |

### 5.2 Events to NEVER Log

**CRITICAL - Never log these values**:
- Plain text passwords (even partial)
- Full JWT tokens (log JTI instead)
- Decrypted secrets or API keys
- Full email addresses (use hash or partial mask: `j***@example.com`)
- Session tokens (log session_id instead)
- Credit card numbers or PII
- Password reset tokens
- MFA codes or backup codes

### 5.3 Log Format

Use netrun-logging JSON format with correlation IDs:

```json
{
  "timestamp": "2025-11-25T10:30:00.000Z",
  "level": "WARNING",
  "event": "login_failure",
  "correlation_id": "req-abc123-def456",
  "service": "netrun-auth",
  "version": "1.0.0",
  "data": {
    "user_hash": "sha256:a1b2c3d4e5f6...",
    "ip_address": "192.168.1.100",
    "failure_reason": "invalid_credentials",
    "attempt_count": 3,
    "user_agent": "Mozilla/5.0..."
  },
  "metadata": {
    "environment": "production",
    "region": "westus2"
  }
}
```

**Audit Logging Implementation**:
```python
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hashlib

logger = structlog.get_logger()

async def log_security_event(
    event_type: str,
    user_id: Optional[str],
    request: Request,
    success: bool,
    details: Optional[Dict[str, Any]] = None,
    level: str = "info",
) -> None:
    """
    Log security event with standardized format.

    All authentication events MUST be logged through this function.
    """
    log_data = {
        "event": event_type,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "correlation_id": getattr(request.state, "correlation_id", None),
        "request_path": request.url.path,
        "request_method": request.method,
    }

    # Add user_id if available (hash for failures)
    if user_id:
        if success:
            log_data["user_id"] = user_id
        else:
            log_data["user_hash"] = hashlib.sha256(user_id.encode()).hexdigest()[:16]

    # Add additional details
    if details:
        log_data["details"] = details

    # Log at appropriate level
    log_method = getattr(logger, level)
    await log_method("security_event", **log_data)
```

---

## 6. Security Code Review Checklist

### 6.1 Pre-Merge Security Review

**Authentication & Authorization**:
- [ ] No hardcoded secrets, credentials, or API keys
- [ ] All JWT validation includes signature verification
- [ ] No `verify=False` or `verify_signature=False` in JWT decode calls
- [ ] No `algorithms` parameter allowing HS256 with RS256 keys
- [ ] Algorithm is hard-coded, not read from token header
- [ ] All required claims are validated (exp, iat, sub, iss, aud, jti)
- [ ] Token type is validated (access vs refresh)
- [ ] Blacklist check occurs BEFORE token validation

**Password Security**:
- [ ] Password never logged or included in error messages
- [ ] Password hashing uses Argon2id or bcrypt (cost factor 12+)
- [ ] Password strength validation enforced
- [ ] Password comparison uses constant-time comparison

**Input Validation**:
- [ ] All user input validated and sanitized
- [ ] Pydantic models used for request validation
- [ ] SQL queries use parameterized statements
- [ ] No string concatenation for SQL or commands

**Rate Limiting & Protection**:
- [ ] Rate limiting applied to authentication endpoints
- [ ] Brute force protection implemented
- [ ] Account lockout after failed attempts
- [ ] CAPTCHA or additional verification for sensitive operations

**Logging & Monitoring**:
- [ ] Security events logged with correlation IDs
- [ ] No sensitive data in logs (passwords, tokens, PII)
- [ ] Failed authentication attempts logged with context
- [ ] Audit logging for permission changes

**Session & Cookie Security**:
- [ ] Token blacklist checked before validation
- [ ] HTTPS enforced (except development mode)
- [ ] Secure cookie flags set (HttpOnly, Secure, SameSite)
- [ ] CORS configured restrictively (no wildcards in production)
- [ ] Session ID regenerated on authentication

**Multi-Tenant Security**:
- [ ] Tenant ID validated on every request
- [ ] Cross-tenant access prevented
- [ ] Database queries include tenant filter
- [ ] Row-Level Security (RLS) enforced at database level

### 6.2 Automated Security Checks

**Pre-commit hooks** (required):
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-r", "src/", "-ll"]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]

  - repo: local
    hooks:
      - id: check-jwt-security
        name: Check JWT Security
        entry: python scripts/check_jwt_security.py
        language: python
        files: \.py$
```

**Security scanning commands**:
```bash
# Run security audit
bandit -r src/ -f json -o bandit-report.json

# Check for secrets
detect-secrets scan --all-files

# Check dependencies for vulnerabilities
safety check --full-report

# Run SAST
semgrep --config p/python-security src/
```

---

## 7. Critical Issues from Portfolio Audit

Based on SECURITY_AUDIT_REPORT.md, the following issues MUST be addressed:

### 7.1 P0 - Critical (Fix Immediately)

#### Issue 1: Intirkon JWT Bypass

**Finding**: Development mode disables signature verification

```python
# VULNERABLE CODE (Intirkon - dependencies.py Line 121)
payload = jwt.decode(token, options={"verify_signature": False})
```

**Risk**: Tokens can be forged if this code reaches production. Any attacker can create valid-looking tokens.

**Fix**:
```python
# SECURE - NEVER disable signature verification
# Remove development mode bypass entirely

# Instead, use separate test tokens for development
if settings.ENVIRONMENT == "development":
    # Use a dedicated test public key, NOT disabled verification
    public_key = settings.DEV_PUBLIC_KEY
else:
    public_key = await key_vault.get_public_key()

payload = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],
    options={"verify_signature": True}  # Always True
)
```

**Detection**:
```bash
# Grep for vulnerable patterns
grep -r "verify_signature.*False" src/
grep -r "verify=False" src/
grep -r "options.*verify" src/
```

#### Issue 2: In-Memory Token Storage

**Finding**: Netrun-CRM uses in-memory token blacklist

```python
# VULNERABLE CODE (Netrun-CRM - auth.py)
TOKEN_BLACKLIST = set()  # Lost on restart!
REFRESH_TOKENS = {}      # Lost on restart!
```

**Risk**: Tokens survive logout after server restart. No distributed session management.

**Fix**:
```python
# Use Redis for production
from redis.asyncio import Redis

class ProductionTokenStore:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def blacklist_token(self, jti: str, ttl: int):
        await self.redis.setex(f"blacklist:{jti}", ttl, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        return await self.redis.exists(f"blacklist:{jti}") > 0
```

### 7.2 P1 - High Priority

#### Issue 3: Inconsistent Algorithm Validation

**Finding**: Some projects allow HS256 algorithm

**Detection**:
```bash
grep -r 'algorithms=\["HS256"\]' src/
grep -r "HS256" src/
```

**Fix**: Hard-code RS256 algorithm in netrun-auth:
```python
# ONLY RS256 allowed - no configuration option
ALLOWED_ALGORITHMS = ["RS256"]

payload = jwt.decode(token, public_key, algorithms=ALLOWED_ALGORITHMS)
```

#### Issue 4: Missing Token Blacklisting

**Finding**: 4 projects lack logout invalidation

**Fix**: Mandatory blacklist integration in netrun-auth:
```python
class AuthMiddleware:
    def __init__(self, blacklist: TokenBlacklist):
        self.blacklist = blacklist

    async def __call__(self, request: Request, call_next):
        # Extract JTI from token
        jti = extract_jti_from_token(request)

        # CRITICAL: Check blacklist FIRST
        if await self.blacklist.is_blacklisted(jti):
            raise HTTPException(401, "Token revoked")

        response = await call_next(request)
        return response
```

### 7.3 P2 - Medium Priority

#### Issue 5: Missing Security Headers

**Finding**: Netrun-CRM, Intirkon lack OWASP security headers

**Fix**: Security headers middleware (from GhostGrid):
```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response
```

---

## 8. Multi-Tenant Security

### 8.1 Tenant Isolation Requirements

| Control | Requirement | Implementation |
|---------|-------------|----------------|
| Database RLS | CRITICAL | PostgreSQL Row-Level Security policies |
| JWT tenant_id | CRITICAL | Include organization_id in all tokens |
| Middleware validation | CRITICAL | Validate tenant on every request |
| Cross-tenant tests | CRITICAL | 25+ security test cases |
| API key scoping | HIGH | Tenant-specific API keys |
| Audit logging | HIGH | Log tenant_id in all events |

### 8.2 Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on tenant tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
CREATE POLICY tenant_isolation ON users
    USING (organization_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation ON resources
    USING (organization_id = current_setting('app.current_tenant')::uuid);

-- Force RLS for all users except superuser
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE resources FORCE ROW LEVEL SECURITY;
```

### 8.3 Tenant Context Middleware

```python
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

class TenantContextMiddleware:
    """
    Middleware to set tenant context for every request.

    CRITICAL: All database queries will be filtered by tenant.
    """

    async def __call__(self, request: Request, call_next):
        # Extract tenant from token claims
        claims = getattr(request.state, "claims", None)
        if not claims:
            return await call_next(request)

        organization_id = claims.organization_id

        # Validate tenant exists and user has access
        if not await self.validate_tenant_access(claims.user_id, organization_id):
            raise HTTPException(403, "Access to tenant denied")

        # Set tenant context for RLS
        request.state.tenant_id = organization_id

        # Set PostgreSQL session variable for RLS
        db: Session = request.state.db
        db.execute(f"SET app.current_tenant = '{organization_id}'")

        response = await call_next(request)
        return response
```

### 8.4 Cross-Tenant Security Tests

```python
import pytest
from httpx import AsyncClient

class TestTenantIsolation:
    """Cross-tenant security test suite."""

    async def test_user_cannot_access_other_tenant_resources(
        self,
        client: AsyncClient,
        tenant_a_user_token: str,
        tenant_b_resource_id: str,
    ):
        """Verify user cannot access resources from another tenant."""
        response = await client.get(
            f"/api/resources/{tenant_b_resource_id}",
            headers={"Authorization": f"Bearer {tenant_a_user_token}"}
        )
        assert response.status_code == 404  # Not 403 (no information leak)

    async def test_user_cannot_enumerate_other_tenant_users(
        self,
        client: AsyncClient,
        tenant_a_user_token: str,
    ):
        """Verify user list only shows same-tenant users."""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {tenant_a_user_token}"}
        )
        assert response.status_code == 200
        users = response.json()

        # All returned users must be from same tenant
        for user in users:
            assert user["organization_id"] == "tenant_a_id"

    async def test_api_key_scoped_to_tenant(
        self,
        client: AsyncClient,
        tenant_a_api_key: str,
        tenant_b_resource_id: str,
    ):
        """Verify API key cannot access other tenant resources."""
        response = await client.get(
            f"/api/resources/{tenant_b_resource_id}",
            headers={"X-API-Key": tenant_a_api_key}
        )
        assert response.status_code == 404
```

---

## 9. Azure AD Integration Security

### 9.1 Token Validation Requirements

| Check | Required | Implementation |
|-------|----------|----------------|
| JWKS signature | CRITICAL | Fetch keys from Microsoft JWKS endpoint |
| Audience (aud) | CRITICAL | Must match client_id |
| Issuer (iss) | CRITICAL | Must match Azure AD issuer |
| Expiration (exp) | CRITICAL | Token not expired |
| Tenant (tid) | HIGH | Validate against allowed tenants |
| Token version | MEDIUM | Prefer v2.0 tokens |

### 9.2 JWKS Caching

```python
from jwt import PyJWKClient
import asyncio
from datetime import datetime, timedelta

class CachedJWKSClient:
    """JWKS client with caching to reduce Azure API calls."""

    def __init__(
        self,
        jwks_url: str = "https://login.microsoftonline.com/common/discovery/v2.0/keys",
        cache_ttl: int = 3600,  # 1 hour
    ):
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self.client = PyJWKClient(jwks_url)
        self._cache = {}
        self._cache_time = None

    async def get_signing_key(self, token: str):
        """Get signing key with caching."""
        now = datetime.now()

        # Refresh cache if expired
        if self._cache_time is None or now > self._cache_time + timedelta(seconds=self.cache_ttl):
            # PyJWKClient fetches keys automatically
            self._cache_time = now

        return self.client.get_signing_key_from_jwt(token)
```

### 9.3 Multi-Tenant Validation

```python
from typing import List, Optional
import jwt

class AzureADValidator:
    """
    Validates Azure AD tokens for multi-tenant applications.
    """

    def __init__(
        self,
        client_id: str,
        allowed_tenants: Optional[List[str]] = None,
    ):
        self.client_id = client_id
        self.allowed_tenants = allowed_tenants
        self.jwks_client = CachedJWKSClient()

    async def validate_token(self, token: str) -> dict:
        """
        Validate Azure AD token.

        Validates:
        - Signature using JWKS
        - Audience matches client_id
        - Token not expired
        - Tenant is allowed (if restrictions configured)
        """
        # Get signing key from JWKS
        signing_key = await self.jwks_client.get_signing_key(token)

        # Decode and validate
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.client_id,
            options={
                "verify_iss": False,  # Multi-tenant has variable issuer
                "verify_exp": True,
                "verify_aud": True,
            }
        )

        # Validate tenant if restrictions configured
        if self.allowed_tenants:
            tenant_id = claims.get("tid")
            if tenant_id not in self.allowed_tenants:
                raise jwt.InvalidTokenError(f"Tenant {tenant_id} not allowed")

        # Validate required claims
        if not claims.get("oid") and not claims.get("sub"):
            raise jwt.InvalidTokenError("Missing required identity claims")

        return claims
```

---

## 10. API Security Requirements

### 10.1 OWASP API Top 10 Mitigations

| Risk | Mitigation | Implementation |
|------|------------|----------------|
| **API1: BOLA** | Verify resource ownership | Check user owns resource before access |
| **API2: Broken Auth** | Strong authentication | OAuth 2.0, MFA, rate limiting |
| **API3: Object Property Auth** | Filter response data | Return only permitted fields |
| **API4: Resource Consumption** | Rate limiting | Redis-backed limits per endpoint |
| **API5: Function Level Auth** | RBAC/ABAC | Permission decorators |
| **API6: Sensitive Flows** | Flow validation | CAPTCHA, rate limits |
| **API7: SSRF** | URL validation | Allowlists, no user URLs |
| **API8: Misconfiguration** | Security hardening | Hide errors, secure defaults |
| **API9: Inventory** | API documentation | OpenAPI, version management |
| **API10: Unsafe Consumption** | Input validation | Validate all external data |

### 10.2 Rate Limiting Configuration

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis

# Rate limit configuration by endpoint type
RATE_LIMITS = {
    "auth_endpoints": "5/minute",      # Strict for auth
    "api_endpoints": "100/minute",     # Standard for APIs
    "admin_endpoints": "30/minute",    # Moderate for admin
    "public_endpoints": "1000/minute", # Generous for public
}

# Apply rate limits
@router.post("/auth/login")
@limiter.limit(RATE_LIMITS["auth_endpoints"])
async def login(request: Request, credentials: LoginRequest):
    pass

@router.get("/api/resources")
@limiter.limit(RATE_LIMITS["api_endpoints"])
async def list_resources(request: Request, user: User = Depends(get_current_user)):
    pass
```

---

## 11. Password Security

### 11.1 Password Policy (NIST SP 800-63B)

```python
PASSWORD_POLICY = {
    "min_length": 12,           # NIST minimum
    "max_length": 128,          # Prevent DoS
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": False,   # NIST no longer recommends
    "check_common": True,       # Check against breach lists
    "check_context": True,      # Check against username, email
}
```

### 11.2 Password Validation

```python
from typing import List
import re

class PasswordValidator:
    """Validates password against security policy."""

    def __init__(self, policy: dict):
        self.policy = policy
        self.common_passwords = self._load_common_passwords()

    def validate(self, password: str, context: dict = None) -> List[str]:
        """
        Validate password against policy.

        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Length checks
        if len(password) < self.policy["min_length"]:
            errors.append(f"Password must be at least {self.policy['min_length']} characters")
        if len(password) > self.policy["max_length"]:
            errors.append(f"Password must be at most {self.policy['max_length']} characters")

        # Character requirements
        if self.policy["require_uppercase"] and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        if self.policy["require_lowercase"] and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        if self.policy["require_digit"] and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        if self.policy["require_special"] and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")

        # Common password check
        if self.policy["check_common"] and password.lower() in self.common_passwords:
            errors.append("Password is too common")

        # Context check (username, email in password)
        if self.policy["check_context"] and context:
            password_lower = password.lower()
            for key, value in context.items():
                if value and value.lower() in password_lower:
                    errors.append(f"Password cannot contain {key}")

        return errors
```

---

## 12. Key Management

### 12.1 Key Rotation Procedure

```python
from datetime import datetime, timedelta
import asyncio

class KeyRotationManager:
    """
    Manages RSA key rotation for JWT signing.

    Rotation procedure:
    1. Generate new key pair
    2. Add new public key to JWKS
    3. Wait grace period (tokens using old key still valid)
    4. Switch signing to new private key
    5. Remove old public key after max token lifetime
    """

    def __init__(
        self,
        key_vault: KeyVaultClient,
        rotation_interval: timedelta = timedelta(days=90),
        grace_period: timedelta = timedelta(days=7),
    ):
        self.key_vault = key_vault
        self.rotation_interval = rotation_interval
        self.grace_period = grace_period

    async def rotate_keys(self) -> None:
        """
        Execute key rotation.

        This should be run as a scheduled task.
        """
        # 1. Generate new key pair
        new_private, new_public = generate_rsa_key_pair(key_size=4096)

        # 2. Store new keys with version
        version = datetime.now().strftime("%Y%m%d")
        await self.key_vault.set_secret(f"jwt-private-key-{version}", new_private)
        await self.key_vault.set_secret(f"jwt-public-key-{version}", new_public)

        # 3. Add new public key to JWKS (keep old keys for grace period)
        await self.update_jwks(new_public, version)

        # 4. Schedule switch to new signing key after grace period
        await asyncio.sleep(self.grace_period.total_seconds())
        await self.key_vault.set_secret("jwt-private-key-current", new_private)

        # 5. Schedule removal of old public key after max token lifetime
        # (refresh tokens valid for 30 days)
        await asyncio.sleep(timedelta(days=30).total_seconds())
        await self.remove_old_jwks_keys()
```

### 12.2 JWKS Endpoint

```python
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/.well-known/jwks.json")
async def get_jwks() -> Dict:
    """
    Publish public keys for external token verification.

    Returns JSON Web Key Set (JWKS) containing all valid public keys.
    """
    keys: List[Dict] = []

    # Get all active public keys
    active_keys = await key_vault.get_active_public_keys()

    for key_version, public_key_pem in active_keys.items():
        jwk = public_key_to_jwk(public_key_pem)
        jwk["kid"] = key_version  # Key ID for matching
        jwk["use"] = "sig"        # Signature use
        jwk["alg"] = "RS256"      # Algorithm
        keys.append(jwk)

    return {"keys": keys}
```

---

## 13. Incident Response

### 13.1 Security Incident Types

| Incident | Severity | Immediate Action |
|----------|----------|------------------|
| Credential breach | CRITICAL | Rotate all affected secrets |
| Token theft | HIGH | Blacklist all user tokens |
| Brute force attack | MEDIUM | Increase lockout duration |
| Suspicious login | LOW | Enable MFA requirement |

### 13.2 Emergency Response Procedures

```python
class SecurityIncidentResponse:
    """Emergency security incident response procedures."""

    async def credential_breach(self, affected_scope: str) -> None:
        """
        Response to credential breach.

        1. Immediately rotate affected secrets
        2. Invalidate all active sessions
        3. Force password reset for affected users
        4. Generate incident report
        """
        # 1. Rotate secrets
        await self.key_vault.rotate_secret(affected_scope)

        # 2. Invalidate all sessions
        await self.session_store.invalidate_all()

        # 3. Force password reset
        await self.user_service.force_password_reset(affected_users)

        # 4. Log incident
        await log_security_event(
            event_type="credential_breach",
            severity="CRITICAL",
            details={"affected_scope": affected_scope}
        )

    async def revoke_all_user_tokens(self, user_id: str, reason: str) -> None:
        """
        Emergency token revocation for a user.

        Use when:
        - Account compromise suspected
        - User reports unauthorized access
        - Admin-initiated security action
        """
        # Blacklist all tokens by setting user-level invalidation timestamp
        await self.blacklist.invalidate_user(user_id)

        # Log event
        await log_security_event(
            event_type="emergency_revocation",
            user_id=user_id,
            details={"reason": reason}
        )

    async def global_token_revocation(self) -> None:
        """
        Nuclear option: Revoke ALL tokens system-wide.

        Use ONLY in catastrophic breach scenarios.
        """
        # Rotate signing keys immediately
        await self.key_rotation.emergency_rotate()

        # All tokens signed with old key are now invalid
        await log_security_event(
            event_type="global_revocation",
            severity="CRITICAL"
        )
```

### 13.3 Rollback Procedures

```bash
# Emergency rollback script
#!/bin/bash

# 1. Revert to previous key version
az keyvault secret set --vault-name [VAULT_NAME] \
  --name jwt-private-key-current \
  --value @previous-private-key.pem

# 2. Clear token blacklist (if corrupted)
redis-cli FLUSHDB

# 3. Restart authentication services
kubectl rollout restart deployment/netrun-auth

# 4. Verify service health
curl -f https://api.netrunsystems.com/health || exit 1
```

---

## Appendix A: Security Testing Requirements

### A.1 Required Security Tests

```python
# Minimum security test coverage for netrun-auth

class TestJWTSecurity:
    """JWT security test cases."""

    def test_reject_unsigned_token(self): pass
    def test_reject_hs256_token_with_rs256_key(self): pass
    def test_reject_none_algorithm(self): pass
    def test_reject_expired_token(self): pass
    def test_reject_future_issued_token(self): pass
    def test_reject_wrong_audience(self): pass
    def test_reject_wrong_issuer(self): pass
    def test_reject_blacklisted_token(self): pass
    def test_reject_token_missing_required_claims(self): pass
    def test_refresh_token_rotation(self): pass

class TestAuthenticationSecurity:
    """Authentication security test cases."""

    def test_brute_force_lockout(self): pass
    def test_rate_limiting_enforcement(self): pass
    def test_password_hashing_strength(self): pass
    def test_timing_attack_resistance(self): pass
    def test_credential_stuffing_protection(self): pass

class TestMultiTenantSecurity:
    """Multi-tenant isolation test cases."""

    def test_cross_tenant_resource_access_denied(self): pass
    def test_tenant_id_required_in_token(self): pass
    def test_rls_enforcement_at_database(self): pass
    def test_api_key_tenant_scoping(self): pass
```

---

## Appendix B: Compliance Mapping

### B.1 NIST SP 800-63B Compliance

| Requirement | Section | Status |
|-------------|---------|--------|
| AAL1: Single-factor | Section 1, 2 | Supported |
| AAL2: Multi-factor | Future v1.1 | Planned |
| Password complexity | Section 11 | Implemented |
| Session management | Section 2, 4 | Implemented |
| Token expiration | Section 2 | Implemented |

### B.2 SOC2 Compliance

| Trust Criteria | Section | Status |
|----------------|---------|--------|
| CC6.1 Logical access | Section 3, 4 | Implemented |
| CC6.2 Authentication credentials | Section 1, 11 | Implemented |
| CC6.3 Access segregation | Section 8 | Implemented |
| CC7.2 Monitoring | Section 5 | Implemented |

### B.3 OWASP API Top 10 Compliance

| Risk | Section | Status |
|------|---------|--------|
| API1: BOLA | Section 8 | Implemented |
| API2: Broken Auth | Section 1-4 | Implemented |
| API3: Object Property Auth | Section 8 | Implemented |
| API4: Resource Consumption | Section 10 | Implemented |
| API5: Function Level Auth | Section 4, 8 | Implemented |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-25 | Security Engineer | Initial release |

---

## References

**Source Documents**:
1. `AUTH_PATTERN_ANALYSIS_REPORT.md` - GhostGrid reference implementation analysis
2. `SECURITY_AUDIT_REPORT.md` - Portfolio security findings (7.8/10 score)
3. `AUTHENTICATION_BEST_PRACTICES_RESEARCH.md` - Industry best practices research

**External Standards**:
- NIST SP 800-63B: Digital Identity Guidelines
- OWASP API Security Top 10 (2023)
- SOC2 Type II Trust Services Criteria
- ISO 27001:2022 Information Security Controls
- RFC 7519: JSON Web Token (JWT)
- RFC 7636: PKCE for OAuth

**GhostGrid Security Patterns** (Reusability Score: 92%):
- JWT Manager: 600 LOC, RS256 with key rotation
- Middleware Stack: 535 LOC, comprehensive security
- RBAC System: 811 LOC, fine-grained permissions
- Security Test Suite: 153 tests, 2,630 LOC

---

**Document Classification**: INTERNAL - ENGINEERING REFERENCE
**Distribution**: Engineering Team, Security Team
**Review Schedule**: Quarterly (next review: February 2026)

---

*End of Document*
