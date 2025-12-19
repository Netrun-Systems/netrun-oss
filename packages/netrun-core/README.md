# netrun-core

Namespace package foundation for the Netrun Systems enterprise Python toolkit.

## Installation

```bash
pip install netrun-core
```

## Purpose

This package establishes the `netrun` namespace that all other Netrun packages share. Install this package to enable unified imports:

```python
# After installing netrun-core + netrun-auth + netrun-config:
from netrun.auth import JWTAuthMiddleware
from netrun.config import Settings
from netrun.errors import NetrunError
```

## Available Packages

| Package | Import Path | Description |
|---------|-------------|-------------|
| netrun-auth | `netrun.auth` | JWT, OAuth, Azure AD B2C authentication |
| netrun-config | `netrun.config` | Configuration with Azure Key Vault |
| netrun-errors | `netrun.errors` | FastAPI error handling |
| netrun-logging | `netrun.logging` | Structured logging with App Insights |
| netrun-db-pool | `netrun.db` | Async database connection pooling |
| netrun-llm | `netrun.llm` | Multi-provider LLM orchestration |
| netrun-rbac | `netrun.rbac` | Role-based access control |
| netrun-ratelimit | `netrun.ratelimit` | API rate limiting |

## Requirements

- Python 3.10+

## License

MIT License - Netrun Systems 2025
