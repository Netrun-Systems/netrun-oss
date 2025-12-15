"""
netrun-logging v1.1.0 Features Demo
Demonstrates all new features in v1.1.0 release
"""

import asyncio
from netrun_logging import (
    configure_logging,
    get_logger,
    bind_context,
    clear_context,
    correlation_id_context,
)


def demo_basic_logging():
    """Demo 1: Basic structlog usage with key-value logging."""
    print("\n=== Demo 1: Basic Structlog Logging ===\n")

    configure_logging(app_name="demo-app", environment="development", enable_json=False)
    logger = get_logger(__name__)

    # Traditional message (still works)
    logger.info("Application started")

    # Key-value logging (recommended)
    logger.info("user_login", user_id=12345, ip="192.168.1.1", duration=1.23)

    # Error logging with context
    logger.error("database_error", error_code="DB001", table="users", operation="insert")


def demo_sensitive_field_sanitization():
    """Demo 2: Automatic sensitive field sanitization."""
    print("\n=== Demo 2: Sensitive Field Sanitization ===\n")

    configure_logging(app_name="security-demo", enable_json=False)
    logger = get_logger(__name__)

    # These sensitive fields will be automatically redacted
    logger.info(
        "api_request",
        user="alice",
        password="secret123",  # Will be redacted
        api_key="sk-abc123",  # Will be redacted
        token="bearer xyz",  # Will be redacted
        safe_field="this is visible",
    )


def demo_context_binding():
    """Demo 3: Enhanced context management with bind_context()."""
    print("\n=== Demo 3: Context Binding ===\n")

    configure_logging(app_name="context-demo", enable_json=False)
    logger = get_logger(__name__)

    # Bind context once - applies to all subsequent logs
    bind_context(user_id="user-12345", tenant_id="acme-corp", session_id="sess-789")

    logger.info("user_action", action="login")
    logger.info("user_action", action="view_dashboard")
    logger.info("user_action", action="update_profile")

    # Clear context
    clear_context()
    logger.info("logged_out")  # No user_id, tenant_id, session_id


def demo_correlation_id():
    """Demo 4: Correlation ID tracking."""
    print("\n=== Demo 4: Correlation ID Tracking ===\n")

    configure_logging(app_name="correlation-demo", enable_json=False)
    logger = get_logger(__name__)

    # Use correlation_id_context for request scoping
    with correlation_id_context() as cid:
        logger.info("request_started", endpoint="/api/users")
        logger.info("processing_request", step="validate_input")
        logger.info("processing_request", step="query_database")
        logger.info("request_completed", status=200, duration=0.45)


async def demo_async_logging():
    """Demo 5: Async logging support."""
    print("\n=== Demo 5: Async Logging ===\n")

    configure_logging(app_name="async-demo", enable_json=False)
    logger = get_logger(__name__)

    # Async logging methods
    await logger.ainfo("async_request_started", request_id=123)

    # Simulate async operation
    await asyncio.sleep(0.1)

    await logger.ainfo("async_operation_completed", request_id=123, duration=0.1)
    await logger.awarning("async_warning", message="Rate limit approaching")
    await logger.aerror("async_error", error="Connection timeout")


def demo_opentelemetry_trace():
    """Demo 6: OpenTelemetry trace injection."""
    print("\n=== Demo 6: OpenTelemetry Trace Injection ===\n")

    configure_logging(app_name="trace-demo", enable_json=False)
    logger = get_logger(__name__)

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        # Set up OpenTelemetry (for demo purposes)
        provider = TracerProvider()
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        tracer = trace.get_tracer(__name__)

        # Logging within a trace span
        with tracer.start_as_current_span("process_request"):
            logger.info("processing_request")  # Will include trace_id and span_id
            logger.info("operation_completed")

    except ImportError:
        logger.info(
            "opentelemetry_not_installed",
            message="Install opentelemetry-api for trace injection demo",
        )


def demo_performance_comparison():
    """Demo 7: Performance comparison with timing."""
    print("\n=== Demo 7: Performance Comparison ===\n")

    import time

    configure_logging(app_name="perf-demo", enable_json=True)
    logger = get_logger(__name__)

    # Time 1000 log operations
    iterations = 1000
    start = time.perf_counter()

    for i in range(iterations):
        logger.info("performance_test", iteration=i, data="test_data")

    elapsed = time.perf_counter() - start
    avg_time = (elapsed / iterations) * 1_000_000  # Convert to microseconds

    print(f"\nLogged {iterations} messages in {elapsed:.3f} seconds")
    print(f"Average time per log: {avg_time:.2f} µs")
    print(f"Throughput: {iterations/elapsed:.0f} logs/second")


def main():
    """Run all demos."""
    print("=" * 80)
    print("netrun-logging v1.1.0 Feature Demonstrations")
    print("=" * 80)

    # Run synchronous demos
    demo_basic_logging()
    demo_sensitive_field_sanitization()
    demo_context_binding()
    demo_correlation_id()
    demo_opentelemetry_trace()
    demo_performance_comparison()

    # Run async demo
    print("\n" + "=" * 80)
    asyncio.run(demo_async_logging())

    print("\n" + "=" * 80)
    print("All demos completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
