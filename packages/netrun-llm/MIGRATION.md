# Migration Guide: netrun-llm v1.x to v2.0

This guide helps you upgrade from netrun-llm v1.x to v2.0, which integrates Charlotte's production-tested adapter architecture.

## Overview of Changes

### New Features in v2.0

1. **Azure OpenAI Adapter** - Multi-resource failover with cloud credit utilization
2. **Google Gemini Adapter** - Free tier support with daily quota tracking
3. **Enhanced Base Adapter** - Charlotte's circuit breaker and health monitoring patterns
4. **Production-Tested Patterns** - Direct extraction from Charlotte orchestration platform

### Breaking Changes

**None** - v2.0 is backward compatible with v1.x. All existing code continues to work.

---

## Installation

### Upgrade Package

```bash
# Basic upgrade (existing adapters)
pip install --upgrade netrun-llm

# Install with Azure OpenAI support
pip install --upgrade 'netrun-llm[azure]'

# Install with Gemini support
pip install --upgrade 'netrun-llm[gemini]'

# Install with all providers
pip install --upgrade 'netrun-llm[all]'
```

### Dependency Changes

#### Azure OpenAI (Optional Extra)
```bash
pip install 'netrun-llm[azure]'
```

Installs:
- `openai>=1.0.0` - Azure OpenAI SDK
- `azure-identity>=1.16.0` - DefaultAzureCredential for authentication

#### Gemini (Optional Extra)
```bash
pip install 'netrun-llm[gemini]'
```

Installs:
- `google-generativeai>=0.8.3` - Google Generative AI SDK

---

## Using New Adapters

### Azure OpenAI Adapter

The Azure OpenAI adapter provides multi-resource failover and cloud credit utilization (effectively free until credits exhausted).

#### Basic Usage

```python
from netrun.llm import AzureOpenAIAdapter

# Initialize with default resources (Netrun infrastructure)
adapter = AzureOpenAIAdapter(preferred_model="gpt-4o")

# Execute prompt
response = adapter.execute("Explain REST APIs in one paragraph")
print(response.content)
print(f"Effective savings: ${response.metadata['effective_cost_saved']:.4f}")
```

#### Custom Resources

```python
from netrun.llm import AzureOpenAIAdapter
from netrun.llm.adapters.azure_openai import AzureResource

# Define custom Azure OpenAI resources
custom_resources = [
    AzureResource(
        name="my-primary",
        endpoint="https://my-primary.openai.azure.com",
        resource_group="my-rg",
        models=["gpt-4o", "gpt-4-turbo"],
        priority=1  # Highest priority
    ),
    AzureResource(
        name="my-fallback",
        endpoint="https://my-fallback.openai.azure.com",
        resource_group="my-rg",
        models=["gpt-3.5-turbo"],
        priority=2  # Fallback
    )
]

adapter = AzureOpenAIAdapter(
    resources=custom_resources,
    preferred_model="gpt-4o"
)
```

#### Environment Variables

```bash
# Optional configuration
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
export AZURE_OPENAI_DEFAULT_MODEL="gpt-4o"
export AZURE_OPENAI_TIMEOUT="30"

# Custom resources via JSON (alternative to code)
export AZURE_OPENAI_RESOURCES='[
    {
        "name": "my-resource",
        "endpoint": "https://my-resource.openai.azure.com",
        "resource_group": "my-rg",
        "models": ["gpt-4o"],
        "priority": 1
    }
]'
```

#### Prerequisites

```bash
# Authenticate with Azure CLI (required)
az login
az account show  # Verify authentication
```

### Google Gemini Adapter

The Gemini adapter supports free tier with automatic daily quota tracking (1,500 requests/day).

#### Basic Usage

```python
from netrun.llm import GeminiAdapter

# Initialize with free tier (1,500 req/day)
adapter = GeminiAdapter(use_free_tier=True)

# Execute prompt
response = adapter.execute("Write a haiku about AI")
print(response.content)
print(f"Quota remaining: {response.metadata['quota_remaining']}")
```

#### Paid Tier

```python
# Use paid tier (no quota limits)
adapter = GeminiAdapter(
    api_key="your-google-ai-api-key",
    use_free_tier=False
)

response = adapter.execute("Explain quantum computing")
print(f"Cost: ${response.cost_usd:.6f}")
```

#### Quota Management

```python
# Check quota status
quota_status = adapter.get_quota_status()
print(f"Requests today: {quota_status['requests_today']}")
print(f"Remaining: {quota_status['requests_remaining']}")
print(f"Quota reset: {quota_status['date']}")

# Manual quota reset (for testing)
adapter.reset_quota()
```

#### Environment Variables

```bash
# Required for API access
export GEMINI_API_KEY="your-google-ai-api-key"

# Optional configuration
export GEMINI_DEFAULT_MODEL="gemini-1.5-flash"
export GEMINI_MAX_TOKENS="2048"
export GEMINI_TIMEOUT="30"
export GEMINI_USE_FREE_TIER="true"
export GEMINI_QUOTA_FILE=".gemini_quota.json"
```

#### Supported Models

- `gemini-1.5-pro` - Best quality, 1M context (paid: $1.25 input / $5.00 output per 1M tokens)
- `gemini-1.5-flash` - Faster/cheaper, 1M context (paid: $0.075 input / $0.30 output per 1M tokens)
- `gemini-2.0-flash-exp` - Experimental, free during preview

---

## Migrating Existing Code

### No Changes Required

All existing v1.x code continues to work without modification:

```python
# v1.x code still works in v2.0
from netrun.llm import ClaudeAdapter, OpenAIAdapter, LLMFallbackChain

# Existing Claude adapter
claude = ClaudeAdapter(api_key="sk-ant-...")
response = claude.execute("Hello world")

# Existing OpenAI adapter
openai = OpenAIAdapter(api_key="sk-...")
response = openai.execute("Hello world")

# Existing fallback chain
chain = LLMFallbackChain([claude, openai])
response = chain.execute("Hello world")
```

### Enhanced Fallback Chains

New adapters work seamlessly with existing fallback chains:

```python
from netrun.llm import (
    ClaudeAdapter,
    OpenAIAdapter,
    AzureOpenAIAdapter,
    GeminiAdapter,
    LLMFallbackChain
)

# Create fallback chain with new adapters
# Priority: Azure (free) → Gemini (free) → OpenAI (paid) → Claude (paid)
adapters = [
    AzureOpenAIAdapter(preferred_model="gpt-4o"),  # FREE (cloud credits)
    GeminiAdapter(use_free_tier=True),  # FREE (1,500 req/day)
    OpenAIAdapter(api_key="sk-..."),  # PAID (fallback)
    ClaudeAdapter(api_key="sk-ant-..."),  # PAID (last resort)
]

chain = LLMFallbackChain(adapters)
response = chain.execute("Explain microservices")
```

### Cost Optimization Strategy

Leverage free tiers first, paid services as fallback:

```python
from netrun.llm import AzureOpenAIAdapter, GeminiAdapter, ClaudeAdapter
from netrun.llm import LLMFallbackChain

# Cost-optimized chain
adapters = [
    # Tier 1: Cloud credits (effectively free)
    AzureOpenAIAdapter(preferred_model="gpt-4o"),

    # Tier 2: Free tier (1,500 req/day)
    GeminiAdapter(use_free_tier=True, model="gemini-1.5-flash"),

    # Tier 3: Paid services (only if above fail or quota exceeded)
    ClaudeAdapter(api_key=os.getenv("ANTHROPIC_API_KEY"))
]

chain = LLMFallbackChain(adapters)

# Execute - will use cheapest available adapter
response = chain.execute("Your prompt here")
print(f"Adapter used: {response.adapter_name}")
print(f"Cost: ${response.cost_usd:.6f}")
```

---

## Feature Compatibility Matrix

| Feature | v1.x | v2.0 | Notes |
|---------|------|------|-------|
| ClaudeAdapter | ✅ | ✅ | No changes |
| OpenAIAdapter | ✅ | ✅ | No changes |
| OllamaAdapter | ✅ | ✅ | No changes |
| LLMFallbackChain | ✅ | ✅ | Works with new adapters |
| ThreeTierCognition | ✅ | ✅ | No changes |
| PolicyEnforcer | ✅ | ✅ | No changes |
| TelemetryCollector | ✅ | ✅ | No changes |
| AzureOpenAIAdapter | ❌ | ✅ | NEW - Multi-resource failover |
| GeminiAdapter | ❌ | ✅ | NEW - Free tier quota tracking |
| Circuit Breaker | Partial | ✅ | Enhanced from Charlotte |
| Health Monitoring | Partial | ✅ | Enhanced from Charlotte |

---

## Testing Your Migration

### Run Existing Tests

Your existing tests should pass without modification:

```bash
# Run your existing test suite
pytest tests/

# Verify no regressions
pytest tests/ --cov=netrun.llm
```

### Test New Adapters

```python
# test_azure_openai.py
from netrun.llm import AzureOpenAIAdapter
import pytest

def test_azure_openai_basic():
    adapter = AzureOpenAIAdapter()

    # Skip if Azure not configured
    if not adapter.check_availability():
        pytest.skip("Azure CLI not authenticated")

    response = adapter.execute("Say hello")
    assert response.status == "success"
    assert response.cost_usd == 0.0  # Cloud credits
    assert "effective_cost_saved" in response.metadata

# test_gemini.py
from netrun.llm import GeminiAdapter
import os

def test_gemini_basic():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    adapter = GeminiAdapter(use_free_tier=True)
    response = adapter.execute("Say hello")

    assert response.status == "success"
    assert response.cost_usd == 0.0  # Free tier
    assert "quota_remaining" in response.metadata
```

---

## Troubleshooting

### Azure OpenAI Issues

**Problem**: `Adapter is disabled` error

**Solution**: Authenticate with Azure CLI:
```bash
az login
az account show
```

**Problem**: `No client initialized for resource`

**Solution**: Verify resource endpoints are correct and accessible:
```python
adapter = AzureOpenAIAdapter()
metadata = adapter.get_metadata()
print(f"Clients initialized: {metadata['clients_initialized']}")
print(f"Azure authenticated: {metadata['azure_authenticated']}")
```

### Gemini Issues

**Problem**: `Free tier quota exceeded`

**Solution**: Quota resets at midnight UTC. Check status:
```python
adapter = GeminiAdapter()
status = adapter.get_quota_status()
print(f"Requests today: {status['requests_today']}/{status['daily_limit']}")
print(f"Quota resets: {status['date']} 23:59:59 UTC")
```

**Problem**: `ImportError: google-generativeai SDK not installed`

**Solution**: Install Gemini extra:
```bash
pip install 'netrun-llm[gemini]'
```

### General Issues

**Problem**: Adapter not available after installation

**Solution**: Check optional dependencies:
```python
from netrun.llm import AzureOpenAIAdapter, GeminiAdapter

if AzureOpenAIAdapter is None:
    print("Azure not installed: pip install 'netrun-llm[azure]'")

if GeminiAdapter is None:
    print("Gemini not installed: pip install 'netrun-llm[gemini]'")
```

---

## Best Practices

### 1. Use Cost-Optimized Fallback Chains

Always prioritize free/credit-based services first:

```python
# Good: Free first, paid fallback
chain = LLMFallbackChain([
    AzureOpenAIAdapter(),  # FREE (cloud credits)
    GeminiAdapter(),  # FREE (quota)
    ClaudeAdapter()  # PAID (fallback)
])

# Bad: Paid first (wastes money)
chain = LLMFallbackChain([
    ClaudeAdapter(),  # Wastes paid API calls
    AzureOpenAIAdapter()
])
```

### 2. Monitor Quota Usage

Track Gemini free tier usage:

```python
adapter = GeminiAdapter(use_free_tier=True)

# Check before bulk operations
status = adapter.get_quota_status()
if status['quota_percentage_used'] > 80:
    print(f"Warning: {status['quota_percentage_used']}% quota used")
```

### 3. Configure Timeouts

Adjust timeouts for your use case:

```python
# Long-running tasks
adapter = AzureOpenAIAdapter(timeout=120)

# Quick responses
adapter = GeminiAdapter(timeout=10)
```

### 4. Check Availability Before Use

Validate adapters are ready:

```python
adapter = AzureOpenAIAdapter()

if adapter.check_availability():
    response = adapter.execute("Your prompt")
else:
    print("Azure not available, using fallback")
    fallback = GeminiAdapter()
    response = fallback.execute("Your prompt")
```

---

## Support

For issues, questions, or feedback:

- **GitHub Issues**: https://github.com/netrunsystems/netrun-service-library/issues
- **Documentation**: https://netrunsystems.com/docs/netrun-llm
- **Email**: support@netrunsystems.com

---

## Changelog

### v2.0.0 (December 2025)

**Added**:
- `AzureOpenAIAdapter` - Multi-resource Azure OpenAI with automatic failover
- `GeminiAdapter` - Google Gemini with free tier quota tracking
- Charlotte production architecture patterns (circuit breaker, health monitoring)

**Enhanced**:
- Base adapter with Charlotte's circuit breaker implementation
- Health monitoring with per-resource metrics
- Cost tracking with "effective savings" calculation

**Maintained**:
- 100% backward compatibility with v1.x
- All existing adapters unchanged
- Existing fallback chains work with new adapters

---

*Last Updated: December 29, 2025*
*Version: 2.0.0*
*Author: Netrun Systems*
