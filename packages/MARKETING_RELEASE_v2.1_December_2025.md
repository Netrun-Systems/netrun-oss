# Marketing Release: Netrun Service Library v2.1 - December 2025

**Release Date:** December 30, 2025
**Total Packages:** 18 (4 new packages, 1 major upgrade)
**Total Tests:** 1,100+ passing tests
**Coverage:** >80% on all packages (avg 92%)

---

## Executive Summary

The Netrun Service Library expands to 18 packages with the addition of four production-ready infrastructure packages: caching, resilience patterns, validation, and WebSocket management. This release also adds Azure OpenAI and Google Gemini adapters to the LLM orchestration package, and introduces **netrun-rbac v3.0.0** with comprehensive tenant isolation testing, hierarchical teams, and resource sharing.

---

## Reddit Post

### Suggested Subreddits
- r/Python
- r/FastAPI
- r/SaaS
- r/selfhosted

---

### Post Title

**[Update] Netrun FastAPI Building Blocks - 4 New Packages + RBAC v3 with Tenant Isolation Testing (18 total)**

---

### Post Body

Two weeks ago I shared the Netrun namespace packages v2.0 with LLM policies and tenant isolation testing. Today I'm releasing v2.1 with four entirely new packages plus a major RBAC upgrade that addresses the most critical multi-tenant security concern: proving tenant isolation.

**TL;DR:** 18 packages now on PyPI. New packages cover caching (Redis/memory), resilience patterns (retry/circuit breaker), Pydantic validation, and WebSocket session management. Also added Azure OpenAI and Gemini adapters to netrun-llm. Plus **netrun-rbac v3.0.0** with hierarchical teams, resource sharing, and comprehensive tenant isolation testing.

---

### What's New

**1. netrun-cache - Two-Tier Caching**

Redis and in-memory caching with a clean decorator API. The pattern I kept copy-pasting between projects, now extracted.

```python
from netrun.cache import CacheManager, cached

cache = CacheManager()

@cached(ttl=300, namespace="users")
async def get_user(user_id: str):
    # Expensive database lookup - cached for 5 minutes
    return await db.fetch_user(user_id)

# Invalidate when data changes
await cache.invalidate("users", f"user:{user_id}")
```

Features:
- L1 (memory) + L2 (Redis) caching
- `@cached` decorator with TTL and namespace
- Automatic serialization
- Batch operations (`get_many`, `set_many`)
- 89% test coverage, 177 tests

---

**2. netrun-resilience - Distributed Systems Patterns**

Retry, circuit breaker, timeout, and bulkhead patterns. Async-first, works with both sync and async code.

```python
from netrun.resilience import retry, circuit_breaker, timeout

@retry(max_attempts=3, backoff_factor=2.0, jitter=True)
@circuit_breaker(failure_threshold=5, recovery_timeout=30)
@timeout(seconds=10)
async def call_external_api():
    return await client.fetch_data()
```

Features:
- Exponential backoff with jitter
- Circuit breaker with half-open state
- Timeout for both sync and async functions
- Bulkhead for resource isolation
- 98% test coverage, 45 tests

---

**3. netrun-validation - Pydantic Validators**

Comprehensive validators I kept rewriting: IP addresses, CIDRs, URLs, API keys, JWT secrets, email formats, datetime parsing.

```python
from netrun.validation import validate_ip_address, validate_cidr_notation
from netrun.validation.custom_types import SafeEmail, StrongPassword
from netrun.validation.security import validate_api_key_format

class ServiceConfig(BaseModel):
    email: SafeEmail
    password: StrongPassword
    api_key: str
    allowed_cidrs: list[str]

    @field_validator("api_key")
    def check_key(cls, v):
        return validate_api_key_format(v, min_length=32)

    @field_validator("allowed_cidrs")
    def check_cidrs(cls, v):
        return [validate_cidr_notation(cidr) for cidr in v]
```

Features:
- Network validators (IP, CIDR, URL, hostname, port)
- Security validators (API keys, JWT secrets, encryption keys)
- DateTime utilities with timezone handling
- Custom Pydantic types with built-in validation
- 98% test coverage, 233 tests

---

**4. netrun-websocket - Production WebSocket Management**

Session management, heartbeats, Redis-backed state, JWT auth. The WebSocket boilerplate I never want to write again.

```python
from netrun.websocket import WebSocketSessionManager

manager = WebSocketSessionManager(redis_url="redis://localhost:6379")
await manager.initialize()

# In your WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = await manager.create_connection(
        websocket=websocket,
        user_id=current_user.id,
        metadata={"room": "general"}
    )

    try:
        while True:
            data = await websocket.receive_json()
            await manager.update_heartbeat(connection_id)
            # Handle message...
    finally:
        await manager.disconnect(connection_id, save_state=True)
```

Features:
- Redis-backed session persistence
- JWT authentication middleware
- Heartbeat monitoring with auto-cleanup
- Connection pooling and metrics
- Namespace support for multi-tenant apps
- Reconnection handling with state restoration
- 94% test coverage, 205 tests

---

**5. netrun-llm Updates - Azure OpenAI & Gemini**

Added two new LLM adapters plus improved test coverage:

```python
from netrun.llm import LLMFallbackChain
from netrun.llm.adapters import (
    AzureOpenAIAdapter,
    GeminiAdapter,
    ClaudeAdapter,
    OllamaAdapter
)

# Multi-cloud with local fallback
chain = LLMFallbackChain([
    AzureOpenAIAdapter(model="gpt-4o"),      # Primary: Azure
    GeminiAdapter(model="gemini-1.5-pro"),   # Fallback: Google
    ClaudeAdapter(model="claude-3-haiku"),   # Fallback: Anthropic
    OllamaAdapter(model="llama3:8b")         # Local fallback
])

response = await chain.execute("Analyze this data...")
```

New adapters:
- **AzureOpenAIAdapter**: Azure OpenAI Service with managed identity support
- **GeminiAdapter**: Google Gemini with quota tracking and free tier support

---

**6. netrun-rbac v3.0.0 - Tenant Isolation Testing & Hierarchical Teams**

This is the big one for SaaS builders. In v2.x, we had basic RBAC with PostgreSQL RLS. In v3.0.0, we've added the tools to **prove** tenant isolation works - critical for SOC2/ISO27001 compliance and peace of mind.

```python
from netrun.rbac import (
    # New v3 middleware - one-line setup
    setup_tenancy_middleware, TenancyConfig, IsolationMode,
    # Tenant isolation testing
    TenantTestContext, assert_tenant_isolation,
    TenantEscapePathScanner, ci_fail_on_findings,
)

# One-line middleware setup
app = FastAPI()
setup_tenancy_middleware(
    app,
    config=TenancyConfig(isolation_mode=IsolationMode.HYBRID),
    get_session=get_db_session
)

# Contract test: Tenant B MUST NOT see Tenant A's data
async with TenantTestContext(db_session) as ctx:
    # Create secret data in Tenant A
    secret = Item(name="Secret", tenant_id=ctx.tenant_a_id)
    session.add(secret)
    await session.commit()

    # Switch to Tenant B
    await ctx.switch_to_tenant_b()

    # This MUST return empty - cross-tenant access is impossible
    result = await session.execute(select(Item))
    assert len(result.scalars().all()) == 0  # PASSES

# CI/CD escape path scanner
scanner = TenantEscapePathScanner()
findings = scanner.scan_directory("./src")
sys.exit(ci_fail_on_findings(findings))  # Fails build on critical findings
```

**New v3.0.0 Features:**
- **Hierarchical Teams**: Sub-teams with inherited permissions
- **Resource Sharing**: Share resources across users/teams/tenants
- **TenantQueryService**: Generic auto-filtered CRUD service
- **Hybrid Isolation**: PostgreSQL RLS + application-level filtering
- **Contract Testing**: `TenantTestContext` proves isolation is impossible
- **Escape Path Scanner**: Static analysis finds SQL without tenant filters
- **Background Task Context**: `BackgroundTaskTenantContext` for Celery/workers
- **Compliance Docs**: Auto-generated SOC2/ISO27001/NIST documentation

**Backward Compatible**: All v2.x APIs still work.

---

### Full Package List (18 packages)

| Package | Version | Tests | Coverage | What It Does |
|---------|---------|-------|----------|--------------|
| netrun-core | 2.0.0 | - | - | Namespace foundation |
| netrun-auth | 2.0.0 | 89 | 95% | JWT, OAuth2, RBAC |
| netrun-cache | **1.0.0** | **177** | **89%** | **Redis/memory caching** |
| netrun-config | 2.0.0 | 67 | 92% | Azure Key Vault, settings |
| netrun-cors | 2.0.0 | 23 | 88% | CORS middleware |
| netrun-db-pool | 2.0.0 | 45 | 90% | Async connection pooling |
| netrun-dogfood | 2.0.0 | 12 | 85% | Internal testing |
| netrun-env | 2.0.0 | 34 | 91% | Environment validation |
| netrun-errors | 2.0.0 | 56 | 94% | Error handling |
| netrun-llm | **2.0.0** | **393** | **83%** | **LLM orchestration** |
| netrun-logging | 2.0.0 | 78 | 96% | Structured logging |
| netrun-oauth | 2.0.0 | 45 | 89% | OAuth2 providers |
| netrun-pytest-fixtures | 2.0.0 | 67 | 87% | Test fixtures |
| netrun-ratelimit | 2.0.0 | 34 | 90% | Rate limiting |
| netrun-rbac | **3.0.0** | **78** | **93%** | **Tenant isolation + teams** |
| netrun-resilience | **1.0.0** | **45** | **98%** | **Retry, circuit breaker** |
| netrun-validation | **1.0.0** | **233** | **98%** | **Pydantic validators** |
| netrun-websocket | **1.0.0** | **205** | **94%** | **WebSocket sessions** |

**Bold** = new or significantly updated in this release

---

### Install

```bash
# New infrastructure packages
pip install netrun-cache netrun-resilience netrun-validation netrun-websocket

# With optional dependencies
pip install netrun-cache[redis]      # Redis support
pip install netrun-websocket[all]    # Redis + JWT auth
pip install netrun-llm[all]          # All LLM providers

# Full suite (18 packages)
pip install netrun-core netrun-auth netrun-cache netrun-config netrun-cors \
    netrun-db-pool netrun-dogfood netrun-env netrun-errors netrun-llm \
    netrun-logging netrun-oauth netrun-pytest-fixtures netrun-ratelimit \
    netrun-rbac netrun-resilience netrun-validation netrun-websocket
```

---

### Why These Four?

These aren't innovative new concepts - they're boring infrastructure that every FastAPI app needs. I kept copying the same patterns between projects:

1. **Caching**: Every app needs it, but setting up Redis fallback + memory cache + decorators takes time
2. **Resilience**: Circuit breakers and retries are essential for external API calls, but the boilerplate is tedious
3. **Validation**: IP addresses, CIDRs, API keys - I've written these validators dozens of times
4. **WebSocket**: Session management, heartbeats, reconnection - the boring parts of real-time features

Now they're packages with tests. Use them, fork them, or use them as reference implementations.

---

### What We're NOT Claiming

Same as before - transparency about where we are:

- These work in our development environments
- They have good test coverage (avg 92%)
- They're MIT licensed and free to use
- We're actively maintaining them

But we're pre-launch on our platforms, so no production-at-scale metrics yet. Use your judgment.

---

**Links:**
- PyPI: https://pypi.org/search/?q=netrun-
- GitHub: https://github.com/Netrun-Systems/netrun-oss
- All package README files have detailed docs

Questions or feedback? Happy to discuss implementation details.

---

## Blog Post Outline

**Title:** "Netrun Service Library v2.1: 4 New Packages + RBAC v3 Tenant Isolation Testing"

**Meta Description (155 chars):**
> Netrun adds caching, resilience, validation, WebSocket + RBAC v3 with tenant isolation testing. 18 Python packages, 1,100+ tests, SOC2/ISO27001 ready.

### Sections

1. **Introduction** (200 words)
   - The problem: infrastructure code duplication + proving tenant isolation
   - What we're releasing: 4 new packages + major RBAC upgrade
   - Total ecosystem: 18 packages, 1,100+ tests

2. **netrun-cache** (400 words)
   - Problem: every app needs caching
   - Solution: two-tier cache with decorator API
   - Code examples: basic usage, invalidation, batch ops
   - Optional deps: `[redis]`

3. **netrun-resilience** (400 words)
   - Problem: external API calls fail
   - Solution: retry, circuit breaker, timeout, bulkhead
   - Code examples: decorator stacking, circuit breaker states
   - Works with sync and async

4. **netrun-validation** (400 words)
   - Problem: rewriting validators for every project
   - Solution: comprehensive Pydantic validators
   - Code examples: network, security, datetime validators
   - Custom types: SafeEmail, StrongPassword

5. **netrun-websocket** (400 words)
   - Problem: WebSocket session management is complex
   - Solution: Redis-backed sessions with heartbeats
   - Code examples: connection lifecycle, reconnection
   - Optional deps: `[redis]`, `[auth]`, `[all]`

6. **netrun-llm Updates** (300 words)
   - New adapters: Azure OpenAI, Gemini
   - Multi-cloud fallback chains
   - Code example: 4-provider chain

7. **netrun-rbac v3.0.0 - The Big One** (500 words)
   - Problem: proving tenant isolation for compliance audits
   - Solution: contract testing + escape path scanning
   - New features: hierarchical teams, resource sharing
   - Code examples: TenantTestContext, TenantEscapePathScanner
   - Compliance mapping: SOC2, ISO27001, NIST

8. **Installation Guide** (200 words)
   - Individual packages
   - With optional dependencies
   - Full suite installation

9. **Test Coverage & Quality** (150 words)
   - 1,100+ tests total
   - >80% coverage on all packages
   - CI/CD pipeline

10. **Conclusion & CTA** (150 words)
   - Summary of value proposition
   - Links to PyPI, GitHub
   - Request for feedback

---

## LinkedIn Post

**Netrun Service Library v2.1: 18 Python packages for FastAPI**

We just released 4 new packages + a major RBAC upgrade to our open-source Python library:

**New Packages:**
- **netrun-cache** - Redis + memory caching with @cached decorator
- **netrun-resilience** - Retry, circuit breaker, timeout patterns
- **netrun-validation** - Pydantic validators for network, security, datetime
- **netrun-websocket** - Production WebSocket session management

**Major Upgrade:**
- **netrun-rbac v3.0.0** - Tenant isolation testing, hierarchical teams, resource sharing

The RBAC upgrade is the big one for SaaS builders. You can now **prove** tenant isolation works with contract tests and CI/CD escape path scanning. Critical for SOC2/ISO27001 compliance.

Plus Azure OpenAI and Gemini adapters for netrun-llm.

Total: 18 packages, 1,100+ tests, >80% coverage across the board.

MIT licensed. Use them, fork them, or just use them as reference.

pip install netrun-cache netrun-resilience netrun-validation netrun-websocket netrun-rbac

Links:
- PyPI: pypi.org/search/?q=netrun-
- GitHub: github.com/Netrun-Systems/netrun-oss

#Python #FastAPI #OpenSource #SaaS #MultiTenant #Security

---

## Twitter/X Thread

**Tweet 1:**
Netrun Service Library v2.1 is live - 18 Python packages for FastAPI

4 new packages + RBAC v3 major upgrade:
- netrun-cache (Redis/memory)
- netrun-resilience (retry, circuit breaker)
- netrun-validation (Pydantic validators)
- netrun-websocket (session management)
- netrun-rbac v3.0.0 (tenant isolation testing!)

1,100 tests. MIT licensed.

---

**Tweet 2:**
netrun-rbac v3.0.0: The big one for SaaS builders

Now you can PROVE tenant isolation works:

```python
async with TenantTestContext(db) as ctx:
    secret = Item(tenant_id=ctx.tenant_a_id)
    await ctx.switch_to_tenant_b()
    items = await session.query(Item)
    assert len(items) == 0  # MUST pass
```

Critical for SOC2/ISO27001 audits.

---

**Tweet 3:**
netrun-cache: Two-tier caching with a clean API

```python
@cached(ttl=300, namespace="users")
async def get_user(user_id: str):
    return await db.fetch_user(user_id)
```

89% coverage, 177 tests. pip install netrun-cache[redis]

---

**Tweet 4:**
netrun-resilience: Distributed systems patterns

```python
@retry(max_attempts=3, backoff_factor=2.0)
@circuit_breaker(failure_threshold=5)
@timeout(seconds=10)
async def call_api():
    ...
```

98% coverage, 45 tests. pip install netrun-resilience

---

**Tweet 5:**
netrun-websocket: Production WebSocket management

- Redis-backed sessions
- Heartbeat monitoring
- JWT authentication
- Reconnection handling

94% coverage, 205 tests. pip install netrun-websocket[all]

---

**Tweet 6:**
Also added Azure OpenAI and Gemini adapters to netrun-llm for multi-cloud LLM fallback chains.

Full package list: pypi.org/search/?q=netrun-
GitHub: github.com/Netrun-Systems/netrun-oss

---

## Email Newsletter

**Subject:** 4 New Packages + RBAC v3 with Tenant Isolation Testing

**Preview Text:** Netrun Service Library grows to 18 packages - now with SOC2/ISO27001 compliant isolation testing

---

Hi,

We've expanded the Netrun Service Library with four new infrastructure packages and a major RBAC upgrade:

**New Packages:**
1. **netrun-cache** - Redis and memory caching with @cached decorator
2. **netrun-resilience** - Retry, circuit breaker, timeout, bulkhead patterns
3. **netrun-validation** - Pydantic validators for network, security, datetime
4. **netrun-websocket** - WebSocket session management with Redis

**Major Upgrade - netrun-rbac v3.0.0:**
- Tenant isolation contract testing - prove cross-tenant access is impossible
- Hierarchical teams with sub-team support
- Resource-level sharing (user/team/tenant/external)
- CI/CD escape path scanner - catches SQL without tenant filters
- Background task context preservation for Celery/workers
- Auto-generated SOC2/ISO27001/NIST compliance documentation

**Also Updated:**
- netrun-llm now includes Azure OpenAI and Gemini adapters

**By The Numbers:**
- 18 total packages
- 1,100+ passing tests
- >80% coverage on all packages

All MIT licensed. Install with:
```
pip install netrun-cache netrun-resilience netrun-validation netrun-websocket netrun-rbac
```

The RBAC v3 upgrade is the big one for SaaS builders. If you're building multi-tenant apps and need to prove isolation works for compliance audits, this is for you.

Questions? Reply to this email or open a GitHub issue.

Best,
Daniel Garza
Netrun Systems

---

## Release Checklist

- [x] Packages published to PyPI
- [x] GitHub repository updated
- [x] README updated with new packages
- [ ] Blog post drafted
- [ ] Reddit post drafted
- [ ] LinkedIn post drafted
- [ ] Twitter thread drafted
- [ ] Email newsletter drafted
- [ ] Schedule social posts (stagger over 3-5 days)

---

**Created by:** Claude Code
**Date:** December 29, 2025
**Version:** 1.0
**SDLC Compliance:** v2.3
