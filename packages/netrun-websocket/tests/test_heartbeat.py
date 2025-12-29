"""Tests for heartbeat module - ping/pong monitoring."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from netrun.websocket.heartbeat import (
    HeartbeatConfig,
    HeartbeatMonitor,
)


class TestHeartbeatConfig:
    """Test HeartbeatConfig dataclass."""

    def test_default_configuration(self):
        """Test default heartbeat configuration."""
        config = HeartbeatConfig()

        assert config.interval == 30
        assert config.timeout == 90
        assert config.max_missed == 3
        assert config.enabled is True

    def test_custom_configuration(self):
        """Test custom heartbeat configuration."""
        config = HeartbeatConfig(
            interval=60,
            timeout=180,
            max_missed=5,
            enabled=False
        )

        assert config.interval == 60
        assert config.timeout == 180
        assert config.max_missed == 5
        assert config.enabled is False


class TestHeartbeatMonitor:
    """Test HeartbeatMonitor class."""

    def test_initialization_with_defaults(self):
        """Test monitor initialization with default config."""
        monitor = HeartbeatMonitor()

        assert monitor.config.interval == 30
        assert monitor.config.timeout == 90
        assert monitor.config.max_missed == 3
        assert monitor.config.enabled is True
        assert len(monitor.connections) == 0
        assert len(monitor.missed_counts) == 0
        assert monitor._task is None
        assert monitor._running is False

    def test_initialization_with_custom_config(self):
        """Test monitor initialization with custom config."""
        config = HeartbeatConfig(interval=45, timeout=120, max_missed=4)
        monitor = HeartbeatMonitor(config=config)

        assert monitor.config.interval == 45
        assert monitor.config.timeout == 120
        assert monitor.config.max_missed == 4

    def test_register_connection(self):
        """Test registering connection for heartbeat monitoring."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)

        assert connection_id in monitor.connections
        assert connection_id in monitor.missed_counts
        assert monitor.missed_counts[connection_id] == 0
        assert monitor.connections[connection_id] > 0

    def test_register_multiple_connections(self):
        """Test registering multiple connections."""
        monitor = HeartbeatMonitor()

        monitor.register_connection("conn1")
        monitor.register_connection("conn2")
        monitor.register_connection("conn3")

        assert len(monitor.connections) == 3
        assert "conn1" in monitor.connections
        assert "conn2" in monitor.connections
        assert "conn3" in monitor.connections

    def test_unregister_connection(self):
        """Test unregistering connection from heartbeat monitoring."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)
        assert connection_id in monitor.connections

        monitor.unregister_connection(connection_id)

        assert connection_id not in monitor.connections
        assert connection_id not in monitor.missed_counts

    def test_unregister_nonexistent_connection(self):
        """Test unregistering connection that doesn't exist."""
        monitor = HeartbeatMonitor()

        # Should not raise error
        monitor.unregister_connection("nonexistent")

        assert "nonexistent" not in monitor.connections

    def test_update_heartbeat(self):
        """Test updating heartbeat timestamp."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)
        initial_time = monitor.connections[connection_id]

        # Wait a bit and update
        time.sleep(0.1)
        monitor.update_heartbeat(connection_id)

        updated_time = monitor.connections[connection_id]
        assert updated_time > initial_time
        assert monitor.missed_counts[connection_id] == 0

    def test_update_heartbeat_resets_missed_count(self):
        """Test updating heartbeat resets missed count."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)
        monitor.missed_counts[connection_id] = 2

        monitor.update_heartbeat(connection_id)

        assert monitor.missed_counts[connection_id] == 0

    def test_update_heartbeat_unregistered_connection(self):
        """Test updating heartbeat for unregistered connection."""
        monitor = HeartbeatMonitor()

        # Should not raise error
        monitor.update_heartbeat("nonexistent")

        assert "nonexistent" not in monitor.connections

    def test_get_last_heartbeat(self):
        """Test getting last heartbeat timestamp."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)
        last_heartbeat = monitor.get_last_heartbeat(connection_id)

        assert last_heartbeat is not None
        assert isinstance(last_heartbeat, float)
        assert last_heartbeat > 0

    def test_get_last_heartbeat_nonexistent(self):
        """Test getting last heartbeat for nonexistent connection."""
        monitor = HeartbeatMonitor()

        last_heartbeat = monitor.get_last_heartbeat("nonexistent")

        assert last_heartbeat is None

    def test_get_missed_count(self):
        """Test getting missed heartbeat count."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)
        monitor.missed_counts[connection_id] = 2

        count = monitor.get_missed_count(connection_id)

        assert count == 2

    def test_get_missed_count_nonexistent(self):
        """Test getting missed count for nonexistent connection."""
        monitor = HeartbeatMonitor()

        count = monitor.get_missed_count("nonexistent")

        assert count == 0

    def test_is_stale_fresh_connection(self):
        """Test stale check for fresh connection."""
        monitor = HeartbeatMonitor()
        connection_id = "conn123"

        monitor.register_connection(connection_id)

        is_stale = monitor.is_stale(connection_id)

        assert is_stale is False

    def test_is_stale_old_connection(self):
        """Test stale check for old connection."""
        config = HeartbeatConfig(timeout=1)  # 1 second timeout
        monitor = HeartbeatMonitor(config=config)
        connection_id = "conn123"

        monitor.register_connection(connection_id)

        # Manually set old timestamp
        monitor.connections[connection_id] = time.time() - 2

        is_stale = monitor.is_stale(connection_id)

        assert is_stale is True

    def test_is_stale_nonexistent_connection(self):
        """Test stale check for nonexistent connection."""
        monitor = HeartbeatMonitor()

        is_stale = monitor.is_stale("nonexistent")

        assert is_stale is True

    def test_get_stale_connections_none_stale(self):
        """Test getting stale connections when none are stale."""
        monitor = HeartbeatMonitor()

        monitor.register_connection("conn1")
        monitor.register_connection("conn2")
        monitor.register_connection("conn3")

        stale = monitor.get_stale_connections()

        assert len(stale) == 0

    def test_get_stale_connections_some_stale(self):
        """Test getting stale connections when some are stale."""
        config = HeartbeatConfig(timeout=1)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        monitor.register_connection("conn2")
        monitor.register_connection("conn3")

        # Make conn2 stale
        monitor.connections["conn2"] = time.time() - 2

        stale = monitor.get_stale_connections()

        assert len(stale) == 1
        assert "conn2" in stale

    @pytest.mark.asyncio
    async def test_start_monitoring_disabled(self):
        """Test starting monitoring when disabled."""
        config = HeartbeatConfig(enabled=False)
        monitor = HeartbeatMonitor(config=config)

        ping_callback = AsyncMock()
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        assert monitor._running is False
        assert monitor._task is None

    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self):
        """Test starting monitoring when already running."""
        monitor = HeartbeatMonitor()
        monitor._running = True

        ping_callback = AsyncMock()
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        # Should not create new task
        assert monitor._task is None

    @pytest.mark.asyncio
    async def test_start_and_stop_monitoring(self):
        """Test starting and stopping heartbeat monitoring."""
        config = HeartbeatConfig(interval=0.1, timeout=1)
        monitor = HeartbeatMonitor(config=config)

        ping_callback = AsyncMock(return_value=True)
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        assert monitor._running is True
        assert monitor._task is not None

        # Let it run briefly
        await asyncio.sleep(0.05)

        await monitor.stop()

        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stopping monitor when not running."""
        monitor = HeartbeatMonitor()

        # Should not raise error
        await monitor.stop()

        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_pings(self):
        """Test heartbeat loop sends ping messages."""
        config = HeartbeatConfig(interval=0.1, timeout=1)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")

        ping_callback = AsyncMock(return_value=True)
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        # Wait for at least one ping cycle
        await asyncio.sleep(0.15)

        await monitor.stop()

        # Ping should have been called
        assert ping_callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_loop_detects_stale_connections(self):
        """Test heartbeat loop detects and cleans up stale connections."""
        config = HeartbeatConfig(interval=0.1, timeout=0.2, max_missed=1)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        # Set old timestamp to make it stale
        monitor.connections["conn1"] = time.time() - 1

        ping_callback = AsyncMock(return_value=True)
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        # Wait for cleanup cycle
        await asyncio.sleep(0.25)

        await monitor.stop()

        # Cleanup should have been called
        assert cleanup_callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_loop_handles_failed_pings(self):
        """Test heartbeat loop handles failed ping attempts."""
        config = HeartbeatConfig(interval=0.1, timeout=1)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        # Make connection appear to need ping
        monitor.connections["conn1"] = time.time() - 0.15

        ping_callback = AsyncMock(return_value=False)  # Ping fails
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        # Wait for ping attempt
        await asyncio.sleep(0.15)

        await monitor.stop()

        # Cleanup should be called due to failed ping
        assert cleanup_callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_loop_calls_miss_callback(self):
        """Test heartbeat loop calls miss callback when heartbeats missed."""
        config = HeartbeatConfig(interval=0.1, timeout=0.2, max_missed=2)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        # Set old timestamp to trigger missed heartbeat
        monitor.connections["conn1"] = time.time() - 0.25

        ping_callback = AsyncMock(return_value=True)
        cleanup_callback = AsyncMock()
        miss_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback, miss_callback)

        # Wait for miss detection
        await asyncio.sleep(0.15)

        await monitor.stop()

        # Miss callback should have been called
        assert miss_callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_loop_exception_handling(self):
        """Test heartbeat loop handles exceptions gracefully."""
        config = HeartbeatConfig(interval=0.1, timeout=1)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")

        # Ping callback that raises exception
        ping_callback = AsyncMock(side_effect=Exception("Test error"))
        cleanup_callback = AsyncMock()

        await monitor.start(ping_callback, cleanup_callback)

        # Wait for error to occur
        await asyncio.sleep(0.15)

        # Monitor should still be running despite exception
        assert monitor._running is True

        await monitor.stop()

    def test_get_stats_empty(self):
        """Test getting stats with no connections."""
        monitor = HeartbeatMonitor()

        stats = monitor.get_stats()

        assert stats["enabled"] is True
        assert stats["running"] is False
        assert stats["total_connections"] == 0
        assert stats["healthy_connections"] == 0
        assert stats["warning_connections"] == 0
        assert stats["stale_connections"] == 0
        assert "config" in stats

    def test_get_stats_with_connections(self):
        """Test getting stats with active connections."""
        config = HeartbeatConfig(interval=30, timeout=90)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        monitor.register_connection("conn2")

        stats = monitor.get_stats()

        assert stats["total_connections"] == 2
        assert stats["healthy_connections"] == 2
        assert stats["warning_connections"] == 0
        assert stats["stale_connections"] == 0

    def test_get_stats_with_warning_connections(self):
        """Test getting stats with warning state connections."""
        config = HeartbeatConfig(interval=10, timeout=60)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        monitor.register_connection("conn2")

        # Set conn2 to warning state (between interval and timeout)
        monitor.connections["conn2"] = time.time() - 15

        stats = monitor.get_stats()

        assert stats["total_connections"] == 2
        assert stats["healthy_connections"] == 1
        assert stats["warning_connections"] == 1

    def test_get_stats_with_stale_connections(self):
        """Test getting stats with stale connections."""
        config = HeartbeatConfig(interval=10, timeout=30)
        monitor = HeartbeatMonitor(config=config)

        monitor.register_connection("conn1")
        monitor.register_connection("conn2")

        # Set conn2 to stale state (beyond timeout)
        monitor.connections["conn2"] = time.time() - 35

        stats = monitor.get_stats()

        assert stats["total_connections"] == 2
        assert stats["stale_connections"] == 1

    def test_get_stats_config_values(self):
        """Test stats include correct config values."""
        config = HeartbeatConfig(interval=45, timeout=120, max_missed=5)
        monitor = HeartbeatMonitor(config=config)

        stats = monitor.get_stats()

        assert stats["config"]["interval"] == 45
        assert stats["config"]["timeout"] == 120
        assert stats["config"]["max_missed"] == 5
