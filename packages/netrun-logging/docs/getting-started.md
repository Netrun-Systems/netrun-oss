# Getting Started

## Installation

Install from PyPI:

```bash
pip install netrun-logging
```

For Azure App Insights support:

```bash
pip install netrun-logging[azure]
```

## Basic Usage

### 1. Configure Logging

Call `configure_logging()` once at application startup:

```python
from netrun_logging import configure_logging

configure_logging(
    app_name="my-service",
    environment="production",
    log_level="INFO",
)
```

### 2. Get a Logger

Use `get_logger()` to get a configured logger:

```python
from netrun_logging import get_logger

logger = get_logger(__name__)
```

### 3. Log Messages

```python
# Basic logging
logger.info("User logged in")

# With extra fields
logger.info("Order placed", extra={
    "user_id": 12345,
    "order_id": "ORD-001",
    "total": 99.99,
})

# Error with exception
try:
    process_order()
except Exception:
    logger.exception("Order processing failed")
```

### 4. Output Format

All logs are JSON-formatted:

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "INFO",
  "message": "Order placed",
  "logger": "my_module",
  "extra": {
    "user_id": 12345,
    "order_id": "ORD-001",
    "total": 99.99
  }
}
```

## Next Steps

- [Configuration Options](configuration.md)
- [FastAPI Integration](examples/fastapi.md)
- [Azure App Insights](examples/azure.md)
