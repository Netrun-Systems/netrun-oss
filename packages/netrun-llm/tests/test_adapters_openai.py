"""
Comprehensive tests for OpenAIAdapter.

Tests cover:
    - Adapter initialization
    - API key resolution from placeholders
    - Execute method with mocked OpenAI client
    - Error handling (rate limits, authentication, timeouts)
    - Cost calculation
    - Cost estimation
    - Availability checking
    - Metadata retrieval
    - Circuit breaker integration
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from netrun.llm.adapters.openai import OpenAIAdapter, OPENAI_PRICING, DEFAULT_MODEL
from netrun.llm.adapters.base import LLMResponse, AdapterTier


class TestOpenAIAdapterInitialization:
    """Test OpenAI adapter initialization."""

    def test_default_initialization(self):
        """Test adapter initializes with defaults."""
        adapter = OpenAIAdapter()

        assert adapter.adapter_name == "OpenAI-GPT"
        assert adapter.tier == AdapterTier.API
        assert adapter.reliability_score == 1.0
        assert adapter.default_model == DEFAULT_MODEL
        assert adapter.max_tokens == 4096
        assert adapter.timeout == 30

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        adapter = OpenAIAdapter(
            api_key="test-key",
            default_model="gpt-4o",
            max_tokens=8000,
            timeout=60,
        )

        assert adapter._api_key_placeholder == "test-key"
        assert adapter.default_model == "gpt-4o"
        assert adapter.max_tokens == 8000
        assert adapter.timeout == 60

    def test_initialization_respects_environment_variables(self, monkeypatch):
        """Test initialization reads from environment variables."""
        monkeypatch.setenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_MAX_TOKENS", "2048")
        monkeypatch.setenv("OPENAI_TIMEOUT", "45")

        adapter = OpenAIAdapter()

        assert adapter.default_model == "gpt-4o-mini"
        assert adapter.max_tokens == 2048
        assert adapter.timeout == 45


class TestOpenAIAPIKeyResolution:
    """Test API key placeholder resolution."""

    def test_api_key_placeholder_resolution(self, monkeypatch):
        """Test resolving API key from placeholder."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-12345")

        adapter = OpenAIAdapter(api_key="{{OPENAI_API_KEY}}")
        api_key = adapter._get_api_key()

        assert api_key == "sk-test-12345"

    def test_direct_api_key_usage(self):
        """Test using direct API key (not placeholder)."""
        adapter = OpenAIAdapter(api_key="direct-key-12345")
        api_key = adapter._get_api_key()

        assert api_key == "direct-key-12345"

    def test_api_key_caching(self, monkeypatch):
        """Test API key is cached after first resolution."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-12345")

        adapter = OpenAIAdapter(api_key="{{OPENAI_API_KEY}}")

        # First call resolves
        key1 = adapter._get_api_key()

        # Change environment (should still use cached value)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-different-key")

        # Second call uses cache
        key2 = adapter._get_api_key()

        assert key1 == key2 == "sk-test-12345"


class TestOpenAIExecution:
    """Test OpenAI execute method."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI API response."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(content="This is a test response"),
                finish_reason="stop",
            )
        ]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=200)
        mock_response.model = "gpt-4-turbo"
        mock_response.system_fingerprint = "fp_12345"
        return mock_response

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_success(self, mock_get_client, mock_openai_response):
        """Test successful execution."""
        # Setup mock client
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_client.return_value = mock_client

        adapter = OpenAIAdapter()
        response = adapter.execute("Test prompt")

        # Verify response
        assert response.is_success is True
        assert response.content == "This is a test response"
        assert response.adapter_name == "OpenAI-GPT"
        assert response.tokens_input == 100
        assert response.tokens_output == 200
        assert response.cost_usd > 0

        # Verify metrics recorded
        assert adapter._success_count == 1

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_with_context_parameters(
        self, mock_get_client, mock_openai_response
    ):
        """Test execution with context parameters."""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_client.return_value = mock_client

        adapter = OpenAIAdapter()
        context = {
            "model": "gpt-4o",
            "max_tokens": 2048,
            "temperature": 0.5,
            "system": "You are a coding assistant.",
            "timeout": 45,
        }

        response = adapter.execute("Test prompt", context=context)

        # Verify API was called with correct parameters
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["timeout"] == 45

        # Verify system message
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a coding assistant."

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_with_default_system_prompt(
        self, mock_get_client, mock_openai_response
    ):
        """Test execution uses default system prompt."""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_client.return_value = mock_client

        adapter = OpenAIAdapter()
        response = adapter.execute("Test prompt")

        # Verify default system prompt
        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        assert messages[0]["content"] == "You are a helpful assistant."

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_with_circuit_breaker_open(self, mock_get_client):
        """Test execution when circuit breaker is open."""
        adapter = OpenAIAdapter(circuit_breaker_threshold=1)

        # Open circuit breaker
        adapter._record_failure()

        response = adapter.execute("Test prompt")

        # Should return error without calling API
        assert response.is_success is False
        assert "Circuit breaker open" in response.error
        mock_get_client.assert_not_called()

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_rate_limit_error(self, mock_get_client):
        """Test handling of rate limit errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception(
            "Rate limit exceeded"
        )
        mock_get_client.return_value = mock_client

        adapter = OpenAIAdapter()
        response = adapter.execute("Test prompt")

        assert response.status == "rate_limited"
        assert "Rate limit" in response.error or "rate" in response.error.lower()
        assert adapter._failure_count == 1

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_timeout_error(self, mock_get_client):
        """Test handling of timeout errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Request timeout")
        mock_get_client.return_value = mock_client

        adapter = OpenAIAdapter()
        response = adapter.execute("Test prompt")

        assert response.status == "timeout"
        assert "timeout" in response.error.lower()
        assert adapter._failure_count == 1

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_authentication_error(self, mock_get_client):
        """Test handling of authentication errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception(
            "401 Unauthorized"
        )
        mock_get_client.return_value = mock_client

        adapter = OpenAIAdapter()
        response = adapter.execute("Test prompt")

        assert response.status == "error"
        assert "Authentication failed" in response.error
        assert adapter._failure_count == 1

    @patch("netrun.llm.adapters.openai.OpenAIAdapter._get_client")
    def test_execute_import_error(self, mock_get_client):
        """Test handling when openai package not installed."""
        mock_get_client.side_effect = ImportError("openai package not installed")

        adapter = OpenAIAdapter()
        response = adapter.execute("Test prompt")

        assert response.is_success is False
        assert "openai package not installed" in response.error


class TestOpenAICostCalculation:
    """Test OpenAI cost calculation."""

    def test_calculate_cost_for_gpt4_turbo(self):
        """Test cost calculation for GPT-4 Turbo."""
        adapter = OpenAIAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost("gpt-4-turbo", 1000, 2000)

        # Expected: (1000/1M * $10) + (2000/1M * $30) = $0.010 + $0.060 = $0.070
        expected = 0.070
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_for_gpt4(self):
        """Test cost calculation for GPT-4."""
        adapter = OpenAIAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost("gpt-4", 1000, 2000)

        # Expected: (1000/1M * $30) + (2000/1M * $60) = $0.030 + $0.120 = $0.150
        expected = 0.150
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_for_gpt35_turbo(self):
        """Test cost calculation for GPT-3.5 Turbo (cheapest)."""
        adapter = OpenAIAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost("gpt-3.5-turbo", 1000, 2000)

        # Expected: (1000/1M * $0.50) + (2000/1M * $1.50) = $0.0005 + $0.003 = $0.0035
        expected = 0.0035
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_for_gpt4o_mini(self):
        """Test cost calculation for GPT-4o Mini."""
        adapter = OpenAIAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost("gpt-4o-mini", 1000, 2000)

        # Expected: (1000/1M * $0.15) + (2000/1M * $0.60) = $0.00015 + $0.0012 = $0.00135
        expected = 0.00135
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_unknown_model_uses_default(self):
        """Test unknown model falls back to default pricing."""
        adapter = OpenAIAdapter()

        cost = adapter._calculate_cost("unknown-model", 1000, 2000)

        # Should use default model pricing
        expected_default = adapter._calculate_cost(DEFAULT_MODEL, 1000, 2000)
        assert cost == expected_default


class TestOpenAICostEstimation:
    """Test OpenAI cost estimation."""

    def test_estimate_cost_with_default_params(self):
        """Test cost estimation with default parameters."""
        adapter = OpenAIAdapter()

        # Estimate for a 100-character prompt
        cost = adapter.estimate_cost("a" * 100)

        # Should return non-zero cost estimate
        assert cost > 0

    def test_estimate_cost_with_custom_model(self):
        """Test cost estimation with custom model."""
        adapter = OpenAIAdapter()

        cost_gpt4 = adapter.estimate_cost(
            "Test prompt", context={"model": "gpt-4"}
        )

        cost_gpt35 = adapter.estimate_cost(
            "Test prompt", context={"model": "gpt-3.5-turbo"}
        )

        # GPT-4 should be more expensive than GPT-3.5
        assert cost_gpt4 > cost_gpt35

    def test_estimate_cost_includes_system_prompt(self):
        """Test cost estimation includes system prompt tokens."""
        adapter = OpenAIAdapter()

        cost_with_system = adapter.estimate_cost(
            "User prompt",
            context={"system": "You are a helpful assistant with extensive knowledge."},
        )

        cost_without_system = adapter.estimate_cost("User prompt")

        # Cost with longer system prompt should be higher
        assert cost_with_system > cost_without_system


class TestOpenAIAvailability:
    """Test OpenAI availability checking."""

    def test_check_availability_with_api_key(self, monkeypatch):
        """Test availability check when API key is configured."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-12345")

        adapter = OpenAIAdapter()
        available = adapter.check_availability()

        assert available is True

    def test_check_availability_without_api_key(self, monkeypatch):
        """Test availability check when no API key configured."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        adapter = OpenAIAdapter(api_key="{{OPENAI_API_KEY}}")
        available = adapter.check_availability()

        assert available is False

    def test_check_availability_when_disabled(self):
        """Test availability check when adapter is disabled."""
        adapter = OpenAIAdapter(enabled=False)
        available = adapter.check_availability()

        assert available is False

    def test_check_availability_with_circuit_breaker_open(self):
        """Test availability when circuit breaker is open."""
        adapter = OpenAIAdapter(circuit_breaker_threshold=1)

        # Open circuit breaker
        adapter._record_failure()

        available = adapter.check_availability()

        # is_healthy() returns False when circuit breaker open
        assert available is False


class TestOpenAIMetadata:
    """Test OpenAI metadata retrieval."""

    def test_get_metadata(self, monkeypatch):
        """Test metadata includes all expected fields."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-12345")

        adapter = OpenAIAdapter()

        # Record some metrics
        adapter._record_success(150, 0.02)

        metadata = adapter.get_metadata()

        assert metadata["name"] == "OpenAI-GPT"
        assert metadata["tier"] == "API"
        assert metadata["default_model"] == DEFAULT_MODEL
        assert metadata["max_tokens"] == 4096
        assert metadata["timeout"] == 30
        assert metadata["success_count"] == 1
        assert metadata["failure_count"] == 0
        assert metadata["has_api_key"] is True
        assert "supported_models" in metadata
        assert len(metadata["supported_models"]) > 0

    def test_get_metadata_includes_supported_models(self):
        """Test metadata includes list of supported models."""
        adapter = OpenAIAdapter()
        metadata = adapter.get_metadata()

        assert "supported_models" in metadata
        assert "gpt-4-turbo" in metadata["supported_models"]
        assert "gpt-4o" in metadata["supported_models"]
        assert "gpt-3.5-turbo" in metadata["supported_models"]


class TestOpenAIAsync:
    """Test OpenAI async execution."""

    @pytest.mark.asyncio
    @patch("netrun.llm.adapters.openai.OpenAIAdapter.execute")
    async def test_execute_async_wraps_sync(self, mock_execute):
        """Test async execution wraps synchronous execution."""
        mock_execute.return_value = LLMResponse(
            status="success",
            content="Async response",
            adapter_name="OpenAI-GPT",
        )

        adapter = OpenAIAdapter()
        response = await adapter.execute_async("Test prompt")

        assert response.content == "Async response"
        mock_execute.assert_called_once()
