# Netrun Service Library - Integration Guide

## Overview

The Netrun Service Library provides 10 interconnected Python packages designed for enterprise applications. All packages follow a **soft dependency pattern** that enables seamless integration without mandatory dependencies.

## Package Versions (December 2025)

| Package | Version | Core Purpose |
|---------|---------|--------------|
| netrun-logging | 1.2.0 | Structured logging with Azure App Insights |
| netrun-errors | 1.1.0 | Standardized exception hierarchy |
| netrun-auth | 1.2.0 | JWT + RBAC + MFA authentication |
| netrun-config | 1.2.0 | TTL-cached configuration with Key Vault |
| netrun-cors | 1.1.0 | OWASP-compliant CORS middleware |
| netrun-db-pool | 1.1.0 | Async SQLAlchemy connection pooling |
| netrun-llm | 1.1.0 | Multi-provider LLM orchestration |
| netrun-env | 1.1.0 | Schema-based env variable validation |
| netrun-pytest-fixtures | 1.1.0 | Unified testing fixtures |
| netrun-ratelimit | 1.0.0 | Token bucket rate limiting |

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  netrun-auth    netrun-config    netrun-cors    netrun-llm      │
│       │              │               │              │            │
│       └──────────────┴───────────────┴──────────────┘            │
│                          │                                       │
├──────────────────────────┴───────────────────────────────────────┤
│              Foundation Layer (Optional Dependencies)            │
│  ┌─────────────────────┐  ┌─────────────────────────────────────┐│
│  │   netrun-logging    │  │         netrun-errors               ││
│  │   (Structured Log)  │  │    (Exception Hierarchy)            ││
│  └─────────────────────┘  └─────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                    Testing Layer                                 │
│              netrun-pytest-fixtures (all integrations)           │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Minimal Installation (Single Package)

```bash
pip install netrun-logging
```

### Full Integration

```bash
pip install netrun-logging netrun-errors netrun-auth netrun-config
pip install netrun-auth[all]  # Includes Azure, OAuth, FastAPI, Casbin
```

### With Optional Logging Integration

```bash
# Any package with [logging] extra
pip install netrun-errors[logging]
pip install netrun-auth[logging]
pip install netrun-config[logging]
pip install netrun-env[logging]
```

## Soft Dependency Pattern

All packages use a consistent soft dependency pattern for optional integration:

```python
# Pattern used across all Netrun packages
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

This pattern ensures:
- **Zero mandatory cross-dependencies**
- **Graceful degradation** to stdlib logging
- **Enhanced functionality** when netrun-logging is installed

## Package Integration Examples

### 1. Basic Logging Integration

```python
from netrun_logging import get_logger, configure_logging

# Configure once at startup
configure_logging(
    service_name="my-service",
    environment="production",
    azure_connection_string="InstrumentationKey=..."
)

# Use throughout application
logger = get_logger(__name__)
logger.info("request_processed", user_id="123", latency_ms=45)
```

### 2. Error Handling with Correlation IDs

```python
from netrun_errors import ValidationError, NotFoundError
from netrun_logging import get_correlation_id, bind_context

# Errors automatically capture correlation IDs from netrun-logging
try:
    raise ValidationError(
        message="Invalid email format",
        field="email",
        error_code="VALIDATION_001"
    )
except ValidationError as e:
    # e.correlation_id automatically populated if netrun-logging active
    print(f"Error {e.error_code}: {e.message} (Correlation: {e.correlation_id})")
```

### 3. Auth with Logging Integration

```python
from netrun_auth import JWTManager, RBACManager
from netrun_auth.middleware import AuthMiddleware
from fastapi import FastAPI

app = FastAPI()

# JWT operations are automatically logged when netrun-logging installed
jwt_manager = JWTManager(
    secret_key="your-secret",
    algorithm="HS256"
)

# All auth events logged with correlation IDs
app.add_middleware(AuthMiddleware, jwt_manager=jwt_manager)
```

### 4. Config with Error Standardization

```python
from netrun_config import BaseSettings
from netrun_errors import ConfigurationError

class AppSettings(BaseSettings):
    database_url: str
    redis_url: str

    class Config:
        env_prefix = "APP_"

try:
    settings = AppSettings()
except Exception as e:
    # Wrapped in ConfigurationError with proper error codes
    raise ConfigurationError(
        message=f"Failed to load configuration: {e}",
        error_code="CONFIG_001"
    )
```

### 5. Database Pool with Full Integration

```python
from netrun_db_pool import DatabasePool, PoolConfig
from netrun_logging import get_logger

config = PoolConfig(
    database_url="postgresql+asyncpg://...",
    pool_size=10,
    max_overflow=5
)

# Pool operations logged automatically
pool = DatabasePool(config)
await pool.initialize()

# All queries logged with timing
async with pool.get_session() as session:
    result = await session.execute(query)
```

### 6. LLM Chain with Fallback Logging

```python
from netrun_llm import LLMChain, Provider

chain = LLMChain(
    providers=[
        Provider.ANTHROPIC,
        Provider.OPENAI,
        Provider.OLLAMA
    ],
    fallback_enabled=True
)

# Provider switches and fallbacks are logged
response = await chain.complete(
    prompt="Explain quantum computing",
    max_tokens=500
)
```

### 7. Testing with Unified Fixtures

```python
# conftest.py
pytest_plugins = ["netrun_pytest_fixtures"]

# test_api.py
async def test_authenticated_request(
    test_client,           # From netrun-pytest-fixtures
    jwt_token,             # JWT with configurable claims
    mock_redis,            # Fake Redis client
    async_db_session,      # SQLAlchemy async session
    captured_logs          # Log capture fixture
):
    response = await test_client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert response.status_code == 200

    # Verify logging occurred
    assert any("request_processed" in log for log in captured_logs)
```

## Ecosystem Helper Functions

The `netrun_logging.ecosystem` module provides integration helpers:

```python
from netrun_logging.ecosystem import (
    bind_error_context,
    bind_request_context,
    bind_operation_context,
    log_operation_timing,
    log_timing,
    create_audit_logger
)

# Bind error context for correlation
bind_error_context(
    error_code="AUTH_001",
    status_code=401,
    correlation_id="abc-123"
)

# Bind request context
bind_request_context(
    method="POST",
    path="/api/users",
    user_id="user-456",
    tenant_id="tenant-789"
)

# Time an operation with automatic logging
with log_operation_timing("database_query", resource_type="users"):
    result = await db.execute(query)

# Decorator for function timing
@log_timing(operation="process_payment", level="info")
async def process_payment(amount: float):
    ...

# Audit logging for compliance
audit = create_audit_logger("payment-service", actor_id="admin-1")
audit.info("payment_processed", amount=100.00, currency="USD")
```

## FastAPI Integration Example

```python
from fastapi import FastAPI, Request
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import CorrelationMiddleware
from netrun_errors.handlers import register_exception_handlers
from netrun_cors import create_cors_middleware
from netrun_auth.middleware import AuthMiddleware

app = FastAPI()

# 1. Configure logging first
configure_logging(service_name="api-service", environment="production")
logger = get_logger(__name__)

# 2. Add correlation ID middleware
app.add_middleware(CorrelationMiddleware)

# 3. Add CORS with logging integration
app.add_middleware(create_cors_middleware(
    allow_origins=["https://app.example.com"],
    allow_credentials=True
))

# 4. Add auth middleware
app.add_middleware(AuthMiddleware, jwt_manager=jwt_manager)

# 5. Register error handlers (logs to netrun-logging)
register_exception_handlers(app)

@app.get("/api/health")
async def health_check(request: Request):
    logger.info("health_check", path=request.url.path)
    return {"status": "healthy"}
```

## Configuration Reference

### netrun-logging

```python
from netrun_logging import configure_logging

configure_logging(
    service_name="my-service",
    environment="production",          # dev, staging, production
    log_level="INFO",                   # DEBUG, INFO, WARNING, ERROR
    azure_connection_string="...",      # Optional Azure App Insights
    json_format=True,                   # Structured JSON output
    include_timestamps=True,
    include_caller_info=True
)
```

### netrun-auth

```python
from netrun_auth import AuthConfig

config = AuthConfig(
    jwt_secret="your-secret-key",
    jwt_algorithm="HS256",
    jwt_expiry_minutes=60,
    rbac_enabled=True,
    mfa_enabled=False,
    casbin_model_path="./rbac_model.conf"
)
```

### netrun-config

```python
from netrun_config import BaseSettings, KeyVaultConfig

class Settings(BaseSettings):
    # Environment variables with validation
    database_url: str
    redis_url: str

    # Key Vault integration
    key_vault: KeyVaultConfig = KeyVaultConfig(
        vault_url="https://my-vault.vault.azure.net",
        cache_ttl_seconds=300
    )
```

## Migration Guide

### From v1.0.x to v1.1.x/v1.2.x

1. **No breaking changes** - All upgrades are backwards compatible
2. **Optional logging** - Install `[logging]` extra for enhanced logging
3. **New ecosystem module** - Use `netrun_logging.ecosystem` for integration helpers

```bash
# Upgrade all packages
pip install --upgrade netrun-logging netrun-errors netrun-auth netrun-config

# Add logging integration
pip install netrun-auth[logging] netrun-config[logging]
```

## Best Practices

1. **Always configure logging at startup** before other packages
2. **Use correlation IDs** - They propagate automatically across packages
3. **Install [logging] extras** for full structured logging
4. **Use ecosystem helpers** for consistent context binding
5. **Use pytest fixtures** for comprehensive testing

## Support

- GitHub Issues: https://github.com/netrunsystems/netrun-service-library/issues
- Documentation: https://docs.netrunsystems.com/service-library
- Email: engineering@netrunsystems.com

---

*Netrun Service Library - Enterprise Python Packages*
*Version: 1.2.0 | December 2025*
