#!/usr/bin/env python3
"""
Netrun Service Library - Logging Example

Demonstrates netrun-logging features including structured logging,
ecosystem helpers, and Azure App Insights integration.

Requirements:
    pip install netrun-logging

Run:
    python logging_example.py
"""

import asyncio
import time

# ============================================================================
# BASIC LOGGING
# ============================================================================
from netrun_logging import configure_logging, get_logger

# Configure logging for your service
configure_logging(
    service_name="logging-demo",
    environment="development",
    log_level="DEBUG",
    json_format=True,  # Set to True for structured JSON output
)

# Get a logger instance
logger = get_logger(__name__)

# Basic logging with structured data
logger.info("application_started", version="1.0.0", environment="development")
logger.debug("debug_message", key="value", number=42)
logger.warning("potential_issue", reason="disk space low", threshold_pct=90)


# ============================================================================
# ECOSYSTEM HELPERS
# ============================================================================
from netrun_logging.ecosystem import (
    bind_request_context,
    log_operation_timing,
    log_timing,
    create_audit_logger,
)


# 1. Request Context Binding
def handle_request(request_id: str, user_id: str):
    """Bind request context for all subsequent logs."""
    bind_request_context(
        method="POST",
        path="/api/users",
        user_id=user_id,
        request_id=request_id,
    )

    # All subsequent logs will include request context
    logger.info("processing_request", action="create_user")
    logger.info("validation_passed")
    logger.info("request_complete", status="success")


# 2. Operation Timing Context Manager
def slow_database_operation():
    """Demonstrate operation timing with context manager."""
    with log_operation_timing("database_query", resource_type="users"):
        # Simulate slow operation
        time.sleep(0.1)
        logger.info("query_executed", rows_returned=42)


# 3. Timing Decorator
@log_timing(operation="external_api_call", level="info")
def call_external_api():
    """Demonstrate timing decorator."""
    time.sleep(0.05)
    return {"status": "success"}


# 4. Audit Logger
audit_logger = create_audit_logger("logging-demo")


def perform_sensitive_action(user_id: str, action: str):
    """Demonstrate audit logging for security-sensitive operations."""
    audit_logger.info(
        "sensitive_action",
        user_id=user_id,
        action=action,
        resource="user_permissions",
        details={"role_granted": "admin"},
    )


# ============================================================================
# ASYNC LOGGING
# ============================================================================
async def async_operation():
    """Demonstrate async-safe logging."""
    logger.info("async_operation_started")
    await asyncio.sleep(0.1)
    logger.info("async_operation_completed", result="success")


# ============================================================================
# SENSITIVE DATA REDACTION
# ============================================================================
def demonstrate_redaction():
    """Demonstrate automatic sensitive field redaction."""
    # These fields are automatically redacted
    logger.info(
        "user_created",
        username="john_doe",
        password="secret123",  # Will be redacted to [REDACTED]
        api_key="sk-abc123",   # Will be redacted to [REDACTED]
        email="john@example.com",
    )


# ============================================================================
# MAIN DEMO
# ============================================================================
def main():
    """Run all logging demonstrations."""
    print("=" * 60)
    print("Netrun Logging Demo")
    print("=" * 60)

    print("\n1. Basic Logging")
    logger.info("demo_section", section="basic_logging")

    print("\n2. Request Context Binding")
    handle_request(request_id="req-123", user_id="user-456")

    print("\n3. Operation Timing")
    slow_database_operation()

    print("\n4. Timing Decorator")
    result = call_external_api()
    logger.info("api_result", result=result)

    print("\n5. Audit Logging")
    perform_sensitive_action(user_id="admin-001", action="grant_admin")

    print("\n6. Async Logging")
    asyncio.run(async_operation())

    print("\n7. Sensitive Data Redaction")
    demonstrate_redaction()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
