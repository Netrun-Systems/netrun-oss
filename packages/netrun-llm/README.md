# netrun-llm

Multi-provider LLM orchestration with automatic fallback chains and three-tier cognition system.

## Features

- **Multi-Adapter Fallback Chains**: Automatic failover between LLM providers (Claude -> GPT-4 -> Llama3)
- **Three-Tier Cognition**: Fast ack (<100ms), RAG response (<2s), Deep insight (<5s)
- **Circuit Breaker Protection**: Per-adapter circuit breakers prevent cascade failures
- **Cost Tracking**: Automatic cost estimation and tracking across all providers
- **Async-First**: Full async support with sync wrappers for compatibility
- **Project-Agnostic**: No Wilbur-specific dependencies, works in any Python project

## Installation

```bash
# Base installation (Ollama support only)
pip install netrun-llm

# With Claude/Anthropic support
pip install netrun-llm[anthropic]

# With OpenAI support
pip install netrun-llm[openai]

# Full installation (all providers)
pip install netrun-llm[all]
```

## Quick Start

### Basic Usage with Fallback Chain

```python
from netrun_llm import LLMFallbackChain

# Create default chain: Claude -> OpenAI -> Ollama
chain = LLMFallbackChain()

# Execute with automatic fallback
response = chain.execute("Explain quantum computing in 3 sentences")

print(f"Response: {response.content}")
print(f"Handled by: {response.adapter_name}")
print(f"Cost: ${response.cost_usd:.6f}")
print(f"Fallbacks used: {response.metadata.get('fallback_attempts', 0)}")
```

### Three-Tier Cognition (Streaming)

```python
import asyncio
from netrun_llm import ThreeTierCognition, CognitionTier

async def main():
    cognition = ThreeTierCognition()

    async for response in cognition.stream_response("What is machine learning?"):
        if response.tier == CognitionTier.FAST_ACK:
            print(f"[Thinking...] {response.content}")
        elif response.tier == CognitionTier.RAG:
            print(f"[Context] {response.content}")
        elif response.tier == CognitionTier.DEEP:
            print(f"[Answer] {response.content}")

asyncio.run(main())
```

### Individual Adapters

```python
from netrun_llm import ClaudeAdapter, OpenAIAdapter, OllamaAdapter

# Claude adapter
claude = ClaudeAdapter()
response = claude.execute("Write a haiku about Python")
print(response.content)

# OpenAI adapter
openai = OpenAIAdapter()
response = openai.execute("What is 2+2?")
print(response.content)

# Ollama adapter (local, free)
ollama = OllamaAdapter(model="llama3")
if ollama.check_availability():
    response = ollama.execute("Hello, world!")
    print(response.content)
```

## Configuration

### Environment Variables

```bash
# API Keys (use placeholders in code, set actual values in env)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_HOST=http://localhost:11434

# Optional: Default models
CLAUDE_DEFAULT_MODEL=claude-sonnet-4-5-20250929
OPENAI_DEFAULT_MODEL=gpt-4-turbo
OLLAMA_DEFAULT_MODEL=llama3

# Optional: Timeouts and limits
LLM_REQUEST_TIMEOUT=30
LLM_DEFAULT_MAX_TOKENS=4096
```

### Using Placeholders (Security Best Practice)

```python
from netrun_llm import ClaudeAdapter, LLMConfig

# Placeholders are resolved from environment at runtime
config = LLMConfig(
    anthropic_api_key="{{ANTHROPIC_API_KEY}}",  # Resolved from env
    openai_api_key="{{OPENAI_API_KEY}}",
    ollama_host="{{OLLAMA_HOST}}",
)

# Validate configuration
issues = config.validate()
if issues:
    print(f"Configuration issues: {issues}")
```

## Adapters

### ClaudeAdapter (Anthropic)

```python
from netrun_llm import ClaudeAdapter

adapter = ClaudeAdapter(
    default_model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
)

response = adapter.execute(
    "Analyze this code",
    context={
        "model": "claude-3-opus-20240229",  # Override model
        "temperature": 0.7,
        "system": "You are a code reviewer.",
    }
)
```

**Supported Models:**
- claude-sonnet-4-5-20250929 (recommended)
- claude-3-5-sonnet-20241022
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

### OpenAIAdapter

```python
from netrun_llm import OpenAIAdapter

adapter = OpenAIAdapter(
    default_model="gpt-4-turbo",
    max_tokens=4096,
    timeout=30,
)

response = adapter.execute(
    "Write a Python function to sort a list",
    context={
        "model": "gpt-4o",
        "temperature": 0.5,
    }
)
```

**Supported Models:**
- gpt-4-turbo (recommended)
- gpt-4o, gpt-4o-mini
- gpt-4
- gpt-3.5-turbo

### OllamaAdapter (Local/Free)

```python
from netrun_llm import OllamaAdapter

adapter = OllamaAdapter(
    model="llama3",
    host="http://localhost:11434",
    fallback_hosts=["http://backup-server:11434"],
)

# Check if Ollama is running
if adapter.check_availability():
    response = adapter.execute("Hello!")
    print(response.content)
    print(f"Cost: ${response.cost_usd}")  # Always $0.00

# List available models
models = adapter.list_available_models()
print(f"Available: {models}")
```

**Supported Models:**
- llama3, llama3.1, llama3.2
- codellama
- mistral
- phi-3
- gemma2
- qwen2

## Fallback Chain

### Default Chain

```python
from netrun_llm import LLMFallbackChain

# Default: Claude -> OpenAI -> Ollama
chain = LLMFallbackChain()
```

### Custom Chain

```python
from netrun_llm import LLMFallbackChain, ClaudeAdapter, OpenAIAdapter, OllamaAdapter

# Cost-optimized: Free first, premium last
chain = LLMFallbackChain(adapters=[
    OllamaAdapter(model="llama3"),      # Free
    OpenAIAdapter(default_model="gpt-3.5-turbo"),  # Cheap
    ClaudeAdapter(),                     # Premium fallback
])

response = chain.execute("Simple question")
print(f"Cost: ${response.cost_usd}")  # Likely $0.00 if Ollama available
```

### Chain Metrics

```python
metrics = chain.get_metrics()
print(f"Success rate: {metrics['success_rate']:.1f}%")
print(f"Fallback rate: {metrics['fallback_rate']:.1f}%")
print(f"Total cost: ${metrics['total_cost_usd']:.4f}")
print(f"Adapter usage: {metrics['adapter_usage']}")
```

## Three-Tier Cognition

The cognition system provides progressive response generation with latency targets:

| Tier | Target Latency | Purpose |
|------|----------------|---------|
| FAST_ACK | <100ms | Immediate acknowledgment |
| RAG | <2s | Knowledge-enhanced response |
| DEEP | <5s | Full LLM reasoning |

### Streaming Mode

```python
import asyncio
from netrun_llm import ThreeTierCognition, CognitionTier

async def chat():
    cognition = ThreeTierCognition()

    async for response in cognition.stream_response("Explain quantum computing"):
        print(f"[{response.tier.name}] {response.content}")
        print(f"  Latency: {response.latency_ms}ms, Final: {response.is_final}")

asyncio.run(chat())
```

### Blocking Mode

```python
async def quick_answer():
    cognition = ThreeTierCognition()

    # Returns best response within timeout
    response = await cognition.execute("What is 2+2?", min_confidence=0.5)
    print(f"Answer: {response.content}")
    print(f"Tier: {response.tier.name}, Confidence: {response.confidence}")

asyncio.run(quick_answer())
```

### With RAG Integration

```python
from netrun_llm import ThreeTierCognition

async def retrieve_documents(query: str) -> list[str]:
    """Your document retrieval function."""
    # Could use Pinecone, Chroma, etc.
    return ["Relevant document 1", "Relevant document 2"]

cognition = ThreeTierCognition(
    enable_rag=True,
    rag_retrieval=retrieve_documents,
)
```

## Error Handling

```python
from netrun_llm import (
    LLMFallbackChain,
    AllAdaptersFailedError,
    RateLimitError,
    CircuitBreakerOpenError,
)

chain = LLMFallbackChain()

try:
    response = chain.execute("Test prompt")
except AllAdaptersFailedError as e:
    print(f"All adapters failed: {e.failed_adapters}")
    print(f"Errors: {e.errors}")
except RateLimitError as e:
    print(f"Rate limited on {e.adapter_name}")
    print(f"Retry after: {e.retry_after_seconds}s")
except CircuitBreakerOpenError as e:
    print(f"Circuit breaker open for {e.adapter_name}")
    print(f"Cooldown: {e.cooldown_remaining_seconds}s")
```

## Pricing Reference (2025)

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) |
|----------|-------|----------------------|------------------------|
| Claude | Sonnet 4.5/3.5 | $3.00 | $15.00 |
| Claude | Opus 3 | $15.00 | $75.00 |
| Claude | Haiku 3 | $0.25 | $1.25 |
| OpenAI | GPT-4 Turbo | $10.00 | $30.00 |
| OpenAI | GPT-4o | $5.00 | $15.00 |
| OpenAI | GPT-3.5 Turbo | $0.50 | $1.50 |
| Ollama | All models | $0.00 | $0.00 |

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## Support

- Documentation: https://netrunsystems.com/docs/netrun-llm
- Issues: https://github.com/netrunsystems/netrun-service-library/issues
- Email: support@netrunsystems.com
