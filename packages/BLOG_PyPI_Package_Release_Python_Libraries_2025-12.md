---
title: "Netrun Service Library: 10 Python Packages for Enterprise Cloud Applications"
slug: "pypi-netrun-service-library-10-python-packages-release"
date: "2025-12-04"
updated: "2025-12-15"
author: "Daniel Garza"
category: "Open Source & DevOps"
tags: ["Python", "PyPI", "Open Source", "Azure Integration", "FastAPI", "Authentication", "Configuration Management", "Structured Logging", "CORS", "Database Pooling", "LLM", "Testing", "Rate Limiting"]
excerpt: "Netrun Systems releases the Netrun Service Library: 10 interconnected Python packages for enterprise applications. From authentication and logging to LLM orchestration and database pooling—built from 25 years of production infrastructure experience. All 10 packages now available on PyPI."
featured_image: "netrun-service-library-10-packages.jpg"
featured_image_alt: "Netrun Service Library: 10 Python packages on PyPI"
meta_description: "10 production-ready Python packages for enterprise applications: netrun-auth v1.1.0, netrun-logging v1.1.0, netrun-config v1.1.0, and 7 more. All MIT licensed on PyPI."
reading_time: "8"
related_docs: "NETRUN_SERVICE_LIBRARY_TECHNICAL_REFERENCE.md"
---

## Introduction: A Complete Python Infrastructure Library

When you build multiple enterprise applications, you solve the same problems repeatedly: authentication, configuration, logging, database connections, CORS, rate limiting, testing fixtures. Over the past months developing our internal platform portfolio, we extracted the best patterns into reusable packages.

Today, we're releasing the **Netrun Service Library**: 10 interconnected Python packages designed to work together in FastAPI and async Python applications.

**Quick Install** (All 10 packages now on PyPI):
```bash
pip install netrun-auth[all]==1.1.0 netrun-logging==1.1.0 netrun-config[all]==1.1.0 netrun-errors==1.1.0
```

> **Technical Reference**: For complete API documentation, code examples, and integration patterns, see our [Technical Reference Guide](./NETRUN_SERVICE_LIBRARY_TECHNICAL_REFERENCE.md).

---

## Package Overview

| Package | Version | Purpose | PyPI |
|---------|---------|---------|------|
| **netrun-auth** | 1.1.0 | JWT + RBAC + MFA authentication | [Install](https://pypi.org/project/netrun-auth/) |
| **netrun-config** | 1.1.0 | Configuration with Azure Key Vault | [Install](https://pypi.org/project/netrun-config/) |
| **netrun-logging** | 1.1.0 | Structured logging with Azure App Insights | [Install](https://pypi.org/project/netrun-logging/) |
| **netrun-errors** | 1.1.0 | Standardized exception hierarchy | [Install](https://pypi.org/project/netrun-errors/) |
| **netrun-cors** | 1.1.0 | OWASP-compliant CORS middleware | [Install](https://pypi.org/project/netrun-cors/) |
| **netrun-db-pool** | 1.0.0 | Async SQLAlchemy connection pooling | [Install](https://pypi.org/project/netrun-db-pool/) |
| **netrun-llm** | 1.0.0 | Multi-provider LLM orchestration | [Install](https://pypi.org/project/netrun-llm/) |
| **netrun-env** | 1.0.0 | Schema-based environment validation | [Install](https://pypi.org/project/netrun-env/) |
| **netrun-pytest-fixtures** | 1.0.0 | Unified testing fixtures | [Install](https://pypi.org/project/netrun-pytest-fixtures/) |
| **netrun-ratelimit** | 1.0.0 | Token bucket rate limiting | [Install](https://pypi.org/project/netrun-ratelimit/) |

---

## Integration Architecture

All packages use a **soft dependency pattern** for seamless integration. Each package works standalone but provides enhanced functionality when netrun-logging is installed.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  netrun-auth    netrun-config    netrun-cors    netrun-llm      │
│  netrun-db-pool netrun-ratelimit netrun-env                     │
├─────────────────────────────────────────────────────────────────┤
│              Foundation Layer (Optional Dependencies)            │
│       netrun-logging          netrun-errors                      │
├─────────────────────────────────────────────────────────────────┤
│                    Testing Layer                                 │
│              netrun-pytest-fixtures (all integrations)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Foundation Packages

### netrun-logging v1.1.0

**High-performance structured logging** with Azure App Insights integration.

**Key Capabilities**:
- Structlog backend (2.9x faster than stdlib)
- Async logging support
- Automatic sensitive field redaction (passwords, API keys, tokens)
- Azure App Insights integration
- Ecosystem helper functions for operation timing and audit logging

```bash
pip install netrun-logging==1.1.0
```

---

### netrun-errors v1.1.0

**Standardized exception hierarchy** with automatic correlation ID propagation.

**Key Capabilities**:
- 10+ exception types mapped to HTTP status codes
- Automatic correlation ID from netrun-logging
- FastAPI exception handlers
- **NEW**: RateLimitExceededError, BadGatewayError, GatewayTimeoutError, ExternalServiceError

```bash
pip install netrun-errors==1.1.0
```

---

## Authentication & Authorization

### netrun-auth v1.1.0

**Complete authentication and authorization** without building from scratch.

**Key Capabilities**:
- JWT token management with key rotation
- Casbin RBAC engine with policy-as-code
- Multi-tenant domain isolation
- FastAPI middleware integration
- Azure AD / OAuth 2.0 integration
- MFA support (TOTP)
- Password hashing (Argon2, bcrypt)
- Deep netrun-logging integration

**Optional Dependencies**:
- `[azure]` - Azure AD integration
- `[oauth]` - OAuth providers
- `[fastapi]` - FastAPI middleware
- `[casbin]` - Casbin adapters
- `[all]` - Everything

```bash
pip install netrun-auth[all]==1.1.0
```

---

## Configuration & Environment

### netrun-config v1.1.0

**Secure configuration management** with TTL caching and multi-vault support.

**Key Capabilities**:
- Azure Key Vault with 8-hour TTL caching
- Multi-vault routing (dev/staging/prod/certs)
- Pydantic Settings Source integration
- Configuration validators
- Error standardization with netrun-errors

```bash
pip install netrun-config[all]==1.1.0
```

---

### netrun-env v1.0.0

**Schema-based environment validation** with security checks.

**Key Capabilities**:
- Schema-based validation (type, required, default, pattern)
- Security checks for secrets in .env files
- Diff detection for environment changes
- CLI tool for validation
- netrun-logging integration

```bash
pip install netrun-env==1.0.0

# CLI usage
netrun-env validate --schema env.schema.json
netrun-env security-check
```

---

## Web & API Infrastructure

### netrun-cors v1.1.0

**OWASP-compliant CORS middleware** with security logging.

**Key Capabilities**:
- OWASP-compliant CORS handling
- Wildcard and domain pattern matching
- Security event logging
- Prevents credentials with wildcard origins

```bash
pip install netrun-cors==1.1.0
```

---

### netrun-ratelimit v1.0.0

**Distributed rate limiting** with Redis backend.

**Key Capabilities**:
- Token bucket algorithm
- Redis-backed for distributed systems
- Per-user and per-endpoint limits
- FastAPI middleware and decorator

```bash
pip install netrun-ratelimit==1.0.0
```

---

## Database & LLM

### netrun-db-pool v1.0.0

**Async SQLAlchemy connection pooling** with health checks.

**Key Capabilities**:
- Async SQLAlchemy engine management
- Connection pooling with overflow
- Health checks and statistics
- Transaction management
- Pool operation logging

```bash
pip install netrun-db-pool==1.0.0
```

---

### netrun-llm v1.0.0

**Multi-provider LLM orchestration** with fallback chains.

**Key Capabilities**:
- Multi-provider support (Anthropic Claude, OpenAI GPT, Ollama)
- Automatic fallback chains
- Three-tier cognition (fast/balanced/powerful routing)
- Streaming support
- Provider switch logging

```bash
pip install netrun-llm[all]==1.0.0
```

---

## Testing

### netrun-pytest-fixtures v1.0.0

**Unified testing fixtures** eliminating 71% fixture duplication.

**Key Capabilities**:
- JWT token fixtures with custom claims
- Mock Redis client
- Async database sessions with rollback
- HTTP client mocking
- Environment isolation
- Log capture fixtures

```bash
pip install netrun-pytest-fixtures[all]==1.0.0
```

---

## Quick Start Example

```python
from fastapi import FastAPI, Depends
from netrun_logging import configure_logging, get_logger
from netrun_errors.handlers import register_exception_handlers
from netrun_auth import JWTManager
from netrun_cors import create_cors_middleware

# 1. Configure logging first
configure_logging(service_name="my-api", environment="production")
logger = get_logger(__name__)

# 2. Create app
app = FastAPI()

# 3. Add CORS
cors = create_cors_middleware(
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
)
app.add_middleware(cors.__class__, **cors.__dict__)

# 4. Register error handlers
register_exception_handlers(app)

# 5. Setup auth
jwt_manager = JWTManager(secret_key="your-secret", algorithm="HS256")

@app.get("/health")
async def health():
    logger.info("health_check")
    return {"status": "healthy"}
```

> **Full Example**: See the [Technical Reference](./NETRUN_SERVICE_LIBRARY_TECHNICAL_REFERENCE.md#full-integration-example) for a complete FastAPI application using all packages.

---

## Installation Options

### Minimal (Foundation)
```bash
pip install netrun-logging==1.1.0 netrun-errors==1.1.0
```

### Standard (Core + Web)
```bash
pip install netrun-auth==1.1.0 netrun-logging==1.1.0 netrun-config==1.1.0 \
    netrun-errors==1.1.0 netrun-cors==1.1.0
```

### Full Suite (All 10 Packages)
```bash
pip install netrun-auth[all]==1.1.0 netrun-logging==1.1.0 netrun-config[all]==1.1.0 \
    netrun-errors==1.1.0 netrun-cors==1.1.0 netrun-db-pool==1.0.0 \
    netrun-llm[all]==1.0.0 netrun-env==1.0.0 netrun-pytest-fixtures[all]==1.0.0 \
    netrun-ratelimit==1.0.0
```

### With All Optional Dependencies
```bash
pip install netrun-auth[all]==1.1.0
pip install netrun-config[all]==1.1.0
pip install netrun-llm[all]==1.0.0
pip install netrun-pytest-fixtures[all]==1.0.0
```

---

## Why We're Open Sourcing

These libraries are extracted from our internal development work across 12+ pre-launch platforms. We're sharing patterns that have worked well in our development environment.

**Our goals**:
1. **Community feedback**: Input on API design before production launch
2. **Transparency**: How Netrun Systems approaches infrastructure
3. **Contribution**: If these patterns help other developers, that's a win

---

## Resources

**PyPI Packages**:
- [netrun-logging](https://pypi.org/project/netrun-logging/) | [netrun-errors](https://pypi.org/project/netrun-errors/) | [netrun-auth](https://pypi.org/project/netrun-auth/)
- [netrun-config](https://pypi.org/project/netrun-config/) | [netrun-cors](https://pypi.org/project/netrun-cors/) | [netrun-db-pool](https://pypi.org/project/netrun-db-pool/)
- [netrun-llm](https://pypi.org/project/netrun-llm/) | [netrun-env](https://pypi.org/project/netrun-env/) | [netrun-pytest-fixtures](https://pypi.org/project/netrun-pytest-fixtures/)
- [netrun-ratelimit](https://pypi.org/project/netrun-ratelimit/)

**Documentation**:
- [Technical Reference Guide](./NETRUN_SERVICE_LIBRARY_TECHNICAL_REFERENCE.md) - Complete API documentation
- [Integration Guide](https://github.com/netrun-systems/netrun-service-library/blob/main/INTEGRATION_GUIDE.md)
- [GitHub Repository](https://github.com/netrun-systems/netrun-service-library)

---

## About Netrun Systems

Netrun Systems was founded in May 2025 by Daniel Garza, building on 25 years of consulting experience in cloud infrastructure, DevSecOps, and multi-tenant management platforms. The Netrun Service Library represents our internal tooling—patterns refined across our product portfolio.

---

## Get Started

```bash
# Core packages
pip install netrun-auth[all]==1.1.0 netrun-logging==1.1.0 netrun-config[all]==1.1.0

# Full suite (all 10 packages)
pip install netrun-auth[all]==1.1.0 netrun-config[all]==1.1.0 netrun-logging==1.1.0 \
    netrun-errors==1.1.0 netrun-cors==1.1.0 netrun-db-pool==1.0.0 netrun-llm[all]==1.0.0 \
    netrun-env==1.0.0 netrun-pytest-fixtures[all]==1.0.0 netrun-ratelimit==1.0.0
```

**Questions?** Open an issue on GitHub. **Want to contribute?** Submit a pull request. **Need enterprise support?** Contact [Netrun Systems](https://www.netrunsystems.com).
