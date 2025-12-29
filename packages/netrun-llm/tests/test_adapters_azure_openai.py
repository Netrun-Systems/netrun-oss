"""
Comprehensive tests for AzureOpenAIAdapter.

Tests cover:
    - Adapter initialization with multi-resource support
    - Resource selection and fallback
    - Execute method with resource failover
    - Azure authentication checking
    - Cost calculation (cloud credits = $0)
    - Availability checking
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from netrun.llm.adapters.azure_openai import (
    AzureOpenAIAdapter,
    AzureResource,
)
from netrun.llm.adapters.base import LLMResponse, AdapterTier


@pytest.fixture
def mock_azure_available():
    """Mock Azure as available."""
    with patch("netrun.llm.adapters.azure_openai.AZURE_AVAILABLE", True):
        with patch("netrun.llm.adapters.azure_openai.AzureOpenAI") as mock_azure:
            with patch(
                "netrun.llm.adapters.azure_openai.DefaultAzureCredential"
            ) as mock_cred:
                with patch(
                    "netrun.llm.adapters.azure_openai.get_bearer_token_provider"
                ) as mock_token:
                    yield mock_azure, mock_cred, mock_token


class TestAzureOpenAIInitialization:
    """Test Azure OpenAI adapter initialization."""

    def test_default_initialization(self, mock_azure_available):
        """Test adapter initializes with default resources."""
        mock_azure, mock_cred, mock_token = mock_azure_available

        adapter = AzureOpenAIAdapter()

        # Default model reads from AZURE_OPENAI_DEFAULT_MODEL env var (line 96-98)
        # or falls back to "gpt-4o" if env var not set
        # Current environment has AZURE_OPENAI_DEFAULT_MODEL=gpt-4o-mini
        expected_model = os.getenv("AZURE_OPENAI_DEFAULT_MODEL", "gpt-4o")
        assert adapter.adapter_name == f"AzureOpenAI-{expected_model}"
        assert adapter.preferred_model == expected_model
        assert adapter.tier == AdapterTier.API
        assert adapter.reliability_score == 1.0
        assert len(adapter.resources) > 0

    def test_initialization_without_azure_package(self):
        """Test initialization fails when package not installed."""
        with patch("netrun.llm.adapters.azure_openai.AZURE_AVAILABLE", False):
            with pytest.raises(ImportError):
                AzureOpenAIAdapter()

    def test_initialization_with_custom_resources(self, mock_azure_available):
        """Test initialization with custom resources."""
        custom_resources = [
            AzureResource(
                name="custom-resource",
                endpoint="https://custom.openai.azure.com",
                resource_group="custom-rg",
                models=["gpt-4"],
                priority=1,
            )
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)

        assert len(adapter.resources) == 1
        assert adapter.resources[0].name == "custom-resource"


class TestAzureResourceSelection:
    """Test Azure resource selection logic."""

    def test_get_resource_for_model(self, mock_azure_available):
        """Test selecting resource that supports model."""
        custom_resources = [
            AzureResource(
                name="resource1",
                endpoint="https://r1.openai.azure.com",
                resource_group="rg1",
                models=["gpt-4"],
                priority=1,
            ),
            AzureResource(
                name="resource2",
                endpoint="https://r2.openai.azure.com",
                resource_group="rg2",
                models=["gpt-4o"],
                priority=2,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)

        # Should select resource1 (higher priority) for gpt-4
        resource = adapter._get_resource_for_model("gpt-4")
        assert resource.name == "resource1"

        # Should select resource2 for gpt-4o
        resource = adapter._get_resource_for_model("gpt-4o")
        assert resource.name == "resource2"

    def test_get_resource_for_unsupported_model(self, mock_azure_available):
        """Test handling when no resource supports model."""
        custom_resources = [
            AzureResource(
                name="resource1",
                endpoint="https://r1.openai.azure.com",
                resource_group="rg1",
                models=["gpt-4"],
                priority=1,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)

        # Should return None for unsupported model
        resource = adapter._get_resource_for_model("unsupported-model")
        assert resource is None

    def test_select_fallback_resource(self, mock_azure_available):
        """Test selecting fallback resource."""
        custom_resources = [
            AzureResource(
                name="resource1",
                endpoint="https://r1.openai.azure.com",
                resource_group="rg1",
                models=["gpt-4"],
                priority=1,
            ),
            AzureResource(
                name="resource2",
                endpoint="https://r2.openai.azure.com",
                resource_group="rg2",
                models=["gpt-4o"],
                priority=2,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)

        # Should select highest priority resource not in failed list
        fallback = adapter._select_fallback_resource(["resource1"])
        assert fallback.name == "resource2"


class TestAzureExecution:
    """Test Azure OpenAI execute method."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI API response."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=200)
        return mock_response

    def test_execute_success(
        self, mock_azure_available, mock_openai_response
    ):
        """Test successful execution."""
        mock_azure, mock_cred, mock_token = mock_azure_available

        # Setup mock client
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        custom_resources = [
            AzureResource(
                name="test-resource",
                endpoint="https://test.openai.azure.com",
                resource_group="test-rg",
                models=["gpt-4o"],
                priority=1,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)
        adapter.clients["test-resource"] = mock_client

        response = adapter.execute("Test prompt")

        # Verify response
        assert response.is_success is True
        assert response.content == "Test response"
        assert response.cost_usd == 0.0  # Cloud credits
        assert "effective_cost_saved" in response.metadata

    def test_execute_with_fallback(
        self, mock_azure_available, mock_openai_response
    ):
        """Test execution with resource fallback."""
        mock_azure, mock_cred, mock_token = mock_azure_available

        # First client fails
        mock_client1 = Mock()
        mock_client1.chat.completions.create.side_effect = Exception(
            "Resource error"
        )

        # Second client succeeds
        mock_client2 = Mock()
        mock_client2.chat.completions.create.return_value = mock_openai_response

        custom_resources = [
            AzureResource(
                name="resource1",
                endpoint="https://r1.openai.azure.com",
                resource_group="rg1",
                models=["gpt-4o"],
                priority=1,
            ),
            AzureResource(
                name="resource2",
                endpoint="https://r2.openai.azure.com",
                resource_group="rg2",
                models=["gpt-4o"],
                priority=2,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)
        adapter.clients["resource1"] = mock_client1
        adapter.clients["resource2"] = mock_client2

        response = adapter.execute("Test prompt")

        # Should succeed with fallback
        assert response.is_success is True
        assert response.metadata["resource_name"] == "resource2"

    def test_execute_with_circuit_breaker_open(self, mock_azure_available):
        """Test execution when circuit breaker is open."""
        # Note: AzureOpenAIAdapter doesn't accept circuit_breaker_threshold in __init__
        # Circuit breaker is managed by BaseLLMAdapter with default threshold
        adapter = AzureOpenAIAdapter()

        # Manually set circuit breaker threshold to 1 for testing
        adapter._circuit_breaker_threshold = 1

        # Open circuit breaker by recording failure
        adapter._record_failure()

        response = adapter.execute("Test prompt")

        assert response.is_success is False
        assert "Circuit breaker open" in response.error

    def test_execute_when_disabled(self, mock_azure_available):
        """Test execution when adapter is disabled."""
        adapter = AzureOpenAIAdapter()
        adapter.enabled = False

        response = adapter.execute("Test prompt")

        assert response.is_success is False
        assert "disabled" in response.error.lower()


class TestAzureCostCalculation:
    """Test Azure cost calculation."""

    def test_estimate_cost_always_zero(self, mock_azure_available):
        """Test cost estimation always returns $0.00 (cloud credits)."""
        adapter = AzureOpenAIAdapter()

        cost = adapter.estimate_cost("Test prompt")

        assert cost == 0.0

    def test_calculate_effective_cost(self, mock_azure_available):
        """Test calculating effective cost saved."""
        adapter = AzureOpenAIAdapter()

        # Should calculate what we would have paid
        effective_cost = adapter._calculate_effective_cost("gpt-4o", 1000, 2000)

        assert effective_cost > 0


class TestAzureAvailability:
    """Test Azure availability checking."""

    @patch("netrun.llm.adapters.azure_openai.subprocess.run")
    def test_check_availability_authenticated(
        self, mock_run, mock_azure_available
    ):
        """Test availability when Azure CLI authenticated."""
        mock_run.return_value = Mock(returncode=0)

        custom_resources = [
            AzureResource(
                name="test-resource",
                endpoint="https://test.openai.azure.com",
                resource_group="test-rg",
                models=["gpt-4o"],
                priority=1,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)
        adapter.clients["test-resource"] = Mock()  # Simulate initialized client

        available = adapter.check_availability()

        assert available is True

    @patch("netrun.llm.adapters.azure_openai.subprocess.run")
    def test_check_availability_not_authenticated(
        self, mock_run, mock_azure_available
    ):
        """Test availability when Azure CLI not authenticated."""
        mock_run.return_value = Mock(returncode=1)

        adapter = AzureOpenAIAdapter()

        available = adapter.check_availability()

        assert available is False

    def test_check_availability_no_clients(self, mock_azure_available):
        """Test availability when no clients initialized."""
        adapter = AzureOpenAIAdapter()
        adapter.clients = {}

        available = adapter.check_availability()

        assert available is False


class TestAzureMetadata:
    """Test Azure metadata retrieval."""

    def test_get_metadata(self, mock_azure_available):
        """Test metadata includes all expected fields."""
        custom_resources = [
            AzureResource(
                name="test-resource",
                endpoint="https://test.openai.azure.com",
                resource_group="test-rg",
                models=["gpt-4o"],
                priority=1,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)
        adapter.clients["test-resource"] = Mock()

        # Record some metrics
        adapter._resource_success_count["test-resource"] = 10
        adapter._resource_failure_count["test-resource"] = 2

        metadata = adapter.get_metadata()

        # Metadata name is constructed from preferred_model (line 105 in implementation)
        # Default reads from AZURE_OPENAI_DEFAULT_MODEL env var or "gpt-4o"
        expected_model = os.getenv("AZURE_OPENAI_DEFAULT_MODEL", "gpt-4o")
        assert metadata["name"] == f"AzureOpenAI-{expected_model}"
        assert adapter.preferred_model == expected_model
        assert metadata["tier"] == "API"
        assert "resource_health" in metadata
        assert "test-resource" in metadata["resource_health"]

    def test_get_metadata_resource_health(self, mock_azure_available):
        """Test metadata includes per-resource health."""
        custom_resources = [
            AzureResource(
                name="test-resource",
                endpoint="https://test.openai.azure.com",
                resource_group="test-rg",
                models=["gpt-4o"],
                priority=1,
            ),
        ]

        adapter = AzureOpenAIAdapter(resources=custom_resources)

        adapter._resource_success_count["test-resource"] = 8
        adapter._resource_failure_count["test-resource"] = 2

        metadata = adapter.get_metadata()

        resource_health = metadata["resource_health"]["test-resource"]
        assert resource_health["success_count"] == 8
        assert resource_health["failure_count"] == 2
        assert resource_health["success_rate"] == 80.0
