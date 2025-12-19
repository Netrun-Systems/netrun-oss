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
v2.0.0: Migrated to netrun.llm namespace structure

Author: Netrun Systems
Version: 2.0.0
License: MIT
"""

from netrun.llm.adapters.base import (
    BaseLLMAdapter,
    AdapterTier,
    LLMResponse,
)
from netrun.llm.adapters.claude import ClaudeAdapter
from netrun.llm.adapters.openai import OpenAIAdapter
from netrun.llm.adapters.ollama import OllamaAdapter
from netrun.llm.chain import LLMFallbackChain
from netrun.llm.cognition import ThreeTierCognition, CognitionTier
from netrun.llm.config import LLMConfig
from netrun.llm.exceptions import (
    LLMError,
    AdapterUnavailableError,
    RateLimitError,
    CircuitBreakerOpenError,
    AllAdaptersFailedError,
)
from netrun.llm.policies import (
    ProviderPolicy,
    TenantPolicy,
    PolicyEnforcer,
    UsageRecord,
    CostTier,
    MODEL_COSTS,
    MODEL_COST_TIERS,
    get_model_pricing,
    PolicyViolationError,
    ProviderDisabledError,
    BudgetExceededError,
    RateLimitExceededError,
    FallbackToLocalError,
)
from netrun.llm.telemetry import (
    LLMRequestMetrics,
    AggregatedMetrics,
    TelemetryCollector,
    RequestTracker,
    get_collector,
    configure_telemetry,
)

__version__ = "2.0.0"
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
    # Policies
    "ProviderPolicy",
    "TenantPolicy",
    "PolicyEnforcer",
    "UsageRecord",
    "CostTier",
    "MODEL_COSTS",
    "MODEL_COST_TIERS",
    "get_model_pricing",
    "PolicyViolationError",
    "ProviderDisabledError",
    "BudgetExceededError",
    "RateLimitExceededError",
    "FallbackToLocalError",
    # Telemetry
    "LLMRequestMetrics",
    "AggregatedMetrics",
    "TelemetryCollector",
    "RequestTracker",
    "get_collector",
    "configure_telemetry",
]
