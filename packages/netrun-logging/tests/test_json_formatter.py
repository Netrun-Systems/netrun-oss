"""Tests for JSON formatter."""

import json
import logging
import pytest
from netrun_logging.formatters.json_formatter import JsonFormatter


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_format_basic_message(self, sample_log_record):
        """Test basic log message formatting."""
        formatter = JsonFormatter()
        output = formatter.format(sample_log_record)

        data = json.loads(output)

        assert "timestamp" in data
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test.logger"

    def test_format_with_extra_fields(self):
        """Test that extra fields are included."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.user_id = 12345
        record.action = "login"

        output = formatter.format(record)
        data = json.loads(output)

        assert "extra" in data
        assert data["extra"]["user_id"] == 12345
        assert data["extra"]["action"] == "login"

    def test_format_with_correlation_id(self):
        """Test correlation ID inclusion."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "abc-123-def"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["correlation_id"] == "abc-123-def"

    def test_format_with_exception(self):
        """Test exception formatting."""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "Test error" in data["exception"]["message"]

    def test_timestamp_iso8601_format(self, sample_log_record):
        """Test ISO 8601 timestamp format."""
        formatter = JsonFormatter(timestamp_format="iso8601")
        output = formatter.format(sample_log_record)
        data = json.loads(output)

        # ISO 8601 format should contain T separator
        assert "T" in data["timestamp"]

    def test_timestamp_epoch_format(self, sample_log_record):
        """Test epoch timestamp format."""
        formatter = JsonFormatter(timestamp_format="epoch")
        output = formatter.format(sample_log_record)
        data = json.loads(output)

        # Epoch format should be numeric
        assert float(data["timestamp"])
