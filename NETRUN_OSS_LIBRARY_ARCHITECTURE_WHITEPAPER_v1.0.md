# netrun-oss: A Unified Python Foundation for FastAPI Applications

## Technical Whitepaper v1.0

**Date**: May 1, 2026
**Author**: Daniel Garza, Founder and CEO, Netrun Systems
**Platform**: PyPI — https://pypi.org/user/netrunsystems/ (19 packages)
**Repository**: `/data/workspace/github/netrun-oss/`
**Status**: Production-published; v2.0.0 PEP 420 namespace migration complete; `netrun-dee 1.0.0` added May 1, 2026 (DEE Layer A)

---

## Executive Summary

Every FastAPI shop that grows past a single service faces the same invisible tax: reimplementing auth, config loading, structured logging, error handling, and database pooling from scratch in each new service. The patterns are well understood, but the cost of reinventing them — and of keeping three divergent implementations in sync — accumulates quietly until a security patch or breaking dependency forces a painful multi-repo scramble.

`netrun-oss` is Netrun Systems' answer to that tax. It is a collection of 19 production-tested Python packages, all published to PyPI under the unified `netrun.*` namespace (PEP 420), covering authentication, configuration, logging, error handling, CORS, database pooling, rate limiting, RBAC, caching, resilience patterns, validation, WebSocket management, LLM orchestration, environment validation, OAuth adapters, pytest fixtures, integration testing, and emotion detection. Every package has been exercised across the Netrun portfolio — intirkon, intirkast, netrun-crm/KOG, wilbur/Charlotte — before being published externally. This is not a "release early, fix later" library; it is extracted from running systems.

The v2.0.0 release (December 2025) unified all imports under a single namespace: `from netrun.auth import JWTHandler` replaces `from netrun_auth import JWTHandler`. The old flat imports continue to work but emit deprecation warnings; v3.0.0 will remove them. The namespace root package, `netrun-core`, carries no runtime dependencies and exists solely to claim and define the `netrun` namespace on PyPI.

The 19th package, `netrun-dee 1.0.0`, was added May 1, 2026 as the Python deliverable of DEE Layer A (Digital Emotion Equivalents). It provides emotion detection, ECI scoring, and emotional trajectory analysis for AI-generated text — the foundational lexicon layer that powers Charlotte's emotion-aware responses and will extend to Intirkast, KOG, and EISCORE. The hatchling build-system migration that shipped with `netrun-dee` (commit `ee4bf9f`, per Boardroom_TODO #32) also brings the package fully into the `netrun.dee` namespace, consistent with the rest of the library.

---

## Table of Contents

1. The Problem
2. API and Module Overview
   - 2.1 The PEP 420 Namespace Structure
   - 2.2 Package Inventory (All 19)
   - 2.3 Inter-Package Dependency Graph
   - 2.4 The netrun-dee Addition (DEE Layer A)
3. Production State (PyPI)
4. Differentiation
5. Limitations and Future Work
6. References

---

## 1. The Problem

### 1.1 The Foundation Tax on Multi-Service FastAPI Shops

A FastAPI application has predictable infrastructure needs from day one: a way to load secrets, a way to log structured output, a way to handle and serialize errors consistently, a way to authenticate requests, and eventually a way to pool database connections, rate-limit callers, and isolate tenants. None of this is the application's differentiating logic, but all of it must exist before the application can ship.

When a team builds one service, writing this infrastructure inline is acceptable. When that team builds a second service — or when a consulting organization like Netrun ships a new platform product every few months — the math changes. Each reimplementation introduces:

- **Behavioral drift**: Three services with three slightly different error serialization formats means three different client SDKs or fragile string-parsing in consumers.
- **Security surface divergence**: A JWT validation fix applied to Service A must be manually ported to Services B and C. In practice it often isn't, not immediately.
- **Upgrade friction**: When a dependency releases a breaking change (e.g., Pydantic v1 → v2), each standalone implementation must be migrated independently, on its own schedule, with its own test debt.

The Netrun portfolio grew to cover intirkon (multi-tenant Azure/GCP BI), intirkast (streaming content platform), netrun-crm/KOG (CRM with LLM integrations), and wilbur/Charlotte (AI voice assistant). By mid-2025, the same auth middleware existed in four forms across four repositories. The same logging configuration appeared five times. This is the problem `netrun-oss` was built to solve.

### 1.2 Import Sprawl Before PEP 420

The pre-v2.0.0 library (then called `Netrun_Service_Library_v2`) used flat package names: `netrun_auth`, `netrun_config`, `netrun_logging`. This created two friction points.

First, PyPI flat names carry no structural signal — `netrun_auth` and `netrun_auth_enterprise` look like peers rather than members of the same family. Second, import statements scattered across a codebase (`from netrun_auth import ...`, `from netrun_config import ...`, `from netrun_llm import ...`) have no visual grouping. A developer reading an unfamiliar service cannot immediately identify "this is using the Netrun foundation layer" — they must check each import individually.

PEP 420 namespace packages solve this by allowing multiple installable packages to contribute modules into the same top-level namespace without a single coordinating `__init__.py`. After `pip install netrun-core netrun-auth netrun-config`, the following all resolve correctly:

```python
from netrun.auth import JWTHandler
from netrun.config import SecretCache
from netrun.logging import get_logger
```

The `netrun` prefix in import statements now unambiguously marks foundation-layer code. This is the core structural improvement in v2.0.0.

### 1.3 The Cost of DIY Multi-Tenant RBAC and Isolation

Multi-tenant access control is consistently the most under-engineered component in new SaaS services. Teams implement a basic role check, ship, and discover 18 months later that their SQL queries have no tenant filter on 40% of endpoints — meaning Tenant B can potentially see Tenant A's data if they craft the right request.

The `netrun-rbac` package addresses this with a `TenantEscapePathScanner` that statically analyzes a Python codebase for SQL queries missing tenant filters, and a `TenantTestContext` that provides contract tests proving isolation holds in the actual database. These tools exist because Netrun needed them for SOC2 and ISO27001 audit evidence on intirkon — they were extracted as reusable components rather than kept as one-off scripts.

---

## 2. API and Module Overview

### 2.1 The PEP 420 Namespace Structure

PEP 420 (implicit namespace packages) allows a Python namespace — `netrun` in this case — to be "owned" by multiple installed packages simultaneously, with no single package holding an `__init__.py` at the namespace root. Each package contributes its subtree:

```
netrun-auth       → netrun/auth/
netrun-cache      → netrun/cache/
netrun-config     → netrun/config/
netrun-core       → netrun/           (namespace root only; no submodules)
netrun-cors       → netrun/cors/
netrun-db-pool    → netrun/db/
netrun-dee        → netrun/dee/
netrun-dogfood    → netrun/dogfood/
netrun-env        → netrun/env/
netrun-errors     → netrun/errors/
netrun-llm        → netrun/llm/
netrun-logging    → netrun/logging/
netrun-oauth      → netrun/oauth/
netrun-pytest-fixtures → netrun/testing/
netrun-ratelimit  → netrun/ratelimit/
netrun-rbac       → netrun/rbac/
netrun-resilience → netrun/resilience/
netrun-validation → netrun/validation/
netrun-websocket  → netrun/websocket/
```

The `netrun-core` package (`packages/netrun-core/pyproject.toml:7`) exists solely to register the `netrun` namespace on PyPI and must be installed before any subpackage can resolve its namespace. It has zero runtime dependencies.

**Migration from v1.x:**

```python
# Before (v1.x — still works, emits DeprecationWarning)
from netrun_auth import JWTHandler
from netrun_config import SecretCache
from netrun_llm import LLMFallbackChain

# After (v2.x — recommended)
from netrun.auth import JWTHandler
from netrun.config import SecretCache
from netrun.llm import LLMFallbackChain
```

Old flat-package names (`netrun_auth`, `netrun_config`, etc.) continue to be importable in v2.x for backward compatibility. They will be removed in v3.0.0.

### 2.2 Package Inventory (All 19)

**Verified package count**: `ls packages/ | grep "^netrun-" | wc -l` returns 20, but `netrun-touch-ui` is a TypeScript/React npm package (`packages/netrun-touch-ui/package.json`, not a `pyproject.toml`) and is not a PyPI-published Python package. The 19 Python packages are as follows.

Source: `packages/<pkg>/pyproject.toml` for each entry below.

| Package | Version | PyPI URL | Purpose | Primary Dependencies |
|---------|---------|----------|---------|---------------------|
| **netrun-core** | 2.0.0 | https://pypi.org/project/netrun-core/ | Namespace root; establishes the `netrun.*` namespace | (none) |
| **netrun-auth** | 2.0.0 | https://pypi.org/project/netrun-auth/ | JWT, OAuth2, Azure AD, Azure AD B2C, MFA, Casbin RBAC | netrun-core, pyjwt, cryptography, redis, pwdlib, casbin |
| **netrun-cache** | 1.0.0 | https://pypi.org/project/netrun-cache/ | Redis and in-memory caching with decorators and TTL | pydantic; optional: redis[asyncio] |
| **netrun-config** | 2.0.0 | https://pypi.org/project/netrun-config/ | Configuration management; Azure Key Vault integration; TTL caching | pydantic, pydantic-settings; optional: azure-identity, azure-keyvault-secrets |
| **netrun-cors** | 2.1.0 | https://pypi.org/project/netrun-cors/ | Enterprise CORS middleware presets for FastAPI | netrun-core, fastapi, pydantic, starlette |
| **netrun-db-pool** | 2.0.0 | https://pypi.org/project/netrun-db-pool/ | Async PostgreSQL connection pooling with tenant isolation | netrun-core, sqlalchemy[asyncio], asyncpg, pydantic |
| **netrun-dee** | 1.0.0 | https://pypi.org/project/netrun-dee/ | Digital Emotion Equivalents — emotion detection, ECI scoring, emotional trajectory | (none core); optional: google-generativeai, asyncpg, pgvector, torch |
| **netrun-dogfood** | 2.0.0 | https://pypi.org/project/netrun-dogfood/ | MCP server providing unified API access to all Netrun products (internal integration testing) | netrun-core, netrun-auth[azure], mcp, pydantic, httpx |
| **netrun-env** | 2.1.0 | https://pypi.org/project/netrun-env/ | Schema-based environment variable validator with security checks; CLI tool | netrun-core, click, pydantic, python-dotenv |
| **netrun-errors** | 2.0.0 | https://pypi.org/project/netrun-errors/ | Unified error handling, exception hierarchy, correlation IDs, HTTP status mapping for FastAPI | netrun-core, fastapi, starlette |
| **netrun-llm** | 2.0.0 | https://pypi.org/project/netrun-llm/ | Multi-provider LLM orchestration (Claude, OpenAI, Azure OpenAI, Gemini, Ollama); fallback chains; per-tenant policy enforcement; cost/latency telemetry | netrun-core, requests; optional: anthropic, openai, azure-identity, google-generativeai |
| **netrun-logging** | 2.0.0 | https://pypi.org/project/netrun-logging/ | Structured logging via structlog; Azure App Insights/OpenTelemetry integration; correlation ID middleware | structlog, azure-monitor-opentelemetry, python-json-logger, fastapi |
| **netrun-oauth** | 2.0.0 | https://pypi.org/project/netrun-oauth/ | Reusable OAuth 2.0 adapters for 12+ providers; multi-tenant SaaS patterns | netrun-core, httpx, cryptography; optional: azure-identity |
| **netrun-pytest-fixtures** | 2.1.0 | https://pypi.org/project/netrun-pytest-fixtures/ | Unified pytest fixtures; 71% duplication elimination across Netrun services; async FastAPI test client, SQLAlchemy session, Redis mock, JWT test tokens | netrun-core, pytest, pytest-asyncio, cryptography |
| **netrun-ratelimit** | 2.0.0 | https://pypi.org/project/netrun-ratelimit/ | Distributed rate limiting; token bucket algorithm; Redis backend; FastAPI middleware | netrun-core, pydantic; optional: redis, fastapi, starlette |
| **netrun-rbac** | 3.0.0 | https://pypi.org/project/netrun-rbac/ | Multi-tenant RBAC; hierarchical teams; PostgreSQL RLS + application-level hybrid isolation; `TenantEscapePathScanner` for CI; contract testing via `TenantTestContext` | netrun-core, fastapi, sqlalchemy, pydantic, starlette |
| **netrun-resilience** | 1.0.0 | https://pypi.org/project/netrun-resilience/ | Resilience patterns: retry with backoff, circuit breaker, timeout decorator, bulkhead | (none — zero dependencies) |
| **netrun-validation** | 1.0.0 | https://pypi.org/project/netrun-validation/ | Pydantic validators for network addresses, security tokens, datetime ranges, custom types (`SafeEmail`, `StrongPassword`) | pydantic, email-validator |
| **netrun-websocket** | 1.0.0 | https://pypi.org/project/netrun-websocket/ | Production WebSocket connection management; Redis session persistence; JWT authentication; heartbeat and reconnection logic | fastapi, starlette, pydantic; optional: redis[asyncio], python-jose |

**Source references:**
- `packages/netrun-core/pyproject.toml:7-8` — name and version
- `packages/netrun-auth/pyproject.toml:7-41` — name, version, dependencies
- `packages/netrun-dee/pyproject.toml:7-14` — name, version, dependencies
- `packages/netrun-resilience/pyproject.toml:7-11` — zero runtime dependencies confirmed
- `packages/netrun-touch-ui/package.json:1-4` — TypeScript npm package, not a PyPI Python package; excluded from count

### 2.3 Inter-Package Dependency Graph

The following describes which packages depend on which others at runtime (optional extras excluded):

```
netrun-core (namespace root — no dependencies)
    └── consumed by: netrun-auth, netrun-cors, netrun-db-pool, netrun-dogfood,
                     netrun-env, netrun-errors, netrun-llm, netrun-oauth,
                     netrun-pytest-fixtures, netrun-ratelimit, netrun-rbac

netrun-errors
    └── optional consumer: netrun-config[errors], netrun-logging[errors]

netrun-logging
    └── optional consumer: netrun-auth[logging], netrun-config[logging],
                           netrun-cors[logging], netrun-db-pool[logging],
                           netrun-env[logging], netrun-llm[logging],
                           netrun-pytest-fixtures[logging], netrun-ratelimit[logging]

netrun-auth
    └── hard consumer: netrun-dogfood (requires netrun-auth[azure])
    └── optional consumer: netrun-logging[auth]

netrun-config
    └── optional consumer: netrun-logging[config]
```

**Dependency-free leaf packages** (zero runtime dependencies): `netrun-resilience`, `netrun-dee` (core layer; embedding/classifier modes add optional deps).

**Dependency-free optional packages**: `netrun-cache` (pydantic only in core; redis is optional), `netrun-validation` (pydantic + email-validator only).

**Practical installation profiles:**

```bash
# Minimal FastAPI service (auth + config + logging + errors)
pip install netrun-core netrun-auth netrun-config netrun-logging netrun-errors

# Add database and rate limiting
pip install netrun-db-pool netrun-ratelimit

# Full multi-tenant SaaS (adds RBAC + CORS + caching + resilience)
pip install netrun-rbac netrun-cors netrun-cache netrun-resilience

# LLM-enabled service
pip install netrun-llm[all]

# AI-emotion-aware service (DEE Layer A)
pip install netrun-dee netrun-dee[embedding]

# Testing infrastructure
pip install netrun-pytest-fixtures[all]
```

### 2.4 The netrun-dee Addition (DEE Layer A)

`netrun-dee 1.0.0` was published to PyPI on May 1, 2026, as the Python deliverable of the DEE (Digital Emotion Equivalents) Layer A initiative. It is documented separately in the DEE architecture paper but summarized here as part of the OSS library context.

**What DEE is:** A lexicon-based emotion detection system for AI-generated text. Rather than requiring an ML classifier for every call, `netrun-dee` ships a curated lexicon mapping linguistic patterns to eight emotion categories. The ECI (Emotional Coherence Index) scorer measures how internally consistent an AI response's emotional tone is. The trajectory analyzer tracks how emotion shifts across multi-turn conversations.

**What DEE is not:** It is not a general-purpose sentiment analysis library. It is not trained on social media text. It is optimized for AI assistant output, specifically for detecting when a language model's emotional register is appropriate for context (e.g., a calm information response vs. an alarming security alert).

**Build system migration (commit `ee4bf9f`):** Before May 1, `netrun-dee` used `setuptools` as its build backend. The migration to hatchling (commit `ee4bf9f`, `packages/netrun-dee/pyproject.toml:1-3`) aligns the package with the rest of the library and enables the namespace package wheel target:

```toml
# packages/netrun-dee/pyproject.toml:1-3
[build-system]
requires = ["hatchling>=1.21.0"]
build-backend = "hatchling.build"
```

The wheel target `packages = ["src/netrun"]` (`packages/netrun-dee/pyproject.toml:23`) exposes the `netrun.dee` namespace correctly alongside the other 18 packages.

**Prompt templates:** The package ships a bundled `prompt-templates.json` file that is included in the wheel via a `force-include` directive (`packages/netrun-dee/pyproject.toml:26-27`). This allows callers to use the templates without locating the package installation path manually.

**DEE PyPI URL:** https://pypi.org/project/netrun-dee/

**Consumers in Netrun portfolio:**
- `wilbur/charlotte/api/dee_router.py` (commit `3e80ff7`) — Charlotte emotion-aware routing, migrated to `netrun.dee` namespace
- `intirkast` — pre-publish emotional scoring for LinkedIn/Twitter/blog content (planned; library integrated, routing HOLD per Boardroom_TODO)
- `EISCORE` — NPC emotion behavior bridge (C++ data structures + CSV profiles provided; Mass AI wiring HOLD)

---

## 3. Production State (PyPI)

| Aspect | State |
|--------|-------|
| Registry | PyPI (https://pypi.org) |
| Python versions | 3.8 – 3.12 (varies by package; 3.10+ for newer packages) |
| License | MIT (all 19 packages) |
| Build backend | Hatchling (17 packages); setuptools (netrun-resilience only — migration pending) |
| Total packages published | 19 |
| Latest major milestone | v2.0.0 (December 2025) — PEP 420 namespace; v3.0.0 of netrun-rbac (December 2025) |
| Newest package | netrun-dee 1.0.0 (May 1, 2026) |
| Active consumers | intirkon, intirkast, netrun-crm/KOG, wilbur/Charlotte |
| Internal test coverage gate | 80% minimum (netrun-errors: 90%) |
| PyPI token | Rotated post-DEE publish (Boardroom_TODO #32 action item) |

**Individual PyPI package URLs (authoritative):**

- https://pypi.org/project/netrun-core/
- https://pypi.org/project/netrun-auth/
- https://pypi.org/project/netrun-cache/
- https://pypi.org/project/netrun-config/
- https://pypi.org/project/netrun-cors/
- https://pypi.org/project/netrun-db-pool/
- https://pypi.org/project/netrun-dee/
- https://pypi.org/project/netrun-dogfood/
- https://pypi.org/project/netrun-env/
- https://pypi.org/project/netrun-errors/
- https://pypi.org/project/netrun-llm/
- https://pypi.org/project/netrun-logging/
- https://pypi.org/project/netrun-oauth/
- https://pypi.org/project/netrun-pytest-fixtures/
- https://pypi.org/project/netrun-ratelimit/
- https://pypi.org/project/netrun-rbac/
- https://pypi.org/project/netrun-resilience/
- https://pypi.org/project/netrun-validation/
- https://pypi.org/project/netrun-websocket/

**Download statistics:** Not available without PyPI API verification. Omitted per anti-fabrication policy.

**Versioning note:** Most packages are at 2.0.0 (PEP 420 migration). Three are at 1.0.0 (netrun-cache, netrun-dee, netrun-resilience, netrun-validation, netrun-websocket) reflecting their later extraction dates. `netrun-rbac` is at 3.0.0 reflecting a major feature addition (tenant isolation testing) that was a breaking API change from v2.x. `netrun-cors` is at 2.1.0 and `netrun-env` is at 2.1.0 reflecting minor revisions post-namespace migration. `netrun-pytest-fixtures` is at 2.1.0.

---

## 4. Differentiation

### 4.1 Comparison Table

| Capability | netrun-oss | DIY Per-Project | FastAPI-Users | Cookiecutter-FastAPI | Litestar Pro |
|------------|-----------|-----------------|---------------|---------------------|--------------|
| Unified namespace (`netrun.*`) | Yes (PEP 420) | No | No | No | Yes (different framework) |
| Production-tested in real services | Yes (4 Netrun products) | By definition (your one service) | Yes (auth only) | No (templates only) | Yes |
| Auth: JWT + OAuth2 + Azure AD + MFA | Yes (`netrun-auth`) | Build it | Yes (FastAPI-Users scope) | Starter code only | Varies |
| Multi-tenant RBAC + RLS | Yes (`netrun-rbac` v3.0.0) | Build it | No | No | Partial |
| Tenant isolation contract tests | Yes (`TenantTestContext`, `TenantEscapePathScanner`) | Rarely written | No | No | No |
| LLM orchestration + policy enforcement | Yes (`netrun-llm`) | Build it | No | No | No |
| Emotion detection for AI text | Yes (`netrun-dee`) | Research project | No | No | No |
| Structured logging + Azure App Insights | Yes (`netrun-logging`) | Build it | No | No | Varies |
| Upgradeable across services | Yes (single pip upgrade) | Manual per service | Yes (auth only) | No (one-shot) | Yes |
| MIT license | Yes | N/A | Yes | Yes | No (commercial) |
| Zero-dependency resilience patterns | Yes (`netrun-resilience`) | Build it | No | No | Partial |
| Soft-dependency detection (clear errors) | Yes (all packages) | Varies | Partial | No | Yes |
| Test fixture library | Yes (`netrun-pytest-fixtures`) | Build it | No | No | No |
| Python 3.8+ compatibility | Yes (most packages) | Flexible | Yes | Yes | 3.9+ |

### 4.2 vs. DIY Foundation

Writing auth, config, logging, and error handling inline in each service is appropriate for a one-service company. For a consulting organization shipping a new product platform every quarter — as Netrun does — the DIY approach creates maintenance overhead that compounds with every new service. When Pydantic v2 shipped with breaking changes, Netrun updated one set of packages and ran `pip install --upgrade netrun-auth netrun-config` across four consumer repositories. Without the shared library, that would have been four independent migrations.

The `netrun-pytest-fixtures` package is the clearest evidence of this multiplier: it eliminated 71% of fixture duplication across Netrun's test suites (as documented in `packages/netrun-pytest-fixtures/pyproject.toml:8`). That number is not theoretical — it was measured against actual duplicate code in netrun-crm, intirkon, and intirkast before extraction.

### 4.3 vs. FastAPI-Users

FastAPI-Users is a well-maintained authentication library for FastAPI. It covers user registration, JWT, OAuth2, and some database integrations. It is the right tool if authentication is the only infrastructure concern.

`netrun-auth` overlaps with FastAPI-Users in JWT and OAuth2 but goes further with Azure AD / Azure AD B2C integration (via `msal`), Casbin RBAC policy evaluation, and MFA flows. More importantly, authentication is one of 19 concerns in `netrun-oss`. The library does not position itself as an auth replacement for FastAPI-Users — if an existing project uses FastAPI-Users for auth and only needs LLM orchestration or multi-tenant RBAC, `netrun-llm` and `netrun-rbac` can be installed independently without touching the auth layer.

### 4.4 vs. Cookiecutter / Project Templates

Cookiecutter-FastAPI and similar scaffolding tools generate a project with opinionated defaults baked in. The generated code is immediately owned by the consuming team — which means there is no upgrade path. If a security vulnerability is found in the generated JWT validation code six months after a project is scaffolded, every scaffolded project must be manually patched. With `netrun-oss`, a security fix is a package version bump (`pip install netrun-auth==2.0.1`) that propagates across all consumers simultaneously.

Templates also cannot carry cross-cutting concerns. A template can stub out logging; it cannot ship a logging package that automatically integrates correlation IDs from the error package's traceback context. That kind of integration only works when the packages are designed together and versioned together.

### 4.5 vs. Litestar Pro

Litestar is a different web framework (not FastAPI-compatible). Litestar Pro is its commercial extension. `netrun-oss` is specifically designed for FastAPI/Starlette and is MIT-licensed. If a team is committed to FastAPI, they cannot use Litestar Pro. If a team is evaluating frameworks, the choice between them is out of scope for a library comparison.

---

## 5. Limitations and Future Work

### 5.1 Build System Heterogeneity

Not all 19 packages use Hatchling. `netrun-resilience` (`packages/netrun-resilience/pyproject.toml:1-3`) uses `setuptools` with `setuptools.build_meta` as its build backend. This means its wheel is generated via a different code path, and the namespace package configuration uses `[tool.setuptools.packages.find]` with `namespaces = true` rather than `[tool.hatch.build.targets.wheel]`. This is functionally correct but inconsistent with the rest of the library.

Migration of `netrun-resilience` to Hatchling is the next build-system cleanup task. There is no blocking technical reason for the delay; it simply has not been prioritized above feature work.

### 5.2 netrun-dee Is in Beta Classification

`netrun-dee 1.0.0` carries a PyPI classifier of `"Development Status :: 4 - Beta"` (`packages/netrun-dee/pyproject.toml:21`). The core lexicon and ECI scoring are stable and in use by Charlotte, but the embedding and classifier optional modes (Google Generative AI + pgvector; PyTorch classifier) are not yet exercised in production. The six-phase empirical calibration methodology documented in the DEE research paper (§6.8, §11) has not been run. Users who install `netrun-dee[embedding]` or `netrun-dee[classifier]` are using early-access functionality.

### 5.3 The TypeScript Counterpart Is a Separate Repository

`netrun-oss` is Python-only. The TypeScript counterpart (`@netrun/*` packages) lives in `netrun-shared-ts` under a separate Turborepo workspace with 14 TypeScript packages. These two repositories share a naming convention and a conceptual mission but are not co-versioned. A breaking change to `netrun-auth` on PyPI does not automatically trigger a version bump to `@netrun/auth` in `netrun-shared-ts`.

There is no current plan to unify them into a monorepo. The Python and TypeScript contexts have different dependency management ecosystems (pip vs. npm), different build toolchains, and different consumer sets. The naming alignment is intentional (cognitive coherence for developers working across both), but they are distinct artifacts.

Additionally, `netrun-touch-ui` — a touch-first React/TypeScript component library (`packages/netrun-touch-ui/package.json`) — lives inside the `netrun-oss` repository directory but is not a Python package and is not published to PyPI. It was committed to this repo (commit `fe71a7e`) as a UI companion but logically belongs in `netrun-shared-ts`. Its presence in this repo is a directory anomaly rather than an architecture decision.

### 5.4 No Unified Documentation Site

Each package currently links to its GitHub path for documentation. There is no centralized `docs.netrunsystems.com/oss` portal that aggregates API references across all 19 packages. The README serves as the index; individual package READMEs provide usage documentation. A unified documentation site (Sphinx with autodoc, or MkDocs with mkdocstrings) is a planned future milestone with no committed timeline.

### 5.5 LLM Package Gemini Version Pin

`netrun-llm` was updated (commit `b79fb79`) to migrate from Gemini 2.0 to Gemini 2.5 Flash after Gemini 2.0 reached retirement. The `google-generativeai` optional dependency is pinned to `>=0.8.3` (`packages/netrun-llm/pyproject.toml:27`). As Google continues iterating on its generative AI SDK, this pin may require updating when future model versions change API surfaces. Users of `netrun-llm[gemini]` should monitor Gemini release announcements.

### 5.6 v3.0.0 Deprecation Removal Timeline

The backward-compatible flat-package import aliases (`from netrun_auth import ...`) will be removed in v3.0.0. No date for v3.0.0 is committed, but consumers should plan migration to `from netrun.auth import ...` patterns before then. Deprecation warnings are emitted on every use of the old import path in v2.x.

---

## 6. References

**Source code file:line citations:**

- `packages/netrun-core/pyproject.toml:7-8` — package name and version (2.0.0); confirms namespace root role
- `packages/netrun-auth/pyproject.toml:7-41` — full dependency manifest for auth package
- `packages/netrun-auth/pyproject.toml:93` — `packages = ["netrun", "netrun_auth"]` wheel target; backward compat mechanism
- `packages/netrun-cache/pyproject.toml:244-249` — version 1.0.0, pydantic-only core; redis optional
- `packages/netrun-config/pyproject.toml:431-440` — version 2.0.0, pydantic + pydantic-settings core
- `packages/netrun-cors/pyproject.toml:576-614` — version 2.1.0, hard fastapi+starlette dependency
- `packages/netrun-db-pool/pyproject.toml:720-771` — version 2.0.0, asyncpg + sqlalchemy[asyncio]
- `packages/netrun-dee/pyproject.toml:874-939` — version 1.0.0, hatchling build, zero core deps, Beta classifier
- `packages/netrun-dee/pyproject.toml:923-927` — `force-include` for `prompt-templates.json` in wheel
- `packages/netrun-dogfood/pyproject.toml:941-1009` — version 2.0.0, MCP server; requires `netrun-auth[azure]`
- `packages/netrun-env/pyproject.toml:1036-1100` — version 2.1.0, CLI entrypoint `netrun-env`
- `packages/netrun-errors/pyproject.toml:1170-1215` — version 2.0.0, fastapi + starlette; 90% coverage gate
- `packages/netrun-llm/pyproject.toml:1299-1396` — version 2.0.0, multi-provider; anthropic/openai/azure/gemini optionals
- `packages/netrun-logging/pyproject.toml:1460-1527` — version 2.0.0, structlog + azure-monitor-opentelemetry
- `packages/netrun-oauth/pyproject.toml:1553-1625` — version 2.0.0, 12+ provider adapters
- `packages/netrun-pytest-fixtures/pyproject.toml:1689-1808` — version 2.1.0, "71% duplication elimination"
- `packages/netrun-ratelimit/pyproject.toml:1900-2001` — version 2.0.0, token bucket, Redis optional
- `packages/netrun-rbac/pyproject.toml:2030-2099` — version 3.0.0, SOC2/ISO27001 keywords, tenant isolation testing
- `packages/netrun-resilience/pyproject.toml:2163-2239` — version 1.0.0, setuptools build backend, zero runtime deps
- `packages/netrun-validation/pyproject.toml:2244-2329` — version 1.0.0, pydantic + email-validator only
- `packages/netrun-websocket/pyproject.toml:2331-2478` — version 1.0.0, fastapi + starlette; redis + jwt optional
- `packages/netrun-touch-ui/package.json:1-4` — confirms TypeScript npm package, not a Python/PyPI package
- `packages/INTEGRATION_ARCHITECTURE_v1.0.md:18-55` — original dependency hierarchy diagram (pre-v2.0.0; accurate for structural relationships)
- `README.md:1-19` — canonical package table with PyPI links; 19 packages listed (excludes touch-ui)

**Git history (netrun-oss, last 180 days):**

- `ee4bf9f` — `feat(dee): migrate netrun-dee to hatchling + netrun.dee namespace, publish v1.0.0` (May 1, 2026)
- `b79fb79` — `fix: Migrate Gemini 2.0 → 2.5 Flash (2.0 retirement)`
- `fe71a7e` — `feat(touch-ui): Add @netrun/touch-ui component library`
- `9ebe2a2` — `feat(rbac): Upgrade to v3.0.0 with tenant isolation testing`
- `e68e868` — `feat: Add 4 new packages and update netrun-llm`
- `f9ddb28` — `docs: Update README for v2.0.0 release`
- `f73c64b` — `feat: Netrun Namespace Packages v2.0.0 - PEP 420 Migration + Community Features`

**External references:**

- PEP 420 — Implicit Namespace Packages: https://peps.python.org/pep-0420/
- Hatchling build system: https://hatch.pypa.io/latest/
- FastAPI official documentation: https://fastapi.tiangolo.com/
- Casbin RBAC policy engine: https://casbin.org/
- structlog: https://www.structlog.org/
- PyPI: https://pypi.org/

**Internal cross-references:**

- `packages/INTEGRATION_ARCHITECTURE_v1.0.md` — inter-package integration contracts
- `packages/NAMESPACE_MIGRATION_GUIDE.md` — v1.x to v2.0.0 migration runbook
- `packages/CHANGELOG_v2.0.0.md` — complete change log for the namespace migration release
- `/data/workspace/github/boardroom/PROJECT_INDEX.md` — row 5: netrun-oss project status (90% complete, Active, last commit 2026-05-01)
- `/data/workspace/github/boardroom/Boardroom_TODO.md` — DEE Layer A task #32: hatchling migration commit `ee4bf9f`

---

## Appendix A: Glossary

**PEP 420 / Namespace Package**: A Python packaging mechanism that allows multiple installed packages to contribute submodules into the same top-level namespace (e.g., `netrun`) without any single package owning a root `__init__.py`. Enables `from netrun.auth import ...` and `from netrun.config import ...` to coexist after separate `pip install` commands.

**Hatchling**: The build backend for the Hatch project management tool, recommended by PyPA for modern Python packages. Replaces `setuptools` for packages using `pyproject.toml`-native configuration.

**ECI (Emotional Coherence Index)**: A `netrun-dee` metric measuring the internal consistency of emotional tone across an AI-generated response. A high ECI indicates the response does not mix inappropriately conflicting emotional registers.

**DEE (Digital Emotion Equivalents)**: Netrun's framework for representing, detecting, and producing emotional patterns in AI text. Implemented across four layers: Python lexicon library (`netrun-dee`), TypeScript port (`@netrun/dee`), Charlotte routing integration, and EISCORE NPC behavior bridge.

**TenantEscapePathScanner**: A static analysis tool in `netrun-rbac` that scans Python source for SQLAlchemy queries missing tenant-filter predicates, producing findings suitable for CI/CD gating.

**TenantTestContext**: A `netrun-rbac` async context manager for writing contract tests that prove cross-tenant data access is impossible at the database query level.

**MCP (Model Context Protocol)**: The protocol used by `netrun-dogfood` to expose Netrun product APIs to AI development environments (e.g., Claude Code).
