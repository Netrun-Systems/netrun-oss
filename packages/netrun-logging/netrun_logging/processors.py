"""
Structlog Processors for Netrun Logging
Custom processors for log enrichment, security, and observability
"""

import structlog
from typing import Any, MutableMapping
from structlog.contextvars import merge_contextvars


def add_netrun_context(app_name: str, environment: str):
    """
    Processor to add Netrun standard context to all log entries.

    Args:
        app_name: Application name for log context
        environment: Environment name (development, staging, production)

    Returns:
        Processor function that adds app and env fields
    """
    def processor(
        logger: Any,
        method_name: str,
        event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        event_dict["app"] = app_name
        event_dict["env"] = environment
        return event_dict
    return processor


def add_opentelemetry_trace(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Inject OpenTelemetry trace context into log entries.

    Adds trace_id and span_id to logs when running within an active span.
    This enables correlation between logs and distributed traces.

    Args:
        logger: Logger instance
        method_name: Log method name (info, error, etc.)
        event_dict: Log event dictionary

    Returns:
        Updated event_dict with trace context
    """
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except ImportError:
        # OpenTelemetry not installed, skip trace injection
        pass
    except Exception:
        # Gracefully handle any other errors
        pass

    return event_dict


def sanitize_sensitive_fields(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Redact sensitive information from logs.

    Scans all keys in the event dictionary and redacts values for fields
    containing sensitive keywords (password, api_key, secret, token, etc.).

    Args:
        logger: Logger instance
        method_name: Log method name (info, error, etc.)
        event_dict: Log event dictionary

    Returns:
        Updated event_dict with sensitive fields redacted
    """
    sensitive_keys = {
        "password",
        "api_key",
        "apikey",
        "secret",
        "token",
        "authorization",
        "auth",
        "credential",
        "private_key",
        "access_token",
        "refresh_token",
    }

    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            event_dict[key] = "[REDACTED]"

    return event_dict


def add_log_context(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Add LogContext fields to log entries.

    Merges user_id, tenant_id, version, and extra fields from the
    LogContext into the log event.

    Args:
        logger: Logger instance
        method_name: Log method name (info, error, etc.)
        event_dict: Log event dictionary

    Returns:
        Updated event_dict with context fields
    """
    try:
        from netrun_logging.context import get_context
        ctx = get_context()

        if ctx.user_id:
            event_dict["user_id"] = ctx.user_id
        if ctx.tenant_id:
            event_dict["tenant_id"] = ctx.tenant_id
        if ctx.version:
            event_dict["version"] = ctx.version
        if ctx.extra:
            event_dict.update(ctx.extra)
    except Exception:
        # Gracefully handle any errors
        pass

    return event_dict
