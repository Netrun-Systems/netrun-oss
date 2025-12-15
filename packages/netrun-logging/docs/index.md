# netrun-logging

**Unified structured logging with correlation ID tracking and Azure App Insights integration.**

## Features

- **JSON Structured Logging**: Machine-readable log output with ISO 8601 timestamps
- **Correlation ID Tracking**: Thread-safe request tracing across distributed systems
- **FastAPI Integration**: Middleware for automatic request/response logging
- **Azure App Insights**: Optional cloud logging with graceful fallback
- **Zero Configuration**: Sensible defaults that just work

## Quick Start

```python
from netrun_logging import configure_logging, get_logger

# Configure once at startup
configure_logging(app_name="my-service", environment="production")

# Get logger anywhere
logger = get_logger(__name__)
logger.info("Application started", extra={"version": "1.0.0"})
```

## Installation

```bash
pip install netrun-logging
```

## Why netrun-logging?

| Feature | Standard logging | netrun-logging |
|---------|-----------------|----------------|
| JSON output | Manual setup | Built-in |
| Correlation IDs | Not included | Thread-safe |
| Azure integration | Separate package | Optional built-in |
| FastAPI middleware | DIY | Included |

## License

MIT License - Copyright (c) 2025 Netrun Systems
