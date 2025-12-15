# Azure App Insights Integration

## Installation

Install with Azure support:

```bash
pip install netrun-logging[azure]
```

## Basic Configuration

```python
from netrun_logging import configure_logging
import os

# Configure with Azure App Insights
configure_logging(
    app_name="my-service",
    environment="production",
    log_level="INFO",
    azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
)
```

## Environment Setup

### Azure Portal

1. Create Application Insights resource
2. Copy connection string
3. Set as environment variable:

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;IngestionEndpoint=https://xxx.in.applicationinsights.azure.com/;LiveEndpoint=https://xxx.live.applicationinsights.azure.com/"
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;..."
ENV ENVIRONMENT="production"
ENV LOG_LEVEL="INFO"

CMD ["python", "main.py"]
```

### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-insights-config
data:
  connection_string: "InstrumentationKey=xxx;..."

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
      - name: my-service
        image: my-service:1.0.0
        env:
        - name: APPLICATIONINSIGHTS_CONNECTION_STRING
          valueFrom:
            configMapKeyRef:
              name: app-insights-config
              key: connection_string
        - name: ENVIRONMENT
          value: "production"
```

## FastAPI with Azure

```python
from fastapi import FastAPI
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
import os

# Configure at startup
configure_logging(
    app_name="fastapi-service",
    environment=os.getenv("ENVIRONMENT", "development"),
    log_level="INFO",
    azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
)

# Create app
app = FastAPI(title="FastAPI Service")

# Add logging middleware
add_logging_middleware(app)

# Get logger
logger = get_logger(__name__)

@app.get("/api/endpoint")
async def my_endpoint():
    logger.info("Endpoint called")
    return {"message": "Hello from Azure"}

@app.on_event("startup")
async def startup():
    logger.info("Application starting", extra={"version": "1.0.0"})

@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down")
```

## Multi-Environment Setup

```python
from netrun_logging import configure_logging
import os

def setup_logging():
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # Production: Azure + JSON + correlation IDs
        configure_logging(
            app_name="my-service",
            environment="production",
            log_level="INFO",
            enable_json=True,
            enable_correlation_id=True,
            azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        )
    elif environment == "staging":
        # Staging: Azure + verbose logging
        configure_logging(
            app_name="my-service",
            environment="staging",
            log_level="DEBUG",
            enable_json=True,
            enable_correlation_id=True,
            azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        )
    else:
        # Development: local JSON + debug info
        configure_logging(
            app_name="my-service",
            environment="development",
            log_level="DEBUG",
            enable_json=True,
            enable_correlation_id=True,
        )
```

## Azure Monitoring Queries

After logs are sent to Azure, query them with KQL (Kusto Query Language):

### All Logs for Service

```kusto
traces
| where customDimensions.app_name == "my-service"
| order by timestamp desc
| limit 100
```

### Error Logs

```kusto
traces
| where customDimensions.app_name == "my-service"
| where severityLevel >= 2  // ERROR level
| order by timestamp desc
```

### By Correlation ID

```kusto
traces
| where customDimensions.correlation_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
| order by timestamp asc
```

### Performance Analysis

```kusto
traces
| where customDimensions.app_name == "my-service"
| where customDimensions.duration_ms > 1000
| summarize count(), avg(todouble(customDimensions.duration_ms)) by customDimensions.operation
```

### Error Rate by Endpoint

```kusto
traces
| where customDimensions.app_name == "my-service"
| summarize
    total=count(),
    errors=sumif(1, severityLevel >= 2)
    by customDimensions.endpoint
| extend error_rate = errors * 100.0 / total
| order by error_rate desc
```

## Alerting

### Alert on High Error Rate

1. Go to Application Insights resource
2. Create Alert Rule
3. Condition:
   - Custom log search
   - Query: `traces | where customDimensions.app_name == "my-service" and severityLevel >= 2 | summarize count()`
   - Threshold: > 10 errors in 5 minutes

### Alert on Slow Requests

```kusto
traces
| where customDimensions.app_name == "my-service"
| where todouble(customDimensions.duration_ms) > 5000
| summarize count()
```

## Integration with Other Services

### Sending to Azure from Background Jobs

```python
import asyncio
from netrun_logging import configure_logging, get_logger
from netrun_logging.correlation import correlation_id_context
import os

configure_logging(
    app_name="background-jobs",
    environment=os.getenv("ENVIRONMENT", "production"),
    azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
)

logger = get_logger(__name__)

async def process_job(job_id: str):
    with correlation_id_context(job_id) as cid:
        logger.info("Job started", extra={"job_id": job_id})

        try:
            # Do work
            await asyncio.sleep(1)
            logger.info("Job completed", extra={"job_id": job_id})
        except Exception:
            logger.exception("Job failed")

# Run job
asyncio.run(process_job("job-123"))
```

## Graceful Degradation

If Azure connection fails, logging continues to console:

```python
from netrun_logging import configure_logging

# If Azure is unavailable, falls back to local logging
configure_logging(
    app_name="resilient-service",
    azure_insights_connection_string="invalid-or-missing-string",  # Will fall back gracefully
)

# Logging continues to work - just goes to console instead of Azure
logger = get_logger(__name__)
logger.info("This logs successfully even if Azure is unavailable")
```

## Troubleshooting

### Connection String Not Found

```python
import os
from netrun_logging import configure_logging

connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if not connection_string:
    print("WARNING: Azure connection string not set. Logs will not go to Application Insights.")

configure_logging(
    app_name="my-service",
    azure_insights_connection_string=connection_string,
)
```

### Verify Logs Are Arriving

In Azure Portal:

1. Open Application Insights resource
2. Go to Logs
3. Run: `traces | where customDimensions.app_name == "my-service" | top 10 by timestamp`
4. Should see recent logs

### Check Environment Variables

```bash
# Linux/Mac
echo $APPLICATIONINSIGHTS_CONNECTION_STRING

# Windows PowerShell
$env:APPLICATIONINSIGHTS_CONNECTION_STRING

# Windows Command Prompt
echo %APPLICATIONINSIGHTS_CONNECTION_STRING%
```
