# Netrun Namespace Packages v2.0.0 Release Notes

**Release Date:** December 18, 2025
**Total Packages:** 14 (4 new packages added)

---

## Overview

This major release migrates all Netrun packages to PEP 420 namespace packages (`netrun.*`) and adds significant new functionality based on community feedback. The release includes new LLM policy enforcement, cost/latency telemetry, tenant isolation testing, and comprehensive soft-dependency documentation.

---

## What's New

### New Packages

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-core** | 1.0.0 | Foundation namespace package providing `netrun.*` namespace |
| **netrun-llm** | 2.0.0 | LLM integration with NEW policy enforcement and telemetry |
| **netrun-rbac** | 2.0.0 | Role-based access control with NEW tenant isolation testing |
| **netrun-dogfood** | 2.0.0 | Internal testing and validation utilities |

### Updated Packages (v2.0.0)

All existing packages migrated to namespace imports:

| Package | New Import | Old Import (deprecated) |
|---------|------------|------------------------|
| netrun-auth | `from netrun.auth import *` | `from netrun_auth import *` |
| netrun-config | `from netrun.config import *` | `from netrun_config import *` |
| netrun-errors | `from netrun.errors import *` | `from netrun_errors import *` |
| netrun-logging | `from netrun.logging import *` | `from netrun_logging import *` |
| netrun-db-pool | `from netrun.db_pool import *` | `from netrun_db_pool import *` |
| netrun-cors | `from netrun.cors import *` | `from netrun_cors import *` |
| netrun-env | `from netrun.env import *` | `from netrun_env import *` |
| netrun-oauth | `from netrun.oauth import *` | `from netrun_oauth import *` |
| netrun-ratelimit | `from netrun.ratelimit import *` | `from netrun_ratelimit import *` |
| netrun-pytest-fixtures | `from netrun.pytest_fixtures import *` | `from netrun_pytest_fixtures import *` |

---

## Major Features

### 1. LLM Policy Enforcement (netrun-llm)

Per-provider and per-tenant policy controls for LLM usage:

```python
from netrun.llm.policies import (
    ProviderPolicy,
    TenantPolicy,
    PolicyEnforcer,
    CostTier,
)

# Define tenant policy with budget limits
tenant_policy = TenantPolicy(
    tenant_id="acme-corp",
    monthly_budget_usd=100.0,
    daily_budget_usd=10.0,
    fallback_to_local=True,  # Fall back to Ollama if budget exceeded
    provider_policies={
        "openai": ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini", "gpt-4o"],
            max_tokens_per_request=4096,
            max_cost_per_request=0.10,
            rate_limit_rpm=60,
            rate_limit_tpm=100000,
            cost_tier_limit=CostTier.MEDIUM,
        ),
    },
)

# Enforce policies before making requests
enforcer = PolicyEnforcer(tenant_policy)
try:
    enforcer.validate_request(
        provider="openai",
        model="gpt-4o",
        estimated_tokens=2000,
        reason="Customer support chatbot",
    )
except BudgetExceededError:
    # Use local model instead
    pass
```

**Features:**
- Per-provider model allow/deny lists
- Token and cost limits per request
- Daily and monthly budget enforcement
- Rate limiting (RPM and TPM)
- Cost tier restrictions (FREE, LOW, MEDIUM, HIGH, PREMIUM)
- Automatic fallback to local models (Ollama)
- Reason/justification requirements

### 2. LLM Cost & Latency Telemetry (netrun-llm)

Structured telemetry for cost tracking and performance monitoring:

```python
from netrun.llm.telemetry import (
    TelemetryCollector,
    LLMRequestMetrics,
    AggregatedMetrics,
)

# Initialize collector
collector = TelemetryCollector(
    tenant_id="acme-corp",
    flush_interval_seconds=60,
    export_to_azure_monitor=True,
)

# Record request metrics (automatic with context manager)
async with collector.track_request(
    provider="openai",
    model="gpt-4o",
    operation="chat_completion",
) as tracker:
    response = await openai_client.chat.completions.create(...)
    tracker.set_tokens(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )

# Get aggregated metrics
metrics = collector.get_aggregated_metrics(hours=24)
print(f"Total cost: ${metrics.total_cost_usd:.2f}")
print(f"P95 latency: {metrics.latency_p95_ms:.0f}ms")
print(f"Success rate: {metrics.success_rate:.1%}")
```

**Features:**
- Per-request cost calculation with accurate model pricing
- Latency tracking with percentiles (P50, P95, P99)
- Automatic cost estimation for 20+ models
- Azure Monitor / Application Insights export
- Time-period aggregations (hourly, daily, monthly)
- Provider and model breakdowns

### 3. Tenant Isolation Testing (netrun-rbac)

Security testing utilities for multi-tenant applications:

```python
from netrun.rbac.testing import (
    assert_tenant_isolation,
    TenantTestContext,
    BackgroundTaskTenantContext,
    TenantEscapePathScanner,
)

# Assert tenant isolation in database queries
@pytest.fixture
def isolated_query_checker():
    return assert_tenant_isolation

def test_user_query_includes_tenant_filter(db_session, isolated_query_checker):
    """Verify all user queries filter by tenant."""
    query = db_session.query(User).filter(User.email == "test@example.com")
    isolated_query_checker(query, expected_tenant_id="tenant-123")

# Test cross-tenant access attempts
async def test_cross_tenant_access_denied():
    async with TenantTestContext(tenant_id="tenant-a") as ctx_a:
        resource = await create_resource(name="secret")

    async with TenantTestContext(tenant_id="tenant-b") as ctx_b:
        # Should raise TenantAccessDeniedError
        with pytest.raises(TenantAccessDeniedError):
            await get_resource(resource.id)

# Preserve tenant context in background tasks
async def process_webhook(data: dict, tenant_id: str):
    async with BackgroundTaskTenantContext(tenant_id):
        # Tenant context preserved even in Celery/background workers
        await process_data(data)

# Static analysis for CI/CD
scanner = TenantEscapePathScanner(project_root="./src")
violations = scanner.scan()
assert len(violations) == 0, f"Tenant escape paths found: {violations}"
```

**Features:**
- Query-level tenant isolation assertions
- Cross-tenant access testing context managers
- Background task tenant context preservation
- Static analysis scanner for CI/CD integration
- PostgreSQL RLS policy validation

### 4. Soft-Dependency Detection Documentation

Comprehensive documentation for optional dependency integration:

| Package | Optional Dependency | Feature Enabled |
|---------|-------------------|-----------------|
| netrun-auth | netrun-logging | Structured auth event logging |
| netrun-auth | casbin | Advanced RBAC policies |
| netrun-config | netrun-errors | Standardized config exceptions |
| netrun-config | netrun-logging | Config change logging |
| netrun-config | azure-identity | Azure Key Vault integration |
| netrun-errors | netrun-logging | Correlation ID in error responses |
| netrun-llm | netrun-logging | LLM request/response logging |
| netrun-llm | openai | OpenAI provider support |
| netrun-llm | anthropic | Anthropic provider support |
| netrun-rbac | netrun-logging | RBAC decision logging |
| netrun-rbac | casbin | Policy-based access control |
| netrun-db-pool | netrun-logging | Connection pool metrics |

See `DEPENDENCY_DETECTION.md` for full integration matrix and troubleshooting.

---

## Breaking Changes

### Import Path Migration

All imports must migrate from `netrun_*` to `netrun.*`:

```python
# OLD (deprecated, will warn)
from netrun_auth import JWTManager
from netrun_config import BaseConfig

# NEW (recommended)
from netrun.auth import JWTManager
from netrun.config import BaseConfig
```

**Backwards compatibility shims are included** - old imports will work but emit deprecation warnings. Plan migration before v3.0.0.

### Minimum Python Version

- Python 3.10+ required (previously 3.9+)
- Full type hint support with PEP 604 union syntax

---

## Bug Fixes

- **Fixed:** TPM rate limiting now correctly tracks tokens across requests (was storing timestamps instead of token counts)
- **Fixed:** Cost-per-request validation now triggers before token limit validation
- **Fixed:** Budget exceeded errors now properly trigger fallback to local models

---

## Installation

```bash
# Install all packages
pip install netrun-core netrun-auth netrun-config netrun-errors \
    netrun-logging netrun-llm netrun-rbac netrun-db-pool \
    netrun-cors netrun-env netrun-oauth netrun-ratelimit \
    netrun-pytest-fixtures netrun-dogfood

# Or install specific packages with extras
pip install netrun-auth[logging]  # With netrun-logging integration
pip install netrun-llm[openai,anthropic]  # With provider SDKs
pip install netrun-rbac[casbin]  # With Casbin support
```

---

## PyPI Links

| Package | PyPI |
|---------|------|
| netrun-core | https://pypi.org/project/netrun-core/ |
| netrun-auth | https://pypi.org/project/netrun-auth/ |
| netrun-config | https://pypi.org/project/netrun-config/ |
| netrun-errors | https://pypi.org/project/netrun-errors/ |
| netrun-logging | https://pypi.org/project/netrun-logging/ |
| netrun-llm | https://pypi.org/project/netrun-llm/ |
| netrun-rbac | https://pypi.org/project/netrun-rbac/ |
| netrun-db-pool | https://pypi.org/project/netrun-db-pool/ |
| netrun-cors | https://pypi.org/project/netrun-cors/ |
| netrun-env | https://pypi.org/project/netrun-env/ |
| netrun-oauth | https://pypi.org/project/netrun-oauth/ |
| netrun-ratelimit | https://pypi.org/project/netrun-ratelimit/ |
| netrun-pytest-fixtures | https://pypi.org/project/netrun-pytest-fixtures/ |
| netrun-dogfood | https://pypi.org/project/netrun-dogfood/ |

---

## Acknowledgments

Special thanks to the Reddit community for valuable feedback that shaped this release:

- **Soft-dependency documentation** - Clarifying which features activate when optional packages are installed
- **Tenant escape path testing** - Critical security testing for multi-tenant SaaS applications
- **LLM per-provider policies** - Fine-grained control over model usage and costs
- **LLM cost/latency telemetry** - Structured metrics for FinOps and performance monitoring

Your feedback directly improved these packages. Thank you!

---

## What's Next (v2.1.0)

- Azure Monitor telemetry export integration
- Prometheus metrics endpoint for LLM telemetry
- Additional tenant isolation test patterns
- OpenTelemetry trace context propagation

---

## License

MIT License - Netrun Systems

---

*Questions or feedback? Open an issue on GitHub or reach out on Reddit.*
