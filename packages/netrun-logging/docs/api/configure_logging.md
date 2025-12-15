# configure_logging

Configure unified logging for your application.

## Signature

```python
def configure_logging(
    app_name: str = "app",
    environment: Optional[str] = None,
    log_level: str = "INFO",
    enable_json: bool = True,
    enable_correlation_id: bool = True,
    azure_insights_connection_string: Optional[str] = None,
) -> None
```

## Parameters

### app_name
- **Type**: `str`
- **Default**: `"app"`
- **Description**: Application name included in log context

### environment
- **Type**: `Optional[str]`
- **Default**: `None` (falls back to `ENVIRONMENT` env var, then `"development"`)
- **Description**: Environment name (development, staging, production)

### log_level
- **Type**: `str`
- **Default**: `"INFO"`
- **Description**: Minimum log level. One of: DEBUG, INFO, WARNING, ERROR, CRITICAL

### enable_json
- **Type**: `bool`
- **Default**: `True`
- **Description**: Use JSON formatter for structured output

### enable_correlation_id
- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable correlation ID tracking

### azure_insights_connection_string
- **Type**: `Optional[str]`
- **Default**: `None`
- **Description**: Azure Application Insights connection string

## Example

```python
from netrun_logging import configure_logging
import os

configure_logging(
    app_name="order-service",
    environment="production",
    log_level="INFO",
    azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
)
```

## Notes

- Call once at application startup
- Subsequent calls will reconfigure logging
- Azure integration gracefully degrades if SDK not installed
