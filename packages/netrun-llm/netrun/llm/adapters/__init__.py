"""
Netrun LLM - Adapter Package

Provides unified interfaces to multiple LLM providers.
All adapters inherit from BaseLLMAdapter for consistent behavior.

Adapters:
    - ClaudeAdapter: Anthropic Claude API (claude-sonnet-4.5, claude-3.5-sonnet, etc.)
    - OpenAIAdapter: OpenAI API (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
    - OllamaAdapter: Ollama local models (llama3, mistral, codellama)
    - AzureOpenAIAdapter: Azure OpenAI with multi-resource failover (requires azure extra)
    - GeminiAdapter: Google Gemini with free tier quota tracking (requires gemini extra)

v2.0.0: Added Azure OpenAI and Gemini adapters from Charlotte production architecture
"""

from netrun.llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun.llm.adapters.claude import ClaudeAdapter
from netrun.llm.adapters.openai import OpenAIAdapter
from netrun.llm.adapters.ollama import OllamaAdapter

# Optional adapters (require extra dependencies)
try:
    from netrun.llm.adapters.azure_openai import AzureOpenAIAdapter
except ImportError:
    AzureOpenAIAdapter = None

try:
    from netrun.llm.adapters.gemini import GeminiAdapter
except ImportError:
    GeminiAdapter = None

__all__ = [
    "BaseLLMAdapter",
    "AdapterTier",
    "LLMResponse",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "AzureOpenAIAdapter",
    "GeminiAdapter",
]
