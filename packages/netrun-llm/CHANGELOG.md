# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-04

### Added
- Initial stable release of netrun-llm
- Multi-provider LLM orchestration with automatic fallback chains
- Three-tier cognition system (Fast Ack <100ms, RAG <2s, Deep Insight <5s)
- ClaudeAdapter for Anthropic Claude models with support for Sonnet 4.5, Opus 3, Haiku 3
- OpenAIAdapter for OpenAI models (GPT-4, GPT-4o, GPT-3.5-turbo)
- OllamaAdapter for local/free inference (llama3, mistral, codellama, etc.)
- Circuit breaker protection per-adapter preventing cascade failures
- Automatic cost tracking and estimation across all providers
- Async-first design with sync wrappers for backward compatibility
- Project-agnostic implementation suitable for any Python application
- LLMFallbackChain with default configuration (Claude -> OpenAI -> Ollama)
- Custom fallback chains with flexible adapter ordering
- ThreeTierCognition system for progressive response generation
- Streaming and blocking execution modes
- RAG integration support for knowledge-enhanced responses
- Comprehensive error handling (AllAdaptersFailedError, RateLimitError, CircuitBreakerOpenError)
- Cost tracking and metrics collection
- Support for Python 3.8, 3.9, 3.10, 3.11, 3.12
- Full type safety with mypy support

### Adapters

#### ClaudeAdapter (Anthropic)
- Support for claude-sonnet-4-5-20250929 (recommended)
- claude-3-5-sonnet-20241022, claude-3-opus-20240229, claude-3-sonnet-20240229
- claude-3-haiku-20240307
- Configurable max_tokens and system prompts
- Context parameter support for runtime configuration

#### OpenAIAdapter
- Support for gpt-4-turbo (recommended), gpt-4o, gpt-4o-mini
- gpt-4, gpt-3.5-turbo
- Configurable max_tokens, temperature, timeouts
- Context parameter support for runtime configuration

#### OllamaAdapter
- Support for llama3, llama3.1, llama3.2, codellama
- mistral, phi-3, gemma2, qwen2
- Local/free inference at http://localhost:11434
- Availability checking and model listing
- Fallback host support for reliability

### Features
- **Multi-Adapter Fallback Chains**: Automatic failover between providers with configurable ordering
- **Three-Tier Cognition**: Progressive response generation with latency targets for different use cases
- **Circuit Breaker Protection**: Per-adapter circuit breakers prevent cascade failures
- **Cost Tracking**: Automatic cost estimation and aggregation across providers
- **Async-First**: Full async/await support with sync wrappers for compatibility
- **Project-Agnostic**: No Wilbur-specific dependencies, works in any Python project

### Configuration
- ANTHROPIC_API_KEY: Claude API key (use {{ANTHROPIC_API_KEY}} placeholders)
- OPENAI_API_KEY: OpenAI API key (use {{OPENAI_API_KEY}} placeholders)
- OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
- CLAUDE_DEFAULT_MODEL: Default Claude model
- OPENAI_DEFAULT_MODEL: Default OpenAI model
- OLLAMA_DEFAULT_MODEL: Default Ollama model
- LLM_REQUEST_TIMEOUT: Request timeout in seconds (default: 30)
- LLM_DEFAULT_MAX_TOKENS: Default maximum tokens (default: 4096)

### Dependencies
- requests >= 2.28.0

### Optional Dependencies
- anthropic >= 0.25.0 (for Claude support)
- openai >= 1.0.0 (for OpenAI support)

### Development Dependencies
- pytest >= 7.0.0, pytest-cov >= 4.0.0, pytest-asyncio >= 0.21.0
- black >= 23.0.0 (code formatting)
- ruff >= 0.1.0 (linting)
- mypy >= 1.0.0 (type checking)

### Pricing Reference (2025)
| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| Claude | Sonnet 4.5 | $3.00/1M tokens | $15.00/1M tokens |
| Claude | Opus 3 | $15.00/1M tokens | $75.00/1M tokens |
| Claude | Haiku 3 | $0.25/1M tokens | $1.25/1M tokens |
| OpenAI | GPT-4 Turbo | $10.00/1M tokens | $30.00/1M tokens |
| OpenAI | GPT-4o | $5.00/1M tokens | $15.00/1M tokens |
| OpenAI | GPT-3.5 Turbo | $0.50/1M tokens | $1.50/1M tokens |
| Ollama | All models | $0.00 | $0.00 |

### Error Types
- `AllAdaptersFailedError`: All adapters in chain failed
- `RateLimitError`: Rate limit exceeded with retry_after_seconds
- `CircuitBreakerOpenError`: Circuit breaker open for adapter with cooldown_remaining_seconds

---

## Release Notes

### What's Included

This initial release provides production-grade multi-provider LLM orchestration for Python applications. It enables automatic failover between Claude, OpenAI, and local Ollama models while providing cost tracking and advanced features like three-tier cognition for progressive response generation.

### Key Benefits

- **Automatic Failover**: Seamlessly fallback between providers if one is unavailable
- **Cost Optimization**: Track and optimize LLM spending across providers
- **Progressive Responses**: Three-tier cognition provides fast acknowledgment, RAG-enhanced responses, or deep analysis
- **Circuit Breaker Protection**: Prevents cascade failures across provider integrations
- **Local Inference Option**: Use free Ollama models as fallback for cost reduction

### Compatibility

- Python: 3.8, 3.9, 3.10, 3.11, 3.12
- Requires requests >= 2.28.0
- Optional: anthropic >= 0.25.0, openai >= 1.0.0

### Installation

```bash
# Base installation (Ollama support only)
pip install netrun-llm

# With Claude support
pip install netrun-llm[anthropic]

# With OpenAI support
pip install netrun-llm[openai]

# Full installation
pip install netrun-llm[all]
```

### Quick Start

```python
from netrun_llm import LLMFallbackChain

# Default chain: Claude -> OpenAI -> Ollama
chain = LLMFallbackChain()
response = chain.execute("Explain quantum computing in 3 sentences")
print(f"Response: {response.content}")
print(f"Cost: ${response.cost_usd:.6f}")
```

### Three-Tier Cognition

```python
import asyncio
from netrun_llm import ThreeTierCognition, CognitionTier

async def main():
    cognition = ThreeTierCognition()
    async for response in cognition.stream_response("What is machine learning?"):
        print(f"[{response.tier.name}] {response.content}")

asyncio.run(main())
```

### Support

- Documentation: https://netrunsystems.com/docs/netrun-llm
- GitHub: https://github.com/netrunsystems/netrun-service-library
- Issues: https://github.com/netrunsystems/netrun-service-library/issues
- Email: support@netrunsystems.com
- Website: https://netrunsystems.com

---

**[1.0.0] - 2025-12-04**
