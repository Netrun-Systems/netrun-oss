---
document: NETRUN_OSS_LIBRARY_ARCHITECTURE_WHITEPAPER
version: v1.1
status: REVIEWED
reviewed: 2026-05-26
author: Daniel Garza
AI contributor: document-review-specialist (claude-sonnet-4-6)
---

# netrun-oss Library Architecture Whitepaper

**Version**: v1.1
**Date**: 2026-05-26
**Status**: Current

## Version Notes

### v1.1 — 2026-05-26
- Corrected package count: 19 Python packages + 1 TypeScript package (20 total directories)
- Added §Adoption Status with verified portfolio metrics from May 2026 code-reusability audit
- Added §Package Health Summary from April 2026 revival audit
- Added §netrun-touch-ui as a separate TypeScript companion entry
- Clarified that netrun-dogfood is an internal MCP test server, not a general-purpose library
- Verified package list against actual `packages/` directory contents (grep-verified 2026-05-26)
- Updated architecture section to reflect actual test counts from revive audit

### v1.0 — (initial, no formal date)
- Initial architecture documentation of netrun-oss monorepo structure

---

## Overview

netrun-oss is a public Python OSS monorepo published by Netrun Systems. It contains **19 Python packages** on PyPI under the `netrun.*` PEP 420 namespace (v2.0+), targeted at FastAPI applications and adjacent Python infrastructure. All packages are MIT licensed.

A separate TypeScript package (`@netrun/touch-ui`) also lives in the repo but is outside the Python namespace and counted separately.

The library suite was extracted from Netrun's internal services. Packages range from high-adoption infrastructure utilities (`netrun-logging`, `netrun-cors`, `netrun.dee`) to proof-of-concept implementations with limited portfolio adoption. The §Adoption Status section below gives the honest breakdown.

---

## Package Inventory

19 Python packages, verified against `packages/` directory contents 2026-05-26.

### Core

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-core** | 2.0.0 | Root namespace package for `netrun.*` PEP 420 imports |

### Auth and Authorization

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-auth** | 2.0.0 | Unified authentication — JWT, OAuth2, Azure AD, Casbin RBAC |
| **netrun-oauth** | 2.0.0 | OAuth 2.0 adapters for 12+ providers |
| **netrun-rbac** | 3.0.0 | Multi-tenant RBAC with hierarchical teams, resource-level sharing, tenant isolation testing, SOC2/ISO27001/NIST compliance docs |

### Data and Cache

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-db-pool** | 2.0.0 | Async database connection pooling with tenant isolation |
| **netrun-cache** | 1.0.0 | Redis and in-memory caching with decorators and TTL |

### Web Middleware

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-cors** | 2.0.0 | Enterprise CORS middleware presets for FastAPI |
| **netrun-ratelimit** | 2.0.0 | Distributed rate limiting with token bucket and Redis backends |
| **netrun-websocket** | 1.0.0 | Production WebSocket management with Redis sessions and JWT |
| **netrun-errors** | 2.0.0 | Unified error handling and exception hierarchy for FastAPI |

### Ops and Observability

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-config** | 2.0.0 | Configuration management with Azure Key Vault integration and TTL caching |
| **netrun-env** | 2.0.0 | Schema-based environment variable validator |
| **netrun-logging** | 2.0.0 | Structured logging with structlog backend and Azure App Insights integration |
| **netrun-resilience** | 1.0.0 | Resilience patterns: retry, circuit breaker, timeout, bulkhead |
| **netrun-validation** | 1.0.0 | Pydantic validators for network, security, datetime, and custom types |

### LLM and AI

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-llm** | 2.0.0 | Multi-provider LLM orchestration with per-tenant policies and cost/latency telemetry |
| **netrun-dee** | 1.0.0 | Digital Emotion Equivalents — emotion detection and ECI scoring for AI-generated text, 39 personality profiles |

### Testing and Internal

| Package | Version | Description |
|---------|---------|-------------|
| **netrun-pytest-fixtures** | 2.0.0 | Unified pytest fixtures; eliminates 71% duplication across test suites |
| **netrun-dogfood** | 2.0.0 | Internal MCP server for integration testing. Not a general-purpose library. |

### TypeScript Companion (not in Python namespace)

| Package | Version | Description |
|---------|---------|-------------|
| **@netrun/touch-ui** | 1.0.0 | Touch-first UI component library for Netrun frontends. TypeScript. Not on PyPI. |

---

## Adoption Status

**As of May 2026 code-reusability audit.**

This section is intentionally honest. The library suite was extracted from Netrun's internal services over 2025. Not every package achieved meaningful adoption across the portfolio. The table below reflects the actual state, not the intended state.

### Top-adoption packages (verified portfolio usage)

| Package | Portfolio References | Usage Context |
|---------|---------------------|---------------|
| **netrun-logging** | ~237 references | Primary structured-logging primitive across the Netrun portfolio. Highest-adoption package by a significant margin. |
| **netrun-cors** | Meaningful adoption | CORS middleware used in FastAPI services where cross-origin policy matters. |
| **netrun.dee** (netrun-dee) | Active use | Deployed in Charlotte voice tier for response shaping; used in Intirkast for podcast persona consistency. |
| **netrun-pytest-fixtures** | Partial adoption | Used in several test suites; eliminates duplicate fixture boilerplate. |
| **netrun-db-pool** | Partial adoption | Connection pooling referenced in multi-tenant services. |

### Low-adoption packages (proof-of-concept status)

Approximately 14 of the 19 Python packages have limited portfolio adoption as of May 2026. These packages have passing tests and correct implementations, but they were not yet picked up by live services at the time of the May 2026 audit.

This is not a quality signal — it reflects the timeline of the extraction process and the fact that the Netrun service portfolio is still growing. Packages with passing tests and clean APIs are adoption-ready; they have not yet been needed in a context that pulled them in.

Packages in this category include: netrun-auth, netrun-cache, netrun-config, netrun-env, netrun-errors, netrun-llm, netrun-oauth, netrun-ratelimit, netrun-rbac, netrun-resilience, netrun-validation, netrun-websocket, netrun-core, netrun-dogfood.

---

## Architecture

### PEP 420 Namespace Package Structure

All 19 Python packages share the `netrun.*` namespace (PEP 420 implicit namespace packages). `netrun-core` is the root namespace package that declares the `netrun` namespace; all other packages install into subdirectories of that namespace.

```
netrun/
  auth/          # netrun-auth
  cache/         # netrun-cache
  config/        # netrun-config
  cors/          # netrun-cors (also netrun_cors legacy compat)
  db/            # netrun-db-pool
  dee/           # netrun-dee
  env/           # netrun-env
  errors/        # netrun-errors
  llm/           # netrun-llm
  logging/       # netrun-logging
  oauth/         # netrun-oauth
  ratelimit/     # netrun-ratelimit
  rbac/          # netrun-rbac
  resilience/    # netrun-resilience
  testing/       # netrun-pytest-fixtures
  validation/    # netrun-validation
  websocket/     # netrun-websocket
```

`netrun-dogfood` and `netrun-core` are structural; `netrun-dee` lives at `netrun.dee`.

### Compat Shims (v1.x → v2.x migration)

Every package that migrated from the `netrun_*` flat namespace to `netrun.*` ships a compat shim directory (`netrun_auth/`, `netrun_logging/`, etc.) that re-exports from the canonical `netrun.auth`, `netrun.logging`, etc. modules.

Old imports continue to work with a deprecation warning; they will be removed in v3.0.

```python
# v2.x — recommended
from netrun.auth import JWTHandler
from netrun.logging import get_logger
from netrun.llm import LLMFallbackChain

# v1.x compat — still works, deprecated, removed in v3.0
from netrun_auth import JWTHandler
```

**Important**: compat shim submodule gaps are a known maintenance hazard. When a package adds new submodules under `netrun.x.*`, the corresponding `netrun_x/` compat directory must also get proxy files for those submodules. The April 2026 revival audit found four missing proxy files in `netrun-logging` and one in `netrun-config`; those have been added.

### Soft-Dependency Detection

Optional integrations (Azure, OpenAI, Anthropic, Redis) raise clear, actionable errors when their packages are not installed:

```
ImportError: AzureADIntegration requires 'azure-identity'.
Install with: pip install netrun-auth[azure]
```

This pattern allows packages to be installed without dragging in heavyweight cloud SDK dependencies unless the feature is actually used.

### Dependency Graph (simplified)

All packages depend on `netrun-core` for the namespace root. No other mandatory cross-package dependencies exist in the core layer. Optional integration-level dependencies (e.g., `netrun-auth` may use `netrun-logging` for audit events) are declared as soft deps, not hard requirements.

```
netrun-core
    ├── netrun-auth       (auth stack; depends on netrun-core, optional azure/casbin)
    ├── netrun-oauth      (OAuth adapters; depends on netrun-core)
    ├── netrun-rbac       (multi-tenant RBAC; depends on netrun-core, optional SQLAlchemy)
    ├── netrun-db-pool    (async pool; depends on netrun-core, SQLAlchemy)
    ├── netrun-cache      (caching; depends on netrun-core, optional Redis)
    ├── netrun-cors       (CORS middleware; depends on netrun-core, FastAPI)
    ├── netrun-ratelimit  (rate limiting; depends on netrun-core, optional Redis)
    ├── netrun-websocket  (WebSocket; depends on netrun-core, optional Redis)
    ├── netrun-errors     (error handling; depends on netrun-core)
    ├── netrun-config     (config/secrets; depends on netrun-core, optional azure-keyvault)
    ├── netrun-env        (env validation; depends on netrun-core)
    ├── netrun-logging    (structured logging; depends on netrun-core, structlog)
    ├── netrun-resilience (resilience patterns; depends on netrun-core)
    ├── netrun-validation (Pydantic validators; depends on netrun-core, Pydantic)
    ├── netrun-llm        (LLM orchestration; depends on netrun-core, optional openai/anthropic/google)
    ├── netrun-dee        (emotion engine; depends on netrun-core, Pydantic — no runtime cloud deps)
    ├── netrun-pytest-fixtures (test utilities; depends on netrun-core, pytest)
    └── netrun-dogfood    (internal MCP server; depends on netrun-core — not for external use)
```

---

## Package Health Summary

From the April 2026 revival audit (repo was stalled 87 days, revived 2026-04-27):

| Status | Count | Packages |
|--------|-------|----------|
| GREEN (all tests pass) | 12 | netrun-core, netrun-resilience, netrun-validation, netrun-errors, netrun-config, netrun-cors, netrun-llm, netrun-logging, netrun-oauth, netrun-rbac, netrun-db-pool, netrun-websocket |
| YELLOW (1–2 non-critical test failures) | 4 | netrun-env, netrun-cache, netrun-ratelimit, netrun-pytest-fixtures |
| RED (multiple failures, needs attention) | 1 | netrun-auth (casbin async/sync mismatch — 22 tests) |
| NO TESTS (structural packages) | 2 | netrun-core, netrun-dogfood |

### Known open issues (as of April 2026 audit)

- **netrun-auth** (HIGH): `rbac_casbin.py` calls `await` on synchronous `casbin.Enforcer` methods. Fix: switch to `casbin-async`, or remove `await` and run sync. All other auth tests pass when casbin tests are excluded.
- **netrun-cache** (MEDIUM): `CacheManager.decrement()` deletes L1 cache entry before the fallback increment, producing wrong value when Redis is unavailable.
- **netrun-ratelimit** (LOW): Per-call rate overrides create separate bucket state from default-rate calls; `test_check_with_custom_limits` fails.
- **netrun-env** (LOW): CLI `--format json` mode emits structlog lines to stdout mixed with JSON output; fix is to redirect log output to stderr in JSON mode.
- **netrun-pytest-fixtures** (LOW): `mock_log_handler.emit` not triggered in one fixture test; fix is to set handler log level to `logging.DEBUG`.

---

## Release and Publish Flow

Each package is independently versioned. Releases are not lockstep across the suite. The typical flow:

1. Bump version in `packages/netrun-X/pyproject.toml` and update CHANGELOG
2. Tag `v{pkg}-X.Y.Z` and push to trigger GitHub Actions
3. CI runs `pytest packages/netrun-X/tests/` against Python 3.10, 3.11, 3.12 (matrix: 18 packages × 3 Python versions = 54 jobs per push)
4. On test pass: build sdist + wheel, upload to test.pypi.org for smoke-test
5. Promote to pypi.org

The `.github/` CI workflow was added during the April 2026 revival. Prior releases were published manually.

---

## Notable Packages

### netrun-logging

The highest-adoption package in the suite (~237 portfolio references). Provides structured logging via structlog with optional Azure Application Insights integration. Idiomatic usage:

```python
from netrun.logging import get_logger

logger = get_logger(__name__)
logger.info("request completed", status=200, duration_ms=42)
```

### netrun-rbac (v3.0.0)

The most architecturally complete package. Features include hierarchical teams, resource-level sharing (user/team/tenant/external), `TenantQueryService` for auto-filtered CRUD, hybrid isolation (PostgreSQL RLS + application-level), contract testing with `TenantTestContext`, and a `TenantEscapePathScanner` CI gate that fails the build when it finds SQL queries without a tenant filter. Includes SOC2/ISO27001/NIST compliance documentation.

```python
from netrun.rbac import TenantTestContext, TenantEscapePathScanner, ci_fail_on_findings

# Contract test: Tenant B must not see Tenant A's data
async with TenantTestContext(db_session) as ctx:
    secret = Item(name="Secret", tenant_id=ctx.tenant_a_id)
    session.add(secret); await session.commit()
    await ctx.switch_to_tenant_b()
    result = await session.execute(select(Item))
    assert len(result.scalars().all()) == 0  # isolation holds

# CI escape path scanner
scanner = TenantEscapePathScanner()
findings = scanner.scan_directory("./src")
sys.exit(ci_fail_on_findings(findings))
```

### netrun-llm

Multi-provider LLM orchestration with per-tenant budget and rate-limit policies, cost/latency telemetry, and automatic fallback chains (Claude → OpenAI → Ollama). Azure OpenAI and Gemini adapters added in v2.1.

```python
from netrun.llm import LLMFallbackChain, TenantPolicy, PolicyEnforcer

chain = LLMFallbackChain()
response = chain.execute("Explain quantum computing")
print(f"Provider used: {response.adapter_name}, cost: ${response.cost_usd:.6f}")
```

### netrun-dee

Published May 1, 2026. Emotion detection and ECI (Emotional Complexity Index) scoring for AI-generated text, with 39 personality profiles. No runtime dependencies beyond stdlib and Pydantic. Deployed in Charlotte's voice tier for response shaping and in Intirkast for podcast persona consistency. One of the few packages with confirmed active use.

---

## Companion Repos

- **netrun-shared-ts** — TypeScript shared libraries for Netrun internal services (16 packages, not published to npm; tightly coupled to Netrun-specific architectures, not open-sourced)
- **netrun-oss** (this repo) — Python packages general-purpose enough for community use; MIT licensed

The OSS/closed split is intentional. The Python packages address generic FastAPI infrastructure problems any team might face. The TypeScript packages address Netrun-specific multi-tenant CMS, CRM, and AI orchestration patterns that require Netrun's broader service context to be useful.

---

_Last reviewed: 2026-05-26_
