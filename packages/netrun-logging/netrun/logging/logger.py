"""
Core Logger Configuration
Unified logging configuration with structlog backend and optional Azure integration
"""

import logging
import os
from typing import Optional
import structlog
from structlog.contextvars import merge_contextvars

from netrun.logging.processors import (
    add_netrun_context,
    add_opentelemetry_trace,
    sanitize_sensitive_fields,
    add_log_context,
)

# Global configuration state
_configured = False
_app_name: Optional[str] = None
_environment: Optional[str] = None


def configure_logging(
    app_name: str = "app",
    environment: Optional[str] = None,
    log_level: str = "INFO",
    enable_json: bool = True,
    enable_correlation_id: bool = True,
    azure_insights_connection_string: Optional[str] = None,
) -> None:
    """
    Configure unified logging for the application with structlog backend.

    Args:
        app_name: Application name for log context
        environment: Environment name (development, staging, production)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Use JSON formatter (default: True)
        enable_correlation_id: Enable correlation ID tracking (default: True)
        azure_insights_connection_string: Azure App Insights connection string

    Example:
        >>> configure_logging(
        ...     app_name="my-service",
        ...     environment="production",
        ...     log_level="INFO",
        ...     enable_json=True
        ... )
        >>> logger = get_logger(__name__)
        >>> logger.info("service_started", version="1.0.0")
    """
    global _configured, _app_name, _environment

    _app_name = app_name
    _environment = environment or os.getenv("ENVIRONMENT", "development")

    # Build processor pipeline
    processors = []

    # Add correlation ID support via contextvars
    if enable_correlation_id:
        processors.append(merge_contextvars)

    # Add log context (user_id, tenant_id, version, extra fields)
    processors.append(add_log_context)

    # Add Netrun standard context (app, env)
    processors.append(add_netrun_context(_app_name, _environment))

    # Add log level
    processors.append(structlog.processors.add_log_level)

    # Add ISO 8601 UTC timestamp
    processors.append(structlog.processors.TimeStamper(fmt="iso", utc=True))

    # Add OpenTelemetry trace context
    processors.append(add_opentelemetry_trace)

    # Sanitize sensitive fields
    processors.append(sanitize_sensitive_fields)

    # Format exception info
    processors.append(structlog.processors.format_exc_info)

    # Add stack info for exceptions
    processors.append(structlog.processors.StackInfoRenderer())

    # Choose renderer based on enable_json flag
    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging for compatibility
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        force=True,
    )

    # Configure Azure App Insights if connection string provided
    if azure_insights_connection_string:
        try:
            from netrun.logging.integrations.azure_insights import configure_azure_insights
            configure_azure_insights(azure_insights_connection_string, app_name)
        except ImportError:
            structlog.get_logger(__name__).warning(
                "azure_insights_unavailable",
                reason="Azure App Insights integration not available"
            )

    _configured = True

    # Log configuration complete
    structlog.get_logger(__name__).info(
        "logging_configured",
        app=_app_name,
        environment=_environment,
        log_level=log_level,
        json_enabled=enable_json,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structlog logger instance with correlation ID support and async methods.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog.BoundLogger instance with async support

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_login", user_id=12345, ip="192.168.1.1")
        >>> await logger.ainfo("async_operation_complete", duration=1.23)
    """
    return structlog.get_logger(name)
