# Netrun Service Library - Technical Reference

**Version**: 1.2.0 (December 2025)
**Last Updated**: December 15, 2025
**Maintainer**: Netrun Systems Engineering

This document provides comprehensive technical documentation for all 10 packages in the Netrun Service Library, including complete API references, code examples, and integration patterns. **All 10 packages are now available on PyPI.**

---

## Table of Contents

1. [Package Overview](#package-overview)
2. [Installation Guide](#installation-guide)
3. [Integration Architecture](#integration-architecture)
4. [netrun-auth v1.1.0](#netrun-auth-v110)
5. [netrun-config v1.1.0](#netrun-config-v110)
6. [netrun-logging v1.1.0](#netrun-logging-v110)
7. [netrun-errors v1.1.0](#netrun-errors-v110)
8. [netrun-cors v1.1.0](#netrun-cors-v110)
9. [netrun-db-pool v1.0.0](#netrun-db-pool-v100)
10. [netrun-llm v1.0.0](#netrun-llm-v100)
11. [netrun-env v1.0.0](#netrun-env-v100)
12. [netrun-pytest-fixtures v1.0.0](#netrun-pytest-fixtures-v100)
13. [netrun-ratelimit v1.0.0](#netrun-ratelimit-v100)
14. [Full Integration Example](#full-integration-example)
15. [Migration Guide](#migration-guide)

---

## Package Overview

| Package | Version | PyPI | Dependencies |
|---------|---------|------|--------------|
| netrun-auth | 1.1.0 | [PyPI](https://pypi.org/project/netrun-auth/) | pyjwt, cryptography, casbin |
| netrun-config | 1.1.0 | [PyPI](https://pypi.org/project/netrun-config/) | pydantic, pydantic-settings |
| netrun-logging | 1.1.0 | [PyPI](https://pypi.org/project/netrun-logging/) | structlog, azure-monitor-opentelemetry |
| netrun-errors | 1.1.0 | [PyPI](https://pypi.org/project/netrun-errors/) | pydantic |
| netrun-cors | 1.1.0 | [PyPI](https://pypi.org/project/netrun-cors/) | starlette |
| netrun-db-pool | 1.0.0 | [PyPI](https://pypi.org/project/netrun-db-pool/) | sqlalchemy[asyncio] |
| netrun-llm | 1.0.0 | [PyPI](https://pypi.org/project/netrun-llm/) | requests |
| netrun-env | 1.0.0 | [PyPI](https://pypi.org/project/netrun-env/) | click, pydantic, python-dotenv |
| netrun-pytest-fixtures | 1.0.0 | [PyPI](https://pypi.org/project/netrun-pytest-fixtures/) | pytest, pytest-asyncio |
| netrun-ratelimit | 1.0.0 | [PyPI](https://pypi.org/project/netrun-ratelimit/) | redis |

---

## Installation Guide

### Minimal Installation (Foundation)
```bash
pip install netrun-logging==1.1.0 netrun-errors==1.1.0
```

### Standard Installation (Core + Web)
```bash
pip install netrun-auth==1.1.0 netrun-logging==1.1.0 netrun-config==1.1.0 \
    netrun-errors==1.1.0 netrun-cors==1.1.0
```

### Full Installation (All 10 Packages)
```bash
pip install netrun-auth[all]==1.1.0 netrun-logging==1.1.0 netrun-config[all]==1.1.0 \
    netrun-errors==1.1.0 netrun-cors==1.1.0 netrun-db-pool==1.0.0 \
    netrun-llm[all]==1.0.0 netrun-env==1.0.0 netrun-pytest-fixtures[all]==1.0.0 \
    netrun-ratelimit==1.0.0
```

### Package-Specific Extras

```bash
# netrun-auth extras
pip install netrun-auth[azure]      # Azure AD integration
pip install netrun-auth[oauth]      # OAuth providers (authlib, httpx)
pip install netrun-auth[fastapi]    # FastAPI middleware
pip install netrun-auth[casbin]     # Casbin adapters (SQLAlchemy, Redis)
pip install netrun-auth[logging]    # netrun-logging integration
pip install netrun-auth[all]        # All extras

# netrun-config extras
pip install netrun-config[azure]    # Azure Key Vault
pip install netrun-config[errors]   # netrun-errors integration
pip install netrun-config[logging]  # netrun-logging integration
pip install netrun-config[all]      # All extras

# netrun-llm extras
pip install netrun-llm[anthropic]   # Anthropic Claude
pip install netrun-llm[openai]      # OpenAI GPT
pip install netrun-llm[logging]     # netrun-logging integration
pip install netrun-llm[all]         # All extras

# netrun-pytest-fixtures extras
pip install netrun-pytest-fixtures[sqlalchemy]  # Database fixtures
pip install netrun-pytest-fixtures[redis]       # Redis fixtures
pip install netrun-pytest-fixtures[httpx]       # HTTP client fixtures
pip install netrun-pytest-fixtures[fastapi]     # FastAPI test client
pip install netrun-pytest-fixtures[yaml]        # YAML fixtures
pip install netrun-pytest-fixtures[logging]     # Log capture fixtures
pip install netrun-pytest-fixtures[all]         # All extras
```

---

## Integration Architecture

### Soft Dependency Pattern

All packages use a consistent soft dependency pattern for optional integration:

```python
# Standard pattern used across all Netrun packages
_use_netrun_logging = False
_logger = None

try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)

def _log(level: str, message: str, **kwargs) -> None:
    """Unified logging that works with or without netrun-logging."""
    if _use_netrun_logging:
        log_method = getattr(_logger, level, _logger.info)
        log_method(message, **kwargs)
    else:
        log_method = getattr(_logger, level, _logger.info)
        log_method(f"{message} {kwargs}" if kwargs else message)
```

### Package Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Application Layer                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  auth    │ │  config  │ │   cors   │ │   llm    │ │ db-pool  │      │
│  │  v1.1.0  │ │  v1.1.0  │ │  v1.1.0  │ │  v1.0.0  │ │  v1.0.0  │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
│       │            │            │            │            │             │
│  ┌────┴────┐  ┌────┴────┐                                               │
│  │ratelimit│  │   env   │                                               │
│  │ v1.0.0  │  │  v1.0.0 │                                               │
│  └────┬────┘  └────┬────┘                                               │
│       │            │                                                     │
├───────┴────────────┴─────────────────────────────────────────────────────┤
│                       Foundation Layer                                   │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │      netrun-logging         │  │        netrun-errors            │   │
│  │          v1.1.0             │  │           v1.1.0                │   │
│  │  • Structured logging       │  │  • Exception hierarchy          │   │
│  │  • Correlation IDs          │  │  • Error codes                  │   │
│  │  • Azure App Insights       │  │  • FastAPI handlers             │   │
│  │  • Ecosystem helpers        │  │  • Correlation ID propagation   │   │
│  └─────────────────────────────┘  └─────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                         Testing Layer                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   netrun-pytest-fixtures v1.0.0                  │    │
│  │  • JWT fixtures  • Redis mocks  • DB sessions  • Log capture    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## netrun-logging v1.1.0

### Overview

High-performance structured logging with Azure App Insights integration and ecosystem helper functions.

### Installation

```bash
pip install netrun-logging==1.1.0
```

### Core API

#### `configure_logging()`

Configure the logging system. Call once at application startup.

```python
from netrun_logging import configure_logging

configure_logging(
    service_name: str = "app",           # Service identifier
    environment: str = "development",     # dev, staging, production
    log_level: str = "INFO",             # DEBUG, INFO, WARNING, ERROR, CRITICAL
    azure_connection_string: str = None,  # Azure App Insights connection
    json_format: bool = True,            # Output as JSON
    include_timestamps: bool = True,
    include_caller_info: bool = True,
    redact_patterns: list[str] = None,   # Additional patterns to redact
)
```

**Example**:
```python
from netrun_logging import configure_logging

# Development configuration
configure_logging(
    service_name="my-api",
    environment="development",
    log_level="DEBUG",
    json_format=False,  # Human-readable in dev
)

# Production configuration
configure_logging(
    service_name="my-api",
    environment="production",
    log_level="INFO",
    azure_connection_string="InstrumentationKey=xxx;IngestionEndpoint=xxx",
    json_format=True,
)
```

#### `get_logger()`

Get a configured logger instance.

```python
from netrun_logging import get_logger

logger = get_logger(name: str) -> structlog.BoundLogger
```

**Example**:
```python
from netrun_logging import get_logger

logger = get_logger(__name__)

# Synchronous logging
logger.info("User logged in", user_id="123", ip_address="192.168.1.1")
logger.warning("Rate limit approaching", current=95, limit=100)
logger.error("Database connection failed", error="Connection refused", retry_count=3)

# With context binding
bound_logger = logger.bind(request_id="req-456", tenant_id="tenant-789")
bound_logger.info("Processing request")  # Includes request_id and tenant_id
```

#### `get_correlation_id()` / `set_correlation_id()`

Manage correlation IDs for request tracing.

```python
from netrun_logging import get_correlation_id, set_correlation_id

# Get current correlation ID
correlation_id = get_correlation_id() -> str | None

# Set correlation ID (usually done by middleware)
set_correlation_id(correlation_id: str) -> None
```

**Example**:
```python
from netrun_logging import get_correlation_id, set_correlation_id
import uuid

# Set at request start
set_correlation_id(str(uuid.uuid4()))

# Access anywhere in the request lifecycle
correlation_id = get_correlation_id()
logger.info("Processing", correlation_id=correlation_id)
```

#### `bind_context()`

Bind context variables to all subsequent log entries in the current context.

```python
from netrun_logging import bind_context

bind_context(**kwargs) -> None
```

**Example**:
```python
from netrun_logging import bind_context, get_logger

logger = get_logger(__name__)

# Bind user context for all subsequent logs
bind_context(user_id="user-123", session_id="sess-456")

logger.info("Action performed")  # Includes user_id and session_id
logger.info("Another action")    # Also includes user_id and session_id
```

### Ecosystem Module (v1.1.0)

The `ecosystem` module provides helper functions for integration with other Netrun packages.

#### `bind_error_context()`

Bind error-specific context for correlation with netrun-errors.

```python
from netrun_logging.ecosystem import bind_error_context

bind_error_context(
    error_code: str,
    status_code: int,
    correlation_id: str = None,
    **additional_context
) -> None
```

**Example**:
```python
from netrun_logging.ecosystem import bind_error_context

bind_error_context(
    error_code="AUTH_001",
    status_code=401,
    correlation_id="corr-123",
    user_id="user-456",
    attempted_resource="/api/admin"
)
```

#### `bind_request_context()`

Bind HTTP request context for API logging.

```python
from netrun_logging.ecosystem import bind_request_context

bind_request_context(
    method: str,
    path: str,
    correlation_id: str = None,
    user_id: str = None,
    tenant_id: str = None,
    **additional_context
) -> None
```

**Example**:
```python
from netrun_logging.ecosystem import bind_request_context

bind_request_context(
    method="POST",
    path="/api/users",
    correlation_id="req-789",
    user_id="user-123",
    tenant_id="tenant-456",
    client_ip="192.168.1.100"
)
```

#### `bind_operation_context()`

Bind operation context for business logic tracking.

```python
from netrun_logging.ecosystem import bind_operation_context

bind_operation_context(
    operation: str,
    resource_type: str = None,
    resource_id: str = None,
    **additional_context
) -> None
```

**Example**:
```python
from netrun_logging.ecosystem import bind_operation_context

bind_operation_context(
    operation="create_invoice",
    resource_type="invoice",
    resource_id="inv-12345",
    customer_id="cust-789"
)
```

#### `log_operation_timing()`

Context manager for timing operations with automatic logging.

```python
from netrun_logging.ecosystem import log_operation_timing

@contextmanager
def log_operation_timing(
    operation: str,
    logger_name: str = None,
    level: str = "info",
    **context
) -> Generator
```

**Example**:
```python
from netrun_logging.ecosystem import log_operation_timing

# Time a database query
with log_operation_timing("database_query", resource_type="users", query_type="select"):
    users = await db.fetch_all("SELECT * FROM users")

# Output: operation=database_query resource_type=users query_type=select duration_ms=45.2

# Time an external API call
with log_operation_timing("external_api_call", service="payment-gateway", endpoint="/charge"):
    response = await payment_client.charge(amount=100)
```

#### `log_timing()`

Decorator for timing function execution.

```python
from netrun_logging.ecosystem import log_timing

def log_timing(
    operation: str = None,  # Defaults to function name
    level: str = "info",
    include_args: bool = False
) -> Callable
```

**Example**:
```python
from netrun_logging.ecosystem import log_timing

@log_timing(operation="process_payment", level="info")
async def process_payment(amount: float, currency: str):
    # Payment processing logic
    return {"status": "success"}

# Output: operation=process_payment duration_ms=234.5

@log_timing(include_args=True)
async def fetch_user(user_id: str):
    return await db.get_user(user_id)

# Output: operation=fetch_user user_id=user-123 duration_ms=12.3
```

#### `create_audit_logger()`

Create an audit logger for compliance logging.

```python
from netrun_logging.ecosystem import create_audit_logger

def create_audit_logger(
    service_name: str,
    actor_id: str = None,
    tenant_id: str = None
) -> structlog.BoundLogger
```

**Example**:
```python
from netrun_logging.ecosystem import create_audit_logger

# Create audit logger
audit = create_audit_logger(
    service_name="payment-service",
    actor_id="admin-user-123",
    tenant_id="tenant-456"
)

# Log audit events
audit.info("payment_processed",
    amount=100.00,
    currency="USD",
    payment_method="credit_card",
    transaction_id="txn-789"
)

audit.warning("refund_requested",
    original_transaction="txn-789",
    refund_amount=50.00,
    reason="customer_request"
)

audit.info("user_permission_changed",
    target_user="user-456",
    old_role="viewer",
    new_role="editor"
)
```

### Middleware

#### `CorrelationMiddleware`

FastAPI middleware for automatic correlation ID management.

```python
from netrun_logging.middleware import CorrelationMiddleware
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(CorrelationMiddleware)
```

**Behavior**:
- Reads `X-Correlation-ID` header from incoming requests
- Generates new correlation ID if not present
- Sets correlation ID in response headers
- Binds correlation ID to logging context

### Automatic Redaction

The following fields are automatically redacted:

- `password`, `passwd`, `pwd`
- `secret`, `secret_key`
- `api_key`, `apikey`
- `token`, `access_token`, `refresh_token`
- `authorization`, `auth`
- `credential`, `credentials`
- `private_key`, `private`

**Example**:
```python
logger.info("User authentication",
    username="alice@example.com",
    password="secret123",           # Becomes [REDACTED]
    api_key="sk_live_abc123",       # Becomes [REDACTED]
    user_id="user-123"              # Not redacted
)

# Output: username=alice@example.com password=[REDACTED] api_key=[REDACTED] user_id=user-123
```

---

## netrun-errors v1.1.0

### Overview

Standardized exception hierarchy with automatic correlation ID propagation and FastAPI integration.

### Installation

```bash
pip install netrun-errors==1.1.0

# With logging integration
pip install netrun-errors[logging]==1.1.0
```

### Exception Hierarchy

```
NetrunException (base)
├── ValidationError (400)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── NotFoundError (404)
├── ConflictError (409)
├── RateLimitExceededError (429)  # NEW in v1.1.0
├── ConfigurationError (500)
├── ExternalServiceError (502)    # NEW in v1.1.0
├── BadGatewayError (502)         # NEW in v1.1.0
└── GatewayTimeoutError (504)     # NEW in v1.1.0
```

### Core API

#### `NetrunException` (Base Class)

```python
from netrun_errors import NetrunException

class NetrunException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: dict = None,
        correlation_id: str = None,  # Auto-populated from netrun-logging
    ):
        ...

    @property
    def status_code(self) -> int: ...

    def to_dict(self) -> dict: ...
```

#### `ValidationError`

For input validation failures. HTTP 400.

```python
from netrun_errors import ValidationError

raise ValidationError(
    message: str,
    field: str = None,           # Field that failed validation
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import ValidationError

# Single field validation
raise ValidationError(
    message="Email format is invalid",
    field="email",
    error_code="VALIDATION_001"
)

# Multiple field validation
raise ValidationError(
    message="Multiple validation errors",
    error_code="VALIDATION_002",
    details={
        "errors": [
            {"field": "email", "message": "Invalid format"},
            {"field": "age", "message": "Must be positive"}
        ]
    }
)
```

#### `AuthenticationError`

For authentication failures. HTTP 401.

```python
from netrun_errors import AuthenticationError

raise AuthenticationError(
    message: str,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import AuthenticationError

raise AuthenticationError(
    message="Invalid or expired token",
    error_code="AUTH_001"
)

raise AuthenticationError(
    message="MFA verification required",
    error_code="AUTH_002",
    details={"mfa_methods": ["totp", "sms"]}
)
```

#### `AuthorizationError`

For permission/access denied. HTTP 403.

```python
from netrun_errors import AuthorizationError

raise AuthorizationError(
    message: str,
    required_permission: str = None,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import AuthorizationError

raise AuthorizationError(
    message="Insufficient permissions to access resource",
    required_permission="admin:write",
    error_code="AUTHZ_001"
)

raise AuthorizationError(
    message="Cross-tenant access denied",
    error_code="AUTHZ_002",
    details={
        "requested_tenant": "tenant-456",
        "user_tenant": "tenant-123"
    }
)
```

#### `NotFoundError`

For resource not found. HTTP 404.

```python
from netrun_errors import NotFoundError

raise NotFoundError(
    message: str,
    resource_type: str = None,
    resource_id: str = None,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import NotFoundError

raise NotFoundError(
    message="User not found",
    resource_type="user",
    resource_id="user-123",
    error_code="USER_001"
)
```

#### `ConflictError`

For resource conflicts (duplicate, version mismatch). HTTP 409.

```python
from netrun_errors import ConflictError

raise ConflictError(
    message: str,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import ConflictError

raise ConflictError(
    message="Email already registered",
    error_code="CONFLICT_001",
    details={"field": "email"}
)

raise ConflictError(
    message="Resource version mismatch",
    error_code="CONFLICT_002",
    details={
        "expected_version": 5,
        "actual_version": 7
    }
)
```

#### `RateLimitExceededError` (NEW in v1.1.0)

For rate limiting. HTTP 429.

```python
from netrun_errors import RateLimitExceededError

raise RateLimitExceededError(
    message: str,
    retry_after: int = None,     # Seconds until retry allowed
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import RateLimitExceededError

raise RateLimitExceededError(
    message="API rate limit exceeded",
    retry_after=60,
    error_code="RATE_001",
    details={
        "limit": 100,
        "window": "1 minute",
        "current": 105
    }
)
```

#### `ConfigurationError`

For configuration/setup errors. HTTP 500.

```python
from netrun_errors import ConfigurationError

raise ConfigurationError(
    message: str,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import ConfigurationError

raise ConfigurationError(
    message="Database connection string not configured",
    error_code="CONFIG_001"
)

raise ConfigurationError(
    message="Invalid Azure Key Vault configuration",
    error_code="CONFIG_002",
    details={"missing_fields": ["vault_url", "tenant_id"]}
)
```

#### `ExternalServiceError` (NEW in v1.1.0)

For external service failures. HTTP 502.

```python
from netrun_errors import ExternalServiceError

raise ExternalServiceError(
    message: str,
    service_name: str = None,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import ExternalServiceError

raise ExternalServiceError(
    message="Payment gateway unavailable",
    service_name="stripe",
    error_code="EXTERNAL_001",
    details={
        "status_code": 503,
        "response": "Service temporarily unavailable"
    }
)
```

#### `BadGatewayError` (NEW in v1.1.0)

For bad gateway responses. HTTP 502.

```python
from netrun_errors import BadGatewayError

raise BadGatewayError(
    message: str,
    error_code: str = None,
    details: dict = None,
)
```

#### `GatewayTimeoutError` (NEW in v1.1.0)

For gateway timeouts. HTTP 504.

```python
from netrun_errors import GatewayTimeoutError

raise GatewayTimeoutError(
    message: str,
    timeout_seconds: int = None,
    error_code: str = None,
    details: dict = None,
)
```

**Example**:
```python
from netrun_errors import GatewayTimeoutError

raise GatewayTimeoutError(
    message="Upstream service timed out",
    timeout_seconds=30,
    error_code="TIMEOUT_001"
)
```

### FastAPI Integration

#### `register_exception_handlers()`

Register exception handlers with a FastAPI application.

```python
from netrun_errors.handlers import register_exception_handlers
from fastapi import FastAPI

app = FastAPI()
register_exception_handlers(app)
```

**Response Format**:
```json
{
    "error": {
        "code": "VALIDATION_001",
        "message": "Email format is invalid",
        "field": "email",
        "correlation_id": "corr-123-456",
        "details": {}
    }
}
```

#### Custom Error Responses

```python
from netrun_errors.handlers import create_error_response
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(CustomException)
async def custom_handler(request: Request, exc: CustomException):
    return create_error_response(
        status_code=400,
        error_code="CUSTOM_001",
        message=str(exc),
        correlation_id=get_correlation_id()
    )
```

### Correlation ID Integration

When `netrun-logging` is installed, errors automatically capture the current correlation ID:

```python
from netrun_logging import set_correlation_id
from netrun_errors import ValidationError

set_correlation_id("request-123")

try:
    raise ValidationError(message="Invalid input", error_code="VAL_001")
except ValidationError as e:
    print(e.correlation_id)  # "request-123"
    print(e.to_dict())
    # {
    #     "error_code": "VAL_001",
    #     "message": "Invalid input",
    #     "correlation_id": "request-123",
    #     "status_code": 400
    # }
```

---

## netrun-auth v1.1.0

### Overview

Complete authentication and authorization library with JWT, Casbin RBAC, multi-tenant support, and MFA.

### Installation

```bash
pip install netrun-auth[all]==1.1.0
```

### JWT Management

#### `JWTManager`

```python
from netrun_auth import JWTManager

jwt_manager = JWTManager(
    secret_key: str,                    # For HS256/HS384/HS512
    algorithm: str = "HS256",           # HS256, HS384, HS512, RS256, RS512, ES256
    expiry_minutes: int = 60,
    refresh_expiry_minutes: int = 10080,  # 7 days
    issuer: str = None,
    audience: str = None,
    private_key: str = None,            # For RS/ES algorithms
    public_key: str = None,             # For RS/ES algorithms
)
```

#### Creating Tokens

```python
from netrun_auth import JWTManager

jwt_manager = JWTManager(secret_key="your-secret-key", algorithm="HS256")

# Create access token
access_token = jwt_manager.create_token(
    sub: str,                           # Subject (user ID)
    roles: list[str] = None,
    permissions: list[str] = None,
    tenant_id: str = None,
    custom_claims: dict = None,
    expiry_minutes: int = None,         # Override default
)

# Create refresh token
refresh_token = jwt_manager.create_refresh_token(
    sub: str,
    expiry_minutes: int = None,
)
```

**Example**:
```python
from netrun_auth import JWTManager

jwt_manager = JWTManager(
    secret_key="your-256-bit-secret-key",
    algorithm="HS256",
    expiry_minutes=60,
    issuer="my-api",
    audience="my-app"
)

# Create token with roles
access_token = jwt_manager.create_token(
    sub="user-123",
    roles=["user", "admin"],
    tenant_id="tenant-456",
    custom_claims={
        "email": "alice@example.com",
        "name": "Alice Smith"
    }
)

# Create refresh token
refresh_token = jwt_manager.create_refresh_token(sub="user-123")
```

#### Decoding/Verifying Tokens

```python
from netrun_auth import JWTManager
from netrun_auth.models import TokenPayload

# Decode and verify token
payload: TokenPayload = jwt_manager.decode_token(token: str)

# Access payload attributes
print(payload.sub)        # "user-123"
print(payload.roles)      # ["user", "admin"]
print(payload.tenant_id)  # "tenant-456"
print(payload.exp)        # datetime
print(payload.iat)        # datetime
```

**Example with error handling**:
```python
from netrun_auth import JWTManager
from netrun_auth.exceptions import TokenExpiredError, InvalidTokenError

try:
    payload = jwt_manager.decode_token(token)
    print(f"User: {payload.sub}")
except TokenExpiredError:
    print("Token has expired")
except InvalidTokenError as e:
    print(f"Invalid token: {e}")
```

#### Token Refresh

```python
from netrun_auth import JWTManager

# Refresh an access token
new_access_token, new_refresh_token = jwt_manager.refresh_tokens(
    refresh_token: str,
    rotate_refresh: bool = True,  # Issue new refresh token
)
```

### RBAC with Casbin

#### `RBACManager`

```python
from netrun_auth import RBACManager

rbac = RBACManager(
    model_path: str = None,             # Path to Casbin model file
    model_text: str = None,             # Or inline model definition
    policy_adapter: str = None,         # Database URL for policy storage
    policy_file: str = None,            # Or file path for CSV policy
)
```

#### Casbin Model (RBAC)

```ini
# rbac_model.conf
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

#### Checking Permissions

```python
from netrun_auth import RBACManager

rbac = RBACManager(
    model_path="rbac_model.conf",
    policy_file="policy.csv"
)

# Check permission
allowed = rbac.check_permission(
    user_id: str,
    resource: str,
    action: str,
) -> bool

# Check with tenant context
allowed = rbac.check_permission(
    user_id: str,
    resource: str,
    action: str,
    tenant_id: str = None,
)
```

**Example**:
```python
from netrun_auth import RBACManager

rbac = RBACManager(
    model_path="rbac_model.conf",
    policy_adapter="postgresql://localhost/authdb"
)

# Add policies
rbac.add_policy("admin", "users", "read")
rbac.add_policy("admin", "users", "write")
rbac.add_policy("user", "users", "read")

# Add role assignment
rbac.add_role_for_user("alice", "admin")
rbac.add_role_for_user("bob", "user")

# Check permissions
rbac.check_permission("alice", "users", "write")  # True
rbac.check_permission("bob", "users", "write")    # False
rbac.check_permission("bob", "users", "read")     # True
```

#### Multi-Tenant RBAC

```python
# Model with tenant support (rbac_with_tenant.conf)
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
```

```python
from netrun_auth import RBACManager

rbac = RBACManager(model_path="rbac_with_tenant.conf")

# Add tenant-scoped policies
rbac.add_policy("admin", "tenant-1", "reports", "read")
rbac.add_policy("admin", "tenant-1", "reports", "write")

# Assign role within tenant
rbac.add_role_for_user_in_domain("alice", "admin", "tenant-1")

# Check with tenant context
rbac.check_permission("alice", "reports", "write", tenant_id="tenant-1")  # True
rbac.check_permission("alice", "reports", "write", tenant_id="tenant-2")  # False
```

### Password Hashing

#### `PasswordManager`

```python
from netrun_auth import PasswordManager

pwd_manager = PasswordManager(
    algorithm: str = "argon2",  # argon2, bcrypt, pbkdf2
    rounds: int = None,         # Algorithm-specific
)

# Hash password
hashed = pwd_manager.hash(password: str) -> str

# Verify password
is_valid = pwd_manager.verify(password: str, hashed: str) -> bool

# Check if rehash needed
needs_rehash = pwd_manager.needs_rehash(hashed: str) -> bool
```

**Example**:
```python
from netrun_auth import PasswordManager

pwd_manager = PasswordManager(algorithm="argon2")

# Register user
hashed_password = pwd_manager.hash("user_password_123")
# Store hashed_password in database

# Login
stored_hash = get_hash_from_database(username)
if pwd_manager.verify(submitted_password, stored_hash):
    # Password correct
    if pwd_manager.needs_rehash(stored_hash):
        # Update hash with new parameters
        new_hash = pwd_manager.hash(submitted_password)
        update_hash_in_database(username, new_hash)
```

### FastAPI Middleware

#### `AuthMiddleware`

```python
from netrun_auth.middleware import AuthMiddleware
from fastapi import FastAPI

app = FastAPI()

app.add_middleware(
    AuthMiddleware,
    jwt_manager: JWTManager,
    exclude_paths: list[str] = ["/health", "/docs"],
    exclude_methods: list[str] = ["OPTIONS"],
)
```

**Example**:
```python
from fastapi import FastAPI, Request
from netrun_auth import JWTManager
from netrun_auth.middleware import AuthMiddleware

app = FastAPI()

jwt_manager = JWTManager(secret_key="secret", algorithm="HS256")

app.add_middleware(
    AuthMiddleware,
    jwt_manager=jwt_manager,
    exclude_paths=["/health", "/login", "/docs", "/openapi.json"]
)

@app.get("/protected")
async def protected_route(request: Request):
    # Access user from request state
    user = request.state.user
    return {"user_id": user.sub, "roles": user.roles}
```

#### `require_auth` Dependency

```python
from netrun_auth.dependencies import require_auth, require_roles, require_permissions
from fastapi import Depends

@app.get("/profile")
async def get_profile(user = Depends(require_auth)):
    return {"user_id": user.sub}

@app.get("/admin")
async def admin_only(user = Depends(require_roles(["admin"]))):
    return {"message": "Admin access granted"}

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user = Depends(require_permissions(["users:delete"]))
):
    return {"deleted": user_id}
```

### MFA Support

#### `MFAManager`

```python
from netrun_auth.mfa import MFAManager

mfa = MFAManager(
    issuer: str = "MyApp",
    algorithm: str = "SHA1",
    digits: int = 6,
    period: int = 30,
)

# Generate secret for user
secret = mfa.generate_secret() -> str

# Generate provisioning URI (for QR code)
uri = mfa.get_provisioning_uri(
    secret: str,
    user_email: str,
) -> str

# Verify TOTP code
is_valid = mfa.verify_totp(
    secret: str,
    code: str,
) -> bool
```

**Example**:
```python
from netrun_auth.mfa import MFAManager
import qrcode

mfa = MFAManager(issuer="MyApp")

# Setup MFA for user
secret = mfa.generate_secret()
# Store secret in database for user

# Generate QR code
uri = mfa.get_provisioning_uri(secret, "alice@example.com")
qr = qrcode.make(uri)
qr.save("mfa_qr.png")

# Verify code during login
user_code = "123456"  # From authenticator app
if mfa.verify_totp(secret, user_code):
    print("MFA verified")
else:
    print("Invalid MFA code")
```

---

## netrun-config v1.1.0

### Overview

Configuration management with Azure Key Vault integration, TTL caching, and multi-vault support.

### Installation

```bash
pip install netrun-config[all]==1.1.0
```

### Pydantic Settings

#### `BaseSettings`

Extended Pydantic settings with Azure Key Vault support.

```python
from netrun_config import BaseSettings
from pydantic import Field

class AppSettings(BaseSettings):
    # Environment variables
    app_name: str = Field(default="MyApp")
    debug: bool = Field(default=False)

    # Secrets (can come from Key Vault)
    database_url: str
    api_key: str

    class Config:
        env_prefix = "APP_"          # APP_DATABASE_URL, APP_API_KEY
        env_file = ".env"
        case_sensitive = False
```

**Example**:
```python
from netrun_config import BaseSettings
from pydantic import Field, field_validator

class DatabaseSettings(BaseSettings):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str
    user: str
    password: str
    pool_size: int = Field(default=10, ge=1, le=100)

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v):
        if v < 1:
            raise ValueError("Pool size must be at least 1")
        return v

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    class Config:
        env_prefix = "DB_"

settings = DatabaseSettings()
print(settings.connection_string)
```

### Secret Caching

#### `SecretCache`

TTL-based caching for Azure Key Vault secrets.

```python
from netrun_config import SecretCache

cache = SecretCache(
    vault_url: str,
    cache_ttl: int = 28800,        # 8 hours (Microsoft recommended)
    credential = None,              # Azure credential (DefaultAzureCredential if None)
)

# Get secret (cached)
value = cache.get_secret(name: str) -> str

# Get secret (force refresh)
value = cache.get_secret(name: str, force_refresh: bool = True) -> str

# Clear cache
cache.clear()

# Get cache statistics
stats = cache.get_stats() -> dict
```

**Example**:
```python
from netrun_config import SecretCache
from azure.identity import DefaultAzureCredential

# Using default Azure credential
cache = SecretCache(
    vault_url="https://my-vault.vault.azure.net/",
    cache_ttl=28800  # 8 hours
)

# First call hits Key Vault
db_password = cache.get_secret("database-password")

# Subsequent calls use cache
db_password = cache.get_secret("database-password")  # Cache hit

# Force refresh
db_password = cache.get_secret("database-password", force_refresh=True)

# Check stats
print(cache.get_stats())
# {"hits": 10, "misses": 2, "size": 5, "ttl": 28800}
```

### Multi-Vault Support

#### `MultiVaultClient`

Route secrets to different vaults.

```python
from netrun_config import MultiVaultClient

client = MultiVaultClient(
    vaults: dict[str, str],        # name -> vault_url mapping
    default_vault: str = None,
    cache_ttl: int = 28800,
)

# Get secret from specific vault
value = client.get_secret(vault_name: str, secret_name: str) -> str

# Get secret from default vault
value = client.get_secret(secret_name: str) -> str
```

**Example**:
```python
from netrun_config import MultiVaultClient

client = MultiVaultClient(
    vaults={
        "dev": "https://myapp-dev-kv.vault.azure.net/",
        "staging": "https://myapp-staging-kv.vault.azure.net/",
        "prod": "https://myapp-prod-kv.vault.azure.net/",
        "certs": "https://myapp-certs-kv.vault.azure.net/",
    },
    default_vault="prod",
    cache_ttl=28800
)

# Get from specific vault
dev_api_key = client.get_secret("dev", "api-key")
prod_db_password = client.get_secret("prod", "database-password")
ssl_cert = client.get_secret("certs", "ssl-certificate")

# Get from default vault (prod)
api_key = client.get_secret("api-key")
```

### Pydantic Settings Source

#### `AzureKeyVaultSettingsSource`

Integrate Key Vault with Pydantic settings.

```python
from pydantic_settings import BaseSettings
from netrun_config import AzureKeyVaultSettingsSource

class AppSettings(BaseSettings):
    database_url: str
    api_key: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings
    ):
        return (
            init_settings,
            AzureKeyVaultSettingsSource(
                settings_cls,
                vault_url="https://my-vault.vault.azure.net/",
                secret_prefix="myapp-",  # Optional prefix
            ),
            env_settings,
            dotenv_settings,
        )

# Loads myapp-database-url and myapp-api-key from Key Vault
settings = AppSettings()
```

### Configuration Validators

#### Built-in Validators

```python
from netrun_config.validators import (
    validate_database_url,
    validate_redis_url,
    validate_cors_origins,
    validate_log_level,
)

# Validate database URL
validate_database_url("postgresql://user:pass@host:5432/db")  # OK
validate_database_url("invalid-url")  # Raises ConfigurationError

# Validate Redis URL
validate_redis_url("redis://localhost:6379/0")  # OK

# Validate CORS origins
validate_cors_origins(["https://example.com", "https://*.example.com"])  # OK
validate_cors_origins(["*"])  # Warning: wildcard

# Validate log level
validate_log_level("INFO")  # OK
validate_log_level("VERBOSE")  # Raises ConfigurationError
```

---

## netrun-env v1.0.0

### Overview

Schema-based environment variable validation with security checks and CLI tool.

### Installation

```bash
pip install netrun-env==1.0.0
```

### Schema Definition

#### `EnvSchema`

```python
from netrun_env import EnvSchema

schema = EnvSchema({
    "VAR_NAME": {
        "type": str,           # str, int, float, bool, list, dict
        "required": bool,      # Default: False
        "default": any,        # Default value
        "secret": bool,        # Marks as sensitive (don't log)
        "pattern": str,        # Regex pattern for validation
        "min": number,         # Minimum value (int/float)
        "max": number,         # Maximum value (int/float)
        "choices": list,       # Allowed values
        "description": str,    # Documentation
    }
})
```

**Example**:
```python
from netrun_env import EnvSchema

schema = EnvSchema({
    "DATABASE_URL": {
        "type": "string",
        "required": True,
        "secret": True,
        "pattern": r"^postgresql://",
        "description": "PostgreSQL connection string"
    },
    "API_KEY": {
        "type": "string",
        "required": True,
        "secret": True,
        "description": "External API key"
    },
    "DEBUG": {
        "type": "boolean",
        "default": False,
        "description": "Enable debug mode"
    },
    "LOG_LEVEL": {
        "type": "string",
        "default": "INFO",
        "choices": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "description": "Logging level"
    },
    "MAX_CONNECTIONS": {
        "type": "integer",
        "default": 10,
        "min": 1,
        "max": 100,
        "description": "Maximum database connections"
    },
    "ALLOWED_HOSTS": {
        "type": "list",
        "default": ["localhost"],
        "description": "Allowed host headers"
    }
})
```

### Validation

#### `EnvValidator`

```python
from netrun_env import EnvValidator, EnvSchema

validator = EnvValidator(
    schema: EnvSchema,
    env_file: str = ".env",        # Optional .env file
    strict: bool = False,          # Fail on unknown variables
)

# Validate and get result
result = validator.validate() -> ValidationResult

# Access result
result.is_valid: bool
result.errors: list[str]
result.warnings: list[str]
result.values: dict[str, any]     # Parsed values
```

**Example**:
```python
from netrun_env import EnvValidator, EnvSchema
import os

# Set environment
os.environ["DATABASE_URL"] = "postgresql://localhost/mydb"
os.environ["API_KEY"] = "sk-123456"
os.environ["DEBUG"] = "true"

schema = EnvSchema({
    "DATABASE_URL": {"type": "string", "required": True, "secret": True},
    "API_KEY": {"type": "string", "required": True, "secret": True},
    "DEBUG": {"type": "boolean", "default": False},
    "LOG_LEVEL": {"type": "string", "default": "INFO", "choices": ["DEBUG", "INFO", "WARNING", "ERROR"]},
})

validator = EnvValidator(schema)
result = validator.validate()

if result.is_valid:
    print("Configuration valid!")
    print(f"Debug mode: {result.values['DEBUG']}")
    print(f"Log level: {result.values['LOG_LEVEL']}")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

### Security Checks

#### `SecurityChecker`

```python
from netrun_env import SecurityChecker

checker = SecurityChecker(
    env_file: str = ".env",
)

# Run security checks
issues = checker.check() -> list[SecurityIssue]

# Check specific patterns
issues = checker.check_for_secrets() -> list[SecurityIssue]
issues = checker.check_permissions() -> list[SecurityIssue]
```

**Example**:
```python
from netrun_env import SecurityChecker

checker = SecurityChecker(env_file=".env")
issues = checker.check()

for issue in issues:
    print(f"[{issue.severity}] {issue.message}")
    if issue.suggestion:
        print(f"  Suggestion: {issue.suggestion}")

# Example output:
# [HIGH] Possible secret in .env file: API_KEY appears to contain a token
#   Suggestion: Move API_KEY to a secrets manager
# [MEDIUM] .env file has world-readable permissions
#   Suggestion: Run chmod 600 .env
```

### Diff Detection

#### `EnvDiff`

```python
from netrun_env import EnvDiff, EnvSchema

diff = EnvDiff(
    schema: EnvSchema,
    env_file: str = ".env",
)

# Get differences
changes = diff.compare() -> DiffResult

changes.added: list[str]      # New variables not in schema
changes.removed: list[str]    # Schema variables missing from env
changes.changed: list[str]    # Variables with different values
changes.unchanged: list[str]  # Variables matching schema defaults
```

### CLI Tool

```bash
# Validate environment
netrun-env validate --schema env.schema.json
netrun-env validate --schema env.schema.json --env-file .env.production

# Security check
netrun-env security-check
netrun-env security-check --env-file .env.production

# Show diff
netrun-env diff --schema env.schema.json

# Generate schema from existing .env
netrun-env generate-schema --env-file .env --output env.schema.json

# Export documentation
netrun-env docs --schema env.schema.json --format markdown > ENV_VARS.md
```

---

## netrun-cors v1.1.0

### Overview

OWASP-compliant CORS middleware with security logging.

### Installation

```bash
pip install netrun-cors==1.1.0
```

### Middleware Factory

#### `create_cors_middleware()`

```python
from netrun_cors import create_cors_middleware

middleware = create_cors_middleware(
    allow_origins: list[str],            # Allowed origins
    allow_credentials: bool = False,
    allow_methods: list[str] = ["GET"],
    allow_headers: list[str] = [],
    expose_headers: list[str] = [],
    max_age: int = 600,                  # Preflight cache seconds
)
```

**Example**:
```python
from fastapi import FastAPI
from netrun_cors import create_cors_middleware

app = FastAPI()

# Basic CORS
cors = create_cors_middleware(
    allow_origins=["https://app.example.com"],
    allow_methods=["GET", "POST"],
)

# Full CORS configuration
cors = create_cors_middleware(
    allow_origins=[
        "https://app.example.com",
        "https://admin.example.com",
        "https://*.example.com",         # Wildcard subdomain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Correlation-ID",
        "X-Tenant-ID",
    ],
    expose_headers=[
        "X-Correlation-ID",
        "X-RateLimit-Remaining",
    ],
    max_age=3600,  # 1 hour preflight cache
)

app.add_middleware(cors.__class__, **cors.__dict__)
```

### Origin Patterns

```python
from netrun_cors import create_cors_middleware

cors = create_cors_middleware(
    allow_origins=[
        "https://example.com",           # Exact match
        "https://*.example.com",         # Wildcard subdomain
        "https://app.example.com:3000",  # With port
        "http://localhost:*",            # Any localhost port (dev only)
    ]
)
```

### OWASP Compliance

The middleware automatically enforces OWASP recommendations:

1. **No wildcard with credentials**: Rejects `allow_origins=["*"]` with `allow_credentials=True`
2. **Validates origin format**: Rejects malformed origins
3. **Logs security events**: When netrun-logging is installed

```python
# This will raise an error (OWASP violation)
cors = create_cors_middleware(
    allow_origins=["*"],
    allow_credentials=True,  # Cannot use * with credentials
)

# This is allowed
cors = create_cors_middleware(
    allow_origins=["*"],
    allow_credentials=False,
)
```

### Security Logging

When `netrun-logging` is installed, CORS events are automatically logged:

```python
# Logged events:
# - cors_middleware_configured: Configuration at startup
# - cors_origin_allowed: Successful origin validation
# - cors_origin_rejected: Rejected origin (potential attack)
# - cors_preflight_request: OPTIONS request handling
```

---

## netrun-ratelimit v1.0.0

### Overview

Token bucket rate limiting with Redis backend for distributed systems.

### Installation

```bash
pip install netrun-ratelimit==1.0.0
```

### Rate Limiter

#### `RateLimiter`

```python
from netrun_ratelimit import RateLimiter

limiter = RateLimiter(
    redis_url: str,
    default_limit: int = 100,        # Requests per window
    default_window: int = 60,        # Window in seconds
    key_prefix: str = "ratelimit",
)

# Check if request allowed
is_allowed = await limiter.is_allowed(key: str) -> bool

# Check with custom limit
is_allowed = await limiter.is_allowed(
    key: str,
    limit: int = None,
    window: int = None,
) -> bool

# Get remaining requests
remaining = await limiter.get_remaining(key: str) -> int

# Reset limit for key
await limiter.reset(key: str) -> None
```

**Example**:
```python
from netrun_ratelimit import RateLimiter

limiter = RateLimiter(
    redis_url="redis://localhost:6379/0",
    default_limit=100,
    default_window=60
)

# Per-IP rate limiting
async def check_rate_limit(ip_address: str) -> bool:
    return await limiter.is_allowed(f"ip:{ip_address}")

# Per-user rate limiting with custom limit
async def check_user_rate_limit(user_id: str, is_premium: bool) -> bool:
    limit = 1000 if is_premium else 100
    return await limiter.is_allowed(f"user:{user_id}", limit=limit)

# Per-endpoint rate limiting
async def check_endpoint_limit(user_id: str, endpoint: str) -> bool:
    key = f"user:{user_id}:endpoint:{endpoint}"
    return await limiter.is_allowed(key, limit=10, window=1)  # 10 req/sec
```

### Token Bucket

#### `TokenBucket`

More granular control with token bucket algorithm.

```python
from netrun_ratelimit import TokenBucket

bucket = TokenBucket(
    redis_url: str,
    capacity: int,              # Maximum tokens
    refill_rate: float,         # Tokens per second
    key_prefix: str = "bucket",
)

# Consume tokens
success = await bucket.consume(
    key: str,
    tokens: int = 1,
) -> bool

# Get current tokens
tokens = await bucket.get_tokens(key: str) -> float

# Reset bucket
await bucket.reset(key: str) -> None
```

**Example**:
```python
from netrun_ratelimit import TokenBucket

# 100 tokens, refills at 10/second
bucket = TokenBucket(
    redis_url="redis://localhost:6379/0",
    capacity=100,
    refill_rate=10
)

# API request (1 token)
if await bucket.consume(f"user:{user_id}"):
    return await process_request()
else:
    raise RateLimitExceededError("Rate limit exceeded")

# Expensive operation (10 tokens)
if await bucket.consume(f"user:{user_id}", tokens=10):
    return await expensive_operation()
```

### FastAPI Integration

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from netrun_ratelimit import RateLimiter

app = FastAPI()
limiter = RateLimiter(redis_url="redis://localhost:6379/0")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Get client identifier
    client_ip = request.client.host
    user_id = getattr(request.state, "user_id", None)

    key = f"user:{user_id}" if user_id else f"ip:{client_ip}"

    if not await limiter.is_allowed(key):
        remaining = await limiter.get_remaining(key)
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after": 60},
            headers={"X-RateLimit-Remaining": str(remaining)}
        )

    response = await call_next(request)
    remaining = await limiter.get_remaining(key)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
```

### Decorator

```python
from netrun_ratelimit import rate_limit

@app.get("/api/search")
@rate_limit(limit=10, window=60, key_func=lambda r: r.client.host)
async def search(request: Request, q: str):
    return await perform_search(q)

@app.post("/api/export")
@rate_limit(limit=5, window=3600, key_func=lambda r: r.state.user_id)
async def export_data(request: Request):
    return await generate_export()
```

---

## netrun-db-pool v1.0.0

### Overview

Async SQLAlchemy connection pooling with health checks and statistics.

### Installation

```bash
pip install netrun-db-pool==1.0.0
```

### Pool Configuration

#### `PoolConfig`

```python
from netrun_db_pool import PoolConfig

config = PoolConfig(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 5,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,      # Recycle connections after 1 hour
    pool_pre_ping: bool = True,    # Verify connections before use
    echo: bool = False,            # Log SQL statements
    echo_pool: bool = False,       # Log pool events
)
```

### Database Pool

#### `DatabasePool`

```python
from netrun_db_pool import DatabasePool, PoolConfig

pool = DatabasePool(config: PoolConfig)

# Initialize pool
await pool.initialize() -> None

# Get session context manager
async with pool.get_session() as session:
    result = await session.execute(query)

# Get raw connection
async with pool.get_connection() as conn:
    result = await conn.execute(query)

# Health check
is_healthy = await pool.health_check() -> bool

# Get statistics
stats = pool.get_stats() -> PoolStats

# Close pool
await pool.close() -> None
```

**Example**:
```python
from netrun_db_pool import DatabasePool, PoolConfig
from sqlalchemy import text

config = PoolConfig(
    database_url="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_pre_ping=True
)

pool = DatabasePool(config)

async def main():
    await pool.initialize()

    try:
        # Use session for ORM operations
        async with pool.get_session() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE id = :id"),
                {"id": "user-123"}
            )
            user = result.fetchone()

        # Check health
        if await pool.health_check():
            print("Database healthy")

        # Get stats
        stats = pool.get_stats()
        print(f"Pool size: {stats.size}")
        print(f"Checked out: {stats.checked_out}")
        print(f"Overflow: {stats.overflow}")

    finally:
        await pool.close()
```

### FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from netrun_db_pool import DatabasePool, PoolConfig
from sqlalchemy.ext.asyncio import AsyncSession

config = PoolConfig(database_url="postgresql+asyncpg://...")
pool = DatabasePool(config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.initialize()
    yield
    await pool.close()

app = FastAPI(lifespan=lifespan)

async def get_db() -> AsyncSession:
    async with pool.get_session() as session:
        yield session

@app.get("/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM users WHERE id = :id"),
        {"id": user_id}
    )
    return result.fetchone()

@app.get("/health/db")
async def db_health():
    healthy = await pool.health_check()
    stats = pool.get_stats()
    return {
        "healthy": healthy,
        "pool_size": stats.size,
        "connections_in_use": stats.checked_out
    }
```

### Transaction Management

```python
from netrun_db_pool import DatabasePool

async def transfer_funds(from_id: str, to_id: str, amount: float):
    async with pool.get_session() as session:
        async with session.begin():  # Start transaction
            # Debit
            await session.execute(
                text("UPDATE accounts SET balance = balance - :amount WHERE id = :id"),
                {"amount": amount, "id": from_id}
            )

            # Credit
            await session.execute(
                text("UPDATE accounts SET balance = balance + :amount WHERE id = :id"),
                {"amount": amount, "id": to_id}
            )

            # Transaction commits automatically on exit
            # Rolls back on exception
```

---

## netrun-llm v1.0.0

### Overview

Multi-provider LLM orchestration with fallback chains and three-tier cognition.

### Installation

```bash
pip install netrun-llm[all]==1.0.0
```

### Providers

#### Supported Providers

```python
from netrun_llm import Provider

Provider.ANTHROPIC   # Claude models
Provider.OPENAI      # GPT models
Provider.OLLAMA      # Local models
```

### LLM Chain

#### `LLMChain`

```python
from netrun_llm import LLMChain, Provider

chain = LLMChain(
    providers: list[Provider],
    fallback_enabled: bool = True,
    timeout: int = 30,
    max_retries: int = 3,
)

# Complete (async)
response = await chain.complete(
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    system_prompt: str = None,
    **kwargs
) -> LLMResponse

# Stream (async generator)
async for chunk in chain.stream(prompt: str, **kwargs):
    print(chunk.text, end="")
```

**Example**:
```python
from netrun_llm import LLMChain, Provider
import os

# Set API keys
os.environ["ANTHROPIC_API_KEY"] = "your-key"
os.environ["OPENAI_API_KEY"] = "your-key"

# Create chain with fallbacks
chain = LLMChain(
    providers=[
        Provider.ANTHROPIC,  # Primary: Claude
        Provider.OPENAI,     # Fallback 1: GPT-4
        Provider.OLLAMA,     # Fallback 2: Local
    ],
    fallback_enabled=True,
    timeout=30
)

# Simple completion
response = await chain.complete(
    prompt="Explain quantum computing in simple terms",
    max_tokens=500,
    temperature=0.7
)

print(response.text)
print(f"Provider used: {response.provider}")
print(f"Tokens used: {response.usage.total_tokens}")

# With system prompt
response = await chain.complete(
    prompt="What are the key differences?",
    system_prompt="You are an expert in programming languages. Be concise.",
    max_tokens=200
)

# Streaming
async for chunk in chain.stream("Write a poem about coding"):
    print(chunk.text, end="", flush=True)
```

### Provider Configuration

#### `ProviderConfig`

```python
from netrun_llm import LLMChain, Provider, ProviderConfig

chain = LLMChain(
    providers=[Provider.ANTHROPIC, Provider.OPENAI],
    provider_configs={
        Provider.ANTHROPIC: ProviderConfig(
            api_key="your-anthropic-key",
            model="claude-3-opus-20240229",
            base_url=None,  # Use default
        ),
        Provider.OPENAI: ProviderConfig(
            api_key="your-openai-key",
            model="gpt-4-turbo",
            base_url=None,
        ),
    }
)
```

### Three-Tier Cognition

#### `CognitionManager`

Route prompts to appropriate model tiers based on complexity.

```python
from netrun_llm import CognitionManager, CognitionTier

manager = CognitionManager(
    fast_provider: Provider,    # Simple tasks
    balanced_provider: Provider, # Medium tasks
    powerful_provider: Provider, # Complex tasks
)

# Auto-route based on prompt analysis
response = await manager.complete(
    prompt: str,
    tier: CognitionTier = None,  # Auto-detect if None
    **kwargs
)

# Explicitly specify tier
response = await manager.complete(
    prompt="Complex analysis...",
    tier=CognitionTier.POWERFUL
)
```

**Example**:
```python
from netrun_llm import CognitionManager, CognitionTier, Provider

manager = CognitionManager(
    fast_provider=Provider.OLLAMA,      # Llama for simple tasks
    balanced_provider=Provider.OPENAI,   # GPT-4 for medium tasks
    powerful_provider=Provider.ANTHROPIC # Claude Opus for complex
)

# Auto-routes based on prompt complexity
responses = await asyncio.gather(
    manager.complete("What's 2+2?"),                    # -> FAST (Ollama)
    manager.complete("Summarize this paragraph: ..."),  # -> BALANCED (GPT-4)
    manager.complete("Analyze this codebase and suggest architectural improvements: ..."),  # -> POWERFUL (Claude)
)

# Force specific tier
response = await manager.complete(
    "Simple question",
    tier=CognitionTier.POWERFUL  # Use Claude anyway
)
```

### Response Types

```python
from netrun_llm import LLMResponse, TokenUsage

# LLMResponse
response.text: str              # Response text
response.provider: Provider     # Provider used
response.model: str             # Model name
response.usage: TokenUsage      # Token usage
response.finish_reason: str     # stop, length, etc.
response.raw_response: dict     # Provider-specific response

# TokenUsage
usage.prompt_tokens: int
usage.completion_tokens: int
usage.total_tokens: int
```

---

## netrun-pytest-fixtures v1.0.0

### Overview

Unified pytest fixtures eliminating 71% fixture duplication across test suites.

### Installation

```bash
pip install netrun-pytest-fixtures[all]==1.0.0
```

### Setup

```python
# conftest.py
pytest_plugins = ["netrun_pytest_fixtures"]
```

### Basic Fixtures

#### `temp_dir`

Temporary directory that's cleaned up after test.

```python
def test_file_operations(temp_dir):
    test_file = temp_dir / "test.txt"
    test_file.write_text("Hello")
    assert test_file.read_text() == "Hello"
    # Directory removed after test
```

#### `random_string`

Generate random strings for test data.

```python
def test_unique_username(random_string):
    username = f"user_{random_string}"
    assert len(random_string) == 16  # Default length
```

#### `sample_uuid`

Generate UUID for test identifiers.

```python
def test_with_uuid(sample_uuid):
    user_id = str(sample_uuid)
    assert len(user_id) == 36
```

### JWT Fixtures

#### `jwt_secret`

Secure JWT secret for testing.

```python
def test_jwt_operations(jwt_secret):
    # 256-bit secure secret
    assert len(jwt_secret) >= 32
```

#### `jwt_token`

Pre-generated JWT token.

```python
def test_auth_header(jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    # Token has default claims: sub="test-user", roles=["user"]
```

#### `jwt_token_factory`

Factory for custom JWT tokens.

```python
def test_admin_access(jwt_token_factory):
    admin_token = jwt_token_factory(
        sub="admin-user",
        roles=["admin", "user"],
        custom_claims={"tenant_id": "tenant-123"}
    )
    # Use admin_token for admin-only endpoints
```

### Redis Fixtures

#### `mock_redis`

Fake Redis client for testing.

```python
@pytest.mark.asyncio
async def test_caching(mock_redis):
    await mock_redis.set("key", "value")
    result = await mock_redis.get("key")
    assert result == "value"

    await mock_redis.set("expiring", "data", ex=300)
    await mock_redis.delete("key")
    assert await mock_redis.get("key") is None
```

#### `redis_data`

Pre-populate Redis with test data.

```python
@pytest.fixture
def redis_data(mock_redis):
    async def _populate():
        await mock_redis.set("user:123", '{"name": "Alice"}')
        await mock_redis.set("config:app", '{"debug": true}')
    return _populate

@pytest.mark.asyncio
async def test_with_data(mock_redis, redis_data):
    await redis_data()
    user = await mock_redis.get("user:123")
    assert "Alice" in user
```

### Database Fixtures

#### `async_db_session`

Async SQLAlchemy session with transaction rollback.

```python
@pytest.mark.asyncio
async def test_db_operations(async_db_session):
    # All operations rolled back after test
    result = await async_db_session.execute(
        text("INSERT INTO users (name) VALUES ('Test')")
    )
    await async_db_session.commit()

    result = await async_db_session.execute(
        text("SELECT * FROM users WHERE name = 'Test'")
    )
    assert result.fetchone() is not None
```

#### `db_session_factory`

Factory for multiple sessions.

```python
@pytest.mark.asyncio
async def test_concurrent_access(db_session_factory):
    session1 = await db_session_factory()
    session2 = await db_session_factory()

    # Test concurrent operations
    await session1.execute(...)
    await session2.execute(...)
```

### HTTP Client Fixtures

#### `mock_httpx_client`

Mock HTTPX async client.

```python
@pytest.mark.asyncio
async def test_api_call(mock_httpx_client):
    from unittest.mock import AsyncMock

    mock_httpx_client.get = AsyncMock(return_value=AsyncMock(
        status_code=200,
        json=lambda: {"data": "test"}
    ))

    response = await mock_httpx_client.get("https://api.example.com/data")
    assert response.status_code == 200
```

#### `test_client`

FastAPI TestClient fixture.

```python
@pytest.fixture
def app():
    from myapp import create_app
    return create_app()

@pytest.mark.asyncio
async def test_endpoint(test_client, app):
    response = await test_client.get("/api/health")
    assert response.status_code == 200
```

### Logging Fixtures (NEW in v1.0.0)

#### `captured_logs`

Capture log messages during test.

```python
def test_logging(captured_logs):
    import logging
    logger = logging.getLogger("myapp")

    logger.info("Test message")
    logger.warning("Warning message")

    assert len(captured_logs) == 2
    assert "Test message" in captured_logs[0]
```

#### `mock_logger`

Mock logger for verifying log calls.

```python
def test_service_logging(mock_logger):
    from myapp.service import MyService

    service = MyService(logger=mock_logger)
    service.process_item("item-123")

    mock_logger.info.assert_called_with(
        "item_processed",
        item_id="item-123"
    )
```

### Environment Fixtures

#### `clean_env`

Isolated environment for testing.

```python
def test_env_vars(clean_env):
    import os

    os.environ["MY_VAR"] = "test_value"
    assert os.environ.get("MY_VAR") == "test_value"
    # MY_VAR removed after test
```

#### `temp_env`

Temporary environment variables.

```python
def test_config_loading(temp_env):
    temp_env["DATABASE_URL"] = "postgresql://test"
    temp_env["API_KEY"] = "test-key"

    from myapp.config import load_config
    config = load_config()
    assert config.database_url == "postgresql://test"
```

### Markers

```python
@pytest.mark.unit
def test_unit_function():
    """Fast unit test."""
    pass

@pytest.mark.integration
async def test_integration():
    """Integration test requiring setup."""
    pass

@pytest.mark.e2e
async def test_end_to_end():
    """Full end-to-end test."""
    pass

@pytest.mark.asyncio
async def test_async_operation():
    """Async test."""
    pass
```

---

## Full Integration Example

Complete FastAPI application using all Netrun packages:

```python
"""
Complete FastAPI Application with Netrun Service Library

Requirements:
    pip install netrun-auth[all] netrun-logging netrun-config[all]
    pip install netrun-errors netrun-cors netrun-db-pool netrun-llm
    pip install fastapi uvicorn

Run:
    uvicorn main:app --reload
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, Request, HTTPException
from pydantic import BaseModel, Field

# ============================================================================
# 1. LOGGING (Configure first)
# ============================================================================
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import CorrelationMiddleware
from netrun_logging.ecosystem import (
    bind_request_context,
    log_operation_timing,
    create_audit_logger,
)

configure_logging(
    service_name="my-api",
    environment="production",
    log_level="INFO",
)

logger = get_logger(__name__)
audit = create_audit_logger("my-api")

# ============================================================================
# 2. ERRORS
# ============================================================================
from netrun_errors import (
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
)
from netrun_errors.handlers import register_exception_handlers

# ============================================================================
# 3. CONFIGURATION
# ============================================================================
from netrun_config import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My API"
    debug: bool = False
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    class Config:
        env_prefix = "APP_"

settings = Settings()

# ============================================================================
# 4. AUTHENTICATION
# ============================================================================
from netrun_auth import JWTManager, RBACManager
from netrun_auth.models import TokenPayload

jwt_manager = JWTManager(
    secret_key=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expiry_minutes,
)

# ============================================================================
# 5. CORS
# ============================================================================
from netrun_cors import create_cors_middleware

cors = create_cors_middleware(
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)

# ============================================================================
# 6. RATE LIMITING
# ============================================================================
from netrun_ratelimit import RateLimiter

limiter = RateLimiter(
    redis_url=settings.redis_url,
    default_limit=100,
    default_window=60,
)

# ============================================================================
# 7. DATABASE
# ============================================================================
from netrun_db_pool import DatabasePool, PoolConfig
from sqlalchemy import text

pool = DatabasePool(PoolConfig(
    database_url=settings.database_url,
    pool_size=10,
    max_overflow=5,
))

# ============================================================================
# 8. LLM (Optional)
# ============================================================================
from netrun_llm import LLMChain, Provider

llm_chain = LLMChain(
    providers=[Provider.ANTHROPIC, Provider.OPENAI],
    fallback_enabled=True,
)

# ============================================================================
# APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_starting", app_name=settings.app_name)
    await pool.initialize()
    yield
    await pool.close()
    logger.info("application_stopped")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware (order matters)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(cors.__class__, **cors.__dict__)

# Exception handlers
register_exception_handlers(app)

# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_current_user(request: Request) -> Optional[TokenPayload]:
    """Extract and validate JWT."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    try:
        return jwt_manager.decode_token(token)
    except Exception:
        raise AuthenticationError(
            message="Invalid or expired token",
            error_code="AUTH_001"
        )

def require_auth(user: Optional[TokenPayload] = Depends(get_current_user)) -> TokenPayload:
    """Require authenticated user."""
    if not user:
        raise AuthenticationError(
            message="Authentication required",
            error_code="AUTH_002"
        )
    return user

async def check_rate_limit(request: Request):
    """Check rate limit."""
    client_ip = request.client.host
    if not await limiter.is_allowed(f"ip:{client_ip}"):
        raise RateLimitExceededError(
            message="Rate limit exceeded",
            retry_after=60,
            error_code="RATE_001"
        )

# ============================================================================
# MODELS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    username: str
    email: str

class AIRequest(BaseModel):
    prompt: str
    max_tokens: int = Field(default=500, le=2000)

class AIResponse(BaseModel):
    text: str
    provider: str

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await pool.health_check()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": db_healthy,
    }

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate and return JWT."""
    # Validate credentials (example)
    if request.username != "demo" or request.password != "password":
        audit.warning("login_failed", username=request.username)
        raise AuthenticationError(
            message="Invalid credentials",
            error_code="AUTH_003"
        )

    token = jwt_manager.create_token(
        sub=request.username,
        roles=["user"],
    )

    audit.info("login_success", username=request.username)
    return LoginResponse(access_token=token)

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    user: TokenPayload = Depends(require_auth),
    _: None = Depends(check_rate_limit),
):
    """Get current user info."""
    bind_request_context(method="GET", path="/users/me", user_id=user.sub)

    with log_operation_timing("fetch_user", resource_type="user"):
        async with pool.get_session() as session:
            result = await session.execute(
                text("SELECT id, username, email FROM users WHERE id = :id"),
                {"id": user.sub}
            )
            row = result.fetchone()

    if not row:
        raise NotFoundError(
            message="User not found",
            resource_type="user",
            resource_id=user.sub,
        )

    return UserResponse(id=row.id, username=row.username, email=row.email)

@app.post("/ai/complete", response_model=AIResponse)
async def ai_completion(
    request: AIRequest,
    user: TokenPayload = Depends(require_auth),
    _: None = Depends(check_rate_limit),
):
    """Generate AI completion."""
    bind_request_context(method="POST", path="/ai/complete", user_id=user.sub)

    with log_operation_timing("llm_completion"):
        response = await llm_chain.complete(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
        )

    audit.info("ai_completion", user_id=user.sub, tokens=response.usage.total_tokens)

    return AIResponse(
        text=response.text,
        provider=response.provider.value,
    )

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Migration Guide

### Current Versions (December 2025)

All 10 packages are now available on PyPI with the following versions:

| Package | Version | Status |
|---------|---------|--------|
| netrun-logging | 1.1.0 | Published |
| netrun-errors | 1.1.0 | Published |
| netrun-auth | 1.1.0 | Published |
| netrun-config | 1.1.0 | Published |
| netrun-cors | 1.1.0 | Published |
| netrun-db-pool | 1.0.0 | Published |
| netrun-llm | 1.0.0 | Published |
| netrun-env | 1.0.0 | Published |
| netrun-pytest-fixtures | 1.0.0 | Published |
| netrun-ratelimit | 1.0.0 | Published |

### Key Features by Package

#### netrun-logging v1.1.0

Ecosystem module with helper functions:

```python
from netrun_logging.ecosystem import (
    bind_error_context,
    bind_request_context,
    log_operation_timing,
    log_timing,
    create_audit_logger,
)
```

#### netrun-errors v1.1.0

Additional exception types:

```python
from netrun_errors import (
    RateLimitExceededError,
    BadGatewayError,
    GatewayTimeoutError,
    ExternalServiceError,
)
```

Automatic correlation ID from netrun-logging:

```python
# When netrun-logging is installed, errors auto-capture correlation ID
from netrun_logging import set_correlation_id
from netrun_errors import ValidationError

set_correlation_id("request-123")
error = ValidationError(message="Test")
print(error.correlation_id)  # "request-123"
```

#### netrun-auth v1.1.0

Enhanced logging integration:

```python
# Install with logging extra for full integration
pip install netrun-auth[logging]

# All auth operations now logged with correlation IDs
```

#### netrun-config v1.1.0

Error standardization with netrun-errors:

```python
# Configuration errors now use netrun-errors types
from netrun_errors import ConfigurationError

# Thrown automatically on configuration failures
```

### Adding Logging Integration

To enable enhanced logging for any package:

```bash
pip install netrun-{package}[logging]
```

Packages with `[logging]` extra:
- netrun-errors[logging]
- netrun-auth[logging]
- netrun-config[logging]
- netrun-env[logging]

---

## Support

- **GitHub Issues**: https://github.com/netrun-systems/netrun-service-library/issues
- **Documentation**: https://docs.netrunsystems.com/service-library
- **Email**: engineering@netrunsystems.com

---

*Netrun Service Library - Technical Reference*
*Version 1.2.0 | December 15, 2025*
*Netrun Systems*
