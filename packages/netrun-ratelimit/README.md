# netrun-ratelimit

Distributed rate limiting with token bucket algorithm and Redis backend.

## Features

- **Token Bucket Algorithm**: Allows bursts while maintaining average rate limits
- **Multiple Backends**: In-memory for single instances, Redis for distributed systems
- **FastAPI Integration**: Middleware and decorators for seamless integration
- **Async Support**: Full async/await support for high-performance applications
- **Type-Safe**: Complete type hints with py.typed marker

## Installation

```bash
# Core package (memory backend only)
pip install netrun-ratelimit

# With Redis support
pip install netrun-ratelimit[redis]

# With FastAPI integration
pip install netrun-ratelimit[fastapi]

# All features
pip install netrun-ratelimit[all]
```

## Quick Start

### Basic Usage

```python
from netrun_ratelimit import RateLimiter, MemoryBackend

# Create limiter (100 requests per minute)
limiter = RateLimiter(
    backend=MemoryBackend(),
    rate=100,
    period=60,
)

# Check rate limit
result = limiter.check("user:123")
if result.allowed:
    # Process request
    pass
else:
    # Rate limited
    print(f"Retry after {result.retry_after} seconds")
```

### With Redis (Distributed)

```python
from netrun_ratelimit import RateLimiter, RedisBackend

backend = RedisBackend(redis_url="redis://localhost:6379")
limiter = RateLimiter(backend=backend, rate=100, period=60)

# Works across multiple application instances
result = limiter.check("user:123")
```

### FastAPI Middleware

```python
from fastapi import FastAPI
from netrun_ratelimit import RateLimiter, MemoryBackend, RateLimitMiddleware

app = FastAPI()

limiter = RateLimiter(backend=MemoryBackend(), rate=100, period=60)

app.add_middleware(
    RateLimitMiddleware,
    limiter=limiter,
    exclude_paths=["/health", "/metrics"],
)

@app.get("/api/data")
async def get_data():
    return {"data": "value"}
```

### Route Decorators

```python
from fastapi import FastAPI, Request
from netrun_ratelimit import rate_limit, limit_by_user, limit_by_api_key

app = FastAPI()

# Basic rate limit
@app.get("/api/public")
@rate_limit(rate=10, period=60)
async def public_endpoint(request: Request):
    return {"status": "ok"}

# Per-user rate limit
@app.get("/api/user")
@limit_by_user(rate=100, period=60)
async def user_endpoint(request: Request):
    return {"status": "ok"}

# Per-API-key rate limit
@app.get("/api/partner")
@limit_by_api_key(rate=1000, period=3600)
async def partner_endpoint(request: Request):
    return {"status": "ok"}
```

## Configuration

Use environment variables or Pydantic settings:

```python
from netrun_ratelimit import RateLimitConfig

config = RateLimitConfig(
    rate=100,              # Requests per period
    period=60,             # Period in seconds
    burst=150,             # Max burst size
    redis_url="redis://localhost:6379",
    key_prefix="myapp:",
    include_headers=True,
)
```

Environment variables (prefixed with `RATELIMIT_`):

```bash
RATELIMIT_RATE=100
RATELIMIT_PERIOD=60
RATELIMIT_REDIS_URL=redis://localhost:6379
```

## HTTP Headers

Rate limit information is returned in standard headers:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per period |
| `X-RateLimit-Remaining` | Remaining requests in current period |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |
| `Retry-After` | Seconds until retry (only when limited) |

## Exception Handling

```python
from netrun_ratelimit import RateLimitExceeded
from fastapi import HTTPException

try:
    result = limiter.check("user:123")
    if not result.allowed:
        raise RateLimitExceeded(
            limit=result.limit,
            retry_after=result.retry_after,
        )
except RateLimitExceeded as e:
    raise HTTPException(
        status_code=429,
        detail="Too many requests",
        headers=e.headers,
    )
```

## Token Bucket Algorithm

The token bucket algorithm provides smooth rate limiting with burst capability:

- Bucket starts full with `burst` tokens
- Each request consumes 1 token
- Tokens refill at `rate/period` tokens per second
- Requests are denied when bucket is empty

Example: 100 req/minute with burst of 150
- Can handle initial burst of 150 requests
- Sustained rate limited to ~1.67 requests/second
- Bucket refills even while processing requests

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=netrun_ratelimit

# Type checking
mypy netrun_ratelimit

# Linting
ruff check netrun_ratelimit
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests to the main repository.
