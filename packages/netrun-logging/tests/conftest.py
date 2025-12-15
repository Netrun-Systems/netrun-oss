"""Pytest fixtures for netrun-logging tests."""

import pytest
import logging

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)
    yield
    root_logger.handlers.clear()

@pytest.fixture
def sample_log_record():
    """Create a sample log record for testing."""
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="/test/path.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    return record
