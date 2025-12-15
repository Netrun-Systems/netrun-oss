"""
Basic Usage Example - netrun-logging

Demonstrates core logging functionality with JSON formatting.
"""

from netrun_logging import configure_logging, get_logger
from netrun_logging.correlation import correlation_id_context

# Configure logging
configure_logging(
    app_name="example-service",
    environment="development",
    log_level="DEBUG",
    enable_json=True,
)

# Get a logger
logger = get_logger(__name__)

# Basic logging
logger.info("Application started")
logger.debug("Debug message with details")
logger.warning("Warning: resource usage high")

# Logging with extra fields
logger.info("User action", extra={
    "user_id": 12345,
    "action": "login",
    "ip_address": "192.168.1.100",
})

# Logging with correlation ID
with correlation_id_context() as cid:
    logger.info(f"Processing request", extra={"correlation_id": cid})
    logger.info("Step 1: Validate input", extra={"correlation_id": cid})
    logger.info("Step 2: Process data", extra={"correlation_id": cid})
    logger.info("Step 3: Return result", extra={"correlation_id": cid})

# Exception logging
try:
    raise ValueError("Example error")
except ValueError:
    logger.exception("An error occurred")

print("\n[SUCCESS] Basic logging example complete!")
