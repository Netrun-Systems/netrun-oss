"""
Netrun LLM - Multi-Provider LLM Orchestration with Fallback Chains

This package provides a unified interface for working with multiple LLM providers
(Claude, OpenAI, Ollama) with automatic failover, circuit breaker protection,
and three-tier cognition patterns for optimal response latency.

Features:
    - Multi-adapter fallback chains (Claude -> GPT-4 -> Llama3)
    - Circuit breaker protection per adapter
    - Three-tier cognition: Fast ack (<100ms), RAG response (<2s), Deep insight (<5s)
    - Async-first with sync wrappers
    - Cost tracking and metrics
    - Project-agnostic design

v1.1.0: Added netrun-logging integration for structured LLM operation logging

Author: Netrun Systems
Version: 1.1.0
License: MIT
"""

from netrun_llm.adapters.base import (
    BaseLLMAdapter,
    AdapterTier,
    LLMResponse,
)
from netrun_llm.adapters.claude import ClaudeAdapter
from netrun_llm.adapters.openai import OpenAIAdapter
from netrun_llm.adapters.ollama import OllamaAdapter
from netrun_llm.chain import LLMFallbackChain
from netrun_llm.cognition import ThreeTierCognition, CognitionTier
from netrun_llm.config import LLMConfig
from netrun_llm.exceptions import (
    LLMError,
    AdapterUnavailableError,
    RateLimitError,
    CircuitBreakerOpenError,
    AllAdaptersFailedError,
)

__version__ = "1.1.0"
__author__ = "Netrun Systems"

__all__ = [
    # Core adapters
    "BaseLLMAdapter",
    "AdapterTier",
    "LLMResponse",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    # Fallback chain
    "LLMFallbackChain",
    # Three-tier cognition
    "ThreeTierCognition",
    "CognitionTier",
    # Configuration
    "LLMConfig",
    # Exceptions
    "LLMError",
    "AdapterUnavailableError",
    "RateLimitError",
    "CircuitBreakerOpenError",
    "AllAdaptersFailedError",
]
