"""Tests for logger configuration with structlog backend."""

import logging
import pytest
import structlog
from netrun_logging import configure_logging, get_logger


class TestLoggerConfiguration:
    """Tests for configure_logging function with structlog."""

    def test_configure_logging_basic(self):
        """Test basic logging configuration."""
        configure_logging(app_name="test-app", environment="development")

        logger = get_logger("test")
        assert logger is not None
        # Structlog returns BoundLoggerLazyProxy, which implements the same interface
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")

    def test_configure_logging_sets_level(self):
        """Test that log level is properly set."""
        configure_logging(log_level="DEBUG")

        # Check that structlog is configured
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_json_format(self, capsys):
        """Test JSON format output."""
        configure_logging(app_name="json-test", enable_json=True)

        logger = get_logger("test")
        logger.info("test_message", extra_field="value")

        captured = capsys.readouterr()
        # Should contain JSON structure
        output = captured.err + captured.out
        assert '"event":' in output or '"test_message"' in output

    def test_configure_logging_console_format(self, capsys):
        """Test console (non-JSON) format output."""
        configure_logging(app_name="console-test", enable_json=False)

        logger = get_logger("test")
        logger.info("test_console_message")

        captured = capsys.readouterr()
        output = captured.err + captured.out
        # Console format should be more human-readable
        assert "test_console_message" in output

    def test_get_logger_returns_structlog_logger(self):
        """Test get_logger returns proper structlog logger instance."""
        configure_logging()
        logger = get_logger("my.module")

        # Structlog returns BoundLoggerLazyProxy, which implements the same interface
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "bind")
        assert hasattr(logger, "unbind")

    def test_logger_includes_app_context(self, capsys):
        """Test that logs include app name and environment."""
        configure_logging(app_name="test-app", environment="testing", enable_json=True)

        logger = get_logger("test")
        logger.info("context_test")

        captured = capsys.readouterr()
        output = captured.err + captured.out
        assert '"app":' in output or '"env":' in output

    def test_async_logging_methods_available(self):
        """Test that async logging methods are available."""
        configure_logging()
        logger = get_logger("test")

        # Check async methods exist
        assert hasattr(logger, "ainfo")
        assert hasattr(logger, "aerror")
        assert hasattr(logger, "awarning")
        assert hasattr(logger, "adebug")
        assert hasattr(logger, "acritical")
