"""Tests for reconnection module."""

import pytest
from unittest.mock import AsyncMock

from netrun.websocket.reconnection import (
    ReconnectionConfig,
    ReconnectionManager,
    ReconnectionTracker
)


class TestReconnectionConfig:
    """Test ReconnectionConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ReconnectionConfig()
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.max_attempts == 10
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReconnectionConfig(
            initial_delay=2.0,
            max_delay=120.0,
            max_attempts=5
        )
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.max_attempts == 5


class TestReconnectionManager:
    """Test ReconnectionManager."""

    def test_initialization(self):
        """Test manager initialization."""
        config = ReconnectionConfig(max_attempts=5)
        manager = ReconnectionManager(config)
        assert manager.config.max_attempts == 5
        assert manager.attempt == 0
        assert manager.connected is False

    def test_reset(self):
        """Test resetting reconnection state."""
        manager = ReconnectionManager()
        manager.attempt = 5
        manager.connected = True
        manager.reset()
        assert manager.attempt == 0
        assert manager.connected is False

    def test_calculate_delay(self):
        """Test delay calculation."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        manager = ReconnectionManager(config)

        # First attempt
        delay1 = manager.calculate_delay()
        assert delay1 == 1.0

        # Second attempt
        manager.attempt = 1
        delay2 = manager.calculate_delay()
        assert delay2 == 2.0

        # Third attempt
        manager.attempt = 2
        delay3 = manager.calculate_delay()
        assert delay3 == 4.0

    def test_calculate_delay_with_max(self):
        """Test delay calculation with max delay."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=5.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        manager = ReconnectionManager(config)
        manager.attempt = 10

        delay = manager.calculate_delay()
        assert delay <= 5.0  # Should be capped at max_delay

    @pytest.mark.asyncio
    async def test_successful_reconnect(self):
        """Test successful reconnection."""
        connect_callback = AsyncMock(return_value=True)
        on_success = AsyncMock()

        manager = ReconnectionManager()
        success = await manager.reconnect(
            connect_callback=connect_callback,
            on_success=on_success
        )

        assert success is True
        assert manager.connected is True
        connect_callback.assert_called_once()
        on_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_reconnect_max_attempts(self):
        """Test reconnection with max attempts reached."""
        connect_callback = AsyncMock(return_value=False)
        on_max_attempts = AsyncMock()

        config = ReconnectionConfig(
            max_attempts=2,
            initial_delay=0.01  # Fast for testing
        )
        manager = ReconnectionManager(config)

        success = await manager.reconnect(
            connect_callback=connect_callback,
            on_max_attempts=on_max_attempts
        )

        assert success is False
        assert connect_callback.call_count == 2
        on_max_attempts.assert_called_once()

    def test_get_stats(self):
        """Test getting reconnection statistics."""
        config = ReconnectionConfig(max_attempts=5)
        manager = ReconnectionManager(config)
        manager.attempt = 3

        stats = manager.get_stats()
        assert stats["attempt"] == 3
        assert stats["connected"] is False
        assert "config" in stats
        assert stats["config"]["max_attempts"] == 5


class TestReconnectionTracker:
    """Test ReconnectionTracker."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = ReconnectionTracker()
        assert len(tracker.connections) == 0

    def test_record_attempt(self):
        """Test recording reconnection attempt."""
        tracker = ReconnectionTracker()

        tracker.record_attempt("conn1", success=True)
        stats = tracker.get_connection_stats("conn1")

        assert stats is not None
        assert stats["total_attempts"] == 1
        assert stats["successful_attempts"] == 1
        assert stats["failed_attempts"] == 0

    def test_record_multiple_attempts(self):
        """Test recording multiple attempts."""
        tracker = ReconnectionTracker()

        tracker.record_attempt("conn1", success=True)
        tracker.record_attempt("conn1", success=False)
        tracker.record_attempt("conn1", success=True)

        stats = tracker.get_connection_stats("conn1")
        assert stats["total_attempts"] == 3
        assert stats["successful_attempts"] == 2
        assert stats["failed_attempts"] == 1

    def test_get_global_stats(self):
        """Test getting global statistics."""
        tracker = ReconnectionTracker()

        tracker.record_attempt("conn1", success=True)
        tracker.record_attempt("conn1", success=False)
        tracker.record_attempt("conn2", success=True)

        stats = tracker.get_global_stats()
        assert stats["total_connections"] == 2
        assert stats["total_attempts"] == 3
        assert stats["successful_attempts"] == 2
        assert stats["failed_attempts"] == 1

    def test_clear_connection(self):
        """Test clearing connection stats."""
        tracker = ReconnectionTracker()

        tracker.record_attempt("conn1", success=True)
        assert tracker.get_connection_stats("conn1") is not None

        tracker.clear_connection("conn1")
        assert tracker.get_connection_stats("conn1") is None
