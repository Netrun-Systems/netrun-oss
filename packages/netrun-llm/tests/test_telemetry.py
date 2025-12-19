"""
Tests for LLM Telemetry System

Comprehensive test suite for telemetry collection, aggregation,
cost calculation, and export functionality.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from netrun.llm.telemetry import (
    LLMRequestMetrics,
    AggregatedMetrics,
    TelemetryCollector,
    RequestTracker,
    get_collector,
    configure_telemetry,
)


class TestLLMRequestMetrics:
    """Test LLMRequestMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating basic metrics."""
        metrics = LLMRequestMetrics(
            request_id="req-123",
            tenant_id="tenant-456",
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        assert metrics.request_id == "req-123"
        assert metrics.tenant_id == "tenant-456"
        assert metrics.provider == "openai"
        assert metrics.model == "gpt-4o"
        assert metrics.input_tokens == 1000
        assert metrics.output_tokens == 500
        assert metrics.success is True

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = LLMRequestMetrics(
            request_id="req-123",
            tenant_id="tenant-456",
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.0125,
        )

        d = metrics.to_dict()
        assert d["request_id"] == "req-123"
        assert d["provider"] == "openai"
        assert d["model"] == "gpt-4o"
        assert d["cost_usd"] == 0.0125
        assert isinstance(d["timestamp"], str)

    def test_to_log_context(self):
        """Test converting to structured logging context."""
        metrics = LLMRequestMetrics(
            request_id="req-123",
            tenant_id="tenant-456",
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1234.5,
            cost_usd=0.0125,
        )

        ctx = metrics.to_log_context()
        assert ctx["llm_provider"] == "openai"
        assert ctx["llm_model"] == "gpt-4o"
        assert ctx["llm_tokens"] == 1500
        assert ctx["llm_latency_ms"] == 1234.5
        assert ctx["llm_cost_usd"] == 0.0125
        assert ctx["llm_success"] is True


class TestTelemetryCollector:
    """Test TelemetryCollector functionality."""

    def setup_method(self):
        """Reset global collector before each test."""
        import netrun.llm.telemetry as telemetry_module
        telemetry_module._default_collector = None

    def test_create_collector(self):
        """Test creating a collector."""
        collector = TelemetryCollector()
        assert collector.max_history == 10000
        assert len(collector._metrics) == 0

    def test_create_collector_with_callback(self):
        """Test creating collector with export callback."""
        callback = Mock()
        collector = TelemetryCollector(export_callback=callback)

        metrics = LLMRequestMetrics(
            request_id="req-123",
            tenant_id="tenant-456",
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        collector.record(metrics)
        callback.assert_called_once_with(metrics)

    def test_track_request_sync(self):
        """Test synchronous request tracking."""
        collector = TelemetryCollector()

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            time.sleep(0.01)  # Simulate work
            tracker.set_tokens(1000, 500)

        assert len(collector._metrics) == 1
        metrics = collector._metrics[0]
        assert metrics.provider == "openai"
        assert metrics.model == "gpt-4o"
        assert metrics.input_tokens == 1000
        assert metrics.output_tokens == 500
        assert metrics.total_tokens == 1500
        assert metrics.latency_ms > 0
        assert metrics.success is True

    @pytest.mark.asyncio
    async def test_track_request_async(self):
        """Test async request tracking."""
        collector = TelemetryCollector()

        async with collector.track_request_async(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tenant_id="tenant-123",
        ) as tracker:
            await asyncio.sleep(0.01)  # Simulate async work
            tracker.set_tokens(2000, 1000)

        assert len(collector._metrics) == 1
        metrics = collector._metrics[0]
        assert metrics.provider == "anthropic"
        assert metrics.model == "claude-sonnet-4-5-20250929"
        assert metrics.input_tokens == 2000
        assert metrics.output_tokens == 1000
        assert metrics.latency_ms > 0

    def test_track_request_with_error(self):
        """Test request tracking when exception occurs."""
        collector = TelemetryCollector()

        with pytest.raises(ValueError):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                tracker.set_tokens(1000, 500)
                raise ValueError("Test error")

        # Metrics should still be recorded
        assert len(collector._metrics) == 1
        metrics = collector._metrics[0]
        assert metrics.success is False
        assert metrics.error_type == "ValueError"
        assert metrics.error_message == "Test error"

    def test_automatic_cost_calculation(self):
        """Test automatic cost calculation from token counts."""
        collector = TelemetryCollector()

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        metrics = collector._metrics[0]
        # gpt-4o: $0.0025 input, $0.01 output per 1k tokens
        # (1000 * 0.0025 + 500 * 0.01) / 1000 = 0.0075
        assert metrics.cost_usd > 0
        assert abs(metrics.cost_usd - 0.0075) < 0.0001

    def test_set_cached(self):
        """Test marking request as cached."""
        collector = TelemetryCollector()

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)
            tracker.set_cached(True)

        assert collector._metrics[0].cached is True

    def test_set_streaming(self):
        """Test marking request as streaming with TTFT."""
        collector = TelemetryCollector()

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)
            tracker.set_streaming(ttft_ms=250.5)

        assert collector._metrics[0].streaming is True
        assert collector._metrics[0].time_to_first_token_ms == 250.5

    def test_max_history_limit(self):
        """Test that old metrics are discarded when limit reached."""
        collector = TelemetryCollector(max_history=10)

        # Record 15 requests
        for i in range(15):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
                request_id=f"req-{i}",
            ) as tracker:
                tracker.set_tokens(100, 50)

        # Should only keep last 10
        assert len(collector._metrics) == 10
        assert collector._metrics[0].request_id == "req-5"
        assert collector._metrics[-1].request_id == "req-14"


class TestAggregatedMetrics:
    """Test aggregated metrics functionality."""

    def test_get_stats_empty(self):
        """Test getting stats with no data."""
        collector = TelemetryCollector()
        stats = collector.get_stats(period="1h")

        assert isinstance(stats, AggregatedMetrics)
        assert stats.total_requests == 0
        assert stats.total_cost_usd == 0.0

    def test_get_stats_basic(self):
        """Test basic stats aggregation."""
        collector = TelemetryCollector()

        # Record 3 requests
        for i in range(3):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                tracker.set_tokens(1000, 500)

        stats = collector.get_stats(period="1h")
        assert stats.total_requests == 3
        assert stats.successful_requests == 3
        assert stats.failed_requests == 0
        assert stats.total_input_tokens == 3000
        assert stats.total_output_tokens == 1500
        assert stats.total_cost_usd > 0

    def test_get_stats_with_errors(self):
        """Test stats with failed requests."""
        collector = TelemetryCollector()

        # 2 successful, 1 failed
        for i in range(2):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                tracker.set_tokens(1000, 500)

        try:
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                raise ValueError("Test error")
        except ValueError:
            pass

        stats = collector.get_stats(period="1h")
        assert stats.total_requests == 3
        assert stats.successful_requests == 2
        assert stats.failed_requests == 1
        assert stats.errors_by_type["ValueError"] == 1

    def test_get_stats_by_provider(self):
        """Test provider breakdown."""
        collector = TelemetryCollector()

        # 2 OpenAI, 1 Anthropic
        for _ in range(2):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                tracker.set_tokens(1000, 500)

        with collector.track_request(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(2000, 1000)

        stats = collector.get_stats(period="1h")
        assert len(stats.by_provider) == 2
        assert stats.by_provider["openai"]["requests"] == 2
        assert stats.by_provider["anthropic"]["requests"] == 1

    def test_get_stats_by_model(self):
        """Test model breakdown."""
        collector = TelemetryCollector()

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        with collector.track_request(
            provider="openai",
            model="gpt-4o-mini",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        stats = collector.get_stats(period="1h")
        assert len(stats.by_model) == 2
        assert stats.by_model["gpt-4o"]["requests"] == 1
        assert stats.by_model["gpt-4o-mini"]["requests"] == 1

    def test_get_stats_latency_percentiles(self):
        """Test latency percentile calculation."""
        collector = TelemetryCollector()

        # Create requests with varying latencies
        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for latency in latencies:
            metrics = LLMRequestMetrics(
                request_id=f"req-{latency}",
                tenant_id="tenant-123",
                provider="openai",
                model="gpt-4o",
                input_tokens=100,
                output_tokens=50,
                latency_ms=float(latency),
            )
            collector.record(metrics)

        stats = collector.get_stats(period="1h")
        # P50 with 10 values [100..1000]: index 4.5 -> (500+600)/2 = 550
        assert abs(stats.latency_p50 - 550) < 0.01
        # P95 with 10 values: index 8.55 -> interpolate between 900 and 1000
        assert abs(stats.latency_p95 - 955) < 0.01
        # P99 with 10 values: index 8.91 -> interpolate between 900 and 1000
        assert abs(stats.latency_p99 - 991) < 0.01
        assert abs(stats.latency_avg - 550) < 0.01

    def test_get_stats_tenant_filter(self):
        """Test filtering stats by tenant."""
        collector = TelemetryCollector()

        # 2 for tenant-123, 1 for tenant-456
        for _ in range(2):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                tracker.set_tokens(1000, 500)

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-456",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        # Get stats for tenant-123 only
        stats = collector.get_stats(period="1h", tenant_id="tenant-123")
        assert stats.total_requests == 2
        assert stats.tenant_id == "tenant-123"

        # Get stats for all tenants
        stats_all = collector.get_stats(period="1h")
        assert stats_all.total_requests == 3
        assert stats_all.tenant_id is None

    def test_aggregated_metrics_to_dict(self):
        """Test converting aggregated metrics to dict."""
        collector = TelemetryCollector()

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        stats = collector.get_stats(period="1h")
        d = stats.to_dict()

        assert isinstance(d, dict)
        assert "period_start" in d
        assert "period_end" in d
        assert d["total_requests"] == 1
        assert d["by_provider"]["openai"]["requests"] == 1


class TestCostBreakdown:
    """Test cost breakdown functionality."""

    def test_get_cost_breakdown(self):
        """Test cost breakdown calculation."""
        collector = TelemetryCollector()

        # OpenAI request
        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        # Anthropic request
        with collector.track_request(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(2000, 1000)

        breakdown = collector.get_cost_breakdown(period="1h")
        assert "total_cost_usd" in breakdown
        assert "by_provider" in breakdown
        assert "by_model" in breakdown
        assert breakdown["total_cost_usd"] > 0

        # Check provider breakdown
        assert "openai" in breakdown["by_provider"]
        assert "anthropic" in breakdown["by_provider"]
        assert "cost_usd" in breakdown["by_provider"]["openai"]
        assert "percentage" in breakdown["by_provider"]["openai"]

        # Percentages should sum to ~100
        total_pct = sum(p["percentage"] for p in breakdown["by_provider"].values())
        assert abs(total_pct - 100) < 0.1

    def test_get_tenant_stats(self):
        """Test comprehensive tenant statistics."""
        collector = TelemetryCollector()

        # Multiple requests for tenant
        for i in range(5):
            with collector.track_request(
                provider="openai",
                model="gpt-4o",
                tenant_id="tenant-123",
            ) as tracker:
                tracker.set_tokens(1000, 500)

        stats = collector.get_tenant_stats("tenant-123", period="1h")
        assert stats["tenant_id"] == "tenant-123"
        assert stats["requests"]["total"] == 5
        assert stats["requests"]["success_rate"] == 100.0
        assert "tokens" in stats
        assert "cost" in stats
        assert "latency" in stats


class TestGlobalCollector:
    """Test global collector singleton."""

    def setup_method(self):
        """Reset global collector."""
        import netrun.llm.telemetry as telemetry_module
        telemetry_module._default_collector = None

    def test_get_collector(self):
        """Test getting global collector."""
        collector1 = get_collector()
        collector2 = get_collector()
        assert collector1 is collector2  # Same instance

    def test_configure_telemetry(self):
        """Test configuring global collector."""
        callback = Mock()
        collector = configure_telemetry(
            export_callback=callback,
            max_history=5000,
        )

        assert collector.export_callback is callback
        assert collector.max_history == 5000

        # Should be the global instance
        assert get_collector() is collector


class TestPeriodParsing:
    """Test period string parsing."""

    def test_parse_hours(self):
        """Test parsing hour periods."""
        collector = TelemetryCollector()
        delta = collector._parse_period("1h")
        assert delta == timedelta(hours=1)

        delta = collector._parse_period("24h")
        assert delta == timedelta(hours=24)

    def test_parse_days(self):
        """Test parsing day periods."""
        collector = TelemetryCollector()
        delta = collector._parse_period("1d")
        assert delta == timedelta(days=1)

        delta = collector._parse_period("30d")
        assert delta == timedelta(days=30)

    def test_parse_minutes(self):
        """Test parsing minute periods."""
        collector = TelemetryCollector()
        delta = collector._parse_period("5m")
        assert delta == timedelta(minutes=5)

        delta = collector._parse_period("60m")
        assert delta == timedelta(minutes=60)

    def test_parse_invalid(self):
        """Test parsing invalid periods."""
        collector = TelemetryCollector()

        with pytest.raises(ValueError):
            collector._parse_period("invalid")

        with pytest.raises(ValueError):
            collector._parse_period("1x")


class TestExportCallback:
    """Test export callback functionality."""

    def test_export_callback_called(self):
        """Test that export callback is called for each request."""
        callback = Mock()
        collector = TelemetryCollector(export_callback=callback)

        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        callback.assert_called_once()
        metrics = callback.call_args[0][0]
        assert isinstance(metrics, LLMRequestMetrics)

    def test_export_callback_error_handling(self):
        """Test that export callback errors don't break telemetry."""
        def failing_callback(metrics):
            raise Exception("Export failed")

        collector = TelemetryCollector(export_callback=failing_callback)

        # Should not raise exception
        with collector.track_request(
            provider="openai",
            model="gpt-4o",
            tenant_id="tenant-123",
        ) as tracker:
            tracker.set_tokens(1000, 500)

        # Metrics should still be recorded
        assert len(collector._metrics) == 1


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_recording(self):
        """Test concurrent metric recording from multiple threads."""
        import threading

        collector = TelemetryCollector()
        threads = []

        def record_metrics():
            for _ in range(10):
                with collector.track_request(
                    provider="openai",
                    model="gpt-4o",
                    tenant_id="tenant-123",
                ) as tracker:
                    tracker.set_tokens(100, 50)

        # Create 5 threads, each recording 10 metrics
        for _ in range(5):
            t = threading.Thread(target=record_metrics)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have all 50 metrics
        assert len(collector._metrics) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
