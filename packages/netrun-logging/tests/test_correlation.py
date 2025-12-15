"""Tests for correlation ID management."""

import pytest
from netrun_logging.correlation import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    correlation_id_context,
)


class TestCorrelationId:
    """Tests for correlation ID functions."""

    def test_generate_correlation_id_is_uuid(self):
        """Test that generated ID is valid UUID format."""
        cid = generate_correlation_id()

        # UUID format: 8-4-4-4-12 hex characters
        parts = cid.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_generate_unique_ids(self):
        """Test that each call generates a unique ID."""
        ids = {generate_correlation_id() for _ in range(100)}
        assert len(ids) == 100

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        set_correlation_id("test-id-123")
        assert get_correlation_id() == "test-id-123"
        clear_correlation_id()

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-id")
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_correlation_id_context_manager(self):
        """Test context manager for correlation ID."""
        with correlation_id_context("ctx-id-456") as cid:
            assert cid == "ctx-id-456"
            assert get_correlation_id() == "ctx-id-456"

        # After context, ID should be cleared
        assert get_correlation_id() is None

    def test_correlation_id_context_auto_generate(self):
        """Test context manager auto-generates ID if not provided."""
        with correlation_id_context() as cid:
            assert cid is not None
            assert len(cid) == 36  # UUID length
            assert get_correlation_id() == cid
