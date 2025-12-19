# Netrun Soft-Dependency Detection System

**Version**: 2.0
**Date**: December 18, 2025
**Author**: Netrun Systems
**Audience**: Developers integrating Netrun packages
**Status**: Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Detection Matrix](#detection-matrix)
3. [Detection Mechanism](#detection-mechanism)
4. [Behavior Changes Guide](#behavior-changes-guide)
5. [Explicit vs Implicit Integration](#explicit-vs-implicit-integration)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Overview

### The "Discover and Integrate If Present" Pattern

Netrun packages implement **soft dependency detection** to automatically enhance functionality when complementary packages are available, without requiring them as mandatory dependencies.

**Core Principle**: "Works great standalone, works even better together"

This pattern enables:

- **Zero lock-in**: Use individual packages independently
- **Auto-enhancement**: Add packages and get improved functionality instantly
- **Graceful degradation**: Full functionality even when optional packages are missing
- **Seamless integration**: No configuration needed—detection is automatic

### When Auto-Integration Happens

Auto-integration occurs when:

1. An optional dependency is successfully imported (no ImportError)
2. The package detects the dependency via a `_HAS_*` flag
3. Enhanced behavior is automatically enabled

Example:

```python
# In netrun.errors package
try:
    from netrun.logging import get_logger, bind_context
    _HAS_LOGGING = True
except ImportError:
    _HAS_LOGGING = False

# When _HAS_LOGGING is True:
# - Errors automatically include correlation_id
# - Structured logging for all exceptions
# - Enhanced audit trails for security events
```

---

## Detection Matrix

This matrix shows what happens when you combine Netrun packages:

| Package A | Package B | Auto-Integration Behavior | Performance Impact | Data Flow |
|-----------|-----------|--------------------------|-------------------|-----------|
| **netrun-errors** | netrun-logging | Errors auto-bind correlation_id, request context to logs | Minimal (<2ms) | correlation_id flows from errors → logging |
| **netrun-auth** | netrun-logging | Auth events logged: login attempts, token issuance, permission checks, user_id, tenant_id | Minimal (<1ms per auth op) | user_id, tenant_id, session_id flow to logs |
| **netrun-auth** | netrun-errors | Auth failures return structured NetrunError responses with proper HTTP status codes (401, 403) | None | Error objects created with auth context |
| **netrun-db-pool** | netrun-logging | Query execution times, connection pool metrics, tenant context logged as structured events | <5ms per query | tenant_id, query_duration, pool_status to logs |
| **netrun-ratelimit** | netrun-auth | Rate limits applied per-user/per-tenant automatically; requests from same user share quota | None | user_id, tenant_id used as rate limit key |
| **netrun-ratelimit** | netrun-logging | Rate limit events logged: limit exceeded, quota reset, key metrics; structured metric export | Minimal (<1ms) | rate_limit_key, current_quota to logs |
| **netrun-config** | netrun-logging | Config loading events logged, cache hits/misses tracked, secret names redacted in logs | <2ms per config fetch | config_key, cache_status to logs |
| **netrun-auth** | netrun-config | Auth config (JWT keys, RBAC policies, token TTL) auto-loaded from netrun-config; TTL-cached | None | Uses config's TTL cache for auth settings |
| **netrun-db-pool** | netrun-config | Database connection strings, pool sizes, timeouts loaded from config; respects TTL caching | None | Uses config's TTL cache for DB settings |
| **netrun-cors** | netrun-logging | CORS validation and allowlist decisions logged; origin and allowed headers tracked | Minimal (<1ms) | cors_origin, cors_decision to logs |
| **netrun-llm** | netrun-logging | LLM API calls, token usage, model metrics logged as structured events | <5ms per LLM call | model_name, tokens_used, latency to logs |
| **netrun-auth** | netrun-ratelimit | JWT token endpoint rate-limited per IP/user; brute-force protection auto-enabled | None | Limits failed auth attempts per user |

---

## Detection Mechanism

### Import-Time Detection

All Netrun packages use the same detection pattern at module initialization:

```python
# Pattern from netrun.auth.__init__.py
try:
    from netrun.logging import get_logger, bind_context
    _HAS_LOGGING = True
except ImportError:
    _HAS_LOGGING = False

# Pattern from netrun.errors.__init__.py
try:
    from netrun.logging import get_logger, bind_context
    _HAS_LOGGING = True
except ImportError:
    _HAS_LOGGING = False

# Usage within the package
if _HAS_LOGGING:
    logger = get_logger(__name__)
    bind_context(correlation_id=correlation_id)
else:
    # Fallback to standard logging
    import logging
    logger = logging.getLogger(__name__)
```

### Flags Reference

Each package exports flags for detected dependencies:

**netrun-auth**:
- `_HAS_CASBIN` - Casbin RBAC library available
- `_HAS_FASTAPI` - FastAPI middleware available
- `_HAS_CASBIN_MIDDLEWARE` - Casbin + FastAPI middleware available
- `_HAS_B2C` - Azure AD B2C integration available
- `_HAS_LOGGING` - netrun-logging available (implicit)

**netrun-errors**:
- `_HAS_LOGGING` - netrun-logging available

**netrun-db-pool**:
- `_HAS_LOGGING` - netrun-logging available (implicit)
- `_HAS_CONFIG` - netrun-config available (implicit)

**netrun-ratelimit**:
- `_HAS_LOGGING` - netrun-logging available (implicit)
- `_HAS_AUTH` - netrun-auth available (implicit, for user-based limits)

### Detection Flow Diagram

```
Package Initialization
│
├─► Try importing optional dependencies
│   ├─ netrun.logging
│   ├─ netrun.config
│   ├─ netrun.auth
│   └─ fastapi, casbin, etc.
│
├─► Set _HAS_* flags based on success/failure
│
└─► Initialize enhanced behavior
    ├─ If dependency found: use enhanced features
    └─ If not found: fallback to basic functionality
```

---

## Behavior Changes Guide

### When You Add netrun-logging

**What Changes:**

```python
# Before: netrun-errors only
from netrun.errors import ValidationError
raise ValidationError("Invalid email")
# Logs to standard stderr

# After: netrun-errors + netrun-logging
pip install netrun-logging
from netrun.errors import ValidationError
raise ValidationError("Invalid email")
# Logs to structured JSON with correlation_id, request context, etc.
```

**New Log Fields Appear:**
- `correlation_id` - Unique request identifier
- `request_id` - HTTP request tracking
- `user_id` - Authenticated user identifier
- `tenant_id` - Multi-tenant context
- `error_context` - Structured error details

**Performance Implications:**
- +<2ms per exception handling
- Structured serialization overhead negligible for most apps
- Recommended for all production deployments

**Example Log Output:**

```json
{
  "timestamp": "2025-12-18T14:35:22.123Z",
  "level": "error",
  "message": "Authentication failed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "tenant_id": "acme_corp",
  "error_code": "INVALID_CREDENTIALS",
  "status_code": 401
}
```

---

### When You Add netrun-auth

**What Changes:**

```python
# Before: netrun-logging only
# Logs generic events

# After: netrun-logging + netrun-auth
# Logs with user context automatically
```

**New Log Fields Appear:**
- `user_id` - From JWT token
- `tenant_id` - From token claims
- `session_id` - Session tracking
- `action` - Auth action (login, token_refresh, permission_check)

**Performance Implications:**
- <1ms overhead per authenticated request
- JWT validation cached

**Example: User Context Auto-Binding**

```python
# Automatic binding when user authenticates
from netrun.auth import get_current_user

@app.get("/api/users")
async def list_users(user: User = Depends(get_current_user)):
    # Automatically bound in logs:
    # - user_id: "user_123"
    # - tenant_id: "acme_corp"
    # - session_id: "sess_456"
    logger.info("Fetching user list")
    return get_users(tenant_id=user.tenant_id)
```

---

### When You Add netrun-config

**What Changes:**

```python
# Before: App loads config from environment variables
DB_HOST = os.getenv("DB_HOST")  # Plain string

# After: netrun-config installed
# Config values auto-cached with TTL, secrets auto-redacted in logs
```

**New Behavior:**
- Configuration values cached with TTL (default 5 minutes)
- Cache hits logged as structured events
- Secret values automatically redacted in logs
- Configuration changes trigger optional callbacks

**Log Fields Appear:**
- `config_key` - Configuration key accessed
- `cache_hit` - Whether value came from cache
- `cache_ttl_remaining` - Seconds until cache refresh

**Example Cache Status Logging:**

```json
{
  "message": "Config accessed",
  "config_key": "DB_HOST",
  "cache_hit": true,
  "cache_ttl_remaining": 287,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### When You Add netrun-ratelimit

**What Changes:**

```python
# Before: No rate limiting
# Requests processed immediately

# After: netrun-ratelimit installed
# Per-user rate limits auto-enforced
```

**New Behavior:**
- HTTP 429 responses for exceeded limits
- Per-user quota tracking
- Limit headers added to responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

**Example Response Headers:**

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1450282800
Content-Type: application/json

{"data": [...]}
```

**Performance Implications:**
- <1ms per request (Redis backend)
- <0.1ms per request (Memory backend, single-instance)

---

### When You Add netrun-db-pool

**What Changes:**

```python
# Before: Raw database connections
# Connection per request, no pooling

# After: netrun-db-pool installed
# Connection pooling, metrics logged, tenant context tracked
```

**New Log Fields:**
- `pool_size` - Current pool size
- `available_connections` - Connections available
- `query_duration_ms` - Query execution time
- `tenant_id` - RLS context

**Example Query Logging:**

```json
{
  "message": "Query executed",
  "query_duration_ms": 45,
  "pool_available": 8,
  "pool_size": 10,
  "tenant_id": "acme_corp",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Explicit vs Implicit Integration

### Automatic Integration (Default Behavior)

When packages are installed together, integration is **automatic** with no configuration needed:

```python
from netrun.auth import JWTAuthMiddleware
from netrun.logging import get_logger

# Auto-detection happens at import time
app.add_middleware(JWTAuthMiddleware)

# Logs automatically include user_id, tenant_id
logger.info("Processing request")
```

### Explicit Integration (Optional)

You can explicitly control integrations for advanced use cases:

#### Disable Auto-Logging Integration

```python
from netrun.auth import JWTAuthMiddleware

# Disable automatic logging even if netrun-logging is installed
middleware = JWTAuthMiddleware(auto_log=False)
app.add_middleware(JWTAuthMiddleware, auto_log=False)
```

#### Provide Custom Logger

```python
from netrun.auth import JWTAuthMiddleware
from netrun.logging import get_logger

# Use custom logger configuration
custom_logger = get_logger("my_app.auth")
middleware = JWTAuthMiddleware(logger=custom_logger)

app.add_middleware(
    JWTAuthMiddleware,
    logger=custom_logger
)
```

#### Configure Logging Behavior

```python
from netrun.auth import JWTAuthMiddleware, AuthConfig
from netrun.logging import get_logger

config = AuthConfig()
logger = get_logger(__name__)

# Explicit control over what gets logged
middleware = JWTAuthMiddleware(
    config=config,
    logger=logger,
    log_level="debug",  # All auth events
    log_token_payload=False,  # Never log token content
    log_ip_address=True,  # Track IP addresses
)

app.add_middleware(JWTAuthMiddleware, **middleware_config)
```

#### Manually Bind Context

```python
from netrun.logging import bind_context

# Manual context binding for custom operations
bind_context(
    user_id="user_123",
    tenant_id="acme_corp",
    operation="bulk_import"
)

logger.info("Starting bulk import")  # Will include bound context
```

---

## Troubleshooting

### "Why did my logs change after adding netrun-errors?"

**Symptom**: Logs changed format from plain text to structured JSON.

**Cause**: netrun-logging was already installed; netrun-errors detected it automatically.

**Solution**:

```python
# Option 1: Accept enhanced logging (recommended)
# No action needed—this is the desired behavior

# Option 2: Disable specific package's logging
from netrun.errors.config import ErrorConfig
config = ErrorConfig(auto_log=False)

# Option 3: Configure logging level
from netrun.logging import configure_logging
configure_logging(level="info", format="simple")
```

---

### "Rate limiting suddenly works differently"

**Symptom**: 429 responses appearing after installing netrun-ratelimit, or per-user limits working unexpectedly.

**Cause**: Auto-detection enabled rate limiting that wasn't previously active.

**Solution**:

```python
# Verify detection
from netrun.ratelimit import _HAS_AUTH
print(f"Auth detection enabled: {_HAS_AUTH}")

# Disable auto-integration
from netrun.ratelimit import RateLimitMiddleware, RateLimitConfig

config = RateLimitConfig(
    auto_detect_user=False,  # Don't auto-use user_id from auth
    use_static_key=True,  # Use IP-based limits instead
)

app.add_middleware(RateLimitMiddleware, config=config)
```

---

### "How do I debug detection issues?"

**Check What's Detected:**

```python
# Print detection flags
from netrun.errors import _HAS_LOGGING
from netrun.auth import _HAS_CASBIN, _HAS_FASTAPI
from netrun.config import _HAS_LOGGING as CONFIG_HAS_LOGGING

print(f"Errors → Logging: {_HAS_LOGGING}")
print(f"Auth → Casbin: {_HAS_CASBIN}")
print(f"Auth → FastAPI: {_HAS_FASTAPI}")
print(f"Config → Logging: {CONFIG_HAS_LOGGING}")
```

**Verify Package Installation:**

```bash
pip list | grep netrun
```

**Expected Output**:

```
netrun-auth                2.0.0
netrun-config              1.2.0
netrun-cors                1.1.0
netrun-db-pool             2.0.0
netrun-errors              1.1.0
netrun-env                 1.1.0
netrun-logging             1.2.0
netrun-llm                 1.1.0
netrun-pytest-fixtures     1.1.0
netrun-ratelimit           2.0.0
netrun-rbac                1.0.0
```

**Enable Debug Logging:**

```python
import logging

# Enable debug logging for Netrun packages
logging.getLogger("netrun").setLevel(logging.DEBUG)
logging.getLogger("netrun.auth").setLevel(logging.DEBUG)
logging.getLogger("netrun.errors").setLevel(logging.DEBUG)
```

---

### "Integration not working even though both packages are installed"

**Checklist:**

1. Verify import order is correct:

```python
# Wrong: Auth imported before logging
from netrun.auth import JWTManager
from netrun.logging import get_logger

# Correct: Logging imported first (though order usually doesn't matter)
from netrun.logging import get_logger
from netrun.auth import JWTManager
```

2. Check package versions:

```python
import netrun.auth
import netrun.logging

print(f"Auth version: {netrun.auth.__version__}")
print(f"Logging version: {netrun.logging.__version__}")
```

3. Verify compatibility matrix:

| Feature | Min Auth Version | Min Logging Version |
|---------|------------------|-------------------|
| Basic logging integration | 1.2.0 | 1.0.0 |
| Structured user context | 1.2.0 | 1.2.0 |
| Azure AD integration | 1.3.0+ | 1.2.0 |
| B2C support | 1.3.0 | 1.2.0 |

4. Test detection directly:

```python
# Minimal test case
try:
    from netrun.logging import get_logger
    print("✓ netrun-logging imported successfully")
except ImportError as e:
    print(f"✗ Failed to import netrun-logging: {e}")

try:
    from netrun.auth import JWTManager
    print("✓ netrun-auth imported successfully")
except ImportError as e:
    print(f"✗ Failed to import netrun-auth: {e}")
```

---

### "Performance degradation after adding dependencies"

**Symptom**: Application slower after installing additional Netrun packages.

**Causes**:

1. **Import time overhead**: Soft dependency checking adds <50ms on app startup
2. **Logging overhead**: Structured logging adds <2ms per operation
3. **Config caching**: Initial config load adds <5ms (cached thereafter)

**Solutions**:

```python
# Profile import time
import time
start = time.time()
from netrun.errors import NetrunException
print(f"Import took {(time.time() - start) * 1000:.2f}ms")

# Disable unnecessary integrations
from netrun.auth import AuthConfig
config = AuthConfig(
    auto_log=False,  # Disable logging if not needed
    enable_audit=False  # Disable audit trails if not needed
)

# Use memory backend for ratelimit (faster than Redis)
from netrun.ratelimit import MemoryBackend
backend = MemoryBackend()  # <0.1ms per check vs <1ms for Redis
```

---

### "Different behavior in dev vs production"

**Symptom**: Works perfectly in dev, different behavior in production.

**Causes**:

1. **Different dependencies installed**: Requirements differ between environments
2. **Different Python versions**: Import mechanisms differ
3. **Different configurations**: Environment-specific settings

**Solutions**:

```python
# Detect environment and adjust
import os

if os.getenv("ENVIRONMENT") == "production":
    # Production config
    from netrun.ratelimit import RedisBackend
    backend = RedisBackend(redis_url=os.getenv("REDIS_URL"))
else:
    # Dev config
    from netrun.ratelimit import MemoryBackend
    backend = MemoryBackend()

# Pin versions in requirements
netrun-errors>=1.1.0,<2.0.0
netrun-logging>=1.2.0,<2.0.0
netrun-auth>=2.0.0,<3.0.0
```

---

## Advanced Configuration

### Custom Detection Logic

You can override auto-detection for advanced scenarios:

```python
from netrun.auth import _HAS_LOGGING

# Based on detection flag, configure differently
if _HAS_LOGGING:
    from netrun.logging import configure_logging
    configure_logging(
        level="debug",
        format="json",
        azure_insights_enabled=True
    )
else:
    import logging
    logging.basicConfig(level=logging.INFO)
```

### Multi-Package Initialization Pattern

For complex applications using many packages:

```python
from netrun.errors import _HAS_LOGGING as ERRORS_HAS_LOGGING
from netrun.auth import _HAS_LOGGING as AUTH_HAS_LOGGING
from netrun.config import _HAS_LOGGING as CONFIG_HAS_LOGGING

def initialize_netrun_ecosystem():
    """Initialize all detected Netrun packages with consistent configuration."""

    # Report detections
    if ERRORS_HAS_LOGGING and AUTH_HAS_LOGGING and CONFIG_HAS_LOGGING:
        print("✓ Full Netrun ecosystem detected")
        # Configure for full integration
        return "full"
    elif ERRORS_HAS_LOGGING or AUTH_HAS_LOGGING:
        print("✓ Partial Netrun ecosystem detected")
        # Configure for partial integration
        return "partial"
    else:
        print("⚠ Minimal Netrun configuration (logging not detected)")
        # Fallback configuration
        return "minimal"

ecosystem_level = initialize_netrun_ecosystem()
```

### Conditional Middleware Registration

```python
from fastapi import FastAPI
from netrun.auth import _HAS_FASTAPI, AuthenticationMiddleware, JWTManager
from netrun.cors import _HAS_FASTAPI as CORS_HAS_FASTAPI, CORSMiddleware

app = FastAPI()

# Only register if FastAPI integration is available
if _HAS_FASTAPI:
    jwt_manager = JWTManager()
    app.add_middleware(AuthenticationMiddleware, jwt_manager=jwt_manager)
else:
    print("⚠ FastAPI integration not available")

if CORS_HAS_FASTAPI:
    app.add_middleware(CORSMiddleware)
else:
    print("⚠ CORS FastAPI integration not available")
```

---

## Reference: Dependency Detection Versions

| Package | Version | Logging Detection | Config Detection | Auth Detection | FastAPI Detection |
|---------|---------|------------------|------------------|----------------|-------------------|
| netrun-errors | 1.1.0 | ✓ | | | |
| netrun-auth | 2.0.0 | ✓ | | ✓ (Casbin) | ✓ |
| netrun-config | 1.2.0 | ✓ | | | |
| netrun-db-pool | 2.0.0 | ✓ | ✓ | | |
| netrun-ratelimit | 2.0.0 | ✓ | | ✓ | ✓ |
| netrun-cors | 1.1.0 | ✓ | | | ✓ |
| netrun-llm | 1.1.0 | ✓ | ✓ | | |
| netrun-rbac | 1.0.0 | ✓ | | ✓ (Auth) | |
| netrun-env | 1.1.0 | ✓ | | | |

---

## Summary

The soft-dependency detection system enables Netrun packages to:

✓ **Work independently**: Each package functions without others
✓ **Auto-enhance**: Seamless integration when complementary packages present
✓ **Stay flexible**: Explicit control available when needed
✓ **Perform efficiently**: <5ms overhead per integration
✓ **Simplify configuration**: Detection is automatic and sensible

**Best Practice**: Install the full Netrun ecosystem for optimal functionality:

```bash
pip install netrun-logging netrun-errors netrun-auth netrun-config \
            netrun-db-pool netrun-ratelimit netrun-cors netrun-env
```

---

*Last Updated: December 18, 2025*
*Documentation Version: 2.0*
*Netrun Systems - All Rights Reserved*
