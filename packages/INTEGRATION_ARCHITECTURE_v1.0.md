# Netrun PyPI Package Integration Architecture v1.0

**Date**: December 5, 2025
**Author**: Netrun Systems
**Status**: Implementation Plan for Full Ecosystem Integration
**SDLC Compliance**: v2.3.1

---

## Executive Summary

This document defines the unified integration architecture for all 10 Netrun PyPI packages. The goal is to create a cohesive ecosystem where packages leverage each other's capabilities, eliminating duplication and maximizing value.

---

## Package Dependency Hierarchy

```
                    ┌─────────────────┐
                    │  netrun-errors  │  ◄── Foundation (Level 0)
                    │    (v1.1.0)     │      - Base exception classes
                    └────────┬────────┘      - Correlation ID generation
                             │               - HTTP status mapping
                             ▼
                    ┌─────────────────┐
                    │ netrun-logging  │  ◄── Core Infrastructure (Level 1)
                    │    (v1.2.0)     │      - Structured logging
                    └────────┬────────┘      - Uses netrun-errors for log context
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │netrun-env  │  │netrun-config│ │netrun-auth │  ◄── Configuration Layer (Level 2)
     │  (v1.1.0)  │  │  (v1.2.0)   │ │  (v1.2.0)  │
     └─────┬──────┘  └──────┬─────┘  └─────┬──────┘
           │                │               │
           └────────────────┼───────────────┘
                            ▼
           ┌────────────────────────────────┐
           │      Application Packages       │  ◄── Application Layer (Level 3)
           │                                 │
           │  ┌──────────┐  ┌──────────┐    │
           │  │netrun-   │  │netrun-   │    │
           │  │  cors    │  │ db-pool  │    │
           │  │ (v1.1.0) │  │ (v1.1.0) │    │
           │  └──────────┘  └──────────┘    │
           │                                 │
           │  ┌──────────┐  ┌──────────┐    │
           │  │netrun-   │  │netrun-   │    │
           │  │   llm    │  │ pytest-  │    │
           │  │ (v1.1.0) │  │ fixtures │    │
           │  └──────────┘  │ (v1.1.0) │    │
           │                └──────────┘    │
           └────────────────────────────────┘
```

---

## Integration Contracts

### 1. Exception Handling Contract

**All packages MUST use netrun-errors for exceptions:**

```python
# Standard import pattern
from netrun_errors import (
    NetrunException,           # Base class for all Netrun exceptions
    AuthenticationError,       # 401 errors
    AuthorizationError,        # 403 errors
    ValidationError,           # 400 errors
    ResourceNotFoundError,     # 404 errors
    ServiceUnavailableError,   # 503 errors
    RateLimitExceededError,    # 429 errors (NEW in v1.1.0)
)

# Custom exceptions inherit from NetrunException
class CORSValidationError(NetrunException):
    """CORS configuration validation failed."""
    status_code = 400
    error_code = "CORS_VALIDATION_ERROR"
```

**Required Exception Fields:**
- `status_code: int` - HTTP status code
- `error_code: str` - Machine-readable error code (SCREAMING_SNAKE_CASE)
- `message: str` - Human-readable message
- `details: Optional[Dict]` - Additional context
- `correlation_id: str` - Auto-generated for tracing

### 2. Logging Contract

**All packages MUST use netrun-logging:**

```python
# Standard import pattern
from netrun_logging import get_logger, bind_context

logger = get_logger(__name__)

# Structured logging (key=value style)
logger.info("operation_completed",
    operation="cors_validation",
    origin="https://example.com",
    result="allowed",
    duration_ms=1.5
)

# With context binding
bind_context(tenant_id="acme", user_id="user123")
logger.info("tenant_operation")  # Automatically includes tenant_id, user_id

# Error logging with exception
try:
    # operation
except Exception as e:
    logger.exception("operation_failed", error=str(e))
```

**Logging Standards:**
- Use `get_logger(__name__)` in every module
- Use key=value structured logging (no f-strings)
- Include `operation`, `result`, `duration_ms` for operations
- Use `correlation_id` from request context
- Sensitive fields auto-sanitized (password, token, secret, etc.)

### 3. Configuration Contract

**All packages MUST integrate with netrun-config:**

```python
# Standard pattern for package-specific config
from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator

class CORSConfig(BaseConfig):
    """CORS-specific configuration extending base settings."""

    # Inherit: app_name, app_environment, log_level, etc.

    # Package-specific fields
    cors_preset: str = Field(
        default="development",
        env="CORS_PRESET",
        description="CORS preset: development, staging, production, oauth"
    )
    cors_max_age: int = Field(
        default=3600,
        env="CORS_MAX_AGE",
        ge=0,
        le=86400
    )

    @field_validator("cors_preset")
    @classmethod
    def validate_preset(cls, v: str) -> str:
        valid = {"development", "staging", "production", "oauth", "custom"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid preset: {v}")
        return v.lower()

# Usage
settings = get_settings(CORSConfig)
if settings.is_production:
    # Production behavior
```

**Configuration Standards:**
- Extend `BaseConfig` for consistent base fields
- Use `Field()` with `env=` for environment variable binding
- Use package-specific env prefix (e.g., `CORS_`, `DB_`, `LLM_`)
- Provide sensible defaults for development
- Validate with `@field_validator` decorators

---

## Package-Specific Integration Plans

### netrun-errors (v1.1.0) - Foundation

**Changes Required:**
1. Add `RateLimitExceededError` (HTTP 429)
2. Add `BadGatewayError` (HTTP 502)
3. Add `GatewayTimeoutError` (HTTP 504)
4. Add netrun-logging integration for exception logging
5. Add correlation ID propagation from netrun-logging context

**New Dependencies:**
```toml
dependencies = [
    "fastapi>=0.115.0",
    "starlette>=0.41.0",
    "netrun-logging>=1.1.0",  # NEW
]
```

**Implementation:**
```python
# netrun_errors/base.py
from netrun_logging import get_logger, get_correlation_id

logger = get_logger(__name__)

class NetrunException(Exception):
    def __init__(self, message: str, details: dict = None):
        self.correlation_id = get_correlation_id() or self._generate_correlation_id()
        logger.warning("exception_raised",
            error_code=self.error_code,
            message=message,
            correlation_id=self.correlation_id
        )
        super().__init__(message)
```

---

### netrun-logging (v1.2.0) - Core Infrastructure

**Changes Required:**
1. Add error context injection from netrun-errors
2. Add package-aware logging (auto-detect calling package)
3. Add performance metrics logging helpers
4. Export correlation ID utilities for all packages

**New Features:**
```python
# New helper for timing operations
from netrun_logging import log_operation

@log_operation("database_query")
async def fetch_user(user_id: str):
    # Automatically logs: operation_started, operation_completed with duration
    return await db.get_user(user_id)

# New helper for exception context
from netrun_logging import log_exception

try:
    operation()
except NetrunException as e:
    log_exception(e)  # Logs with full context from netrun-errors
```

---

### netrun-config (v1.2.0) - Configuration Layer

**Changes Required:**
1. Integrate netrun-logging for config load logging
2. Integrate netrun-errors for validation errors
3. Add config reload event hooks

**New Dependencies:**
```toml
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "netrun-logging>=1.1.0",  # NEW
    "netrun-errors>=1.1.0",   # NEW
]

[project.optional-dependencies]
azure = ["azure-identity>=1.12.0", "azure-keyvault-secrets>=4.7.0"]
```

**Implementation:**
```python
# netrun_config/base.py
from netrun_logging import get_logger
from netrun_errors import ValidationError

logger = get_logger(__name__)

class BaseConfig(BaseSettings):
    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)
            logger.info("config_loaded",
                app_name=self.app_name,
                environment=self.app_environment
            )
        except ValidationError as e:
            logger.error("config_validation_failed", error=str(e))
            raise
```

---

### netrun-auth (v1.2.0) - Authentication Layer

**Changes Required:**
1. Replace internal exceptions with netrun-errors
2. Replace stdlib logging with netrun-logging
3. Add audit logging hooks

**New Dependencies:**
```toml
dependencies = [
    # existing deps...
    "netrun-logging>=1.1.0",  # NEW
    "netrun-errors>=1.1.0",   # NEW
]
```

**Implementation:**
```python
# netrun_auth/exceptions.py - DEPRECATE internal exceptions
# Import from netrun-errors instead

from netrun_errors import (
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
    RateLimitExceededError,
    PermissionDeniedError,
)

# Re-export for backward compatibility
__all__ = [
    "AuthenticationError",
    "TokenExpiredError",
    # etc.
]
```

---

### netrun-env (v1.1.0) - Environment Validation

**Changes Required:**
1. Remove unused pydantic dependency
2. Add netrun-logging integration
3. Add netrun-errors for structured validation errors
4. Document complementary role with netrun-config

**New Dependencies:**
```toml
dependencies = [
    "click>=8.0.0",
    "python-dotenv>=1.0.0",
    "netrun-logging>=1.1.0",  # NEW
    "netrun-errors>=1.1.0",   # NEW
]
# REMOVED: pydantic (not used)
```

**Implementation:**
```python
# netrun_env/validator.py
from netrun_logging import get_logger
from netrun_errors import ValidationError

logger = get_logger(__name__)

class EnvValidator:
    def validate(self, env_file: Path) -> ValidationResult:
        logger.info("validation_started", env_file=str(env_file))

        errors = []
        # validation logic...

        if errors:
            logger.error("validation_failed",
                error_count=len(errors),
                first_error=errors[0]
            )
            raise ValidationError(
                message="Environment validation failed",
                details={"errors": errors}
            )

        logger.info("validation_passed", variable_count=len(variables))
        return ValidationResult(valid=True)
```

---

### netrun-cors (v1.1.0) - CORS Middleware

**Changes Required:**
1. Add netrun-logging for CORS decision audit trail
2. Add netrun-errors for structured error responses
3. Add netrun-config integration for environment-based presets
4. Add regex pattern support for wildcard origins

**New Dependencies:**
```toml
dependencies = [
    "fastapi>=0.109.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "starlette>=0.27.0",
    "netrun-logging>=1.1.0",  # NEW
    "netrun-errors>=1.1.0",   # NEW
    "netrun-config>=1.1.0",   # NEW
]
```

**Implementation:**
```python
# netrun_cors/middleware.py
from netrun_logging import get_logger
from netrun_errors import ValidationError
from netrun_config import get_settings

logger = get_logger(__name__)

class CORSMiddleware:
    def __init__(self, app, config: CORSConfig = None):
        self.config = config or get_settings(CORSConfig)
        self.logger = get_logger(__name__)

    async def __call__(self, scope, receive, send):
        origin = self._get_origin(scope)
        allowed = self._is_origin_allowed(origin)

        self.logger.info("cors_decision",
            origin=origin,
            allowed=allowed,
            preset=self.config.cors_preset
        )

        if not allowed:
            self.logger.warning("cors_blocked",
                origin=origin,
                reason="not_in_allowed_list"
            )
```

---

### netrun-db-pool (v1.1.0) - Database Pooling

**Changes Required:**
1. Add netrun-logging for pool metrics and query logging
2. Add netrun-errors for database exceptions
3. Add netrun-config integration for pool configuration
4. Add netrun-auth integration for tenant context
5. Add credential redaction in logs

**New Dependencies:**
```toml
dependencies = [
    "sqlalchemy[asyncio]>=2.0.0,<3.0.0",
    "asyncpg>=0.29.0,<1.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",
    "netrun-logging>=1.1.0",  # NEW
    "netrun-errors>=1.1.0",   # NEW
    "netrun-config>=1.1.0",   # NEW
]

[project.optional-dependencies]
fastapi = ["fastapi>=0.110.0", "netrun-auth>=1.1.0"]  # NEW: auth integration
```

**Implementation:**
```python
# netrun_db_pool/pool.py
from netrun_logging import get_logger
from netrun_errors import ServiceUnavailableError, DatabaseError
from netrun_config import BaseConfig

logger = get_logger(__name__)

class PoolConfig(BaseConfig):
    """Database pool configuration extending base settings."""
    # Inherits database_url, pool_size, etc. from BaseConfig
    pass

class AsyncDatabasePool:
    async def initialize(self):
        try:
            logger.info("pool_initializing",
                pool_size=self.config.pool_size,
                database=self._redact_url(self.config.database_url)
            )
            # initialization...
            logger.info("pool_initialized")
        except Exception as e:
            logger.error("pool_initialization_failed", error=str(e))
            raise ServiceUnavailableError(
                message="Database pool initialization failed",
                details={"error": str(e)}
            )

    def _redact_url(self, url: str) -> str:
        """Redact password from database URL for logging."""
        # postgresql://user:password@host/db -> postgresql://user:***@host/db
        import re
        return re.sub(r':([^:@]+)@', ':***@', url)
```

---

### netrun-llm (v1.1.0) - LLM Integration

**Changes Required:**
1. Add Azure OpenAI adapter (HIGH PRIORITY)
2. Add netrun-logging for provider metrics
3. Add netrun-errors for LLM exceptions
4. Add netrun-config for provider configuration
5. Implement true async clients (not sync-wrapped)

**New Dependencies:**
```toml
dependencies = [
    "requests>=2.28.0",
    "netrun-logging>=1.1.0",  # NEW
    "netrun-errors>=1.1.0",   # NEW
    "netrun-config>=1.1.0",   # NEW
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.25.0"]
openai = ["openai>=1.0.0"]
azure = ["openai>=1.0.0"]  # Azure OpenAI uses same SDK
all = ["anthropic>=0.25.0", "openai>=1.0.0"]
```

**Implementation:**
```python
# netrun_llm/config.py
from netrun_config import BaseConfig, Field

class LLMConfig(BaseConfig):
    """LLM configuration extending base settings."""

    # Provider API keys (from Key Vault in production)
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")

    # Default provider chain
    llm_provider_chain: str = Field(
        default="claude,openai,ollama",
        env="LLM_PROVIDER_CHAIN"
    )

# netrun_llm/adapters/azure_openai.py (NEW)
from netrun_logging import get_logger
from netrun_errors import ServiceUnavailableError

logger = get_logger(__name__)

class AzureOpenAIAdapter(BaseLLMAdapter):
    """Azure OpenAI adapter for enterprise deployments."""

    async def execute_async(self, prompt: str, context: dict) -> LLMResponse:
        logger.info("azure_openai_request",
            model=self.model,
            prompt_length=len(prompt)
        )
        try:
            # Azure OpenAI specific implementation
            response = await self.client.chat.completions.create(...)
            logger.info("azure_openai_response",
                model=self.model,
                tokens_used=response.usage.total_tokens,
                duration_ms=duration
            )
            return response
        except Exception as e:
            logger.error("azure_openai_error", error=str(e))
            raise ServiceUnavailableError(
                message="Azure OpenAI request failed",
                details={"error": str(e)}
            )
```

---

### netrun-pytest-fixtures (v1.1.0) - Test Fixtures

**Changes Required:**
1. Add fixtures for all netrun packages
2. Add netrun-logging test configuration fixtures
3. Add netrun-config mock settings fixtures
4. Add netrun-auth token generation fixtures

**New Dependencies:**
```toml
dependencies = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "cryptography>=41.0.0",
]

[project.optional-dependencies]
netrun = [
    "netrun-logging>=1.1.0",
    "netrun-errors>=1.1.0",
    "netrun-config>=1.1.0",
    "netrun-auth>=1.1.0",
]
```

**New Fixtures:**
```python
# netrun_pytest_fixtures/netrun_integration.py

@pytest.fixture
def netrun_logging_config():
    """Configure netrun-logging for tests."""
    from netrun_logging import configure_logging
    configure_logging(
        app_name="test",
        environment="testing",
        enable_json=False,  # Readable console output
        log_level="DEBUG"
    )
    yield
    # Cleanup handled by reset_logging fixture

@pytest.fixture
def mock_netrun_config(monkeypatch):
    """Mock netrun-config settings for testing."""
    from netrun_config import BaseConfig

    class TestConfig(BaseConfig):
        app_environment: str = "testing"
        app_debug: bool = True

    return TestConfig()

@pytest.fixture
def auth_token_factory(rsa_key_pair):
    """Factory for generating test JWT tokens using netrun-auth."""
    try:
        from netrun_auth import JWTManager, AuthConfig

        private_key, public_key = rsa_key_pair
        config = AuthConfig(
            jwt_private_key=private_key,
            jwt_public_key=public_key
        )
        manager = JWTManager(config)

        def create_token(user_id: str, roles: list = None, **claims):
            return manager.create_access_token(
                user_id=user_id,
                roles=roles or ["user"],
                **claims
            )

        return create_token
    except ImportError:
        pytest.skip("netrun-auth not installed")
```

---

## Version Alignment

All packages will be bumped to align versions:

| Package | Current | Target | Changes |
|---------|---------|--------|---------|
| netrun-errors | 1.0.0 | **1.1.0** | +logging, +new exceptions |
| netrun-logging | 1.1.0 | **1.2.0** | +error context, +helpers |
| netrun-config | 1.1.0 | **1.2.0** | +logging, +errors |
| netrun-auth | 1.1.0 | **1.2.0** | +logging, +errors, deprecate internal exceptions |
| netrun-env | 1.0.0 | **1.1.0** | +logging, +errors, -pydantic |
| netrun-cors | 1.0.0 | **1.1.0** | +logging, +errors, +config, +regex |
| netrun-db-pool | 1.0.0 | **1.1.0** | +logging, +errors, +config, +auth |
| netrun-llm | 1.0.0 | **1.1.0** | +azure, +logging, +errors, +config |
| netrun-pytest-fixtures | 1.0.0 | **1.1.0** | +netrun integration fixtures |

---

## Implementation Timeline

### Week 1: Foundation (netrun-errors, netrun-logging)
- Day 1-2: Update netrun-errors v1.1.0
  - Add new exception classes (429, 502, 504)
  - Add logging integration
  - Update tests
- Day 3-4: Update netrun-logging v1.2.0
  - Add error context helpers
  - Add operation timing decorator
  - Update tests
- Day 5: Cross-test and publish both

### Week 2: Configuration Layer (netrun-config, netrun-auth, netrun-env)
- Day 1-2: Update netrun-config v1.2.0
  - Add logging/errors integration
  - Update tests
- Day 3-4: Update netrun-auth v1.2.0
  - Replace internal exceptions with netrun-errors
  - Replace logging with netrun-logging
  - Update tests
- Day 5: Update netrun-env v1.1.0
  - Remove pydantic, add logging/errors
  - Update tests

### Week 3: Application Layer (netrun-cors, netrun-db-pool)
- Day 1-2: Update netrun-cors v1.1.0
  - Full integration (logging, errors, config)
  - Add regex pattern support
  - Update tests
- Day 3-5: Update netrun-db-pool v1.1.0
  - Full integration (logging, errors, config, auth)
  - Add credential redaction
  - Update tests

### Week 4: Advanced Packages (netrun-llm, netrun-pytest-fixtures)
- Day 1-3: Update netrun-llm v1.1.0
  - Add Azure OpenAI adapter
  - Full integration (logging, errors, config)
  - Update tests
- Day 4-5: Update netrun-pytest-fixtures v1.1.0
  - Add netrun integration fixtures
  - Update tests

### Week 5: Documentation and Release
- Day 1-2: Create unified documentation
- Day 3: Final cross-package testing
- Day 4-5: Coordinated PyPI release

---

## Success Metrics

1. **All 10 packages use netrun-errors** for exceptions
2. **All 10 packages use netrun-logging** for structured logging
3. **All application packages use netrun-config** for configuration
4. **Test coverage ≥ 90%** for all packages
5. **Zero circular dependencies** between packages
6. **Coordinated release** with aligned version numbers
7. **Unified documentation** with integration examples

---

## Appendix: Import Patterns Cheat Sheet

```python
# Standard imports for any Netrun package

# Logging (always)
from netrun_logging import get_logger, bind_context
logger = get_logger(__name__)

# Errors (when raising exceptions)
from netrun_errors import (
    NetrunException,
    ValidationError,
    AuthenticationError,
    ServiceUnavailableError,
)

# Config (when needing settings)
from netrun_config import BaseConfig, get_settings, Field

# Auth (when needing authentication)
from netrun_auth import (
    JWTManager, get_jwt_manager,
    AuthenticationError, TokenExpiredError,
)
```

---

*Document Version: 1.0*
*Last Updated: December 5, 2025*
*Owner: Netrun Systems Engineering*
