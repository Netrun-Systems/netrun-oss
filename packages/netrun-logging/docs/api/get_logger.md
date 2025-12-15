# get_logger

Get a configured logger instance.

## Signature

```python
def get_logger(name: str) -> logging.Logger
```

## Parameters

### name
- **Type**: `str`
- **Description**: Logger name (typically `__name__` in your module)

## Returns

A Python `logging.Logger` instance configured with netrun-logging formatters and handlers.

## Example

```python
from netrun_logging import get_logger

# Get logger for current module
logger = get_logger(__name__)

# Or with explicit name
logger = get_logger("my.module")

# Use logger normally
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

## Best Practices

### 1. Use Module Name

```python
# Recommended
logger = get_logger(__name__)
```

### 2. Add Extra Fields

```python
logger.info("User action", extra={
    "user_id": 12345,
    "action": "login",
    "ip_address": "192.168.1.1",
})
```

### 3. Handle Exceptions

```python
try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")  # Includes traceback
```

### 4. Structured Errors

```python
logger.error(
    "Payment processing failed",
    extra={
        "user_id": user.id,
        "amount": 99.99,
        "error_code": "INSUFFICIENT_FUNDS",
    }
)
```

## Log Levels

| Level | Usage | Severity |
|-------|-------|----------|
| DEBUG | Detailed diagnostic information | Low |
| INFO | General informational messages | Low |
| WARNING | Warning messages (default minimum) | Medium |
| ERROR | Error messages | High |
| CRITICAL | Critical errors | Highest |

## Output Format

All log messages are formatted as JSON:

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "INFO",
  "message": "User action",
  "logger": "my.module",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "extra": {
    "user_id": 12345,
    "action": "login"
  }
}
```
