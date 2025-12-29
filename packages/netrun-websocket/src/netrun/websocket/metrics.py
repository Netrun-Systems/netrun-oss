"""
WebSocket Connection Metrics
File: metrics.py
Netrun Systems - SDLC v2.3 Compliant

Connection metrics tracking for WebSocket connections including
connection count, message throughput, latency, and bandwidth.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """
    Per-connection metrics.

    Tracks detailed metrics for individual WebSocket connections.
    """

    connection_id: str
    user_id: str
    connected_at: float
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    last_activity: float = field(default_factory=time.time)

    def get_duration(self) -> float:
        """Get connection duration in seconds."""
        return time.time() - self.connected_at

    def get_send_rate(self) -> float:
        """Get messages sent per second."""
        duration = self.get_duration()
        return self.messages_sent / duration if duration > 0 else 0

    def get_receive_rate(self) -> float:
        """Get messages received per second."""
        duration = self.get_duration()
        return self.messages_received / duration if duration > 0 else 0

    def get_bandwidth_sent(self) -> float:
        """Get bytes sent per second."""
        duration = self.get_duration()
        return self.bytes_sent / duration if duration > 0 else 0

    def get_bandwidth_received(self) -> float:
        """Get bytes received per second."""
        duration = self.get_duration()
        return self.bytes_received / duration if duration > 0 else 0

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "connected_at": datetime.fromtimestamp(
                self.connected_at, tz=timezone.utc
            ).isoformat(),
            "duration_seconds": self.get_duration(),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "errors": self.errors,
            "send_rate_per_sec": self.get_send_rate(),
            "receive_rate_per_sec": self.get_receive_rate(),
            "bandwidth_sent_per_sec": self.get_bandwidth_sent(),
            "bandwidth_received_per_sec": self.get_bandwidth_received(),
            "last_activity": datetime.fromtimestamp(
                self.last_activity, tz=timezone.utc
            ).isoformat()
        }


@dataclass
class LatencyMetrics:
    """
    Latency tracking metrics.

    Tracks message latency with percentile calculations.
    """

    samples: List[float] = field(default_factory=list)
    max_samples: int = 1000  # Keep last 1000 samples

    def record(self, latency_ms: float):
        """
        Record latency sample.

        Args:
            latency_ms: Latency in milliseconds
        """
        self.samples.append(latency_ms)
        if len(self.samples) > self.max_samples:
            self.samples.pop(0)

    def get_average(self) -> float:
        """Get average latency."""
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    def get_min(self) -> float:
        """Get minimum latency."""
        return min(self.samples) if self.samples else 0.0

    def get_max(self) -> float:
        """Get maximum latency."""
        return max(self.samples) if self.samples else 0.0

    def get_percentile(self, percentile: float) -> float:
        """
        Get latency percentile.

        Args:
            percentile: Percentile (0-100)

        Returns:
            Latency at percentile
        """
        if not self.samples:
            return 0.0

        sorted_samples = sorted(self.samples)
        index = int(len(sorted_samples) * (percentile / 100.0))
        return sorted_samples[min(index, len(sorted_samples) - 1)]

    def to_dict(self) -> dict:
        """Convert latency metrics to dictionary."""
        return {
            "sample_count": len(self.samples),
            "average_ms": self.get_average(),
            "min_ms": self.get_min(),
            "max_ms": self.get_max(),
            "p50_ms": self.get_percentile(50),
            "p75_ms": self.get_percentile(75),
            "p90_ms": self.get_percentile(90),
            "p95_ms": self.get_percentile(95),
            "p99_ms": self.get_percentile(99)
        }


class MetricsCollector:
    """
    WebSocket metrics collector.

    Collects and aggregates metrics for all WebSocket connections.

    Usage:
        collector = MetricsCollector()

        # Register connection
        collector.register_connection(connection_id, user_id)

        # Record activity
        collector.record_message_sent(connection_id, message_size)
        collector.record_message_received(connection_id, message_size)
        collector.record_latency(latency_ms)

        # Get metrics
        stats = collector.get_stats()
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.connections: Dict[str, ConnectionMetrics] = {}
        self.latency = LatencyMetrics()

        # Global counters
        self.total_connections = 0
        self.total_disconnections = 0
        self.peak_connections = 0

    def register_connection(self, connection_id: str, user_id: str):
        """
        Register new connection for metrics tracking.

        Args:
            connection_id: Connection identifier
            user_id: User identifier
        """
        now = time.time()
        self.connections[connection_id] = ConnectionMetrics(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=now,
            last_activity=now
        )

        self.total_connections += 1
        current_count = len(self.connections)
        if current_count > self.peak_connections:
            self.peak_connections = current_count

        logger.debug(f"Registered metrics for connection {connection_id}")

    def unregister_connection(self, connection_id: str):
        """
        Unregister connection from metrics tracking.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.total_disconnections += 1
            logger.debug(f"Unregistered metrics for connection {connection_id}")

    def record_message_sent(self, connection_id: str, size_bytes: int = 0):
        """
        Record message sent.

        Args:
            connection_id: Connection identifier
            size_bytes: Message size in bytes
        """
        if connection_id in self.connections:
            metrics = self.connections[connection_id]
            metrics.messages_sent += 1
            metrics.bytes_sent += size_bytes
            metrics.last_activity = time.time()

    def record_message_received(self, connection_id: str, size_bytes: int = 0):
        """
        Record message received.

        Args:
            connection_id: Connection identifier
            size_bytes: Message size in bytes
        """
        if connection_id in self.connections:
            metrics = self.connections[connection_id]
            metrics.messages_received += 1
            metrics.bytes_received += size_bytes
            metrics.last_activity = time.time()

    def record_error(self, connection_id: str):
        """
        Record error for connection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connections:
            self.connections[connection_id].errors += 1

    def record_latency(self, latency_ms: float):
        """
        Record message latency.

        Args:
            latency_ms: Latency in milliseconds
        """
        self.latency.record(latency_ms)

    def get_connection_metrics(
        self,
        connection_id: str
    ) -> Optional[Dict]:
        """
        Get metrics for specific connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Dict of metrics or None
        """
        if connection_id in self.connections:
            return self.connections[connection_id].to_dict()
        return None

    def get_user_metrics(self, user_id: str) -> List[Dict]:
        """
        Get metrics for all connections of a user.

        Args:
            user_id: User identifier

        Returns:
            List of connection metrics
        """
        return [
            metrics.to_dict()
            for metrics in self.connections.values()
            if metrics.user_id == user_id
        ]

    def get_stats(self) -> dict:
        """
        Get aggregated statistics.

        Returns:
            Dict with aggregated metrics
        """
        active_connections = len(self.connections)

        # Aggregate metrics
        total_messages_sent = sum(m.messages_sent for m in self.connections.values())
        total_messages_received = sum(
            m.messages_received for m in self.connections.values()
        )
        total_bytes_sent = sum(m.bytes_sent for m in self.connections.values())
        total_bytes_received = sum(m.bytes_received for m in self.connections.values())
        total_errors = sum(m.errors for m in self.connections.values())

        # Calculate averages
        avg_messages_sent = (
            total_messages_sent / active_connections if active_connections > 0 else 0
        )
        avg_messages_received = (
            total_messages_received / active_connections if active_connections > 0 else 0
        )

        return {
            "active_connections": active_connections,
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "peak_connections": self.peak_connections,
            "messages": {
                "total_sent": total_messages_sent,
                "total_received": total_messages_received,
                "avg_sent_per_connection": avg_messages_sent,
                "avg_received_per_connection": avg_messages_received
            },
            "bandwidth": {
                "total_bytes_sent": total_bytes_sent,
                "total_bytes_received": total_bytes_received,
                "avg_bytes_sent_per_connection": (
                    total_bytes_sent / active_connections if active_connections > 0 else 0
                ),
                "avg_bytes_received_per_connection": (
                    total_bytes_received / active_connections if active_connections > 0 else 0
                )
            },
            "errors": {
                "total": total_errors,
                "avg_per_connection": (
                    total_errors / active_connections if active_connections > 0 else 0
                )
            },
            "latency": self.latency.to_dict()
        }

    def reset(self):
        """Reset all metrics."""
        self.connections.clear()
        self.latency = LatencyMetrics()
        self.total_connections = 0
        self.total_disconnections = 0
        self.peak_connections = 0
        logger.info("Metrics reset")


__all__ = [
    "ConnectionMetrics",
    "LatencyMetrics",
    "MetricsCollector",
]
