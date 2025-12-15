# Basic Usage Examples

## Minimal Setup

The simplest possible setup:

```python
from netrun_logging import configure_logging, get_logger

# One-time setup
configure_logging(app_name="my-app")

# Get logger
logger = get_logger(__name__)

# Use it
logger.info("Hello, world!")
```

## Logging Levels

```python
from netrun_logging import configure_logging, get_logger

configure_logging(app_name="my-app", log_level="DEBUG")
logger = get_logger(__name__)

# Different log levels
logger.debug("Detailed diagnostic information")
logger.info("General information")
logger.warning("Something unexpected happened")
logger.error("A serious error occurred")
logger.critical("System is in critical state")
```

## Adding Structured Data

Include extra fields for better searchability:

```python
from netrun_logging import get_logger

logger = get_logger("order_service")

# Simple message
logger.info("Order created")

# With structured data
logger.info("Order created", extra={
    "order_id": "ORD-12345",
    "user_id": 789,
    "amount": 99.99,
    "currency": "USD",
})

# Nested data
logger.info("Payment processed", extra={
    "transaction": {
        "id": "TXN-001",
        "amount": 99.99,
        "status": "completed",
    },
    "user_id": 789,
})
```

## Exception Logging

```python
from netrun_logging import get_logger

logger = get_logger(__name__)

# Log with exception context
try:
    result = int("not a number")
except ValueError:
    logger.exception("Failed to parse value")  # Includes traceback
```

## Contextual Logging

```python
from netrun_logging import get_logger
from netrun_logging.context import set_context, clear_context

logger = get_logger(__name__)

# Set context for a request
set_context(
    request_id="REQ-123",
    user_id=456,
    session_id="SESS-789",
)

# All logs automatically include context
logger.info("Processing request")  # Includes request_id, user_id, session_id
logger.info("Validating user")      # Includes same context

# Clear context when done
clear_context()
```

## Distributed Tracing

```python
from netrun_logging import get_logger
from netrun_logging.correlation import correlation_id_context

logger = get_logger(__name__)

# Start request with correlation ID
with correlation_id_context() as correlation_id:
    logger.info("Request started", extra={"cid": correlation_id})

    # Simulate calling downstream service
    logger.info("Calling downstream API")

    # Correlation ID is available throughout
    logger.info("Request completed")
```

## Multiple Loggers

```python
from netrun_logging import get_logger

# Create loggers for different modules
auth_logger = get_logger("auth_service")
payment_logger = get_logger("payment_service")
db_logger = get_logger("database")

# Use independently
auth_logger.info("User authenticated", extra={"user_id": 123})
payment_logger.info("Payment initiated", extra={"amount": 99.99})
db_logger.debug("Query executed", extra={"table": "users", "rows": 42})
```

## Performance Monitoring

```python
import time
from netrun_logging import get_logger

logger = get_logger(__name__)

def slow_operation():
    start = time.time()
    # ... do work ...
    duration = (time.time() - start) * 1000

    logger.info(
        "Operation completed",
        extra={
            "duration_ms": duration,
            "operation": "slow_operation",
        }
    )

slow_operation()
```

## Environment-Specific Configuration

```python
from netrun_logging import configure_logging
import os

environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    configure_logging(
        app_name="my-service",
        environment="production",
        log_level="INFO",
    )
else:
    configure_logging(
        app_name="my-service",
        environment="development",
        log_level="DEBUG",
    )
```

## Application Startup Logging

```python
from netrun_logging import configure_logging, get_logger

# Configure at startup
configure_logging(
    app_name="user-service",
    environment="production",
    log_level="INFO",
)

logger = get_logger(__name__)

# Log startup information
logger.info("Application starting")
logger.info("Configuration loaded", extra={
    "app_name": "user-service",
    "version": "1.0.0",
    "environment": "production",
})

# Your application code
logger.info("Application started successfully")
```

## Monitoring and Alerting

```python
from netrun_logging import get_logger

logger = get_logger("alerts")

# Log errors for monitoring systems to pick up
try:
    process_payment(amount=99.99)
except Exception as e:
    # Alert level logging
    logger.error(
        "Payment processing failed - ALERT",
        extra={
            "severity": "high",
            "alert_enabled": True,
            "amount": 99.99,
            "error_type": type(e).__name__,
        }
    )
```
