"""
Netrun LLM - Adapter Package

Provides unified interfaces to multiple LLM providers.
All adapters inherit from BaseLLMAdapter for consistent behavior.

Adapters:
    - ClaudeAdapter: Anthropic Claude API (claude-sonnet-4.5, claude-3.5-sonnet, etc.)
    - OpenAIAdapter: OpenAI API (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
    - OllamaAdapter: Ollama local models (llama3, mistral, codellama)
"""

from netrun_llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun_llm.adapters.claude import ClaudeAdapter
from netrun_llm.adapters.openai import OpenAIAdapter
from netrun_llm.adapters.ollama import OllamaAdapter

__all__ = [
    "BaseLLMAdapter",
    "AdapterTier",
    "LLMResponse",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
]
