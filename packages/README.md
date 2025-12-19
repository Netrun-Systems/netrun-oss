# Netrun Systems Internal Packages

Unified, reusable Python packages for the Netrun Systems service portfolio. These packages eliminate code duplication across 12+ services while providing production-grade implementations of common functionality.

**Key Benefits:**
- Single source of truth for critical infrastructure components
- Consistent implementations across all Netrun services
- Reduced maintenance burden through centralized updates
- Production-tested code with 80%+ test coverage
- MIT licensed - fully available to all internal services

---

## Namespace Package Migration (v2.0.0+)

Starting with **v2.0.0** (December 2025), all Netrun packages have migrated to **PEP 420 namespace packages** under the unified `netrun` namespace.

### What Changed?

All `netrun_*` packages are now imported via the `netrun.*` namespace:

```python
# OLD (v1.x) - Still works in v2.x with deprecation warning
from netrun_auth import JWTAuthMiddleware
from netrun_config import Settings
from netrun_logging import get_logger

# NEW (v2.x+) - Recommended
from netrun.auth import JWTAuthMiddleware
from netrun.config import Settings
from netrun.logging import get_logger
```

### Why This Change?

1. **Unified Namespace:** All packages under single `netrun.*` hierarchy
2. **Better IDE Support:** Improved autocomplete and type checking
3. **Clearer Organization:** Better module discovery and navigation
4. **Standards Compliance:** PEP 420 and PEP 561 support
5. **Reduced Conflicts:** Single namespace eliminates `netrun_` variations

### Migration Status

| Status | Details |
|--------|---------|
| **v2.0.0** | Namespace migration released, v1.x imports still work with warnings |
| **v2.x** | Current - Full backwards compatibility, deprecation warnings |
| **v3.0+** | Planned - Old imports removed, namespace packages only |

### Migration Resources

- **📖 Migration Guide:** [NAMESPACE_MIGRATION_GUIDE.md](./NAMESPACE_MIGRATION_GUIDE.md)
  - Step-by-step migration instructions
  - Automated migration tools
  - Troubleshooting guide
  - FAQ and common scenarios

- **📝 Detailed Changelog:** [CHANGELOG_v2.0.0.md](./CHANGELOG_v2.0.0.md)
  - Complete list of changes
  - Individual package updates
  - Support timeline
  - Upgrade instructions

### Quick Start

```bash
# 1. Upgrade packages
pip install --upgrade netrun-auth netrun-config netrun-logging netrun-db-pool

# 2. Update imports (manual or use migration script)
# OLD: from netrun_auth import ...
# NEW: from netrun.auth import ...

# 3. Test your application
pytest tests/
```

### Backwards Compatibility

**Important:** v2.x maintains full backwards compatibility with v1.x:

- Old `netrun_*` imports continue to work
- Deprecation warnings emitted (not errors)
- No breaking changes to code functionality
- Time to migrate: Before v3.0.0 (Q2 2026)

For detailed migration instructions, see [NAMESPACE_MIGRATION_GUIDE.md](./NAMESPACE_MIGRATION_GUIDE.md).

---

## Package Catalog

| Package | PyPI Name | Version | Description | Status |
|---------|-----------|---------|-------------|--------|
| **Authentication** | [`netrun-auth`](https://pypi.org/project/netrun-auth/) | 1.1.0 | JWT, OAuth2, Azure AD, MFA, Casbin RBAC | **Published** |
| **Configuration** | [`netrun-config`](https://pypi.org/project/netrun-config/) | 1.1.0 | Pydantic settings with Azure Key Vault, TTL caching, multi-vault | **Published** |
| **Structured Logging** | [`netrun-logging`](https://pypi.org/project/netrun-logging/) | 1.1.0 | Structlog-based JSON logging with Azure App Insights | **Published** |
| **CORS Middleware** | `netrun-cors` | 1.0.0 | Enterprise CORS presets for FastAPI | Production |
| **Database Pooling** | `netrun-db-pool` | 1.0.0 | Async connection pooling, multi-tenant RLS | Production |
| **Dogfood MCP Server** | `netrun-dogfood` | 1.0.0 | MCP server with 53 tools for Netrun product APIs | Production |
| **Environment Validation** | `netrun-env` | 1.0.0 | Schema-based env var validation with CLI | Production |
| **Error Handling** | `netrun-errors` | 1.0.0 | Unified FastAPI exception handling & correlation IDs | Production |
| **LLM Orchestration** | `netrun-llm` | 1.0.0 | Multi-provider LLM with fallback chains & three-tier cognition | Production |
| **OAuth Adapters** | `netrun-oauth` | 1.0.0 | 12-platform OAuth adapter factory with token encryption | Production |
| **RBAC & RLS** | `netrun-rbac` | 1.0.0 | Multi-tenant RBAC with PostgreSQL Row-Level Security | Production |
| **Testing Fixtures** | `netrun-pytest-fixtures` | 1.0.0 | Reusable pytest fixtures (71% duplication eliminated) | Production |
| **Physics Simulation** | `optikal-physics-suite` | 1.0.0 | FSO beam propagation, atmospheric optics, space environment | **Ready** |
| **React UI Components** | `@netrun/ui` | 1.0.0 | State components, design tokens, PdfViewer (npm) | Production |

---

## Package Details

### 1. netrun-auth (Authentication & Authorization)

**PyPI:** `netrun-auth` | **Version:** 1.0.0 | **Status:** ✅ Built & Ready for Publication
**Purpose:** Unified authentication library for Netrun Systems portfolio - Service #59

**Key Features:**
- JWT token generation and validation with crypto support
- OAuth2 client flows for third-party integrations
- Azure Active Directory (Azure AD) integration via MSAL
- Role-Based Access Control (RBAC) enforcement
- Multi-Factor Authentication (MFA) support
- Password hashing with Argon2
- Redis-backed token session management
- FastAPI middleware integration

**Python Support:** 3.10, 3.11, 3.12

**Build Status** (2025-11-28):
- Wheel: `netrun_auth-1.0.0-py3-none-any.whl` (37 KB) ✅
- Source: `netrun_auth-1.0.0.tar.gz` (64 KB) ✅
- Twine Validation: PASSED (no warnings/errors) ✅
- Ready for PyPI Upload: **YES** ✅

**Documentation:**
- Build Status: `BUILD_STATUS_20251128.md`
- Publication Checklist: `PYPI_PUBLICATION_CHECKLIST.md`
- Security Guidelines: `SECURITY_GUIDELINES.md`
- Integration Guide: `INTEGRATIONS_GUIDE.md`

**Dependencies:**
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Settings management
- `pyjwt[crypto]>=2.8.0` - JWT handling
- `cryptography>=41.0.0` - Cryptographic operations
- `redis>=5.0.0` - Token caching
- `pwdlib[argon2]>=0.2.0` - Password hashing

**Optional Dependencies:**
- `azure` - Azure AD integration (MSAL, Azure Identity, Key Vault)
- `oauth` - OAuth2 flows (authlib, httpx)
- `fastapi` - FastAPI integration

**Links:**
- [Package README](./netrun-auth/README.md)
- [Repository](https://github.com/netrunsystems/netrun-auth)
- [Issues](https://github.com/netrunsystems/netrun-auth/issues)

---

### 2. netrun-config (Configuration Management)

**PyPI:** `netrun-config` | **Version:** 1.0.0
**Purpose:** Unified configuration management for Netrun Systems portfolio

**Key Features:**
- Pydantic v2 based settings validation
- Environment variable mapping with type safety
- Azure Key Vault integration for secrets
- Hierarchical configuration loading
- Override-capable settings per environment

**Python Support:** 3.10, 3.11, 3.12

**Dependencies:**
- `pydantic>=2.0.0` - Configuration validation
- `pydantic-settings>=2.0.0` - Environment variable handling

**Optional Dependencies:**
- `azure` - Azure Key Vault support (Azure Identity, Key Vault Secrets)

**Links:**
- [Package README](./netrun-config/README.md)
- [Repository](https://github.com/netrunsystems/netrun-config)
- [Issues](https://github.com/netrunsystems/netrun-config/issues)

---

### 3. netrun-cors (CORS Middleware)

**PyPI:** `netrun-cors` | **Version:** 1.0.0
**Purpose:** Enterprise CORS middleware presets for FastAPI applications

**Key Features:**
- Pre-configured CORS policies for common scenarios
- Azure AD token validation integration
- OAuth2 origin verification
- Starlette middleware compatibility
- Security-first defaults

**Python Support:** 3.11, 3.12

**Dependencies:**
- `fastapi>=0.109.0` - Web framework
- `pydantic>=2.0.0` - Data validation
- `pydantic-settings>=2.0.0` - Settings management
- `starlette>=0.27.0` - Async web framework

**Links:**
- [Package README](./netrun-cors/README.md)
- [Repository](https://github.com/netrunsystems/netrun-cors)
- [Issues](https://github.com/netrunsystems/netrun-cors/issues)

---

### 4. netrun-db-pool (Database Connection Pooling)

**PyPI:** `netrun-db-pool` | **Version:** 1.0.0
**Purpose:** Production-grade async database connection pooling for Netrun Systems services

**Key Features:**
- SQLAlchemy 2.0+ async engine management
- AsyncPG PostgreSQL driver optimization
- Connection pool sizing and lifecycle management
- Multi-tenant Row-Level Security (RLS) support
- Automatic connection health checks
- Circuit breaker pattern for resilience

**Python Support:** 3.10, 3.11, 3.12

**Dependencies:**
- `sqlalchemy[asyncio]>=2.0.0,<3.0.0` - ORM and SQL toolkit
- `asyncpg>=0.29.0,<1.0.0` - PostgreSQL async driver
- `pydantic>=2.0.0,<3.0.0` - Configuration validation
- `pydantic-settings>=2.0.0,<3.0.0` - Settings management

**Optional Dependencies:**
- `fastapi` - FastAPI integration (uvicorn)
- `redis[asyncio]` - Caching layer
- `testing` - SQLite async support for tests

**Links:**
- [Package README](./netrun-db-pool/README.md)
- [Repository](https://github.com/netrunsystems/netrun-db-pool)
- [Issues](https://github.com/netrunsystems/netrun-db-pool/issues)

---

### 5. netrun-dogfood (MCP Server for Netrun Products)

**PyPI:** `netrun-dogfood` | **Version:** 1.0.0 | **Status:** Production
**Purpose:** MCP (Model Context Protocol) server providing unified API access to all Netrun Systems products deployed in Azure

**Key Features:**
- 53 MCP tools with full CRUD operations across 5 products
- Azure AD Client Credentials authentication via MSAL
- Token caching and auto-refresh for service-to-service auth
- Enables Claude Code agents to leverage production Netrun services

**Product Coverage:**

| Product | Tools | Description |
|---------|-------|-------------|
| **Intirkon** | 13 | Azure multi-tenant management |
| **Charlotte** | 12 | AI orchestration and LLM mesh |
| **Meridian** | 10 | Document publishing |
| **NetrunSite** | 8 | Website/blog API |
| **SecureVault** | 10 | Password management |

**Python Support:** 3.10, 3.11, 3.12

**Dependencies:**
- `mcp>=1.0.0` - Model Context Protocol
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Settings management
- `httpx>=0.26.0` - Async HTTP client
- `netrun-auth[azure]>=1.0.0` - Azure AD integration

**Claude Code Integration:**

```json
{
  "mcpServers": {
    "netrun-dogfood": {
      "command": "python",
      "args": ["-m", "netrun_dogfood.server"],
      "env": {
        "AZURE_TENANT_ID": "your-tenant-id",
        "AZURE_CLIENT_ID": "your-client-id",
        "AZURE_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

**Links:**
- [Package README](./netrun-dogfood/README.md)
- [Repository](https://github.com/netrunsystems/netrun-service-library)
- [Issues](https://github.com/netrunsystems/netrun-service-library/issues)

---

### 6. netrun-env (Environment Variable Validation)

**PyPI:** `netrun-env` | **Version:** 1.0.0
**Purpose:** Schema-based environment variable validator with security checks

**Key Features:**
- Pydantic schema validation for environment variables
- CLI tool for environment verification and validation
- Secrets detection and masking
- .env file loading via python-dotenv
- Type coercion and defaults
- Required vs optional variable distinction

**Python Support:** 3.8, 3.9, 3.10, 3.11, 3.12

**Dependencies:**
- `click>=8.0.0` - CLI framework
- `pydantic>=2.0.0` - Schema validation
- `python-dotenv>=1.0.0` - .env file loading

**CLI Entry Point:** `netrun-env`

**Links:**
- [Package README](./netrun-env/README.md)
- [Repository](https://github.com/netrunsystems/netrun-service-library)
- [Issues](https://github.com/netrunsystems/netrun-service-library/issues)

---

### 6. netrun-errors (Unified Error Handling)

**PyPI:** `netrun-errors` | **Version:** 1.0.0
**Purpose:** Unified error handling for Netrun Systems FastAPI applications

**Key Features:**
- Custom exception hierarchy for FastAPI applications
- Automatic HTTP status code mapping
- Correlation ID generation and tracking
- Structured error response formatting
- Integration with structured logging
- Request/response error context preservation

**Python Support:** 3.11, 3.12

**Dependencies:**
- `fastapi>=0.115.0` - Web framework
- `starlette>=0.41.0` - ASGI toolkit

**Optional Dependencies:**
- `dev` - Development and testing tools

**Links:**
- [Package README](./netrun-errors/README.md)
- [Repository](https://github.com/netrun-systems/netrun-errors)
- [Issues](https://github.com/netrun-systems/netrun-errors/issues)

---

### 7. netrun-logging (Structured Logging)

**PyPI:** `netrun-logging` | **Version:** 1.0.0
**Purpose:** Unified structured logging service with Azure App Insights integration

**Key Features:**
- JSON structured logging output
- FastAPI middleware for request/response logging
- Azure Monitor OpenTelemetry integration
- Correlation ID injection and tracking
- Async-safe logging operations
- Automatic exception logging with stack traces

**Python Support:** 3.9, 3.10, 3.11, 3.12

**Dependencies:**
- `azure-monitor-opentelemetry>=1.0.0` - Azure monitoring
- `python-json-logger>=2.0.0` - JSON logging
- `fastapi>=0.100.0` - Web framework

**Optional Dependencies:**
- `dev` - Development and testing tools

**Links:**
- [Package README](./netrun-logging/README.md)
- [Repository](https://github.com/netrun-services/netrun-logging)
- [Documentation](https://netrun-logging.readthedocs.io)

---

### 8. netrun-rbac (Multi-Tenant RBAC & RLS)

**PyPI:** `netrun-rbac` | **Version:** 1.0.0
**Purpose:** Multi-tenant Role-Based Access Control with PostgreSQL Row-Level Security

**Key Features:**
- Role hierarchy enforcement (owner > admin > member > viewer)
- FastAPI dependency injection for route protection
- PostgreSQL Row-Level Security (RLS) policy generators
- Tenant context management for database sessions
- Resource ownership validation utilities
- Project-agnostic with placeholder configuration patterns

**Python Support:** 3.8, 3.9, 3.10, 3.11, 3.12

**Dependencies:**
- `fastapi>=0.100.0` - Web framework integration
- `sqlalchemy>=2.0.0` - Database ORM and async support
- `pydantic>=2.0.0` - Data validation and models

**Extracted From:** Intirkast SaaS Platform (85% code reuse, 12h time savings)

**Links:**
- [Package README](./netrun-rbac/README.md)
- [Repository](https://github.com/netrunsystems/netrun-service-library)
- [Issues](https://github.com/netrunsystems/netrun-service-library/issues)

---

### 9. netrun-pytest-fixtures (Testing Fixtures)

**PyPI:** `netrun-pytest-fixtures` | **Version:** 1.0.0
**Purpose:** Unified pytest fixtures for Netrun Systems services - eliminates 71% fixture duplication

**Key Features:**
- Reusable async fixtures for common test scenarios
- SQLAlchemy ORM fixtures with transaction rollback
- FastAPI test client fixtures
- Redis mock fixtures for caching tests
- HTTP client (httpx) fixtures with auth injection
- YAML configuration loading fixtures
- Database seeding and cleanup utilities

**Python Support:** 3.10, 3.11, 3.12

**Dependencies:**
- `pytest>=7.0.0` - Test framework
- `pytest-asyncio>=0.21.0` - Async test support
- `cryptography>=41.0.0` - Cryptographic utilities

**Optional Dependencies:**
- `sqlalchemy` - Database ORM fixtures (SQLAlchemy, aiosqlite)
- `httpx` - HTTP client fixtures
- `fastapi` - FastAPI test fixtures
- `redis` - Redis mock fixtures
- `yaml` - YAML configuration fixtures
- `all` - All optional dependencies

**Pytest Plugin Entry Point:** `netrun_fixtures`

**Coverage Target:** 80%+

**Links:**
- [Package README](./netrun-pytest-fixtures/README.md)
- [Repository](https://github.com/netrunsystems/netrun-pytest-fixtures)
- [Changelog](https://github.com/netrunsystems/netrun-pytest-fixtures/blob/main/CHANGELOG.md)

---

### 10. netrun-llm (LLM Orchestration)

**PyPI:** `netrun-llm` | **Version:** 1.0.0
**Purpose:** Multi-provider LLM orchestration with automatic fallback chains and three-tier cognition
**Extracted From:** Wilbur/Charlotte AI Orchestration Platform

**Key Features:**
- Multi-adapter fallback chains (Claude -> GPT-4 -> Llama3)
- Three-tier cognition: Fast ack (<100ms), RAG response (<2s), Deep insight (<5s)
- Circuit breaker protection per adapter
- Cost tracking and metrics across all providers
- Async-first with sync wrappers
- Project-agnostic design (no Wilbur-specific dependencies)

**Python Support:** 3.8, 3.9, 3.10, 3.11, 3.12

**Dependencies:**
- `requests>=2.28.0` - HTTP requests for Ollama

**Optional Dependencies:**
- `anthropic` - Claude/Anthropic API support
- `openai` - OpenAI GPT API support
- `all` - All provider dependencies

**Supported Providers:**
- **Claude (Anthropic):** claude-sonnet-4.5, claude-3.5-sonnet, claude-3-opus
- **OpenAI:** gpt-4-turbo, gpt-4o, gpt-4, gpt-3.5-turbo
- **Ollama (Local):** llama3, codellama, mistral, phi-3 (free, local compute)

**Security Placeholders:**
- `{{ANTHROPIC_API_KEY}}` - Anthropic API key
- `{{OPENAI_API_KEY}}` - OpenAI API key
- `{{OLLAMA_HOST}}` - Ollama server host

**Links:**
- [Package README](./netrun-llm/README.md)
- [Repository](https://github.com/netrunsystems/netrun-service-library)
- [Issues](https://github.com/netrunsystems/netrun-service-library/issues)

---

### 11. optikal-physics-suite (Physics Simulation)

**PyPI:** `optikal-physics-suite` | **Version:** 1.0.0 | **Status:** Ready for Publication
**Purpose:** Comprehensive physics simulation framework for FSO optical communications, atmospheric propagation, and space environment modeling

**Key Features:**
- Gaussian beam propagation (TEM00 modeling with divergence, Rayleigh range, intensity)
- Multi-beam VCSEL arrays (12/24/48-beam hexagonal, circular, grid patterns)
- Atmospheric attenuation (fog categories, ITU-R P.1814 compliance)
- Space environment simulation (LEO/MEO/GEO/HEO orbital mechanics)
- Radiation effects and thermal environment modeling
- ML weather prediction with LSTM (NOAA, Visual Crossing data sources)
- Optional GPU acceleration via PyTorch

**Python Support:** 3.10, 3.11, 3.12

**Dependencies:**
- `numpy>=1.24.0` - Numerical computing
- `scipy>=1.10.0` - Scientific computing

**Optional Dependencies:**
- `ml` - ML weather prediction (pandas, tensorflow, scikit-learn)
- `gpu` - GPU acceleration (torch)
- `optics` - Advanced optical modeling (optiland)
- `all` - All optional dependencies

**Modules:**

| Module | Description |
|--------|-------------|
| `optical.beam_propagation` | Gaussian beam and multi-beam array propagation |
| `optical.atmospheric_constants` | Fog categories, attenuation coefficients, diversity gain |
| `orbital.space_environment` | Space environment, radiation, thermal effects |
| `ml_weather` | LSTM weather prediction, multi-source data collection |

**Physics References:**
- Saleh & Teich, "Fundamentals of Photonics" (2007)
- IEC 60825-1: Safety of laser products
- ITU-R P.1814: Free-space optical link prediction

**Extracted From:** GhostGrid Optical Network / Optikal Physics Suite

**Links:**
- [Package README](./optikal-physics-suite/README.md)
- [Repository](https://github.com/Netrun-Systems/Optikal-Physics-Suite)
- [Issues](https://github.com/Netrun-Systems/Optikal-Physics-Suite/issues)

---

## Installation

### From Local Source (Development)

Install all packages in editable mode for local development:

```bash
# Install individual package in editable mode
cd packages/netrun-auth
pip install -e .

# Or install with optional dependencies
pip install -e ".[azure,oauth,fastapi]"

# Install all packages at once (from repository root)
for package in packages/netrun-*/; do
    pip install -e "$package"
done
```

### From PyPI (After Publication)

Once published to PyPI, install packages individually:

```bash
# Single package
pip install netrun-auth

# With optional dependencies
pip install "netrun-auth[azure,oauth,fastapi]"

# Multiple packages
pip install netrun-auth netrun-config netrun-db-pool netrun-pytest-fixtures
```

### Installation with All Optional Dependencies

```bash
# From local source
pip install -e "packages/netrun-auth[all]"

# From PyPI
pip install "netrun-auth[all]"
```

---

## Development Setup

### Prerequisites

- Python 3.10+ (or 3.8+ for netrun-env)
- pip/setuptools/wheel
- Git

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/netrunsystems/netrun-service-library.git
cd netrun-service-library

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all packages in editable mode with dev dependencies
for package in packages/netrun-*/; do
    pip install -e "$package[dev]"
done

# Or individual package
cd packages/netrun-auth
pip install -e ".[dev]"
```

### Development Tools

All packages are configured with the following development tools:

- **pytest** - Unit and integration testing
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage reporting
- **black** - Code formatting
- **ruff** - Fast Python linter
- **mypy** - Static type checking
- **pre-commit** - Git hook automation

### Code Quality Standards

All packages follow consistent code quality standards:

- **Minimum Python Version:** 3.10 (3.8+ for netrun-env)
- **Code Coverage:** 80%+ (90%+ for netrun-errors)
- **Line Length:** 88-120 characters
- **Type Hints:** Required (strict mypy enforcement)
- **Linting:** Ruff + Black
- **Testing:** pytest with async support

---

## Testing Commands

### Run All Tests for a Package

```bash
cd packages/netrun-auth
pytest
```

### Run Tests with Coverage Report

```bash
pytest --cov=netrun_auth --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only (requires external services)
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run Tests Across All Packages

```bash
# From repository root
for package in packages/netrun-*/; do
    echo "Testing $(basename $package)..."
    cd "$package"
    pytest
    cd ../..
done
```

### Type Checking

```bash
cd packages/netrun-auth
mypy netrun_auth/
```

### Code Linting and Formatting

```bash
# Check formatting
black --check netrun_auth/

# Auto-format
black netrun_auth/

# Lint with ruff
ruff check netrun_auth/

# Auto-fix ruff issues
ruff check --fix netrun_auth/
```

---

## Contributing Guidelines

### Before You Start

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e "packages/netrun-auth[dev]"  # or your package
   ```

3. **Enable pre-commit hooks** (if configured):
   ```bash
   pre-commit install
   ```

### Development Workflow

1. **Write code** with full type hints
2. **Write tests** - maintain 80%+ coverage minimum
3. **Format code** - run `black` and `ruff`
4. **Run type checks** - run `mypy`
5. **Run full test suite** - ensure all tests pass
6. **Commit changes** with descriptive messages

### Code Style Requirements

```python
# Imports organized with isort
from typing import Optional

import pydantic
from pydantic import BaseModel, Field

# Type hints required on all functions
def process_data(data: dict[str, str]) -> Optional[str]:
    """Process incoming data."""
    return data.get("key")

# Docstrings on public APIs
class MyException(Exception):
    """Raised when something goes wrong."""
    pass
```

### Testing Requirements

- All public functions must have tests
- Async tests use `pytest-asyncio` fixtures
- Mocking uses `pytest-mock` or `unittest.mock`
- Coverage reports generated with `--cov-report=html`

```python
# Example async test
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Pull Request Process

1. **Ensure all tests pass**: `pytest --cov=netrun_xxx`
2. **Check code formatting**: `black --check .`
3. **Run type checker**: `mypy netrun_xxx/`
4. **Update CHANGELOG.md** with changes
5. **Create descriptive PR** with test evidence
6. **Request review** from maintainers

### Issue Reporting

When reporting issues:

1. **Specify package name** and version
2. **Provide minimal reproduction** code
3. **Include Python version** and OS
4. **Attach error logs** and tracebacks
5. **List any optional dependencies** installed

---

## Package Dependencies & Compatibility

### Dependency Tree

```
netrun-auth
  ├── pydantic 2.5+
  ├── pyjwt[crypto]
  ├── redis 5.0+
  └── Optional: msal, authlib, fastapi

netrun-config
  ├── pydantic 2.0+
  └── Optional: azure-keyvault

netrun-cors
  ├── fastapi 0.109+
  ├── pydantic 2.0+
  └── starlette 0.27+

netrun-db-pool
  ├── sqlalchemy[asyncio] 2.0+
  ├── asyncpg 0.29+
  └── pydantic 2.0+

netrun-dogfood
  ├── mcp 1.0+
  ├── pydantic 2.5+
  ├── pydantic-settings 2.1+
  ├── httpx 0.26+
  └── netrun-auth[azure] 1.0+

netrun-env
  ├── click 8.0+
  ├── pydantic 2.0+
  └── python-dotenv 1.0+

netrun-errors
  ├── fastapi 0.115+
  └── starlette 0.41+

netrun-logging
  ├── azure-monitor-opentelemetry 1.0+
  ├── python-json-logger 2.0+
  └── fastapi 0.100+

netrun-rbac
  ├── fastapi 0.100+
  ├── sqlalchemy 2.0+
  └── pydantic 2.0+

netrun-pytest-fixtures
  ├── pytest 7.0+
  ├── pytest-asyncio 0.21+
  └── cryptography 41.0+
  └── Optional: sqlalchemy, httpx, fastapi, redis, pyyaml

netrun-llm
  ├── requests 2.28+
  └── Optional: anthropic 0.25+, openai 1.0+

optikal-physics-suite
  ├── numpy 1.24+
  ├── scipy 1.10+
  └── Optional: pandas, tensorflow, torch, optiland
```

### Version Compatibility Matrix

| Package | Python 3.8 | Python 3.9 | Python 3.10 | Python 3.11 | Python 3.12 |
|---------|-----------|-----------|-----------|-----------|-----------|
| netrun-auth | - | - | ✓ | ✓ | ✓ |
| netrun-config | - | - | ✓ | ✓ | ✓ |
| netrun-cors | - | - | - | ✓ | ✓ |
| netrun-db-pool | - | - | ✓ | ✓ | ✓ |
| netrun-dogfood | - | - | ✓ | ✓ | ✓ |
| netrun-env | ✓ | ✓ | ✓ | ✓ | ✓ |
| netrun-errors | - | - | - | ✓ | ✓ |
| netrun-logging | - | ✓ | ✓ | ✓ | ✓ |
| netrun-rbac | ✓ | ✓ | ✓ | ✓ | ✓ |
| netrun-pytest-fixtures | - | - | ✓ | ✓ | ✓ |
| netrun-llm | ✓ | ✓ | ✓ | ✓ | ✓ |
| optikal-physics-suite | - | - | ✓ | ✓ | ✓ |

---

## Publishing to PyPI

### Prerequisites

- PyPI account with project ownership
- `twine` installed: `pip install twine`
- API tokens configured in `~/.pypirc`

### Build and Publish Process

```bash
# Build distribution (from package directory)
cd packages/netrun-auth
pip install build
python -m build

# Verify distribution
twine check dist/*

# Upload to PyPI (requires credentials)
twine upload dist/*

# Or upload to TestPyPI first
twine upload --repository testpypi dist/*
```

### Version Management

Versions follow semantic versioning:
- `MAJOR.MINOR.PATCH` (e.g., 1.0.0)
- Update in `pyproject.toml` before publishing
- Create git tag: `git tag v1.0.0`

---

## Quick Reference

### Common Tasks

**Install single package for development:**
```bash
pip install -e packages/netrun-auth
```

**Run tests for all packages:**
```bash
./run_all_tests.sh  # if script exists, or use loop above
```

**Check code quality:**
```bash
black --check packages/
ruff check packages/
mypy packages/netrun-auth/
```

**Generate coverage report:**
```bash
cd packages/netrun-auth && pytest --cov --cov-report=html
```

### Links & Resources

- **Company Website:** https://netrunsystems.com
- **GitHub Organization:** https://github.com/netrunsystems
- **Service Library Repository:** https://github.com/netrunsystems/netrun-service-library
- **Documentation:** https://docs.netrunsystems.com

### Support & Contacts

- **Issues:** Report in respective package repositories
- **Internal Development:** See CONTRIBUTING.md in root repository
- **Questions:** Contact engineering team at engineering@netrunsystems.com

---

## License

All packages are licensed under the **MIT License**. See individual package `LICENSE` files for details.

**Copyright:** Netrun Systems, Inc. (2024-2025)

---

## Open Source Packages

Three packages are published to PyPI and available as open source:

| Package | PyPI | GitHub | Description |
|---------|------|--------|-------------|
| **netrun-config** | [v1.1.0](https://pypi.org/project/netrun-config/) | [netrun-oss](https://github.com/Netrun-Systems/netrun-oss) | Azure Key Vault integration, TTL caching, multi-vault |
| **netrun-logging** | [v1.1.0](https://pypi.org/project/netrun-logging/) | [netrun-oss](https://github.com/Netrun-Systems/netrun-oss) | Structlog backend, async logging, auto-redaction |
| **netrun-auth** | [v1.1.0](https://pypi.org/project/netrun-auth/) | [netrun-oss](https://github.com/Netrun-Systems/netrun-oss) | Casbin RBAC, multi-tenant, FastAPI middleware |

**Install from PyPI:**
```bash
pip install netrun-config==1.1.0 netrun-logging==1.1.0 netrun-auth==1.1.0
```

**Landing Page:** [netrunsystems.com/open-source](https://netrunsystems.com/open-source)

---

## Version History

| Version | Release Date | Notes |
|---------|-------------|-------|
| 1.0.0 | 2025-11-25 | Initial stable release of all 8 core packages |
| 1.0.1 | 2025-11-28 | Added netrun-llm (LLM orchestration extracted from Wilbur) |
| 1.0.2 | 2025-11-29 | Added netrun-dogfood (53-tool MCP server for Netrun product APIs) |
| 1.1.0 | 2025-12-04 | Published netrun-config, netrun-logging, netrun-auth to PyPI |
| 1.1.1 | 2025-12-07 | Added optikal-physics-suite (FSO beam propagation, space environment) |

---

**Last Updated:** December 7, 2025
**Maintained By:** Netrun Systems Engineering Team
**Status:** Production Ready
