"""
JSON Formatter for Structured Logging

Extracted and adapted from GhostGrid audit_logger.py (lines 74-114)
Provides JSON-formatted log output for SIEM integration and structured log analysis.

Copyright (c) 2025 Netrun Systems
SPDX-License-Identifier: MIT
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """
    JSON-formatted logging handler for structured log output.

    Each log entry includes:
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name (usually module path)
    - message: Log message
    - correlation_id: Request correlation ID (if available)
    - extra: Additional fields passed via extra={} parameter
    - exception: Formatted exception with stack trace (if present)

    Usage:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

        logger.info("User action", extra={"user_id": 12345, "action": "login"})
        # Output: {"timestamp": "2025-11-24T22:17:00.123456+00:00", "level": "INFO", ...}
    """

    # Fields to exclude from extra data (internal Python logging fields)
    RESERVED_FIELDS = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "thread",
        "threadName",
        "exc_info",
        "exc_text",
        "stack_info",
        "taskName",
    }

    def __init__(
        self,
        include_logger_name: bool = True,
        include_function_name: bool = False,
        include_line_number: bool = False,
        timestamp_format: str = "iso8601",
    ):
        """
        Initialize JSON formatter.

        Args:
            include_logger_name: Include logger name in output (default: True)
            include_function_name: Include function name in output (default: False)
            include_line_number: Include line number in output (default: False)
            timestamp_format: Timestamp format ("iso8601" or "epoch")
        """
        super().__init__()
        self.include_logger_name = include_logger_name
        self.include_function_name = include_function_name
        self.include_line_number = include_line_number
        self.timestamp_format = timestamp_format

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: Python logging.LogRecord instance

        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add optional fields
        if self.include_logger_name:
            log_entry["logger"] = record.name

        if self.include_function_name:
            log_entry["function"] = record.funcName

        if self.include_line_number:
            log_entry["line"] = record.lineno

        # Add correlation ID if present
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add extra fields (exclude internal Python logging fields)
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.RESERVED_FIELDS and not key.startswith("_")
        }

        # Remove correlation_id from extra (already added above)
        extra_fields.pop("correlation_id", None)

        if extra_fields:
            log_entry["extra"] = extra_fields

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self._format_exception(record.exc_info)

        return json.dumps(log_entry, default=str)

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """
        Format timestamp based on configuration.

        Args:
            record: Python logging.LogRecord instance

        Returns:
            Formatted timestamp string
        """
        if self.timestamp_format == "epoch":
            return str(record.created)
        else:  # iso8601 (default)
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
            return dt.isoformat()

    def _format_exception(self, exc_info: Any) -> Dict[str, Any]:
        """
        Format exception information with stack trace.

        Args:
            exc_info: Exception info tuple (type, value, traceback)

        Returns:
            Dictionary with exception details
        """
        exc_type, exc_value, exc_traceback = exc_info

        return {
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": str(exc_value),
            "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback),
        }
