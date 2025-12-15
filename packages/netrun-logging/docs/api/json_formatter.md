# JSON Formatter

Structured JSON log formatting for machine-readable output.

## JsonFormatter

```python
class JsonFormatter(logging.Formatter)
```

Formats log records as JSON with ISO 8601 timestamps and optional correlation ID/context inclusion.

### Initialization

```python
JsonFormatter(
    app_name: str = "app",
    include_correlation_id: bool = True,
    include_context: bool = True,
)
```

### Parameters

### app_name
- **Type**: `str`
- **Default**: `"app"`
- **Description**: Application name included in all logs

### include_correlation_id
- **Type**: `bool`
- **Default**: `True`
- **Description**: Include correlation ID in JSON output

### include_context
- **Type**: `bool`
- **Default**: `True`
- **Description**: Include log context in JSON output

## Output Format

### Basic Log

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "INFO",
  "message": "Application started",
  "logger": "my_module",
  "app_name": "my-service"
}
```

### With Correlation ID

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "INFO",
  "message": "Processing request",
  "logger": "my_module",
  "app_name": "my-service",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### With Extra Fields

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "INFO",
  "message": "Order placed",
  "logger": "order_service",
  "app_name": "my-service",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "extra": {
    "user_id": 12345,
    "order_id": "ORD-001",
    "total": 99.99
  }
}
```

### With Exception

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "ERROR",
  "message": "Order processing failed",
  "logger": "order_service",
  "app_name": "my-service",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exception": {
    "type": "ValueError",
    "message": "Invalid order amount",
    "traceback": "Traceback (most recent call last):\n  ..."
  }
}
```

## Usage

### Automatic Configuration

`JsonFormatter` is automatically configured when you call `configure_logging()`:

```python
from netrun_logging import configure_logging

configure_logging(
    app_name="my-service",
    enable_json=True,  # Uses JsonFormatter by default
)
```

### Manual Configuration

```python
import logging
from netrun_logging.formatting import JsonFormatter

# Create handler
handler = logging.StreamHandler()

# Create and attach formatter
formatter = JsonFormatter(app_name="my-service")
handler.setFormatter(formatter)

# Attach to logger
logger = logging.getLogger("my_module")
logger.addHandler(handler)
```

## Timestamp Format

All timestamps are ISO 8601 formatted with timezone information:

```
2025-11-24T22:30:00.123456+00:00
```

Format: `YYYY-MM-DDTHH:MM:SS.mmmmmm+TZ:TZ`

## Field Names

Standard JSON fields are always included:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 formatted timestamp |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `message` | string | Log message |
| `logger` | string | Logger name |
| `app_name` | string | Application name |
| `correlation_id` | string | Optional correlation ID (if enabled) |
| `extra` | object | Optional extra fields |
| `exception` | object | Optional exception details (if logging exception) |

## Custom Formatter Extension

Extend `JsonFormatter` for custom behavior:

```python
from netrun_logging.formatting import JsonFormatter
import json

class CustomJsonFormatter(JsonFormatter):
    def format(self, record):
        # Call parent to get base JSON dict
        log_dict = json.loads(super().format(record))

        # Add custom field
        log_dict["custom_field"] = "custom_value"

        return json.dumps(log_dict)
```
