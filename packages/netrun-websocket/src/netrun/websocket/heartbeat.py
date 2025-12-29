"""
WebSocket Heartbeat Monitoring
File: heartbeat.py
Netrun Systems - SDLC v2.3 Compliant

Implements ping/pong heartbeat mechanism for WebSocket connection health
monitoring with automatic stale connection cleanup.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatConfig:
    """
    Heartbeat configuration.

    Attributes:
        interval: Heartbeat interval in seconds (default: 30)
        timeout: Heartbeat timeout in seconds (default: 90)
        max_missed: Maximum missed heartbeats before disconnect (default: 3)
        enabled: Enable heartbeat monitoring (default: True)
    """

    interval: int = 30
    timeout: int = 90
    max_missed: int = 3
    enabled: bool = True


class HeartbeatMonitor:
    """
    Monitor WebSocket connection health using ping/pong heartbeat.

    Automatically sends ping messages and tracks pong responses to detect
    stale connections. Invokes cleanup callbacks for unresponsive connections.

    Usage:
        config = HeartbeatConfig(interval=30, timeout=90)
        monitor = HeartbeatMonitor(config)

        # Register connection
        monitor.register_connection(connection_id)

        # Update on pong received
        monitor.update_heartbeat(connection_id)

        # Start monitoring
        await monitor.start(ping_callback, cleanup_callback)
    """

    def __init__(self, config: Optional[HeartbeatConfig] = None):
        """
        Initialize heartbeat monitor.

        Args:
            config: HeartbeatConfig instance (uses defaults if None)
        """
        self.config = config or HeartbeatConfig()
        self.connections: Dict[str, float] = {}  # connection_id -> last_heartbeat
        self.missed_counts: Dict[str, int] = {}  # connection_id -> missed_count
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def register_connection(self, connection_id: str):
        """
        Register connection for heartbeat monitoring.

        Args:
            connection_id: Connection identifier
        """
        now = time.time()
        self.connections[connection_id] = now
        self.missed_counts[connection_id] = 0
        logger.debug(f"Registered connection {connection_id} for heartbeat monitoring")

    def unregister_connection(self, connection_id: str):
        """
        Unregister connection from heartbeat monitoring.

        Args:
            connection_id: Connection identifier
        """
        self.connections.pop(connection_id, None)
        self.missed_counts.pop(connection_id, None)
        logger.debug(f"Unregistered connection {connection_id} from heartbeat monitoring")

    def update_heartbeat(self, connection_id: str):
        """
        Update last heartbeat timestamp for connection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connections:
            self.connections[connection_id] = time.time()
            self.missed_counts[connection_id] = 0
            logger.debug(f"Updated heartbeat for {connection_id}")

    def get_last_heartbeat(self, connection_id: str) -> Optional[float]:
        """
        Get last heartbeat timestamp for connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Unix timestamp or None
        """
        return self.connections.get(connection_id)

    def get_missed_count(self, connection_id: str) -> int:
        """
        Get missed heartbeat count for connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Number of missed heartbeats
        """
        return self.missed_counts.get(connection_id, 0)

    def is_stale(self, connection_id: str) -> bool:
        """
        Check if connection is stale (exceeded timeout).

        Args:
            connection_id: Connection identifier

        Returns:
            True if stale, False otherwise
        """
        last_heartbeat = self.get_last_heartbeat(connection_id)
        if not last_heartbeat:
            return True

        elapsed = time.time() - last_heartbeat
        return elapsed > self.config.timeout

    def get_stale_connections(self) -> Set[str]:
        """
        Get all stale connections.

        Returns:
            Set of connection IDs that are stale
        """
        now = time.time()
        stale = set()

        for conn_id, last_heartbeat in self.connections.items():
            elapsed = now - last_heartbeat
            if elapsed > self.config.timeout:
                stale.add(conn_id)

        return stale

    async def start(
        self,
        ping_callback: Callable[[str], bool],
        cleanup_callback: Callable[[str], None],
        miss_callback: Optional[Callable[[str, int], None]] = None
    ):
        """
        Start heartbeat monitoring loop.

        Args:
            ping_callback: Async function to send ping (returns True if sent)
            cleanup_callback: Async function to cleanup stale connections
            miss_callback: Optional callback when heartbeat missed
        """
        if not self.config.enabled:
            logger.info("Heartbeat monitoring disabled")
            return

        if self._running:
            logger.warning("Heartbeat monitoring already running")
            return

        self._running = True
        self._task = asyncio.create_task(
            self._heartbeat_loop(ping_callback, cleanup_callback, miss_callback)
        )
        logger.info(
            f"Started heartbeat monitoring: "
            f"interval={self.config.interval}s, timeout={self.config.timeout}s"
        )

    async def stop(self):
        """Stop heartbeat monitoring loop."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped heartbeat monitoring")

    async def _heartbeat_loop(
        self,
        ping_callback: Callable[[str], bool],
        cleanup_callback: Callable[[str], None],
        miss_callback: Optional[Callable[[str, int], None]]
    ):
        """
        Internal heartbeat monitoring loop.

        Args:
            ping_callback: Function to send ping
            cleanup_callback: Function to cleanup stale connections
            miss_callback: Optional callback for missed heartbeats
        """
        while self._running:
            try:
                await asyncio.sleep(self.config.interval)

                now = time.time()
                stale_connections = []

                # Check all connections
                for conn_id, last_heartbeat in list(self.connections.items()):
                    elapsed = now - last_heartbeat

                    # Check if timeout exceeded
                    if elapsed > self.config.timeout:
                        missed = self.missed_counts[conn_id]
                        self.missed_counts[conn_id] = missed + 1

                        logger.warning(
                            f"Connection {conn_id[:8]} missed heartbeat "
                            f"({missed + 1}/{self.config.max_missed})"
                        )

                        if miss_callback:
                            await miss_callback(conn_id, missed + 1)

                        # Check if max missed exceeded
                        if self.missed_counts[conn_id] >= self.config.max_missed:
                            stale_connections.append(conn_id)
                            continue

                    # Send ping if no recent activity
                    if elapsed > self.config.interval:
                        success = await ping_callback(conn_id)
                        if not success:
                            logger.warning(f"Failed to send ping to {conn_id[:8]}")
                            stale_connections.append(conn_id)

                # Cleanup stale connections
                for conn_id in stale_connections:
                    logger.info(
                        f"Cleaning up stale connection {conn_id[:8]} "
                        f"(missed: {self.missed_counts.get(conn_id, 0)})"
                    )
                    await cleanup_callback(conn_id)
                    self.unregister_connection(conn_id)

                if stale_connections:
                    logger.info(f"Cleaned up {len(stale_connections)} stale connections")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}", exc_info=True)

    def get_stats(self) -> dict:
        """
        Get heartbeat monitoring statistics.

        Returns:
            Dict with monitoring stats
        """
        now = time.time()
        total_connections = len(self.connections)
        stale_count = len(self.get_stale_connections())

        # Calculate health distribution
        healthy = 0
        warning = 0

        for conn_id, last_heartbeat in self.connections.items():
            elapsed = now - last_heartbeat
            if elapsed < self.config.interval:
                healthy += 1
            elif elapsed < self.config.timeout:
                warning += 1

        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "total_connections": total_connections,
            "healthy_connections": healthy,
            "warning_connections": warning,
            "stale_connections": stale_count,
            "config": {
                "interval": self.config.interval,
                "timeout": self.config.timeout,
                "max_missed": self.config.max_missed
            }
        }


__all__ = [
    "HeartbeatConfig",
    "HeartbeatMonitor",
]
