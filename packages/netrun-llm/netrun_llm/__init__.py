"""
Netrun LLM - Backwards Compatibility Shim

This module provides backwards compatibility for code using the old
netrun_llm namespace. All functionality has been migrated to netrun.llm.

DEPRECATED: This module will be removed in version 3.0.0
Please update your imports:
    OLD: from netrun_llm import LLMFallbackChain
    NEW: from netrun.llm import LLMFallbackChain

For a complete migration guide, see:
https://netrunsystems.com/docs/netrun-llm/migration-v2
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "The 'netrun_llm' namespace is deprecated and will be removed in v3.0.0. "
    "Please update imports to 'netrun.llm'. "
    "See https://netrunsystems.com/docs/netrun-llm/migration-v2 for details.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from new namespace for backwards compatibility
from netrun.llm import (
    # Core adapters
    BaseLLMAdapter,
    AdapterTier,
    LLMResponse,
    ClaudeAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    # Fallback chain
    LLMFallbackChain,
    # Three-tier cognition
    ThreeTierCognition,
    CognitionTier,
    # Configuration
    LLMConfig,
    # Exceptions
    LLMError,
    AdapterUnavailableError,
    RateLimitError,
    CircuitBreakerOpenError,
    AllAdaptersFailedError,
    __version__,
    __author__,
)

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
    # Version info
    "__version__",
    "__author__",
]
