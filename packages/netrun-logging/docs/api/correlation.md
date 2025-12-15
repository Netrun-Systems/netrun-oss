# Correlation ID

Thread-safe correlation ID management for distributed request tracing.

## generate_correlation_id

Generate a new UUID4 correlation ID.

```python
def generate_correlation_id() -> str
```

### Returns
New UUID4 string (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

### Example

```python
from netrun_logging.correlation import generate_correlation_id

cid = generate_correlation_id()
print(cid)  # "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

## get_correlation_id

Get the current correlation ID from context.

```python
def get_correlation_id() -> Optional[str]
```

### Returns
Current correlation ID string, or `None` if not set

### Example

```python
from netrun_logging.correlation import get_correlation_id

cid = get_correlation_id()
if cid:
    print(f"Current correlation ID: {cid}")
```

## set_correlation_id

Set the correlation ID in the current context.

```python
def set_correlation_id(correlation_id: str) -> None
```

### Parameters
- `correlation_id`: Correlation ID to set

### Example

```python
from netrun_logging.correlation import set_correlation_id, get_correlation_id

set_correlation_id("custom-id-123")
print(get_correlation_id())  # "custom-id-123"
```

## correlation_id_context

Context manager for scoped correlation ID tracking.

```python
@contextmanager
def correlation_id_context(correlation_id: Optional[str] = None)
```

### Parameters
- `correlation_id`: Optional ID to use (generates new one if not provided)

### Yields
The correlation ID being used in this context

### Example

```python
from netrun_logging.correlation import correlation_id_context
from netrun_logging import get_logger

logger = get_logger(__name__)

# Auto-generate correlation ID
with correlation_id_context() as cid:
    logger.info("Processing request", extra={"cid": cid})
    # All logs in this block share the same correlation ID

# Use custom correlation ID
with correlation_id_context("request-123") as cid:
    logger.info("Processing", extra={"cid": cid})
```

## Distributed Tracing

Use correlation IDs to trace requests across multiple services:

```python
from netrun_logging.correlation import get_correlation_id
import httpx

async def call_downstream_service():
    cid = get_correlation_id()
    headers = {"X-Correlation-ID": cid}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://downstream-service/api/endpoint",
            headers=headers
        )
    return response
```

## Thread Safety

Correlation IDs are stored using `contextvars` and are thread-safe:

```python
import threading
from netrun_logging.correlation import set_correlation_id, get_correlation_id

def worker():
    set_correlation_id("thread-specific-id")
    print(get_correlation_id())  # "thread-specific-id"

thread1 = threading.Thread(target=worker)
thread1.start()

set_correlation_id("main-thread-id")
print(get_correlation_id())  # "main-thread-id"
```
