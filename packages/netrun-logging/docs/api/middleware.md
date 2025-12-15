# FastAPI Middleware

Middleware components for FastAPI integration.

## CorrelationIdMiddleware

Injects correlation ID into each request.

```python
class CorrelationIdMiddleware(BaseHTTPMiddleware)
```

### Behavior

1. Reads `X-Correlation-ID` header if present
2. Generates new UUID if not provided
3. Stores in `request.state.correlation_id`
4. Adds `X-Correlation-ID` to response headers

### Example

```python
from fastapi import FastAPI
from netrun_logging.middleware import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)

@app.get("/api/endpoint")
async def my_endpoint():
    return {"status": "ok"}
```

### Response Header

All responses include correlation ID:

```
X-Correlation-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Client Integration

Use correlation ID in client requests:

```python
import httpx

async def call_downstream():
    # Get correlation ID from response
    response = await httpx.get(
        "http://upstream-service/api/endpoint"
    )

    correlation_id = response.headers.get("X-Correlation-ID")

    # Pass it to downstream services
    headers = {"X-Correlation-ID": correlation_id}
    downstream_response = await httpx.get(
        "http://downstream-service/api/endpoint",
        headers=headers
    )
    return downstream_response
```

## LoggingMiddleware

Logs request and response details.

```python
class LoggingMiddleware(BaseHTTPMiddleware)
```

### Logged Information

**Request**:
- HTTP method (GET, POST, etc.)
- URL path
- Query parameters
- Client host/IP
- Correlation ID

**Response**:
- HTTP status code
- Response duration (milliseconds)
- Correlation ID

### Example

```python
from fastapi import FastAPI
from netrun_logging.middleware import LoggingMiddleware

app = FastAPI()
app.add_middleware(LoggingMiddleware, log_level="INFO")

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": "John Doe"}
```

### Sample Output

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "INFO",
  "message": "HTTP Request",
  "logger": "netrun_logging.middleware",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "extra": {
    "method": "GET",
    "path": "/api/users/123",
    "query_params": {},
    "client_host": "192.168.1.1"
  }
}
```

Response log:

```json
{
  "timestamp": "2025-11-24T22:30:00.234567+00:00",
  "level": "INFO",
  "message": "HTTP Response",
  "logger": "netrun_logging.middleware",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "extra": {
    "status_code": 200,
    "duration_ms": 45
  }
}
```

### Log Level Configuration

```python
from fastapi import FastAPI
from netrun_logging.middleware import LoggingMiddleware

app = FastAPI()

# Only log warnings and above
app.add_middleware(LoggingMiddleware, log_level="WARNING")

# Log all requests (default is INFO)
app.add_middleware(LoggingMiddleware, log_level="DEBUG")
```

## add_logging_middleware

Helper function to add both middlewares in correct order.

```python
def add_logging_middleware(app: FastAPI, log_level: str = "INFO") -> None
```

### Parameters
- `app`: FastAPI application instance
- `log_level`: Logging level for requests/responses (default "INFO")

### Example

```python
from fastapi import FastAPI
from netrun_logging import configure_logging
from netrun_logging.middleware import add_logging_middleware

# Configure logging
configure_logging(app_name="my-service")

# Create app
app = FastAPI()

# Add both middlewares in correct order
add_logging_middleware(app, log_level="INFO")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Middleware Order

When using both middlewares, the correct order is important:

```python
# Correct order: Correlation ID first, then Logging
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# OR use the helper
add_logging_middleware(app)  # Handles order automatically
```

The logging middleware needs access to the correlation ID set by the correlation ID middleware, so correlation ID middleware should be added last (they execute first in reverse order).

## Error Handling

Errors in endpoints are automatically logged with full traceback:

```python
from fastapi import FastAPI
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

configure_logging(app_name="my-service")
app = FastAPI()
add_logging_middleware(app)

logger = get_logger(__name__)

@app.get("/api/risky")
async def risky_endpoint():
    try:
        result = 1 / 0  # Oops!
    except Exception:
        logger.exception("Endpoint failed")
        raise
```

Output:

```json
{
  "timestamp": "2025-11-24T22:30:00.123456+00:00",
  "level": "ERROR",
  "message": "Endpoint failed",
  "logger": "__main__",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exception": {
    "type": "ZeroDivisionError",
    "message": "division by zero",
    "traceback": "Traceback (most recent call last):\n  File ..."
  }
}
```
