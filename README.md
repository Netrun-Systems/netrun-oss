# Netrun Open Source Libraries

Open source Python libraries from [Netrun Systems](https://netrunsystems.com) - 18 production-tested packages for FastAPI applications including authentication, configuration, logging, CORS, rate limiting, database pooling, LLM orchestration, RBAC, caching, resilience patterns, validation, WebSocket management, and testing fixtures.

> **v2.0.0 Release** - Now with PEP 420 namespace packages! Use `from netrun.auth import ...` instead of `from netrun_auth import ...`. Old imports still work but are deprecated.

## Packages

| Package | Version | PyPI | Description |
|---------|---------|------|-------------|
| **netrun-core** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-core/) | Root namespace package for `netrun.*` imports |
| **netrun-auth** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-auth/) | Unified authentication - JWT, OAuth2, Azure AD, Casbin RBAC |
| **netrun-cache** | 1.0.0 | [PyPI](https://pypi.org/project/netrun-cache/) | Redis and in-memory caching with decorators and TTL |
| **netrun-config** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-config/) | Configuration management with Azure Key Vault, TTL caching |
| **netrun-cors** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-cors/) | Enterprise CORS middleware presets for FastAPI |
| **netrun-db-pool** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-db-pool/) | Async database connection pooling with tenant isolation |
| **netrun-dogfood** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-dogfood/) | Internal integration testing MCP server |
| **netrun-env** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-env/) | Schema-based environment variable validator |
| **netrun-errors** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-errors/) | Unified error handling for FastAPI applications |
| **netrun-llm** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-llm/) | Multi-provider LLM orchestration with policies & telemetry |
| **netrun-logging** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-logging/) | Structured logging with Azure App Insights integration |
| **netrun-oauth** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-oauth/) | OAuth 2.0 adapters for 12+ providers |
| **netrun-pytest-fixtures** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-pytest-fixtures/) | Unified pytest fixtures - 71% duplication elimination |
| **netrun-ratelimit** | 2.0.0 | [PyPI](https://pypi.org/project/netrun-ratelimit/) | Distributed rate limiting with token bucket & Redis |
| **netrun-rbac** | 3.0.0 | [PyPI](https://pypi.org/project/netrun-rbac/) | Multi-tenant RBAC with hierarchical teams, resource sharing, and isolation testing |
| **netrun-resilience** | 1.0.0 | [PyPI](https://pypi.org/project/netrun-resilience/) | Resilience patterns: retry, circuit breaker, timeout, bulkhead |
| **netrun-validation** | 1.0.0 | [PyPI](https://pypi.org/project/netrun-validation/) | Pydantic validators for network, security, datetime, custom types |
| **netrun-websocket** | 1.0.0 | [PyPI](https://pypi.org/project/netrun-websocket/) | Production WebSocket management with Redis sessions and JWT |

## Installation

```bash
# Core namespace package (required for netrun.* imports)
pip install netrun-core

# Individual packages
pip install netrun-auth netrun-config netrun-logging netrun-llm

# New infrastructure packages
pip install netrun-cache netrun-resilience netrun-validation netrun-websocket

# With optional dependencies
pip install netrun-auth[all] netrun-llm[all] netrun-cache[redis] netrun-websocket[all]

# Full suite (18 packages)
pip install netrun-core netrun-auth netrun-cache netrun-config netrun-cors \
    netrun-db-pool netrun-dogfood netrun-env netrun-errors netrun-llm \
    netrun-logging netrun-oauth netrun-pytest-fixtures netrun-ratelimit \
    netrun-rbac netrun-resilience netrun-validation netrun-websocket
```

## Quick Start (v2.0.0 Namespace)

```python
# New v2.0.0 imports (recommended)
from netrun.auth import JWTHandler, require_permission
from netrun.config import SecretCache
from netrun.logging import get_logger
from netrun.llm import LLMFallbackChain
from netrun.rbac import TenantContext

# Old imports still work (deprecated, will be removed in v3.0.0)
from netrun_auth import JWTHandler  # Still works
```

## What's New in v2.0.0

### PEP 420 Namespace Packages
All packages now use the unified `netrun.*` namespace for cleaner imports.

### LLM Policy Enforcement (netrun-llm)
Control LLM usage with per-tenant budgets, rate limits, and model restrictions:

```python
from netrun.llm import TenantPolicy, PolicyEnforcer, CostTier

policy = TenantPolicy(
    tenant_id="acme-corp",
    monthly_budget_usd=100.0,
    daily_budget_usd=10.0,
    provider_policies={
        "openai": ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini", "gpt-4o"],
            cost_tier_limit=CostTier.MEDIUM,
            rate_limit_rpm=60,
        ),
    },
    fallback_to_local=True,  # Fall back to Ollama if budget exceeded
)

enforcer = PolicyEnforcer(policy)
enforcer.validate_request(provider="openai", model="gpt-4o-mini", estimated_tokens=2000)
```

### LLM Telemetry (netrun-llm)
Track costs and latency across all LLM providers:

```python
from netrun.llm import LLMTelemetry

telemetry = LLMTelemetry()
telemetry.record_request(
    provider="openai", model="gpt-4o-mini",
    tokens_input=1000, tokens_output=500,
    cost_usd=0.002, latency_ms=1200, success=True
)

report = telemetry.get_report(days=30)
print(f"Total cost: ${report['total_cost_usd']:.4f}")
print(f"P95 latency: {report['latency_p95_ms']}ms")
```

### Tenant Isolation Testing (netrun-rbac v3.0.0)
Comprehensive test suite for multi-tenant security - prove isolation works for SOC2/ISO27001 compliance:

```python
from netrun.rbac import TenantTestContext, TenantEscapePathScanner, ci_fail_on_findings

# Contract test: Tenant B MUST NOT see Tenant A's data
async with TenantTestContext(db_session) as ctx:
    secret = Item(name="Secret", tenant_id=ctx.tenant_a_id)
    session.add(secret)
    await session.commit()

    await ctx.switch_to_tenant_b()
    result = await session.execute(select(Item))
    assert len(result.scalars().all()) == 0  # Cross-tenant access impossible

# CI/CD escape path scanner - finds SQL without tenant filters
scanner = TenantEscapePathScanner()
findings = scanner.scan_directory("./src")
sys.exit(ci_fail_on_findings(findings))  # Fails build on critical findings
```

### Soft-Dependency Detection
All packages now provide clear error messages for missing optional dependencies:

```python
from netrun.auth import AzureADIntegration
# If azure-identity not installed:
# ImportError: AzureADIntegration requires 'azure-identity'.
# Install with: pip install netrun-auth[azure]
```

## Package Details

### netrun-llm

Multi-provider LLM orchestration with automatic fallback chains.

```python
from netrun.llm import LLMFallbackChain

# Default chain: Claude -> OpenAI -> Ollama
chain = LLMFallbackChain()
response = chain.execute("Explain quantum computing")

print(f"Response: {response.content}")
print(f"Provider: {response.adapter_name}")
print(f"Cost: ${response.cost_usd:.6f}")
```

### netrun-config

Configuration management with Azure Key Vault integration.

```python
from netrun.config import SecretCache

cache = SecretCache(vault_url="https://your-vault.vault.azure.net/")
secret = cache.get_secret("database-password")
```

### netrun-logging

Structured logging with structlog backend.

```python
from netrun.logging import get_logger

logger = get_logger(__name__)
logger.info("Application started", version="2.0.0")
```

### netrun-auth

Authentication and authorization with Casbin RBAC.

```python
from netrun.auth import CasbinRBACManager

rbac = CasbinRBACManager(model_path="rbac_model.conf")
if rbac.check_permission(user_id, resource, action):
    # proceed
```

### netrun-rbac (v3.0.0)

Multi-tenant RBAC with hierarchical teams, resource sharing, and tenant isolation testing.

```python
from netrun.rbac import (
    # One-line middleware setup
    setup_tenancy_middleware, TenancyConfig, IsolationMode,
    # Tenant isolation testing
    TenantTestContext, TenantEscapePathScanner, ci_fail_on_findings,
)

# One-line middleware setup
app = FastAPI()
setup_tenancy_middleware(
    app,
    config=TenancyConfig(isolation_mode=IsolationMode.HYBRID),
    get_session=get_db_session
)

# Contract test: Prove tenant isolation works
async with TenantTestContext(db_session) as ctx:
    secret = Item(name="Secret", tenant_id=ctx.tenant_a_id)
    session.add(secret)
    await session.commit()

    await ctx.switch_to_tenant_b()
    result = await session.execute(select(Item))
    assert len(result.scalars().all()) == 0  # Cross-tenant access impossible

# CI/CD escape path scanner
scanner = TenantEscapePathScanner()
findings = scanner.scan_directory("./src")
sys.exit(ci_fail_on_findings(findings))  # Fails build on critical findings
```

**v3.0.0 Features:**
- Hierarchical teams with sub-team support
- Resource-level sharing (user/team/tenant/external)
- `TenantQueryService` for auto-filtered CRUD
- Hybrid isolation (PostgreSQL RLS + application-level)
- Contract testing with `TenantTestContext`
- CI/CD escape path scanner
- Background task context preservation
- SOC2/ISO27001/NIST compliance documentation

### netrun-cache

Redis and in-memory caching with decorator support.

```python
from netrun.cache import CacheManager, cached

cache = CacheManager()

@cached(ttl=300, namespace="users")
async def get_user(user_id: str):
    return await db.fetch_user(user_id)
```

### netrun-resilience

Resilience patterns for distributed systems.

```python
from netrun.resilience import retry, circuit_breaker, timeout

@retry(max_attempts=3, backoff_factor=2.0)
@circuit_breaker(failure_threshold=5)
@timeout(seconds=10)
async def call_external_api():
    return await client.fetch_data()
```

### netrun-validation

Comprehensive Pydantic validators for common patterns.

```python
from netrun.validation import validate_ip_address, validate_api_key_format
from netrun.validation.custom_types import SafeEmail, StrongPassword

class UserConfig(BaseModel):
    email: SafeEmail
    password: StrongPassword
```

### netrun-websocket

Production WebSocket connection management.

```python
from netrun.websocket import WebSocketSessionManager

manager = WebSocketSessionManager(redis_url="redis://localhost:6379")
await manager.initialize()

connection_id = await manager.create_connection(
    websocket=ws,
    user_id="user_123",
    metadata={"room": "general"}
)
```

## Migration from v1.x

```python
# Before (v1.x)
from netrun_auth import JWTHandler
from netrun_config import SecretCache
from netrun_llm import LLMFallbackChain

# After (v2.x) - recommended
from netrun.auth import JWTHandler
from netrun.config import SecretCache
from netrun.llm import LLMFallbackChain
```

The old `netrun_*` imports still work but will show deprecation warnings. Update your imports before v3.0.0.

## Contributing

We welcome contributions! Please:
1. Open an issue to discuss proposed changes
2. Submit pull requests with tests
3. Follow existing code style

## License

All packages are MIT licensed.

## About Netrun Systems

Netrun Systems was founded in May 2025 by Daniel Garza, building on 25 years of consulting experience in cloud infrastructure and DevSecOps. We're developing platform products for managed service providers, content creators, and enterprise security teams.

- Website: [netrunsystems.com](https://netrunsystems.com)
- Contact: daniel@netrunsystems.com

## Acknowledgments

Special thanks to the r/Python and r/FastAPI communities for feedback that shaped our releases:

**v2.1 / v3.0.0** (December 2025):
- Tenant isolation contract testing with `TenantTestContext`
- CI/CD escape path scanner for compliance
- Hierarchical teams and resource sharing
- 4 new infrastructure packages (cache, resilience, validation, websocket)
- Azure OpenAI and Gemini adapters for netrun-llm

**v2.0.0** (December 2025):
- Soft-dependency detection improvements
- LLM per-provider policy enforcement
- LLM cost/latency telemetry
