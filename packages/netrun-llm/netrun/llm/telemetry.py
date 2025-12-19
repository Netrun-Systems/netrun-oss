"""
LLM Telemetry - Structured metrics for cost, latency, and usage tracking.

Provides visibility into:
- Cost per provider/model/tenant
- Latency percentiles (p50, p95, p99)
- Token usage patterns
- Error rates and types
- Budget consumption trends

Features:
- Async-first design with sync support
- Export callbacks for Prometheus/Azure Monitor
- Context managers for automatic metric capture
- Aggregated statistics with time-based filtering
- Thread-safe metric collection
- Zero-dependency core (optional integrations)

Example:
    # Basic usage
    collector = get_collector()

    async with collector.track_request("openai", "gpt-4o", "tenant-123") as tracker:
        response = await llm_client.complete(prompt)
        tracker.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

    # Get statistics
    stats = collector.get_stats(period="1h", tenant_id="tenant-123")
    print(f"Total cost: ${stats.total_cost_usd:.4f}")
    print(f"P95 latency: {stats.latency_p95:.2f}ms")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from collections import defaultdict
import time
import asyncio
import threading
from contextlib import contextmanager, asynccontextmanager


@dataclass
class LLMRequestMetrics:
    """
    Metrics for a single LLM request.

    Captured automatically by the telemetry middleware.

    Attributes:
        request_id: Unique identifier for this request
        tenant_id: Tenant identifier for multi-tenant systems
        provider: LLM provider (openai, anthropic, ollama, etc.)
        model: Specific model used (gpt-4o, claude-sonnet-4-5, etc.)
        user_id: Optional user identifier
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        total_tokens: Total tokens (input + output)
        latency_ms: Total request latency in milliseconds
        time_to_first_token_ms: Time to first token for streaming (optional)
        cost_usd: Request cost in USD
        timestamp: When the request was made
        success: Whether the request succeeded
        error_type: Type of error if failed (Exception class name)
        error_message: Error message if failed
        endpoint: API endpoint called (/chat, /complete, /embed)
        streaming: Whether this was a streaming request
        cached: Whether response came from cache
    """
    # Request identification (required fields first)
    request_id: str
    tenant_id: str
    provider: str  # openai, anthropic, ollama, etc.
    model: str

    # Optional fields with defaults
    user_id: Optional[str] = None

    # Token counts
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Timing
    latency_ms: float = 0.0
    time_to_first_token_ms: Optional[float] = None  # For streaming

    # Cost
    cost_usd: float = 0.0

    # Request metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Optional context
    endpoint: Optional[str] = None  # /chat, /complete, /embed
    streaming: bool = False
    cached: bool = False  # Was response from cache?

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "time_to_first_token_ms": self.time_to_first_token_ms,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "endpoint": self.endpoint,
            "streaming": self.streaming,
            "cached": self.cached,
        }

    def to_log_context(self) -> dict:
        """Return dict suitable for structured logging."""
        # Calculate total_tokens if not set
        total_tokens = self.total_tokens if self.total_tokens > 0 else self.input_tokens + self.output_tokens
        return {
            "llm_provider": self.provider,
            "llm_model": self.model,
            "llm_tokens": total_tokens,
            "llm_latency_ms": self.latency_ms,
            "llm_cost_usd": self.cost_usd,
            "llm_success": self.success,
            "llm_cached": self.cached,
        }


@dataclass
class AggregatedMetrics:
    """
    Aggregated metrics over a time period.

    Provides comprehensive statistics for cost optimization,
    performance analysis, and budget tracking.

    Attributes:
        period_start: Start of aggregation period
        period_end: End of aggregation period
        tenant_id: Tenant filter (None = all tenants)
        total_requests: Total number of requests
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        cached_requests: Number of cached responses
        total_input_tokens: Total input tokens consumed
        total_output_tokens: Total output tokens generated
        total_cost_usd: Total cost in USD
        latency_p50: 50th percentile latency (median)
        latency_p95: 95th percentile latency
        latency_p99: 99th percentile latency
        latency_avg: Average latency
        by_provider: Breakdown by provider
        by_model: Breakdown by model
        errors_by_type: Error counts by exception type
    """
    period_start: datetime
    period_end: datetime
    tenant_id: Optional[str] = None  # None = all tenants

    # Counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0

    # Tokens
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # Cost
    total_cost_usd: float = 0.0

    # Latency percentiles (in ms)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_avg: float = 0.0

    # By provider breakdown
    by_provider: dict[str, dict] = field(default_factory=dict)

    # By model breakdown
    by_model: dict[str, dict] = field(default_factory=dict)

    # Error breakdown
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "tenant_id": self.tenant_id,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "cached_requests": self.cached_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "latency_p50": self.latency_p50,
            "latency_p95": self.latency_p95,
            "latency_p99": self.latency_p99,
            "latency_avg": self.latency_avg,
            "by_provider": self.by_provider,
            "by_model": self.by_model,
            "errors_by_type": self.errors_by_type,
        }


class TelemetryCollector:
    """
    Collects and aggregates LLM telemetry.

    Thread-safe collector that tracks LLM request metrics for cost analysis,
    performance monitoring, and usage patterns. Supports both sync and async
    contexts with automatic metric calculation.

    Features:
        - Thread-safe metric collection
        - Automatic cost calculation from model pricing
        - Configurable history retention
        - Export callbacks for external systems
        - Automatic logging integration
        - Per-tenant metric isolation

    Example:
        collector = TelemetryCollector()

        # Async tracking
        async with collector.track_request_async("openai", "gpt-4o", "tenant-123") as tracker:
            response = await client.complete(prompt)
            tracker.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

        # Get aggregated stats
        stats = collector.get_stats(period="1h")
        print(f"Total cost: ${stats.total_cost_usd:.2f}")

        # Cost breakdown
        breakdown = collector.get_cost_breakdown(period="30d", tenant_id="tenant-123")
        for provider, data in breakdown["by_provider"].items():
            print(f"{provider}: ${data['cost_usd']:.2f} ({data['percentage']:.1f}%)")
    """

    def __init__(
        self,
        export_callback: Optional[Callable[[LLMRequestMetrics], None]] = None,
        max_history: int = 10000,
    ):
        """
        Initialize telemetry collector.

        Args:
            export_callback: Optional callback for exporting metrics to external systems.
                           Called with LLMRequestMetrics after each request.
            max_history: Maximum number of metrics to retain in memory.
                        Older metrics are discarded when limit is reached.
        """
        self.export_callback = export_callback
        self.max_history = max_history
        self._metrics: list[LLMRequestMetrics] = []
        self._by_tenant: dict[str, list[LLMRequestMetrics]] = defaultdict(list)
        self._lock = threading.Lock()

    @contextmanager
    def track_request(
        self,
        provider: str,
        model: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """
        Context manager for tracking a synchronous request.

        Automatically measures latency and records metrics. Use set_tokens()
        within the context to provide token counts for cost calculation.

        Args:
            provider: LLM provider name (openai, anthropic, ollama)
            model: Model identifier (gpt-4o, claude-sonnet-4-5, etc.)
            tenant_id: Tenant identifier for multi-tenant systems
            user_id: Optional user identifier
            request_id: Optional request ID (auto-generated if not provided)
            endpoint: Optional endpoint identifier (/chat, /complete)

        Example:
            with collector.track_request("openai", "gpt-4o", "tenant-123") as tracker:
                response = llm.complete(prompt)
                tracker.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

        Yields:
            RequestTracker: Tracker object for setting token counts and other metadata
        """
        tracker = RequestTracker(
            collector=self,
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id or self._generate_request_id(),
            endpoint=endpoint,
            is_async=False,
        )

        try:
            tracker._start_time = time.perf_counter()
            yield tracker
        except Exception as exc:
            tracker.metrics.success = False
            tracker.metrics.error_type = type(exc).__name__
            tracker.metrics.error_message = str(exc)
            raise
        finally:
            tracker.metrics.latency_ms = (time.perf_counter() - tracker._start_time) * 1000
            tracker.metrics.total_tokens = tracker.metrics.input_tokens + tracker.metrics.output_tokens
            self.record(tracker.metrics)

    @asynccontextmanager
    async def track_request_async(
        self,
        provider: str,
        model: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """
        Async context manager for tracking an async request.

        Automatically measures latency and records metrics. Use set_tokens()
        within the context to provide token counts for cost calculation.

        Args:
            provider: LLM provider name (openai, anthropic, ollama)
            model: Model identifier (gpt-4o, claude-sonnet-4-5, etc.)
            tenant_id: Tenant identifier for multi-tenant systems
            user_id: Optional user identifier
            request_id: Optional request ID (auto-generated if not provided)
            endpoint: Optional endpoint identifier (/chat, /complete)

        Example:
            async with collector.track_request_async("openai", "gpt-4o", "tenant-123") as tracker:
                response = await llm.complete_async(prompt)
                tracker.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

        Yields:
            RequestTracker: Tracker object for setting token counts and other metadata
        """
        tracker = RequestTracker(
            collector=self,
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id or self._generate_request_id(),
            endpoint=endpoint,
            is_async=True,
        )

        try:
            tracker._start_time = time.perf_counter()
            yield tracker
        except Exception as exc:
            tracker.metrics.success = False
            tracker.metrics.error_type = type(exc).__name__
            tracker.metrics.error_message = str(exc)
            raise
        finally:
            tracker.metrics.latency_ms = (time.perf_counter() - tracker._start_time) * 1000
            tracker.metrics.total_tokens = tracker.metrics.input_tokens + tracker.metrics.output_tokens
            self.record(tracker.metrics)

    def record(self, metrics: LLMRequestMetrics) -> None:
        """
        Record completed request metrics.

        Thread-safe metric recording with automatic cost calculation,
        history management, and export callback execution.

        Args:
            metrics: Completed request metrics to record
        """
        # Calculate cost if not set
        if metrics.cost_usd == 0.0 and metrics.total_tokens > 0:
            metrics.cost_usd = self._calculate_cost(
                metrics.provider,
                metrics.model,
                metrics.input_tokens,
                metrics.output_tokens,
            )

        with self._lock:
            # Store
            self._metrics.append(metrics)
            self._by_tenant[metrics.tenant_id].append(metrics)

            # Trim history if needed
            if len(self._metrics) > self.max_history:
                removed = self._metrics.pop(0)
                # Also remove from tenant index
                tenant_list = self._by_tenant[removed.tenant_id]
                if tenant_list and tenant_list[0].request_id == removed.request_id:
                    tenant_list.pop(0)

        # Export if callback configured (outside lock to avoid blocking)
        if self.export_callback:
            try:
                self.export_callback(metrics)
            except Exception as e:
                # Don't let export errors break telemetry
                self._log_export_error(e)

        # Auto-log if netrun.logging available
        self._log_metrics(metrics)

    def get_stats(
        self,
        period: str = "1h",
        tenant_id: Optional[str] = None,
    ) -> AggregatedMetrics:
        """
        Get aggregated statistics for a time period.

        Calculates comprehensive metrics including percentiles, error rates,
        and cost breakdowns for the specified period.

        Args:
            period: Time period - "1h", "24h", "7d", "30d", or "{N}{unit}"
                   where unit is 'm' (minutes), 'h' (hours), 'd' (days)
            tenant_id: Filter by tenant. None = all tenants.

        Returns:
            AggregatedMetrics with comprehensive statistics

        Example:
            # Get last hour stats for all tenants
            stats = collector.get_stats(period="1h")

            # Get last 30 days for specific tenant
            stats = collector.get_stats(period="30d", tenant_id="tenant-123")
        """
        now = datetime.utcnow()
        period_delta = self._parse_period(period)
        cutoff = now - period_delta

        # Filter metrics
        with self._lock:
            if tenant_id:
                metrics = [m for m in self._by_tenant.get(tenant_id, []) if m.timestamp >= cutoff]
            else:
                metrics = [m for m in self._metrics if m.timestamp >= cutoff]

        if not metrics:
            return AggregatedMetrics(
                period_start=cutoff,
                period_end=now,
                tenant_id=tenant_id,
            )

        # Calculate aggregates
        latencies = sorted([m.latency_ms for m in metrics])
        by_provider = defaultdict(lambda: {"requests": 0, "cost": 0.0, "tokens": 0})
        by_model = defaultdict(lambda: {"requests": 0, "cost": 0.0, "tokens": 0})
        errors_by_type = defaultdict(int)

        for m in metrics:
            by_provider[m.provider]["requests"] += 1
            by_provider[m.provider]["cost"] += m.cost_usd
            by_provider[m.provider]["tokens"] += m.total_tokens

            by_model[m.model]["requests"] += 1
            by_model[m.model]["cost"] += m.cost_usd
            by_model[m.model]["tokens"] += m.total_tokens

            if not m.success and m.error_type:
                errors_by_type[m.error_type] += 1

        return AggregatedMetrics(
            period_start=cutoff,
            period_end=now,
            tenant_id=tenant_id,
            total_requests=len(metrics),
            successful_requests=sum(1 for m in metrics if m.success),
            failed_requests=sum(1 for m in metrics if not m.success),
            cached_requests=sum(1 for m in metrics if m.cached),
            total_input_tokens=sum(m.input_tokens for m in metrics),
            total_output_tokens=sum(m.output_tokens for m in metrics),
            total_cost_usd=sum(m.cost_usd for m in metrics),
            latency_p50=self._percentile(latencies, 50),
            latency_p95=self._percentile(latencies, 95),
            latency_p99=self._percentile(latencies, 99),
            latency_avg=sum(latencies) / len(latencies) if latencies else 0,
            by_provider=dict(by_provider),
            by_model=dict(by_model),
            errors_by_type=dict(errors_by_type),
        )

    def get_cost_breakdown(
        self,
        period: str = "30d",
        tenant_id: Optional[str] = None,
    ) -> dict:
        """
        Get detailed cost breakdown by provider and model.

        Args:
            period: Time period - "1h", "24h", "7d", "30d"
            tenant_id: Filter by tenant. None = all tenants.

        Returns:
            Dictionary with cost breakdowns:
                - total_cost_usd: Total cost for period
                - by_provider: Cost and percentage per provider
                - by_model: Cost, requests, and avg cost per model

        Example:
            breakdown = collector.get_cost_breakdown(period="30d")
            print(f"Total: ${breakdown['total_cost_usd']:.2f}")

            for provider, data in breakdown["by_provider"].items():
                print(f"{provider}: ${data['cost_usd']:.2f} ({data['percentage']:.1f}%)")
        """
        stats = self.get_stats(period, tenant_id)
        return {
            "total_cost_usd": stats.total_cost_usd,
            "by_provider": {
                p: {
                    "cost_usd": d["cost"],
                    "percentage": d["cost"] / stats.total_cost_usd * 100 if stats.total_cost_usd > 0 else 0
                }
                for p, d in stats.by_provider.items()
            },
            "by_model": {
                m: {
                    "cost_usd": d["cost"],
                    "requests": d["requests"],
                    "avg_cost": d["cost"] / d["requests"] if d["requests"] > 0 else 0
                }
                for m, d in stats.by_model.items()
            },
        }

    def get_tenant_stats(self, tenant_id: str, period: str = "30d") -> dict:
        """
        Get comprehensive statistics for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            period: Time period for analysis

        Returns:
            Dictionary with tenant-specific metrics
        """
        stats = self.get_stats(period=period, tenant_id=tenant_id)
        cost_breakdown = self.get_cost_breakdown(period=period, tenant_id=tenant_id)

        return {
            "tenant_id": tenant_id,
            "period": period,
            "requests": {
                "total": stats.total_requests,
                "successful": stats.successful_requests,
                "failed": stats.failed_requests,
                "success_rate": stats.successful_requests / stats.total_requests * 100 if stats.total_requests > 0 else 0,
            },
            "tokens": {
                "input": stats.total_input_tokens,
                "output": stats.total_output_tokens,
                "total": stats.total_input_tokens + stats.total_output_tokens,
            },
            "cost": cost_breakdown,
            "latency": {
                "p50": stats.latency_p50,
                "p95": stats.latency_p95,
                "p99": stats.latency_p99,
                "avg": stats.latency_avg,
            },
            "errors": stats.errors_by_type,
        }

    def _calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost based on provider and model pricing.

        Args:
            provider: Provider name (openai, anthropic, ollama)
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        from netrun.llm.policies import get_model_pricing

        pricing = get_model_pricing(provider, model)
        if pricing is None:
            return 0.0

        input_rate, output_rate = pricing
        # Rates are per 1k tokens (from MODEL_COSTS)
        return (input_tokens * input_rate + output_tokens * output_rate) / 1000

    def _percentile(self, values: list[float], p: int) -> float:
        """Calculate percentile from sorted list of values."""
        if not values:
            return 0.0
        # Calculate index (0-based)
        idx = (len(values) - 1) * p / 100
        # If exact match, return that value
        if idx.is_integer():
            return values[int(idx)]
        # Otherwise, interpolate between two values
        lower_idx = int(idx)
        upper_idx = min(lower_idx + 1, len(values) - 1)
        fraction = idx - lower_idx
        return values[lower_idx] + (values[upper_idx] - values[lower_idx]) * fraction

    def _parse_period(self, period: str) -> timedelta:
        """Parse period string to timedelta."""
        if not period:
            raise ValueError("Period cannot be empty")

        unit = period[-1]
        try:
            value = int(period[:-1])
        except ValueError:
            raise ValueError(f"Invalid period format: {period}. Expected format: {{N}}{{unit}} (e.g., 1h, 24h, 7d)")

        if unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        elif unit == "m":
            return timedelta(minutes=value)
        else:
            raise ValueError(f"Invalid period unit: {unit}. Use 'm' (minutes), 'h' (hours), or 'd' (days)")

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())[:8]

    def _log_metrics(self, metrics: LLMRequestMetrics) -> None:
        """Log metrics using netrun.logging if available."""
        try:
            from netrun.logging import get_logger
            logger = get_logger("netrun.llm.telemetry")
            logger.info(
                "LLM request completed",
                **metrics.to_log_context(),
            )
        except ImportError:
            pass  # netrun.logging not installed

    def _log_export_error(self, error: Exception) -> None:
        """Log export callback errors."""
        try:
            from netrun.logging import get_logger
            logger = get_logger("netrun.llm.telemetry")
            logger.error(
                f"Telemetry export callback failed: {error}",
                error_type=type(error).__name__,
            )
        except ImportError:
            pass


class RequestTracker:
    """
    Context manager for tracking a single request.

    Provides methods for setting token counts, caching status,
    and streaming metadata during request execution.
    """

    def __init__(
        self,
        collector: TelemetryCollector,
        provider: str,
        model: str,
        tenant_id: str,
        user_id: Optional[str],
        request_id: str,
        endpoint: Optional[str],
        is_async: bool,
    ):
        self.collector = collector
        self.metrics = LLMRequestMetrics(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            model=model,
            endpoint=endpoint,
        )
        self.is_async = is_async
        self._start_time: float = 0.0

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """
        Set token counts from response.

        Args:
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
        """
        self.metrics.input_tokens = input_tokens
        self.metrics.output_tokens = output_tokens

    def set_cached(self, cached: bool = True) -> None:
        """
        Mark response as cached.

        Args:
            cached: Whether response came from cache
        """
        self.metrics.cached = cached

    def set_streaming(self, ttft_ms: Optional[float] = None) -> None:
        """
        Mark as streaming response with optional time-to-first-token.

        Args:
            ttft_ms: Time to first token in milliseconds (optional)
        """
        self.metrics.streaming = True
        self.metrics.time_to_first_token_ms = ttft_ms

    def set_cost(self, cost_usd: float) -> None:
        """
        Manually set cost (overrides automatic calculation).

        Args:
            cost_usd: Cost in USD
        """
        self.metrics.cost_usd = cost_usd


# Global collector instance (can be replaced)
_default_collector: Optional[TelemetryCollector] = None
_collector_lock = threading.Lock()


def get_collector() -> TelemetryCollector:
    """
    Get the global telemetry collector.

    Thread-safe singleton accessor. Creates default collector
    if none has been configured.

    Returns:
        Global TelemetryCollector instance
    """
    global _default_collector
    if _default_collector is None:
        with _collector_lock:
            # Double-check locking pattern
            if _default_collector is None:
                _default_collector = TelemetryCollector()
    return _default_collector


def configure_telemetry(
    export_callback: Optional[Callable[[LLMRequestMetrics], None]] = None,
    max_history: int = 10000,
) -> TelemetryCollector:
    """
    Configure the global telemetry collector.

    Args:
        export_callback: Optional callback for exporting metrics to external systems
        max_history: Maximum number of metrics to retain in memory

    Returns:
        Configured TelemetryCollector instance

    Example:
        # Configure with Prometheus export
        def export_to_prometheus(metrics: LLMRequestMetrics):
            llm_requests_total.labels(
                provider=metrics.provider,
                model=metrics.model,
                status="success" if metrics.success else "error"
            ).inc()

            llm_request_duration.labels(
                provider=metrics.provider,
                model=metrics.model
            ).observe(metrics.latency_ms / 1000)

        configure_telemetry(export_callback=export_to_prometheus)
    """
    global _default_collector
    with _collector_lock:
        _default_collector = TelemetryCollector(
            export_callback=export_callback,
            max_history=max_history,
        )
    return _default_collector
