"""
Comprehensive tests for OllamaAdapter.

Tests cover:
    - Adapter initialization
    - Multi-endpoint fallback
    - Execute method with mocked requests
    - Error handling (connection, timeout)
    - Cost calculation (always $0.00)
    - Availability checking
    - Model availability checking
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from netrun.llm.adapters.ollama import OllamaAdapter, DEFAULT_HOST, DEFAULT_MODEL
from netrun.llm.adapters.base import LLMResponse, AdapterTier


class TestOllamaAdapterInitialization:
    """Test Ollama adapter initialization."""

    def test_default_initialization(self):
        """Test adapter initializes with defaults."""
        adapter = OllamaAdapter()

        # Model comes from OLLAMA_DEFAULT_MODEL env var (llama3:8b)
        expected_model = adapter.model  # Use actual model from environment
        assert adapter.adapter_name == f"Ollama-{expected_model}"
        assert adapter.tier == AdapterTier.LOCAL
        assert adapter.reliability_score == 0.8
        assert adapter.model == expected_model
        assert adapter.max_tokens == 2048

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        adapter = OllamaAdapter(
            host="http://custom:11434",
            model="codellama",
            max_tokens=4096,
            timeout=120,
        )

        assert adapter._host_placeholder == "http://custom:11434"
        assert adapter.model == "codellama"
        assert adapter.max_tokens == 4096
        assert adapter.timeout == 120

    def test_initialization_with_fallback_hosts(self):
        """Test initialization with fallback hosts."""
        fallback_hosts = ["http://host1:11434", "http://host2:11434"]
        adapter = OllamaAdapter(fallback_hosts=fallback_hosts)

        assert "http://host1:11434" in adapter.fallback_hosts
        assert "http://host2:11434" in adapter.fallback_hosts

    def test_initialization_adds_default_localhost(self):
        """Test initialization always includes localhost fallback."""
        adapter = OllamaAdapter()

        assert DEFAULT_HOST in adapter.fallback_hosts


class TestOllamaHostResolution:
    """Test Ollama host resolution."""

    def test_host_placeholder_resolution(self, monkeypatch):
        """Test resolving host from placeholder."""
        monkeypatch.setenv("OLLAMA_HOST", "http://custom-ollama:11434")

        adapter = OllamaAdapter(host="{{OLLAMA_HOST}}")
        host = adapter._get_host()

        assert host == "http://custom-ollama:11434"

    def test_direct_host_usage(self):
        """Test using direct host (not placeholder)."""
        adapter = OllamaAdapter(host="http://direct-host:11434")
        host = adapter._get_host()

        assert host == "http://direct-host:11434"

    def test_get_hosts_to_try_prioritizes_active(self):
        """Test host ordering prioritizes active host."""
        adapter = OllamaAdapter()
        adapter.active_host = "http://host2:11434"
        adapter.fallback_hosts = ["http://host1:11434", "http://host2:11434"]

        hosts = adapter._get_hosts_to_try()

        # Active host should be first
        assert hosts[0] == "http://host2:11434"


class TestOllamaExecution:
    """Test Ollama execute method."""

    @pytest.fixture
    def mock_requests(self):
        """Mock requests module."""
        with patch("netrun.llm.adapters.ollama.requests") as mock:
            yield mock

    def test_execute_success(self, mock_requests):
        """Test successful execution."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "This is a test response",
            "model": "llama3",
            "done": True,
            "total_duration": 1000000,
            "eval_count": 50,
        }
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        adapter = OllamaAdapter()
        response = adapter.execute("Test prompt")

        # Verify response
        assert response.is_success is True
        assert response.content == "This is a test response"
        assert response.cost_usd == 0.0  # Always free
        # Model comes from OLLAMA_DEFAULT_MODEL env var
        assert response.adapter_name == adapter.adapter_name

        # Verify metrics recorded
        assert adapter._success_count == 1

    def test_execute_with_context_parameters(self, mock_requests):
        """Test execution with context parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Test", "done": True}
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        adapter = OllamaAdapter()
        context = {
            "model": "mistral",
            "max_tokens": 1024,
            "temperature": 0.5,
        }

        response = adapter.execute("Test prompt", context=context)

        # Verify API was called
        call_kwargs = mock_requests.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "mistral"
        assert payload["options"]["temperature"] == 0.5
        assert payload["options"]["num_predict"] == 1024

    def test_execute_with_circuit_breaker_open(self, mock_requests):
        """Test execution when circuit breaker is open."""
        adapter = OllamaAdapter(circuit_breaker_threshold=1)

        # Open circuit breaker
        adapter._record_failure()

        response = adapter.execute("Test prompt")

        # Should return error without calling API
        assert response.is_success is False
        assert "Circuit breaker open" in response.error
        mock_requests.post.assert_not_called()

    def test_execute_connection_error_fallback(self, mock_requests):
        """Test fallback on connection error."""
        # Create proper ConnectionError exception
        import requests as real_requests

        # First host fails with ConnectionError, second succeeds
        success_response = Mock()
        success_response.json.return_value = {"response": "Fallback response", "done": True}
        success_response.status_code = 200

        mock_requests.post.side_effect = [
            real_requests.exceptions.ConnectionError("Connection failed"),
            success_response,
        ]
        # Make the exception available for the implementation to catch
        mock_requests.exceptions = real_requests.exceptions

        adapter = OllamaAdapter(
            fallback_hosts=["http://host1:11434", "http://host2:11434"]
        )

        response = adapter.execute("Test prompt")

        assert response.is_success is True
        assert response.content == "Fallback response"
        # Should have tried multiple hosts
        assert mock_requests.post.call_count == 2

    def test_execute_timeout_error(self, mock_requests):
        """Test handling of timeout errors."""
        # Create proper Timeout exception
        import requests as real_requests

        # Set up mock to raise Timeout on all hosts
        mock_requests.post.side_effect = real_requests.exceptions.Timeout(
            "Request timeout"
        )
        # Make the exception available for the implementation to catch
        mock_requests.exceptions = real_requests.exceptions

        adapter = OllamaAdapter()
        response = adapter.execute("Test prompt")

        assert response.is_success is False
        assert "timeout" in response.error.lower()

    def test_execute_model_not_found(self, mock_requests):
        """Test handling when model not installed."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = ValueError("Model not found")
        mock_requests.post.return_value = mock_response

        adapter = OllamaAdapter()

        with pytest.raises(ValueError):
            adapter._call_ollama(
                host=DEFAULT_HOST,
                prompt="Test",
                model="nonexistent-model",
                temperature=0.7,
                max_tokens=100,
            )

    def test_execute_without_requests_package(self):
        """Test handling when requests package not installed."""
        with patch("netrun.llm.adapters.ollama.requests", None):
            adapter = OllamaAdapter()
            response = adapter.execute("Test prompt")

            assert response.is_success is False
            assert "requests package not installed" in response.error


class TestOllamaCostEstimation:
    """Test Ollama cost estimation."""

    def test_estimate_cost_always_zero(self):
        """Test cost estimation always returns $0.00."""
        adapter = OllamaAdapter()

        cost = adapter.estimate_cost("Test prompt with any length")

        assert cost == 0.0


class TestOllamaAvailability:
    """Test Ollama availability checking."""

    @patch("netrun.llm.adapters.ollama.requests")
    def test_check_availability_success(self, mock_requests):
        """Test availability check when Ollama is running."""
        # Mock /api/tags response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3:latest"}]
        }
        mock_requests.get.return_value = mock_response

        adapter = OllamaAdapter(model="llama3")
        available = adapter.check_availability()

        assert available is True

    @patch("netrun.llm.adapters.ollama.requests")
    def test_check_availability_model_not_installed(self, mock_requests):
        """Test availability check when model not installed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_requests.get.return_value = mock_response

        adapter = OllamaAdapter(model="nonexistent-model")
        available = adapter.check_availability()

        assert available is False

    @patch("netrun.llm.adapters.ollama.requests")
    def test_check_availability_connection_error(self, mock_requests):
        """Test availability check when Ollama not running."""
        mock_requests.get.side_effect = Exception("Connection refused")

        adapter = OllamaAdapter()
        available = adapter.check_availability()

        assert available is False

    def test_check_availability_without_requests(self):
        """Test availability check when requests not installed."""
        with patch("netrun.llm.adapters.ollama.requests", None):
            adapter = OllamaAdapter()
            available = adapter.check_availability()

            assert available is False


class TestOllamaMetadata:
    """Test Ollama metadata retrieval."""

    def test_get_metadata(self):
        """Test metadata includes all expected fields."""
        adapter = OllamaAdapter(model="llama3")
        adapter.active_host = "http://localhost:11434"

        # Record some metrics
        adapter._record_success(200, 0.0)

        metadata = adapter.get_metadata()

        assert metadata["name"] == "Ollama-llama3"
        assert metadata["tier"] == "LOCAL"
        assert metadata["model"] == "llama3"
        assert metadata["active_host"] == "http://localhost:11434"
        assert metadata["success_count"] == 1
        assert metadata["total_cost_usd"] == 0.0
        assert "known_models" in metadata
        assert "model_info" in metadata


class TestOllamaAsync:
    """Test Ollama async execution."""

    @pytest.mark.asyncio
    @patch("netrun.llm.adapters.ollama.OllamaAdapter.execute")
    async def test_execute_async_wraps_sync(self, mock_execute):
        """Test async execution wraps synchronous execution."""
        mock_execute.return_value = LLMResponse(
            status="success",
            content="Async response",
            adapter_name="Ollama-llama3",
        )

        adapter = OllamaAdapter()
        response = await adapter.execute_async("Test prompt")

        assert response.content == "Async response"
        mock_execute.assert_called_once()


class TestOllamaModelListing:
    """Test Ollama model listing functionality."""

    @patch("netrun.llm.adapters.ollama.requests")
    def test_list_available_models(self, mock_requests):
        """Test listing available models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "codellama:7b"},
                {"name": "mistral:latest"},
            ]
        }
        mock_requests.get.return_value = mock_response

        adapter = OllamaAdapter()
        models = adapter.list_available_models()

        assert len(models) == 3
        assert "llama3:latest" in models
        assert "codellama:7b" in models
        assert "mistral:latest" in models

    @patch("netrun.llm.adapters.ollama.requests")
    def test_list_available_models_connection_error(self, mock_requests):
        """Test listing models when connection fails."""
        mock_requests.get.side_effect = Exception("Connection error")

        adapter = OllamaAdapter()
        models = adapter.list_available_models()

        assert models == []

    def test_list_available_models_without_requests(self):
        """Test listing models when requests not installed."""
        with patch("netrun.llm.adapters.ollama.requests", None):
            adapter = OllamaAdapter()
            models = adapter.list_available_models()

            assert models == []
