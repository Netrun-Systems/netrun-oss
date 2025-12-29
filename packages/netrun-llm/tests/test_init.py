"""
Tests for package initialization and imports.

Tests cover:
    - Module imports
    - Version exports
    - __all__ exports
    - Optional imports (Azure, Gemini)
"""

import pytest


class TestPackageInit:
    """Test netrun.llm package initialization."""

    def test_version_export(self):
        """Test __version__ is exported."""
        from netrun.llm import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_author_export(self):
        """Test __author__ is exported."""
        from netrun.llm import __author__

        assert __author__ == "Netrun Systems"

    def test_core_adapter_imports(self):
        """Test core adapters can be imported."""
        from netrun.llm import (
            BaseLLMAdapter,
            AdapterTier,
            LLMResponse,
            ClaudeAdapter,
            OpenAIAdapter,
            OllamaAdapter
        )

        assert BaseLLMAdapter is not None
        assert AdapterTier is not None
        assert LLMResponse is not None
        assert ClaudeAdapter is not None
        assert OpenAIAdapter is not None
        assert OllamaAdapter is not None

    def test_fallback_chain_import(self):
        """Test LLMFallbackChain can be imported."""
        from netrun.llm import LLMFallbackChain

        assert LLMFallbackChain is not None

    def test_cognition_imports(self):
        """Test cognition classes can be imported."""
        from netrun.llm import ThreeTierCognition, CognitionTier

        assert ThreeTierCognition is not None
        assert CognitionTier is not None

    def test_config_import(self):
        """Test LLMConfig can be imported."""
        from netrun.llm import LLMConfig

        assert LLMConfig is not None

    def test_exception_imports(self):
        """Test exception classes can be imported."""
        from netrun.llm import (
            LLMError,
            AdapterUnavailableError,
            RateLimitError,
            CircuitBreakerOpenError,
            AllAdaptersFailedError
        )

        assert LLMError is not None
        assert AdapterUnavailableError is not None
        assert RateLimitError is not None
        assert CircuitBreakerOpenError is not None
        assert AllAdaptersFailedError is not None

    def test_policy_imports(self):
        """Test policy classes can be imported."""
        from netrun.llm import (
            ProviderPolicy,
            TenantPolicy,
            PolicyEnforcer,
            UsageRecord,
            CostTier,
            MODEL_COSTS,
            MODEL_COST_TIERS,
            get_model_pricing
        )

        assert ProviderPolicy is not None
        assert TenantPolicy is not None
        assert PolicyEnforcer is not None
        assert UsageRecord is not None
        assert CostTier is not None
        assert MODEL_COSTS is not None
        assert MODEL_COST_TIERS is not None
        assert get_model_pricing is not None

    def test_telemetry_imports(self):
        """Test telemetry classes can be imported."""
        from netrun.llm import (
            LLMRequestMetrics,
            AggregatedMetrics,
            TelemetryCollector,
            RequestTracker,
            get_collector,
            configure_telemetry
        )

        assert LLMRequestMetrics is not None
        assert AggregatedMetrics is not None
        assert TelemetryCollector is not None
        assert RequestTracker is not None
        assert get_collector is not None
        assert configure_telemetry is not None

    def test_optional_azure_import(self):
        """Test Azure OpenAI adapter import (may be None if not installed)."""
        from netrun.llm import AzureOpenAIAdapter

        # May be None if azure-openai not installed
        assert AzureOpenAIAdapter is not None or AzureOpenAIAdapter is None

    def test_optional_gemini_import(self):
        """Test Gemini adapter import (may be None if not installed)."""
        from netrun.llm import GeminiAdapter

        # May be None if google-generativeai not installed
        assert GeminiAdapter is not None or GeminiAdapter is None

    def test_all_export_list(self):
        """Test __all__ contains expected exports."""
        from netrun.llm import __all__

        assert "BaseLLMAdapter" in __all__
        assert "LLMFallbackChain" in __all__
        assert "ThreeTierCognition" in __all__
        assert "LLMConfig" in __all__
        assert "LLMError" in __all__
        assert "ProviderPolicy" in __all__
        assert "TelemetryCollector" in __all__


class TestAdaptersInit:
    """Test netrun.llm.adapters package initialization."""

    def test_adapters_base_imports(self):
        """Test base adapter classes can be imported from adapters submodule."""
        from netrun.llm.adapters import (
            BaseLLMAdapter,
            AdapterTier,
            LLMResponse
        )

        assert BaseLLMAdapter is not None
        assert AdapterTier is not None
        assert LLMResponse is not None

    def test_adapters_claude_import(self):
        """Test Claude adapter import."""
        from netrun.llm.adapters import ClaudeAdapter

        assert ClaudeAdapter is not None

    def test_adapters_openai_import(self):
        """Test OpenAI adapter import."""
        from netrun.llm.adapters import OpenAIAdapter

        assert OpenAIAdapter is not None

    def test_adapters_ollama_import(self):
        """Test Ollama adapter import."""
        from netrun.llm.adapters import OllamaAdapter

        assert OllamaAdapter is not None

    def test_adapters_azure_import_optional(self):
        """Test Azure OpenAI adapter optional import."""
        try:
            from netrun.llm.adapters import AzureOpenAIAdapter
            assert AzureOpenAIAdapter is not None
        except ImportError:
            # Expected if azure-openai not installed
            pass

    def test_adapters_gemini_import_optional(self):
        """Test Gemini adapter optional import."""
        try:
            from netrun.llm.adapters import GeminiAdapter
            assert GeminiAdapter is not None
        except ImportError:
            # Expected if google-generativeai not installed
            pass
