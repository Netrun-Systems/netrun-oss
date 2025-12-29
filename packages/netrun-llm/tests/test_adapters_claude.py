"""
Comprehensive tests for ClaudeAdapter.

Tests cover:
    - Adapter initialization
    - API key resolution from placeholders
    - Execute method with mocked Anthropic client
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

from netrun.llm.adapters.claude import ClaudeAdapter, CLAUDE_PRICING, DEFAULT_MODEL
from netrun.llm.adapters.base import LLMResponse, AdapterTier


class TestClaudeAdapterInitialization:
    """Test Claude adapter initialization."""

    def test_default_initialization(self):
        """Test adapter initializes with defaults."""
        adapter = ClaudeAdapter()

        assert adapter.adapter_name == "Claude-Anthropic"
        assert adapter.tier == AdapterTier.API
        assert adapter.reliability_score == 1.0
        assert adapter.default_model == DEFAULT_MODEL
        assert adapter.max_tokens == 4096

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        adapter = ClaudeAdapter(
            api_key="test-key",
            default_model="claude-3-opus-20240229",
            max_tokens=8000,
            base_url="https://custom.api.com",
        )

        assert adapter._api_key_placeholder == "test-key"
        assert adapter.default_model == "claude-3-opus-20240229"
        assert adapter.max_tokens == 8000
        assert adapter.base_url == "https://custom.api.com"

    def test_initialization_respects_environment_variables(self, monkeypatch):
        """Test initialization reads from environment variables."""
        monkeypatch.setenv("CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
        monkeypatch.setenv("CLAUDE_MAX_TOKENS", "2048")

        adapter = ClaudeAdapter()

        assert adapter.default_model == "claude-3-haiku-20240307"
        assert adapter.max_tokens == 2048


class TestClaudeAPIKeyResolution:
    """Test API key placeholder resolution."""

    def test_api_key_placeholder_resolution(self, monkeypatch):
        """Test resolving API key from placeholder."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-12345")

        adapter = ClaudeAdapter(api_key="{{ANTHROPIC_API_KEY}}")
        api_key = adapter._get_api_key()

        assert api_key == "sk-test-12345"

    def test_direct_api_key_usage(self):
        """Test using direct API key (not placeholder)."""
        adapter = ClaudeAdapter(api_key="direct-key-12345")
        api_key = adapter._get_api_key()

        assert api_key == "direct-key-12345"

    def test_api_key_caching(self, monkeypatch):
        """Test API key is cached after first resolution."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-12345")

        adapter = ClaudeAdapter(api_key="{{ANTHROPIC_API_KEY}}")

        # First call resolves
        key1 = adapter._get_api_key()

        # Change environment (should still use cached value)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-different-key")

        # Second call uses cache
        key2 = adapter._get_api_key()

        assert key1 == key2 == "sk-test-12345"


class TestClaudeExecution:
    """Test Claude execute method."""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create mock Anthropic API response."""
        mock_response = Mock()
        mock_response.content = [Mock(text="This is a test response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=200)
        mock_response.stop_reason = "end_turn"
        mock_response.model = "claude-sonnet-4-5-20250929"
        return mock_response

    @patch("netrun.llm.adapters.claude.ClaudeAdapter._get_client")
    def test_execute_success(self, mock_get_client, mock_anthropic_response):
        """Test successful execution."""
        # Setup mock client
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_get_client.return_value = mock_client

        adapter = ClaudeAdapter()
        response = adapter.execute("Test prompt")

        # Verify response
        assert response.is_success is True
        assert response.content == "This is a test response"
        assert response.adapter_name == "Claude-Anthropic"
        assert response.tokens_input == 100
        assert response.tokens_output == 200
        assert response.cost_usd > 0

        # Verify metrics recorded
        assert adapter._success_count == 1

    @patch("netrun.llm.adapters.claude.ClaudeAdapter._get_client")
    def test_execute_with_context_parameters(
        self, mock_get_client, mock_anthropic_response
    ):
        """Test execution with context parameters."""
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_get_client.return_value = mock_client

        adapter = ClaudeAdapter()
        context = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 2048,
            "temperature": 0.5,
            "system": "You are a helpful assistant.",
        }

        response = adapter.execute("Test prompt", context=context)

        # Verify API was called with correct parameters
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus-20240229"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["system"] == "You are a helpful assistant."

    @patch("netrun.llm.adapters.claude.ClaudeAdapter._get_client")
    def test_execute_with_circuit_breaker_open(self, mock_get_client):
        """Test execution when circuit breaker is open."""
        adapter = ClaudeAdapter(circuit_breaker_threshold=1)

        # Open circuit breaker
        adapter._record_failure()

        response = adapter.execute("Test prompt")

        # Should return error without calling API
        assert response.is_success is False
        assert "Circuit breaker open" in response.error
        mock_get_client.assert_not_called()

    @patch("netrun.llm.adapters.claude.ClaudeAdapter._get_client")
    def test_execute_rate_limit_error(self, mock_get_client):
        """Test handling of rate limit errors."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Rate limit exceeded")
        mock_get_client.return_value = mock_client

        adapter = ClaudeAdapter()
        response = adapter.execute("Test prompt")

        assert response.status == "rate_limited"
        assert "Rate limit" in response.error or "rate" in response.error.lower()
        assert adapter._failure_count == 1

    @patch("netrun.llm.adapters.claude.ClaudeAdapter._get_client")
    def test_execute_authentication_error(self, mock_get_client):
        """Test handling of authentication errors."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("401 Unauthorized")
        mock_get_client.return_value = mock_client

        adapter = ClaudeAdapter()
        response = adapter.execute("Test prompt")

        assert response.status == "error"
        assert "Authentication failed" in response.error
        assert adapter._failure_count == 1

    @patch("netrun.llm.adapters.claude.ClaudeAdapter._get_client")
    def test_execute_import_error(self, mock_get_client):
        """Test handling when anthropic package not installed."""
        mock_get_client.side_effect = ImportError(
            "anthropic package not installed"
        )

        adapter = ClaudeAdapter()
        response = adapter.execute("Test prompt")

        assert response.is_success is False
        assert "anthropic package not installed" in response.error


class TestClaudeCostCalculation:
    """Test Claude cost calculation."""

    def test_calculate_cost_for_sonnet_45(self):
        """Test cost calculation for Sonnet 4.5."""
        adapter = ClaudeAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost(
            "claude-sonnet-4-5-20250929", 1000, 2000
        )

        # Expected: (1000/1M * $3) + (2000/1M * $15) = $0.003 + $0.030 = $0.033
        expected = 0.033
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_for_opus(self):
        """Test cost calculation for Opus."""
        adapter = ClaudeAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost("claude-3-opus-20240229", 1000, 2000)

        # Expected: (1000/1M * $15) + (2000/1M * $75) = $0.015 + $0.150 = $0.165
        expected = 0.165
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_for_haiku(self):
        """Test cost calculation for Haiku (cheapest)."""
        adapter = ClaudeAdapter()

        # 1000 input tokens, 2000 output tokens
        cost = adapter._calculate_cost("claude-3-haiku-20240307", 1000, 2000)

        # Expected: (1000/1M * $0.25) + (2000/1M * $1.25) = $0.00025 + $0.0025 = $0.00275
        expected = 0.00275
        assert pytest.approx(cost, 0.0001) == expected

    def test_calculate_cost_unknown_model_uses_default(self):
        """Test unknown model falls back to default pricing."""
        adapter = ClaudeAdapter()

        cost = adapter._calculate_cost("unknown-model", 1000, 2000)

        # Should use default model pricing (Sonnet 4.5)
        expected_default = adapter._calculate_cost(DEFAULT_MODEL, 1000, 2000)
        assert cost == expected_default


class TestClaudeCostEstimation:
    """Test Claude cost estimation."""

    def test_estimate_cost_with_default_params(self):
        """Test cost estimation with default parameters."""
        adapter = ClaudeAdapter()

        # Estimate for a 100-character prompt (rough estimate: 25 tokens)
        cost = adapter.estimate_cost("a" * 100)

        # Should return non-zero cost estimate
        assert cost > 0

    def test_estimate_cost_with_custom_model(self):
        """Test cost estimation with custom model."""
        adapter = ClaudeAdapter()

        cost_opus = adapter.estimate_cost(
            "Test prompt", context={"model": "claude-3-opus-20240229"}
        )

        cost_haiku = adapter.estimate_cost(
            "Test prompt", context={"model": "claude-3-haiku-20240307"}
        )

        # Opus should be more expensive than Haiku
        assert cost_opus > cost_haiku


class TestClaudeAvailability:
    """Test Claude availability checking."""

    def test_check_availability_with_api_key(self, monkeypatch):
        """Test availability check when API key is configured."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-12345")

        adapter = ClaudeAdapter()
        available = adapter.check_availability()

        assert available is True

    def test_check_availability_without_api_key(self, monkeypatch):
        """Test availability check when no API key configured."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        adapter = ClaudeAdapter(api_key="{{ANTHROPIC_API_KEY}}")
        available = adapter.check_availability()

        assert available is False

    def test_check_availability_when_disabled(self):
        """Test availability check when adapter is disabled."""
        adapter = ClaudeAdapter(enabled=False)
        available = adapter.check_availability()

        assert available is False

    def test_check_availability_with_circuit_breaker_open(self):
        """Test availability when circuit breaker is open."""
        adapter = ClaudeAdapter(circuit_breaker_threshold=1)

        # Open circuit breaker
        adapter._record_failure()

        available = adapter.check_availability()

        # is_healthy() returns False when circuit breaker open
        assert available is False


class TestClaudeMetadata:
    """Test Claude metadata retrieval."""

    def test_get_metadata(self, monkeypatch):
        """Test metadata includes all expected fields."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-12345")

        adapter = ClaudeAdapter()

        # Record some metrics
        adapter._record_success(100, 0.01)

        metadata = adapter.get_metadata()

        assert metadata["name"] == "Claude-Anthropic"
        assert metadata["tier"] == "API"
        assert metadata["default_model"] == DEFAULT_MODEL
        assert metadata["max_tokens"] == 4096
        assert metadata["success_count"] == 1
        assert metadata["failure_count"] == 0
        assert metadata["has_api_key"] is True
        assert "supported_models" in metadata
        assert len(metadata["supported_models"]) > 0

    def test_get_metadata_includes_supported_models(self):
        """Test metadata includes list of supported models."""
        adapter = ClaudeAdapter()
        metadata = adapter.get_metadata()

        assert "supported_models" in metadata
        assert "claude-sonnet-4-5-20250929" in metadata["supported_models"]
        assert "claude-3-opus-20240229" in metadata["supported_models"]


class TestClaudeAsync:
    """Test Claude async execution."""

    @pytest.mark.asyncio
    @patch("netrun.llm.adapters.claude.ClaudeAdapter.execute")
    async def test_execute_async_wraps_sync(self, mock_execute):
        """Test async execution wraps synchronous execution."""
        mock_execute.return_value = LLMResponse(
            status="success",
            content="Async response",
            adapter_name="Claude-Anthropic",
        )

        adapter = ClaudeAdapter()
        response = await adapter.execute_async("Test prompt")

        assert response.content == "Async response"
        mock_execute.assert_called_once()
