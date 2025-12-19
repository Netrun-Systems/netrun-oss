# Reddit Post: Netrun Namespace Packages v2.0.0

## Suggested Subreddits
- r/Python
- r/FastAPI
- r/SaaS (if discussing multi-tenant features)

---

## Post Title

**[Update] Netrun FastAPI Building Blocks v2.0 - Added LLM Policies, Telemetry, and Tenant Isolation Testing (thanks to your feedback!)**

---

## Post Body

A few weeks ago I shared the Netrun namespace packages - a set of opinionated FastAPI building blocks for auth, config, logging, and more. I got some really valuable feedback from the community, and today I'm releasing v2.0.0 with all four suggested enhancements implemented.

**TL;DR:** 14 packages now on PyPI. New features include LLM cost/budget policies, latency telemetry, and tenant escape path testing.

---

### What's New (Based on Your Feedback)

**1. Soft-Dependency Documentation**

One commenter noted the soft-deps pattern was useful but needed clearer documentation on what features activate when. Done - there's now a full integration matrix showing exactly which optional dependencies enable which features.

**2. Tenant Escape Path Testing** (Critical Security)

The feedback: *"On auth, I'd think hard about tenant escape paths—the subtle bugs where background tasks lose tenant context."*

This was a great catch. The new `netrun.rbac.testing` module includes:
- `assert_tenant_isolation()` - Validates queries include tenant filters
- `TenantTestContext` - Context manager for cross-tenant testing
- `BackgroundTaskTenantContext` - Preserves tenant context in Celery/background workers
- `TenantEscapePathScanner` - Static analysis for CI/CD

```python
# Test that cross-tenant access is blocked
async with TenantTestContext(tenant_id="tenant-a") as ctx:
    resource = await create_resource()

async with TenantTestContext(tenant_id="tenant-b") as ctx:
    with pytest.raises(TenantAccessDeniedError):
        await get_resource(resource.id)  # Should fail
```

**3. LLM Per-Provider Policies**

The feedback: *"For LLMs, I'd add simple per-provider policies (which models are allowed, token limits, maybe a cost ceiling per tenant/day)."*

Implemented in `netrun.llm.policies`:
- Per-provider model allow/deny lists
- Token and cost limits per request
- Daily and monthly budget enforcement
- Rate limiting (RPM and TPM)
- Cost tier restrictions (FREE/LOW/MEDIUM/HIGH/PREMIUM)
- Automatic fallback to local models when budget exceeded

```python
tenant_policy = TenantPolicy(
    tenant_id="acme-corp",
    monthly_budget_usd=100.0,
    daily_budget_usd=10.0,
    fallback_to_local=True,
    provider_policies={
        "openai": ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini"],
            max_cost_per_request=0.05,
            cost_tier_limit=CostTier.LOW,
        ),
    },
)

enforcer = PolicyEnforcer(tenant_policy)
enforcer.validate_request(provider="openai", model="gpt-4o-mini", estimated_tokens=2000)
```

**4. LLM Cost & Latency Telemetry**

The feedback: *"Structured telemetry (cost, latency percentiles, maybe token counts) would let teams answer 'why did our LLM bill spike?'"*

New `netrun.llm.telemetry` module:
- Per-request cost calculation with accurate model pricing (20+ models)
- Latency tracking with P50/P95/P99 percentiles
- Time-period aggregations (hourly, daily, monthly)
- Azure Monitor export support

```python
collector = TelemetryCollector(tenant_id="acme-corp")

async with collector.track_request(provider="openai", model="gpt-4o") as tracker:
    response = await client.chat.completions.create(...)
    tracker.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

metrics = collector.get_aggregated_metrics(hours=24)
print(f"24h cost: ${metrics.total_cost_usd:.2f}, P95 latency: {metrics.latency_p95_ms}ms")
```

---

### Full Package List (14 packages)

All now using PEP 420 namespace imports (`from netrun.auth import ...`):

| Package | What It Does |
|---------|--------------|
| netrun-core | Namespace foundation |
| netrun-auth | JWT auth, API keys, multi-tenant |
| netrun-config | Pydantic settings + Azure Key Vault |
| netrun-errors | Structured JSON error responses |
| netrun-logging | Structured logging with correlation IDs |
| netrun-llm | LLM adapters + **NEW policies + telemetry** |
| netrun-rbac | Role-based access + **NEW tenant isolation testing** |
| netrun-db-pool | Async PostgreSQL connection pooling |
| netrun-cors | CORS configuration |
| netrun-env | Environment detection |
| netrun-oauth | OAuth2 provider integration |
| netrun-ratelimit | Redis-backed rate limiting |
| netrun-pytest-fixtures | Test fixtures |
| netrun-dogfood | Internal testing utilities |

---

### Install

```bash
pip install netrun-auth netrun-config netrun-llm netrun-rbac
```

All packages: https://pypi.org/search/?q=netrun-

---

### Thanks!

This release exists because of community feedback. The tenant escape path testing suggestion alone would have caught bugs I've seen in production multi-tenant apps. The LLM policy/telemetry combo is exactly what I needed for a project but hadn't prioritized building.

If you have more feedback or feature requests, I'm listening. What would make these more useful for your projects?

---

**Links:**
- PyPI: https://pypi.org/search/?q=netrun-
- Release Notes: [Link to GitHub release]

---

## Reply Template (for the original commenters)

If you can find the original thread, consider replying:

> Hey! Just wanted to follow up - I implemented all four of your suggestions in v2.0.0:
>
> 1. Soft-dep documentation with full integration matrix
> 2. Tenant escape path testing (`netrun.rbac.testing`)
> 3. LLM per-provider policies with budget limits (`netrun.llm.policies`)
> 4. LLM cost/latency telemetry with percentiles (`netrun.llm.telemetry`)
>
> The tenant context preservation for background tasks was especially valuable - that's a subtle bug I've seen bite people in production.
>
> Thanks for the feedback! Release notes: [link]
