# netrun-resilience

Resilience patterns for distributed systems in Python. Provides decorators for retry logic, circuit breakers, timeouts, and bulkhead isolation.

## Features

- **Retry with Exponential Backoff**: Automatic retry with configurable backoff strategies and jitter
- **Circuit Breaker**: Protect against cascading failures with state-based failure detection
- **Timeout**: Enforce execution time limits for both sync and async functions
- **Bulkhead Isolation**: Limit concurrent executions to prevent resource exhaustion
- **Type-Safe**: Full type annotations for IDE support
- **Async Support**: All patterns work with both sync and async functions
- **Thread-Safe**: Circuit breaker and bulkhead use proper locking

## Installation

```bash
pip install netrun-resilience
```

## Quick Start

### Retry with Exponential Backoff

```python
from netrun.resilience import retry

@retry(max_attempts=3, base_delay_ms=1000, exceptions=(ConnectionError,))
async def fetch_data():
    return await httpx.get("https://api.example.com/data")
```

**Features**:
- Exponential backoff: `delay = min(base_delay * (multiplier ** attempt), max_delay)`
- Optional jitter to prevent thundering herd
- Exception filtering (only retry specific exceptions)
- Retry callbacks for logging/metrics

### Circuit Breaker

```python
from netrun.resilience import circuit_breaker

@circuit_breaker(failure_threshold=5, timeout_seconds=60)
async def call_third_party():
    return await external_service.call()
```

**State Machine**:
```
CLOSED → OPEN → HALF_OPEN → CLOSED

CLOSED: Normal operation, requests pass through
OPEN: Blocking requests due to failures
HALF_OPEN: Testing recovery with limited requests
```

**Features**:
- Automatic state transitions based on failure counts
- Configurable timeout before recovery attempt
- Success threshold in HALF_OPEN before closing
- Thread-safe state management
- Manual reset capability

### Timeout

```python
from netrun.resilience import timeout

@timeout(seconds=5.0, message="Operation timed out")
async def slow_operation():
    await asyncio.sleep(10)  # Will timeout after 5 seconds
```

**Features**:
- Async timeout using `asyncio.wait_for`
- Sync timeout using threading
- Custom timeout exception messages

### Bulkhead Isolation

```python
from netrun.resilience import bulkhead

@bulkhead(max_concurrent=10, max_queue=100)
async def resource_intensive():
    return await heavy_computation()
```

**Features**:
- Semaphore-based concurrency limiting
- Queue with maximum size
- Separate pools for sync/async
- Metrics (active count, queued count)

## Combined Patterns

You can combine multiple patterns for comprehensive resilience:

```python
from netrun.resilience import timeout, retry, circuit_breaker

@timeout(seconds=10.0)
@retry(max_attempts=3, base_delay_ms=1000)
@circuit_breaker(failure_threshold=5)
async def resilient_operation():
    return await risky_call()
```

**Execution Order**:
1. Timeout (outermost) - enforces overall time limit
2. Retry (middle) - retries on transient failures
3. Circuit breaker (innermost) - protects against cascading failures

## Configuration Classes

All patterns support configuration via dataclasses:

```python
from netrun.resilience import RetryConfig, CircuitBreakerConfig, retry, circuit_breaker

# Retry configuration
retry_config = RetryConfig(
    max_attempts=3,
    base_delay_ms=1000,
    max_delay_ms=30000,
    backoff_multiplier=2.0,
    jitter=True,
    exceptions=(ConnectionError, TimeoutError)
)

# Circuit breaker configuration
cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    timeout_seconds=60.0,
    half_open_max_calls=3
)
```

## Exception Handling

Each pattern raises specific exceptions:

```python
from netrun.resilience import (
    RetryExhausted,
    CircuitOpenError,
    BulkheadFullError,
    timeout
)

try:
    result = await resilient_operation()
except RetryExhausted as e:
    # All retry attempts failed
    logger.error(f"Retry exhausted: {e}")
except CircuitOpenError as e:
    # Circuit breaker is open
    logger.warning(f"Circuit open: {e}")
except BulkheadFullError as e:
    # Bulkhead at capacity
    logger.warning(f"Bulkhead full: {e}")
except timeout.TimeoutError as e:
    # Operation timed out
    logger.error(f"Timeout: {e}")
```

## Metrics and Monitoring

Access circuit breaker and bulkhead metrics:

```python
from netrun.resilience import circuit_breaker, bulkhead

@circuit_breaker(failure_threshold=5)
async def monitored_function():
    pass

# Access circuit breaker state
breaker = monitored_function.circuit_breaker
metrics = breaker.get_metrics()
print(metrics)
# {
#     "state": "closed",
#     "failure_count": 0,
#     "success_count": 0,
#     "half_open_calls": 0,
#     "last_failure_time": None
# }

# Manual reset
breaker.reset()

@bulkhead(max_concurrent=10)
async def limited_function():
    pass

# Access bulkhead metrics
bulkhead_instance = limited_function.bulkhead
metrics = bulkhead_instance.get_metrics()
print(metrics)
# {
#     "max_concurrent": 10,
#     "max_queue": 100,
#     "async_active": 0,
#     "async_queued": 0,
#     "total_accepted": 0,
#     "total_rejected": 0
# }
```

## State Change Callbacks

Circuit breaker supports state change callbacks:

```python
from netrun.resilience import circuit_breaker, CircuitState

def on_state_change(old_state: CircuitState, new_state: CircuitState):
    logger.info(f"Circuit breaker: {old_state.value} → {new_state.value}")

@circuit_breaker(
    failure_threshold=5,
    on_state_change=on_state_change
)
async def monitored_service():
    pass
```

## Retry Callbacks

Retry supports callbacks before each retry attempt:

```python
from netrun.resilience import retry

def on_retry(exception: Exception, attempt: int):
    logger.warning(f"Retry attempt {attempt} after error: {exception}")

@retry(
    max_attempts=3,
    base_delay_ms=1000,
    on_retry=on_retry
)
async def fetch_with_logging():
    pass
```

## Real-World Examples

### API Client with Full Resilience

```python
import httpx
from netrun.resilience import retry, circuit_breaker, timeout

class ResilientAPIClient:
    def __init__(self):
        self.client = httpx.AsyncClient()

    @timeout(seconds=10.0)
    @retry(
        max_attempts=3,
        base_delay_ms=1000,
        exceptions=(httpx.ConnectError, httpx.TimeoutException)
    )
    @circuit_breaker(failure_threshold=5, timeout_seconds=60)
    async def get(self, url: str):
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
```

### Database Connection Pool

```python
from netrun.resilience import bulkhead, retry

class DatabasePool:
    @bulkhead(max_concurrent=20, max_queue=100)
    @retry(max_attempts=3, base_delay_ms=100)
    async def execute_query(self, query: str):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query)
```

### Background Worker

```python
from netrun.resilience import retry, circuit_breaker

class BackgroundWorker:
    @retry(max_attempts=5, base_delay_ms=2000, max_delay_ms=60000)
    @circuit_breaker(failure_threshold=10, timeout_seconds=300)
    async def process_task(self, task_id: str):
        # Process task with automatic retry and circuit breaker
        result = await self.process(task_id)
        return result
```

## Architecture Patterns

### Charlotte AI Orchestration Integration

This package was extracted from the Charlotte AI orchestration platform. Example integration:

```python
from netrun.resilience import retry, circuit_breaker

class BaseAdapter:
    """Base adapter with built-in resilience."""

    @retry(max_attempts=3, base_delay_ms=1000)
    @circuit_breaker(failure_threshold=5, timeout_seconds=300)
    async def execute(self, task: str):
        # Adapter-specific implementation
        pass
```

## Testing

Run tests with pytest:

```bash
cd /data/workspace/github/Netrun_Service_Library_v2/packages/netrun-resilience
python -m pytest tests/ -v --cov
```

## License

MIT License - Copyright (c) 2025 Netrun Systems

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

## Support

- **Issues**: https://github.com/netrunsystems/Netrun_Service_Library_v2/issues
- **Documentation**: https://github.com/netrunsystems/Netrun_Service_Library_v2/tree/main/packages/netrun-resilience
- **Email**: daniel.garza@netrunsystems.com
