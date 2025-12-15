# FastAPI Integration

## Quick Start

```python
from fastapi import FastAPI
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

# Configure logging at startup
configure_logging(app_name="fastapi-service", environment="production")

# Create app
app = FastAPI(title="FastAPI Service")

# Add logging middleware
add_logging_middleware(app)

# Get logger
logger = get_logger(__name__)

@app.get("/health")
async def health_check():
    logger.info("Health check called")
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Request/Response Logging

```python
from fastapi import FastAPI
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

configure_logging(app_name="api-service")
app = FastAPI()
add_logging_middleware(app, log_level="INFO")

logger = get_logger(__name__)

@app.post("/api/users")
async def create_user(name: str, email: str):
    logger.info(
        "Creating user",
        extra={
            "name": name,
            "email": email,
        }
    )

    user_id = 123  # Simulated

    logger.info(
        "User created",
        extra={
            "user_id": user_id,
            "name": name,
            "email": email,
        }
    )

    return {"user_id": user_id, "name": name, "email": email}
```

All requests and responses are automatically logged with:
- HTTP method
- Path
- Status code
- Duration
- Correlation ID

## Correlation ID Propagation

```python
from fastapi import FastAPI, Request
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.correlation import get_correlation_id
import httpx

configure_logging(app_name="service-a")
app = FastAPI()
add_logging_middleware(app)

logger = get_logger(__name__)

@app.get("/api/data")
async def get_data():
    # Get correlation ID from request context
    correlation_id = get_correlation_id()

    logger.info(
        "Calling downstream service",
        extra={"downstream": "service-b"}
    )

    # Pass correlation ID to downstream service
    headers = {"X-Correlation-ID": correlation_id}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://service-b:8001/api/endpoint",
            headers=headers
        )

    logger.info(
        "Downstream call completed",
        extra={"status": response.status_code}
    )

    return response.json()
```

## Request-Scoped Context

```python
from fastapi import FastAPI, Request
from netrun_logging import configure_logging, get_logger
from netrun_logging.context import set_context, clear_context
from netrun_logging.middleware import add_logging_middleware

configure_logging(app_name="scoped-context-service")
app = FastAPI()
add_logging_middleware(app)

logger = get_logger(__name__)

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    # Extract user info from request (example)
    user_id = request.headers.get("X-User-ID", "anonymous")
    request_path = request.url.path

    # Set context for this request
    set_context(
        user_id=user_id,
        request_path=request_path,
        method=request.method,
    )

    logger.info("Request received")

    try:
        response = await call_next(request)
        return response
    finally:
        # Clear context when request is done
        clear_context()

@app.get("/api/profile")
async def get_profile():
    # Context is automatically included in all logs
    logger.info("Retrieving user profile")
    return {"user_id": "123", "profile": "data"}
```

## Error Handling with Logging

```python
from fastapi import FastAPI, HTTPException
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

configure_logging(app_name="error-handler-service")
app = FastAPI()
add_logging_middleware(app)

logger = get_logger(__name__)

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    try:
        # Simulate database lookup
        if user_id < 0:
            raise ValueError("Invalid user ID")

        logger.debug(f"Looking up user {user_id}")
        user = {"id": user_id, "name": "John Doe"}
        logger.info("User found", extra={"user_id": user_id})

        return user

    except ValueError as e:
        logger.warning("Invalid user ID provided", extra={"user_id": user_id})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error retrieving user")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Batch Operations

```python
from fastapi import FastAPI
from netrun_logging import configure_logging, get_logger
from netrun_logging.correlation import correlation_id_context

configure_logging(app_name="batch-service")
app = FastAPI()
logger = get_logger(__name__)

@app.post("/api/batch/process")
async def process_batch(items: list):
    # Use correlation ID for entire batch
    with correlation_id_context() as batch_id:
        logger.info(
            "Starting batch processing",
            extra={
                "batch_id": batch_id,
                "item_count": len(items),
            }
        )

        successful = 0
        failed = 0

        for i, item in enumerate(items):
            try:
                logger.debug(
                    "Processing item",
                    extra={"index": i, "item_id": item.get("id")}
                )
                # Process item
                successful += 1
            except Exception as e:
                logger.error(
                    "Failed to process item",
                    extra={
                        "index": i,
                        "item_id": item.get("id"),
                        "error": str(e),
                    }
                )
                failed += 1

        logger.info(
            "Batch processing completed",
            extra={
                "batch_id": batch_id,
                "successful": successful,
                "failed": failed,
                "total": len(items),
            }
        )

        return {
            "batch_id": batch_id,
            "successful": successful,
            "failed": failed,
        }
```

## Custom Middleware with Logging

```python
from fastapi import FastAPI, Request
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
import time

configure_logging(app_name="custom-middleware-service")
app = FastAPI()
add_logging_middleware(app)

logger = get_logger(__name__)

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    duration_ms = duration * 1000

    logger.info(
        "Request timing",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": f"{duration_ms:.2f}",
        }
    )

    return response

@app.get("/api/slow")
async def slow_endpoint():
    import asyncio
    await asyncio.sleep(0.5)
    logger.info("Slow endpoint executed")
    return {"message": "done"}
```

## Startup/Shutdown Events

```python
from fastapi import FastAPI
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

configure_logging(app_name="lifecycle-service")
app = FastAPI()
add_logging_middleware(app)

logger = get_logger(__name__)

@app.on_event("startup")
async def startup():
    logger.info("Application starting up")
    logger.info("Database connecting")
    # Initialize resources
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down")
    # Cleanup resources
    logger.info("Shutdown complete")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```
