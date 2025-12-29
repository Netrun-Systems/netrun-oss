"""Tests for metrics module."""

import pytest
import time

from netrun.websocket.metrics import (
    ConnectionMetrics,
    LatencyMetrics,
    MetricsCollector
)


class TestConnectionMetrics:
    """Test ConnectionMetrics class."""

    def test_create_metrics(self):
        """Test creating connection metrics."""
        metrics = ConnectionMetrics(
            connection_id="conn123",
            user_id="user123",
            connected_at=time.time()
        )
        assert metrics.connection_id == "conn123"
        assert metrics.user_id == "user123"
        assert metrics.messages_sent == 0
        assert metrics.messages_received == 0

    def test_get_duration(self):
        """Test getting connection duration."""
        past_time = time.time() - 10  # 10 seconds ago
        metrics = ConnectionMetrics(
            connection_id="conn123",
            user_id="user123",
            connected_at=past_time
        )
        duration = metrics.get_duration()
        assert duration >= 10

    def test_message_rates(self):
        """Test message rate calculations."""
        past_time = time.time() - 10  # 10 seconds ago
        metrics = ConnectionMetrics(
            connection_id="conn123",
            user_id="user123",
            connected_at=past_time
        )
        metrics.messages_sent = 50
        metrics.messages_received = 30

        send_rate = metrics.get_send_rate()
        receive_rate = metrics.get_receive_rate()

        assert send_rate > 0  # Should be ~5 msgs/sec
        assert receive_rate > 0  # Should be ~3 msgs/sec

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ConnectionMetrics(
            connection_id="conn123",
            user_id="user123",
            connected_at=time.time()
        )
        data = metrics.to_dict()

        assert data["connection_id"] == "conn123"
        assert data["user_id"] == "user123"
        assert "duration_seconds" in data
        assert "messages_sent" in data
        assert "send_rate_per_sec" in data


class TestLatencyMetrics:
    """Test LatencyMetrics class."""

    def test_initialization(self):
        """Test latency metrics initialization."""
        metrics = LatencyMetrics()
        assert len(metrics.samples) == 0
        assert metrics.get_average() == 0.0

    def test_record_samples(self):
        """Test recording latency samples."""
        metrics = LatencyMetrics()
        metrics.record(10.0)
        metrics.record(20.0)
        metrics.record(30.0)

        assert len(metrics.samples) == 3

    def test_average_calculation(self):
        """Test average latency calculation."""
        metrics = LatencyMetrics()
        metrics.record(10.0)
        metrics.record(20.0)
        metrics.record(30.0)

        avg = metrics.get_average()
        assert avg == 20.0

    def test_min_max(self):
        """Test min/max latency."""
        metrics = LatencyMetrics()
        metrics.record(10.0)
        metrics.record(50.0)
        metrics.record(30.0)

        assert metrics.get_min() == 10.0
        assert metrics.get_max() == 50.0

    def test_percentiles(self):
        """Test percentile calculations."""
        metrics = LatencyMetrics()
        for i in range(100):
            metrics.record(float(i))

        p50 = metrics.get_percentile(50)
        p90 = metrics.get_percentile(90)
        p99 = metrics.get_percentile(99)

        assert p50 >= 45  # ~50th percentile
        assert p90 >= 85  # ~90th percentile
        assert p99 >= 95  # ~99th percentile

    def test_max_samples_limit(self):
        """Test that sample count is limited."""
        metrics = LatencyMetrics(max_samples=100)

        # Record more than max_samples
        for i in range(150):
            metrics.record(float(i))

        assert len(metrics.samples) == 100  # Should be capped

    def test_to_dict(self):
        """Test converting to dictionary."""
        metrics = LatencyMetrics()
        metrics.record(10.0)
        metrics.record(20.0)

        data = metrics.to_dict()
        assert "average_ms" in data
        assert "p50_ms" in data
        assert "p99_ms" in data


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector()
        assert len(collector.connections) == 0
        assert collector.total_connections == 0

    def test_register_connection(self):
        """Test registering connection."""
        collector = MetricsCollector()
        collector.register_connection("conn123", "user123")

        assert "conn123" in collector.connections
        assert collector.total_connections == 1
        assert collector.peak_connections == 1

    def test_unregister_connection(self):
        """Test unregistering connection."""
        collector = MetricsCollector()
        collector.register_connection("conn123", "user123")
        collector.unregister_connection("conn123")

        assert "conn123" not in collector.connections
        assert collector.total_disconnections == 1

    def test_record_message_sent(self):
        """Test recording sent message."""
        collector = MetricsCollector()
        collector.register_connection("conn123", "user123")
        collector.record_message_sent("conn123", size_bytes=100)

        metrics = collector.connections["conn123"]
        assert metrics.messages_sent == 1
        assert metrics.bytes_sent == 100

    def test_record_message_received(self):
        """Test recording received message."""
        collector = MetricsCollector()
        collector.register_connection("conn123", "user123")
        collector.record_message_received("conn123", size_bytes=200)

        metrics = collector.connections["conn123"]
        assert metrics.messages_received == 1
        assert metrics.bytes_received == 200

    def test_record_error(self):
        """Test recording error."""
        collector = MetricsCollector()
        collector.register_connection("conn123", "user123")
        collector.record_error("conn123")
        collector.record_error("conn123")

        metrics = collector.connections["conn123"]
        assert metrics.errors == 2

    def test_record_latency(self):
        """Test recording latency."""
        collector = MetricsCollector()
        collector.record_latency(10.5)
        collector.record_latency(20.5)

        assert len(collector.latency.samples) == 2

    def test_get_connection_metrics(self):
        """Test getting connection metrics."""
        collector = MetricsCollector()
        collector.register_connection("conn123", "user123")
        collector.record_message_sent("conn123")

        metrics = collector.get_connection_metrics("conn123")
        assert metrics is not None
        assert metrics["connection_id"] == "conn123"
        assert metrics["messages_sent"] == 1

    def test_get_user_metrics(self):
        """Test getting user metrics."""
        collector = MetricsCollector()
        collector.register_connection("conn1", "user123")
        collector.register_connection("conn2", "user123")
        collector.register_connection("conn3", "user456")

        user_metrics = collector.get_user_metrics("user123")
        assert len(user_metrics) == 2

    def test_get_stats(self):
        """Test getting aggregated statistics."""
        collector = MetricsCollector()
        collector.register_connection("conn1", "user123")
        collector.register_connection("conn2", "user456")
        collector.record_message_sent("conn1", 100)
        collector.record_message_received("conn2", 200)

        stats = collector.get_stats()
        assert stats["active_connections"] == 2
        assert stats["total_connections"] == 2
        assert "messages" in stats
        assert "bandwidth" in stats
        assert "latency" in stats

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()
        collector.register_connection("conn1", "user123")
        collector.record_latency(10.0)

        collector.reset()

        assert len(collector.connections) == 0
        assert collector.total_connections == 0
        assert len(collector.latency.samples) == 0
