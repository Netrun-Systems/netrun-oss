"""
Netrun Unified Logging Service
Structured logging with structlog backend, correlation ID tracking, and Azure App Insights integration

Usage:
    from netrun_logging import configure_logging, get_logger

    configure_logging(app_name="my-service", environment="production")
    logger = get_logger(__name__)
    logger.info("application_started", version="1.1.0")

New in v1.2.0:
    - Ecosystem integration helpers for netrun-errors, netrun-auth, netrun-config
    - bind_error_context() for exception handling integration
    - bind_request_context() for HTTP request tracking
    - bind_operation_context() for business operation tracking
    - log_operation_timing() context manager for timing operations
    - log_timing() decorator for function timing
    - create_audit_logger() factory for audit logging

v1.1.0:
    - Structlog backend for improved performance and flexibility
    - Async logging support (logger.ainfo, logger.aerror, etc.)
    - Enhanced context management with bind_context()
    - OpenTelemetry trace injection
    - Automatic sensitive field sanitization
"""

from netrun_logging.logger import configure_logging, get_logger
from netrun_logging.correlation import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    correlation_id_context,
    bind_context,
    clear_context,
)
from netrun_logging.context import (
    LogContext,
    get_context,
    set_context,
    clear_context as clear_log_context,
)
from netrun_logging.formatters.json_formatter import JsonFormatter
from netrun_logging.ecosystem import (
    bind_error_context,
    bind_request_context,
    bind_operation_context,
    log_operation_timing,
    log_timing,
    create_audit_logger,
)

__version__ = "1.2.0"
__all__ = [
    # Core configuration
    "configure_logging",
    "get_logger",
    # Correlation ID management
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
    "correlation_id_context",
    # Context management (structlog)
    "bind_context",
    "clear_context",
    # Legacy context management (LogContext)
    "LogContext",
    "get_context",
    "set_context",
    "clear_log_context",
    # Formatters
    "JsonFormatter",
    # Ecosystem integration (v1.2.0)
    "bind_error_context",
    "bind_request_context",
    "bind_operation_context",
    "log_operation_timing",
    "log_timing",
    "create_audit_logger",
]
