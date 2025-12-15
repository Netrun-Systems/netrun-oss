# Configuration

## configure_logging()

The main configuration function accepts these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app_name` | str | "app" | Application name for log context |
| `environment` | str | None | Environment (falls back to `ENVIRONMENT` env var) |
| `log_level` | str | "INFO" | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `enable_json` | bool | True | Use JSON formatter |
| `enable_correlation_id` | bool | True | Enable correlation ID tracking |
| `azure_insights_connection_string` | str | None | Azure App Insights connection string |

## Environment Variables

netrun-logging respects these environment variables:

| Variable | Description |
|----------|-------------|
| `ENVIRONMENT` | Default environment if not specified |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure App Insights connection |
| `LOG_LEVEL` | Override log level |

## Example Configurations

### Development

```python
configure_logging(
    app_name="my-service",
    environment="development",
    log_level="DEBUG",
)
```

### Production

```python
configure_logging(
    app_name="my-service",
    environment="production",
    log_level="INFO",
    azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
)
```

### Minimal (Defaults)

```python
configure_logging()  # Uses all defaults
```
