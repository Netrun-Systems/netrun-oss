# LLM Telemetry Guide

Comprehensive guide to tracking LLM costs, latency, and usage metrics with the netrun-llm telemetry system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Export Integration](#export-integration)
5. [Multi-Tenant Tracking](#multi-tenant-tracking)
6. [Cost Dashboards](#cost-dashboards)
7. [Alert Configuration](#alert-configuration)
8. [Production Best Practices](#production-best-practices)

---

## Quick Start

### Installation

```bash
pip install netrun-llm
```

### Basic Example

```python
from netrun.llm.telemetry import get_collector

# Get global collector
collector = get_collector()

# Track a request
async with collector.track_request_async(
    provider="openai",
    model="gpt-4o",
    tenant_id="tenant-123",
) as tracker:
    response = await llm_client.complete(prompt)
    tracker.set_tokens(
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )

# Get statistics
stats = collector.get_stats(period="1h")
print(f"Total cost: ${stats.total_cost_usd:.4f}")
print(f"P95 latency: {stats.latency_p95:.2f}ms")
```

---

## Basic Usage

### Tracking Synchronous Requests

```python
from netrun.llm.telemetry import get_collector

collector = get_collector()

# Track sync request
with collector.track_request(
    provider="openai",
    model="gpt-4o",
    tenant_id="acme-corp",
    user_id="user-456",
) as tracker:
    # Make LLM request
    response = llm.complete("Translate to French: Hello world")

    # Set token counts for cost calculation
    tracker.set_tokens(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
```

### Tracking Async Requests

```python
async with collector.track_request_async(
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",
    tenant_id="acme-corp",
) as tracker:
    response = await llm.complete_async("Explain quantum computing")
    tracker.set_tokens(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
```

### Tracking Streaming Requests

```python
async with collector.track_request_async(
    provider="openai",
    model="gpt-4o",
    tenant_id="acme-corp",
) as tracker:
    stream = await llm.stream("Write a short story")

    start_time = time.perf_counter()
    first_token = True
    total_tokens = 0

    async for chunk in stream:
        if first_token:
            ttft = (time.perf_counter() - start_time) * 1000
            tracker.set_streaming(ttft_ms=ttft)
            first_token = False
        total_tokens += 1

    # Estimate tokens (or get from final chunk)
    tracker.set_tokens(
        input_tokens=len(prompt.split()) * 1.3,  # Rough estimate
        output_tokens=total_tokens,
    )
```

### Tracking Cached Responses

```python
with collector.track_request(
    provider="openai",
    model="gpt-4o",
    tenant_id="acme-corp",
) as tracker:
    # Check cache first
    cached_response = cache.get(prompt_hash)
    if cached_response:
        tracker.set_cached(True)
        tracker.set_tokens(0, 0)  # No tokens consumed
        tracker.set_cost(0.0)  # No cost
        return cached_response

    # Not cached, make request
    response = llm.complete(prompt)
    tracker.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)
    return response
```

---

## Advanced Features

### Getting Aggregated Statistics

```python
# Get last hour stats
stats = collector.get_stats(period="1h")

print(f"Requests: {stats.total_requests}")
print(f"Success rate: {stats.successful_requests / stats.total_requests * 100:.1f}%")
print(f"Total cost: ${stats.total_cost_usd:.4f}")
print(f"Total tokens: {stats.total_input_tokens + stats.total_output_tokens:,}")
print(f"P50 latency: {stats.latency_p50:.2f}ms")
print(f"P95 latency: {stats.latency_p95:.2f}ms")
print(f"P99 latency: {stats.latency_p99:.2f}ms")

# Provider breakdown
for provider, data in stats.by_provider.items():
    print(f"\n{provider}:")
    print(f"  Requests: {data['requests']}")
    print(f"  Cost: ${data['cost']:.4f}")
    print(f"  Tokens: {data['tokens']:,}")

# Model breakdown
for model, data in stats.by_model.items():
    print(f"\n{model}:")
    print(f"  Requests: {data['requests']}")
    print(f"  Cost: ${data['cost']:.4f}")
    print(f"  Avg cost/request: ${data['cost'] / data['requests']:.6f}")
```

### Cost Breakdown Analysis

```python
# Get detailed cost breakdown
breakdown = collector.get_cost_breakdown(period="30d")

print(f"Total 30-day cost: ${breakdown['total_cost_usd']:.2f}")

# By provider
print("\nCost by Provider:")
for provider, data in breakdown["by_provider"].items():
    print(f"  {provider}: ${data['cost_usd']:.2f} ({data['percentage']:.1f}%)")

# By model
print("\nCost by Model:")
for model, data in breakdown["by_model"].items():
    print(f"  {model}:")
    print(f"    Total: ${data['cost_usd']:.2f}")
    print(f"    Requests: {data['requests']}")
    print(f"    Avg: ${data['avg_cost']:.6f}")
```

### Tenant-Specific Statistics

```python
# Get comprehensive stats for a tenant
stats = collector.get_tenant_stats("tenant-123", period="30d")

print(f"Tenant: {stats['tenant_id']}")
print(f"\nRequests:")
print(f"  Total: {stats['requests']['total']}")
print(f"  Successful: {stats['requests']['successful']}")
print(f"  Failed: {stats['requests']['failed']}")
print(f"  Success rate: {stats['requests']['success_rate']:.1f}%")

print(f"\nTokens:")
print(f"  Input: {stats['tokens']['input']:,}")
print(f"  Output: {stats['tokens']['output']:,}")
print(f"  Total: {stats['tokens']['total']:,}")

print(f"\nCost:")
print(f"  Total: ${stats['cost']['total_cost_usd']:.2f}")

print(f"\nLatency:")
print(f"  P50: {stats['latency']['p50']:.2f}ms")
print(f"  P95: {stats['latency']['p95']:.2f}ms")
print(f"  P99: {stats['latency']['p99']:.2f}ms")
```

---

## Export Integration

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge
from netrun.llm.telemetry import configure_telemetry, LLMRequestMetrics

# Define Prometheus metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status', 'tenant_id']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens consumed',
    ['provider', 'model', 'type', 'tenant_id']  # type = input/output
)

llm_cost_usd_total = Counter(
    'llm_cost_usd_total',
    'Total cost in USD',
    ['provider', 'model', 'tenant_id']
)

# Export callback
def export_to_prometheus(metrics: LLMRequestMetrics):
    """Export metrics to Prometheus."""
    status = "success" if metrics.success else "error"

    # Request counter
    llm_requests_total.labels(
        provider=metrics.provider,
        model=metrics.model,
        status=status,
        tenant_id=metrics.tenant_id,
    ).inc()

    # Latency histogram (convert ms to seconds)
    llm_request_duration_seconds.labels(
        provider=metrics.provider,
        model=metrics.model,
    ).observe(metrics.latency_ms / 1000)

    # Token counters
    llm_tokens_total.labels(
        provider=metrics.provider,
        model=metrics.model,
        type="input",
        tenant_id=metrics.tenant_id,
    ).inc(metrics.input_tokens)

    llm_tokens_total.labels(
        provider=metrics.provider,
        model=metrics.model,
        type="output",
        tenant_id=metrics.tenant_id,
    ).inc(metrics.output_tokens)

    # Cost counter
    llm_cost_usd_total.labels(
        provider=metrics.provider,
        model=metrics.model,
        tenant_id=metrics.tenant_id,
    ).inc(metrics.cost_usd)

# Configure telemetry with Prometheus export
configure_telemetry(export_callback=export_to_prometheus)
```

### Azure Monitor / Application Insights

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics
from netrun.llm.telemetry import configure_telemetry, LLMRequestMetrics

# Configure Azure Monitor
configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create metrics
llm_request_counter = meter.create_counter(
    "llm.requests",
    description="LLM request count",
)

llm_latency_histogram = meter.create_histogram(
    "llm.latency",
    unit="ms",
    description="LLM request latency",
)

llm_cost_counter = meter.create_counter(
    "llm.cost",
    unit="USD",
    description="LLM request cost",
)

def export_to_azure_monitor(metrics: LLMRequestMetrics):
    """Export metrics to Azure Monitor."""
    attributes = {
        "provider": metrics.provider,
        "model": metrics.model,
        "tenant_id": metrics.tenant_id,
        "status": "success" if metrics.success else "error",
    }

    # Increment counter
    llm_request_counter.add(1, attributes=attributes)

    # Record latency
    llm_latency_histogram.record(metrics.latency_ms, attributes=attributes)

    # Record cost
    llm_cost_counter.add(metrics.cost_usd, attributes=attributes)

    # Create span for detailed trace
    with tracer.start_as_current_span("llm_request") as span:
        span.set_attributes({
            "llm.provider": metrics.provider,
            "llm.model": metrics.model,
            "llm.tenant_id": metrics.tenant_id,
            "llm.request_id": metrics.request_id,
            "llm.input_tokens": metrics.input_tokens,
            "llm.output_tokens": metrics.output_tokens,
            "llm.cost_usd": metrics.cost_usd,
            "llm.cached": metrics.cached,
        })

configure_telemetry(export_callback=export_to_azure_monitor)
```

### PostgreSQL / TimescaleDB

```python
import asyncpg
from netrun.llm.telemetry import configure_telemetry, LLMRequestMetrics

# Database connection pool
pool = None

async def init_db_pool():
    global pool
    pool = await asyncpg.create_pool(
        host="localhost",
        database="llm_telemetry",
        user="telemetry_user",
        password=os.getenv("DB_PASSWORD"),
    )

    # Create table (if using TimescaleDB)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_metrics (
                timestamp TIMESTAMPTZ NOT NULL,
                request_id TEXT,
                tenant_id TEXT,
                user_id TEXT,
                provider TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms FLOAT,
                time_to_first_token_ms FLOAT,
                cost_usd FLOAT,
                success BOOLEAN,
                error_type TEXT,
                cached BOOLEAN,
                streaming BOOLEAN
            );

            -- Convert to hypertable (TimescaleDB)
            SELECT create_hypertable('llm_metrics', 'timestamp', if_not_exists => TRUE);

            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_tenant_time ON llm_metrics (tenant_id, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_provider_time ON llm_metrics (provider, timestamp DESC);
        """)

async def export_to_postgres(metrics: LLMRequestMetrics):
    """Export metrics to PostgreSQL/TimescaleDB."""
    if pool is None:
        return

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO llm_metrics (
                timestamp, request_id, tenant_id, user_id, provider, model,
                input_tokens, output_tokens, total_tokens, latency_ms,
                time_to_first_token_ms, cost_usd, success, error_type,
                cached, streaming
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
            metrics.timestamp,
            metrics.request_id,
            metrics.tenant_id,
            metrics.user_id,
            metrics.provider,
            metrics.model,
            metrics.input_tokens,
            metrics.output_tokens,
            metrics.total_tokens,
            metrics.latency_ms,
            metrics.time_to_first_token_ms,
            metrics.cost_usd,
            metrics.success,
            metrics.error_type,
            metrics.cached,
            metrics.streaming,
        )

# Wrapper for sync callback
def export_to_postgres_sync(metrics: LLMRequestMetrics):
    asyncio.create_task(export_to_postgres(metrics))

configure_telemetry(export_callback=export_to_postgres_sync)
```

---

## Multi-Tenant Tracking

### Tenant Isolation

```python
from netrun.llm.telemetry import get_collector

collector = get_collector()

# Track per-tenant usage
async def handle_request(tenant_id: str, user_id: str, prompt: str):
    async with collector.track_request_async(
        provider="openai",
        model="gpt-4o",
        tenant_id=tenant_id,
        user_id=user_id,
    ) as tracker:
        response = await llm.complete(prompt)
        tracker.set_tokens(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return response

# Get tenant-specific stats
def get_tenant_usage(tenant_id: str):
    stats = collector.get_stats(period="30d", tenant_id=tenant_id)
    return {
        "requests": stats.total_requests,
        "cost": stats.total_cost_usd,
        "tokens": stats.total_input_tokens + stats.total_output_tokens,
    }
```

### Multi-Tenant Cost Dashboard

```python
from netrun.llm.telemetry import get_collector

def generate_tenant_cost_report(period="30d"):
    """Generate cost report for all tenants."""
    collector = get_collector()

    # Get all unique tenant IDs
    tenant_ids = set(m.tenant_id for m in collector._metrics)

    report = {}
    for tenant_id in tenant_ids:
        stats = collector.get_tenant_stats(tenant_id, period=period)
        report[tenant_id] = {
            "total_cost": stats["cost"]["total_cost_usd"],
            "requests": stats["requests"]["total"],
            "tokens": stats["tokens"]["total"],
            "avg_cost_per_request": (
                stats["cost"]["total_cost_usd"] / stats["requests"]["total"]
                if stats["requests"]["total"] > 0 else 0
            ),
            "success_rate": stats["requests"]["success_rate"],
        }

    # Sort by cost descending
    sorted_report = sorted(
        report.items(),
        key=lambda x: x[1]["total_cost"],
        reverse=True,
    )

    return sorted_report

# Example output
report = generate_tenant_cost_report()
for tenant_id, data in report[:10]:  # Top 10 tenants by cost
    print(f"\nTenant: {tenant_id}")
    print(f"  Cost: ${data['total_cost']:.2f}")
    print(f"  Requests: {data['requests']:,}")
    print(f"  Avg cost/request: ${data['avg_cost_per_request']:.6f}")
```

---

## Cost Dashboards

### Real-Time Cost Monitor

```python
import time
from netrun.llm.telemetry import get_collector

def monitor_costs(interval_seconds=60):
    """Monitor costs in real-time."""
    collector = get_collector()
    last_cost = 0

    while True:
        stats = collector.get_stats(period="1h")
        current_cost = stats.total_cost_usd
        cost_delta = current_cost - last_cost

        print(f"\n--- Cost Monitor ---")
        print(f"Last hour total: ${current_cost:.4f}")
        print(f"Last {interval_seconds}s: ${cost_delta:.4f}")
        print(f"Projected daily: ${current_cost * 24:.2f}")
        print(f"Projected monthly: ${current_cost * 24 * 30:.2f}")

        # Provider breakdown
        for provider, data in stats.by_provider.items():
            print(f"\n{provider}:")
            print(f"  Cost: ${data['cost']:.4f}")
            print(f"  Requests: {data['requests']}")

        last_cost = current_cost
        time.sleep(interval_seconds)

# Run monitor
# monitor_costs(interval_seconds=60)
```

### Cost Optimization Report

```python
def generate_optimization_report():
    """Identify cost optimization opportunities."""
    collector = get_collector()
    stats = collector.get_stats(period="7d")

    print("=== Cost Optimization Report ===\n")

    # Find expensive models
    print("Top 5 Most Expensive Models:")
    sorted_models = sorted(
        stats.by_model.items(),
        key=lambda x: x[1]["cost"],
        reverse=True,
    )
    for model, data in sorted_models[:5]:
        avg_cost = data["cost"] / data["requests"]
        print(f"  {model}:")
        print(f"    Total cost: ${data['cost']:.4f}")
        print(f"    Requests: {data['requests']}")
        print(f"    Avg cost: ${avg_cost:.6f}")

        # Suggest cheaper alternatives
        if "gpt-4" in model and "mini" not in model:
            print(f"    💡 Consider gpt-4o-mini (~10x cheaper)")
        elif "claude-3-opus" in model:
            print(f"    💡 Consider claude-sonnet-4-5 (~5x cheaper)")

    # Find high-latency requests
    print(f"\nLatency Analysis:")
    print(f"  P95 latency: {stats.latency_p95:.2f}ms")
    print(f"  P99 latency: {stats.latency_p99:.2f}ms")
    if stats.latency_p95 > 2000:
        print(f"  ⚠️ High P95 latency - consider caching or async processing")

    # Error analysis
    if stats.failed_requests > 0:
        error_rate = stats.failed_requests / stats.total_requests * 100
        print(f"\nError Analysis:")
        print(f"  Error rate: {error_rate:.2f}%")
        for error_type, count in stats.errors_by_type.items():
            print(f"  {error_type}: {count} occurrences")
```

---

## Alert Configuration

### Budget Alerts

```python
from netrun.llm.telemetry import get_collector

class BudgetAlertMonitor:
    """Monitor and alert on budget thresholds."""

    def __init__(self, daily_budget: float, monthly_budget: float):
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.collector = get_collector()

    def check_budgets(self):
        """Check current spend against budgets."""
        # Check daily budget
        daily_stats = self.collector.get_stats(period="24h")
        daily_spend = daily_stats.total_cost_usd
        daily_pct = (daily_spend / self.daily_budget) * 100

        if daily_pct >= 90:
            self.alert_critical(
                f"Daily budget at {daily_pct:.1f}% (${daily_spend:.2f} / ${self.daily_budget:.2f})"
            )
        elif daily_pct >= 75:
            self.alert_warning(
                f"Daily budget at {daily_pct:.1f}% (${daily_spend:.2f} / ${self.daily_budget:.2f})"
            )

        # Check monthly budget
        monthly_stats = self.collector.get_stats(period="30d")
        monthly_spend = monthly_stats.total_cost_usd
        monthly_pct = (monthly_spend / self.monthly_budget) * 100

        if monthly_pct >= 90:
            self.alert_critical(
                f"Monthly budget at {monthly_pct:.1f}% (${monthly_spend:.2f} / ${self.monthly_budget:.2f})"
            )
        elif monthly_pct >= 75:
            self.alert_warning(
                f"Monthly budget at {monthly_pct:.1f}% (${monthly_spend:.2f} / ${self.monthly_budget:.2f})"
            )

    def alert_warning(self, message: str):
        """Send warning alert."""
        print(f"⚠️ WARNING: {message}")
        # Send email, Slack notification, etc.

    def alert_critical(self, message: str):
        """Send critical alert."""
        print(f"🚨 CRITICAL: {message}")
        # Send PagerDuty alert, etc.

# Run monitor
monitor = BudgetAlertMonitor(daily_budget=10.0, monthly_budget=250.0)
monitor.check_budgets()
```

### Performance Alerts

```python
def check_performance_alerts():
    """Alert on performance degradation."""
    collector = get_collector()
    stats = collector.get_stats(period="1h")

    # Check P95 latency
    if stats.latency_p95 > 5000:
        print(f"🚨 High P95 latency: {stats.latency_p95:.2f}ms")

    # Check error rate
    if stats.total_requests > 0:
        error_rate = stats.failed_requests / stats.total_requests * 100
        if error_rate > 5:
            print(f"🚨 High error rate: {error_rate:.1f}%")

    # Check cost spike
    current_hour_cost = stats.total_cost_usd
    if current_hour_cost > 5.0:  # $5/hour threshold
        print(f"🚨 Cost spike detected: ${current_hour_cost:.2f}/hour")
```

---

## Production Best Practices

### 1. Configure Export on Startup

```python
# app.py
from netrun.llm.telemetry import configure_telemetry
import os

def init_telemetry():
    """Initialize telemetry on app startup."""
    if os.getenv("ENVIRONMENT") == "production":
        # Use Prometheus in production
        configure_telemetry(
            export_callback=export_to_prometheus,
            max_history=50000,  # Keep more history in prod
        )
    else:
        # Development - just use in-memory
        configure_telemetry(max_history=1000)

# Call on startup
init_telemetry()
```

### 2. Graceful Export Failures

```python
def safe_export_callback(metrics):
    """Export callback with error handling."""
    try:
        export_to_external_system(metrics)
    except Exception as e:
        # Log but don't fail
        logger.error(f"Telemetry export failed: {e}")
        # Optionally queue for retry
        retry_queue.put(metrics)

configure_telemetry(export_callback=safe_export_callback)
```

### 3. Periodic Cleanup

```python
import schedule

def cleanup_old_metrics():
    """Clean up old metrics to free memory."""
    collector = get_collector()
    # Metrics older than max_history are auto-cleaned,
    # but you can force cleanup if needed
    print(f"Current metrics count: {len(collector._metrics)}")

# Run cleanup daily
schedule.every().day.at("00:00").do(cleanup_old_metrics)
```

### 4. Performance Impact Monitoring

```python
# The telemetry system itself has minimal overhead:
# - Context manager: ~0.1ms overhead
# - Metric recording: ~0.05ms
# - Export callback: Async/threaded to not block

# Monitor telemetry overhead
import time

def measure_telemetry_overhead():
    collector = TelemetryCollector()
    iterations = 10000

    # Without telemetry
    start = time.perf_counter()
    for _ in range(iterations):
        pass
    no_telemetry = time.perf_counter() - start

    # With telemetry
    start = time.perf_counter()
    for i in range(iterations):
        with collector.track_request("test", "test", "test"):
            pass
    with_telemetry = time.perf_counter() - start

    overhead = (with_telemetry - no_telemetry) / iterations * 1000
    print(f"Avg overhead per request: {overhead:.4f}ms")
```

---

## Summary

The netrun-llm telemetry system provides:

- **Automatic cost tracking** with per-million-token pricing
- **Latency percentiles** (P50, P95, P99) for SLA monitoring
- **Multi-tenant isolation** for SaaS applications
- **Export callbacks** for Prometheus, Azure Monitor, PostgreSQL
- **Thread-safe** operation for concurrent requests
- **Minimal overhead** (~0.1ms per request)

For questions or issues, see the [main README](../README.md) or open an issue on GitHub.
