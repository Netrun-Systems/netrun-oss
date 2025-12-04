# Netrun Open Source Libraries

Open source Python libraries from [Netrun Systems](https://netrunsystems.com) - configuration management, structured logging, and authentication/authorization for FastAPI applications.

## Packages

| Package | Version | PyPI | Description |
|---------|---------|------|-------------|
| **netrun-config** | 1.1.0 | [PyPI](https://pypi.org/project/netrun-config/) | Configuration management with Azure Key Vault integration |
| **netrun-logging** | 1.1.0 | [PyPI](https://pypi.org/project/netrun-logging/) | Structured logging with structlog backend |
| **netrun-auth** | 1.1.0 | [PyPI](https://pypi.org/project/netrun-auth/) | Authentication and Casbin RBAC authorization |

## Installation

```bash
pip install netrun-config==1.1.0
pip install netrun-logging==1.1.0
pip install netrun-auth==1.1.0
```

## About These Libraries

These packages are extracted from our internal development work building 12 platform products. They represent patterns we've found useful and want to share with the Python community.

**Important**: These are early-stage open source projects. Our platforms are pre-launch, so we don't have production metrics to share. We're releasing early to gather community feedback.

### What we're offering:
- MIT licensed code
- 346 passing tests (100% pass rate)
- Patterns that work in our development environments
- Active maintenance and responsiveness to issues

### What we're NOT claiming:
- Production battle-testing at scale
- Enterprise deployment metrics
- Years of reliability data

## netrun-config

Configuration management with Azure Key Vault integration, TTL-based caching, and multi-vault support.

**Features:**
- TTL-based secret caching (8-hour default per Microsoft guidance)
- Multi-vault routing for dev/prod/certs separation
- Secret rotation detection
- Pydantic Settings Source integration

```python
from netrun_config import SecretCache

cache = SecretCache(vault_url="https://your-vault.vault.azure.net/")
secret = cache.get_secret("database-password")
```

## netrun-logging

Structured logging with structlog backend for improved performance.

**Features:**
- Structlog backend (~2.9x faster per structlog benchmarks)
- Async logging support
- Automatic sensitive field redaction
- OpenTelemetry trace context injection

```python
from netrun_logging import get_logger

logger = get_logger(__name__)
logger.info("Application started", version="1.0.0")
```

## netrun-auth

Authentication and authorization with Casbin RBAC engine.

**Features:**
- Casbin RBAC with policy-as-code
- Multi-tenant domain isolation
- FastAPI middleware integration
- JWT handling with Azure AD support

```python
from netrun_auth import CasbinRBACManager

rbac = CasbinRBACManager(model_path="rbac_model.conf")
if rbac.check_permission(user_id, resource, action):
    # proceed
```

## Contributing

We welcome contributions! Please:
1. Open an issue to discuss proposed changes
2. Submit pull requests with tests
3. Follow existing code style

## License

All packages are MIT licensed.

## About Netrun Systems

Netrun Systems was founded in May 2025 by Daniel Garza, building on 25 years of consulting experience in cloud infrastructure and DevSecOps. We're currently developing 12 platform products for managed service providers, content creators, and enterprise security teams.

- Website: [netrunsystems.com](https://netrunsystems.com)
- Contact: daniel@netrunsystems.com
