# Log Context

Thread-safe log context management for adding request-scoped metadata to all logs.

## get_context

Get the current log context.

```python
def get_context() -> Dict[str, Any]
```

### Returns
Dictionary containing current context values

### Example

```python
from netrun_logging.context import get_context

context = get_context()
print(context)  # {"request_id": "123", "user_id": "456"}
```

## set_context

Set log context values (merges with existing context).

```python
def set_context(**kwargs) -> None
```

### Parameters
- `**kwargs`: Key-value pairs to add to context

### Example

```python
from netrun_logging.context import set_context
from netrun_logging import get_logger

logger = get_logger(__name__)

set_context(user_id=12345, request_id="req-001")
logger.info("User action")
# Log output includes: "user_id": 12345, "request_id": "req-001"
```

## clear_context

Clear all context values.

```python
def clear_context() -> None
```

### Example

```python
from netrun_logging.context import clear_context, set_context

set_context(user_id=123)
clear_context()
# Context is now empty
```

## Request-Scoped Context

Use context for request-scoped metadata:

```python
from fastapi import FastAPI, Request
from netrun_logging import get_logger
from netrun_logging.context import set_context, clear_context

app = FastAPI()
logger = get_logger(__name__)

@app.middleware("http")
async def context_middleware(request: Request, call_next):
    # Set context for this request
    set_context(
        request_id=request.headers.get("X-Request-ID", "unknown"),
        user_id=request.state.user_id,
        endpoint=request.url.path,
    )

    try:
        response = await call_next(request)
        logger.info("Request completed", extra={"status_code": response.status_code})
        return response
    finally:
        clear_context()
```

## Nested Context

Context values are merged and automatically included in all logs:

```python
from netrun_logging.context import set_context
from netrun_logging import get_logger

logger = get_logger(__name__)

# Set initial context
set_context(request_id="req-001")

# Add more context
set_context(user_id=123)

# All logs now include both values
logger.info("Doing something")
# Output: {"request_id": "req-001", "user_id": 123}
```

## Context vs Extra

| Feature | Context | Extra Parameter |
|---------|---------|-----------------|
| Scope | Request/operation scoped | Single log message |
| Persistence | Maintained across logs | Single use |
| Use Case | User ID, request ID, session | Operation details |

```python
from netrun_logging.context import set_context
from netrun_logging import get_logger

logger = get_logger(__name__)

# Set context once
set_context(user_id=123, request_id="req-001")

# Context automatically included
logger.info("Starting operation")

# Add operation-specific details
logger.info("Data processed", extra={"records": 100, "duration_ms": 245})
```
