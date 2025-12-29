"""
Comprehensive tests for BaseLLMAdapter.

Tests cover:
    - Adapter initialization
    - Circuit breaker behavior
    - Performance metrics tracking
    - Success/failure recording
    - Health checking
    - Error response creation
"""

import pytest
import time
from unittest.mock import Mock
from typing import Dict, Any, Optional

from netrun.llm.adapters.base import (
    BaseLLMAdapter,
    AdapterTier,
    LLMResponse,
)


class ConcreteAdapter(BaseLLMAdapter):
    """Concrete implementation of BaseLLMAdapter for testing."""

    def __init__(
        self,
        should_fail: bool = False,
        is_available: bool = True,
        response_content: str = "Test response",
        **kwargs,
    ):
        super().__init__(
            adapter_name="TestAdapter",
            tier=AdapterTier.API,
            reliability_score=1.0,
            **kwargs,
        )
        self.should_fail = should_fail
        self._is_available = is_available
        self.response_content = response_content

    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        if self.should_fail:
            self._record_failure()
            return LLMResponse(status="error", error="Test error")

        self._record_success(100, 0.01)
        return LLMResponse(
            status="success",
            content=self.response_content,
            cost_usd=0.01,
            latency_ms=100,
            adapter_name=self.adapter_name,
        )

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        return self.execute(prompt, context)

    def estimate_cost(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        return 0.01

    def check_availability(self) -> bool:
        return self._is_available

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.adapter_name,
            "available": self._is_available,
        }


class TestAdapterTier:
    """Test AdapterTier enum."""

    def test_tier_values(self):
        """Test tier enum has expected values."""
        assert AdapterTier.API.value == 1
        assert AdapterTier.LOCAL.value == 2
        assert AdapterTier.CLI.value == 3
        assert AdapterTier.GUI.value == 4

    def test_tier_ordering(self):
        """Test tier reliability ordering."""
        assert AdapterTier.API.value < AdapterTier.LOCAL.value
        assert AdapterTier.LOCAL.value < AdapterTier.CLI.value
        assert AdapterTier.CLI.value < AdapterTier.GUI.value


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_success_response(self):
        """Test creating successful response."""
        response = LLMResponse(
            status="success",
            content="Test content",
            cost_usd=0.01,
            latency_ms=100,
            adapter_name="TestAdapter",
            model_used="test-model",
            tokens_input=50,
            tokens_output=100,
        )

        assert response.is_success is True
        assert response.content == "Test content"
        assert response.cost_usd == 0.01
        assert response.total_tokens == 150

    def test_error_response(self):
        """Test creating error response."""
        response = LLMResponse(
            status="error",
            error="Test error",
            adapter_name="TestAdapter",
        )

        assert response.is_success is False
        assert response.error == "Test error"
        assert response.content is None

    def test_rate_limited_response(self):
        """Test rate limited response."""
        response = LLMResponse(
            status="rate_limited",
            error="Rate limit exceeded",
            adapter_name="TestAdapter",
        )

        assert response.is_success is False
        assert response.status == "rate_limited"

    def test_total_tokens(self):
        """Test total_tokens property."""
        response = LLMResponse(
            status="success",
            tokens_input=100,
            tokens_output=200,
        )

        assert response.total_tokens == 300

    def test_to_dict(self):
        """Test serialization to dictionary."""
        response = LLMResponse(
            status="success",
            content="Test",
            cost_usd=0.01,
            latency_ms=100,
            adapter_name="TestAdapter",
            metadata={"key": "value"},
        )

        result = response.to_dict()

        assert result["status"] == "success"
        assert result["content"] == "Test"
        assert result["cost_usd"] == 0.01
        assert result["metadata"] == {"key": "value"}


class TestBaseLLMAdapter:
    """Test BaseLLMAdapter implementation."""

    def test_adapter_initialization(self):
        """Test adapter initialization."""
        adapter = ConcreteAdapter()

        assert adapter.adapter_name == "TestAdapter"
        assert adapter.tier == AdapterTier.API
        assert adapter.reliability_score == 1.0
        assert adapter.enabled is True

    def test_adapter_initialization_with_custom_params(self):
        """Test adapter initialization with custom parameters."""
        adapter = ConcreteAdapter(
            enabled=False,
            circuit_breaker_threshold=10,
            circuit_breaker_cooldown=600,
        )

        assert adapter.enabled is False
        assert adapter._circuit_breaker_threshold == 10
        assert adapter._circuit_breaker_cooldown == 600

    def test_record_success(self):
        """Test recording successful execution."""
        adapter = ConcreteAdapter()

        adapter._record_success(100, 0.01)

        assert adapter._success_count == 1
        assert adapter._total_latency_ms == 100
        assert adapter._total_cost_usd == 0.01
        assert adapter._consecutive_failures == 0

    def test_record_failure(self):
        """Test recording failed execution."""
        adapter = ConcreteAdapter()

        adapter._record_failure()

        assert adapter._failure_count == 1
        assert adapter._consecutive_failures == 1
        assert adapter._last_failure_time is not None

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after threshold failures."""
        adapter = ConcreteAdapter(circuit_breaker_threshold=3)

        # Record failures up to threshold
        for _ in range(3):
            adapter._record_failure()

        assert adapter._circuit_breaker_open is True

    def test_circuit_breaker_remains_closed_below_threshold(self):
        """Test circuit breaker stays closed below threshold."""
        adapter = ConcreteAdapter(circuit_breaker_threshold=5)

        # Record failures below threshold
        for _ in range(4):
            adapter._record_failure()

        assert adapter._circuit_breaker_open is False

    def test_circuit_breaker_closes_after_cooldown(self):
        """Test circuit breaker closes after cooldown period."""
        adapter = ConcreteAdapter(
            circuit_breaker_threshold=2,
            circuit_breaker_cooldown=1,  # 1 second cooldown
        )

        # Open circuit breaker
        adapter._record_failure()
        adapter._record_failure()

        assert adapter._circuit_breaker_open is True

        # Wait for cooldown
        time.sleep(1.1)

        # Check circuit breaker
        is_open = adapter._check_circuit_breaker()

        assert is_open is False
        assert adapter._circuit_breaker_open is False

    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets consecutive failures on success."""
        adapter = ConcreteAdapter(circuit_breaker_threshold=5)

        # Record some failures
        adapter._record_failure()
        adapter._record_failure()
        assert adapter._consecutive_failures == 2

        # Record success
        adapter._record_success(100, 0.01)

        assert adapter._consecutive_failures == 0

    def test_get_success_rate(self):
        """Test success rate calculation."""
        adapter = ConcreteAdapter()

        # No executions yet
        assert adapter.get_success_rate() == 100.0

        # Record mixed results
        adapter._record_success(100, 0.01)
        adapter._record_success(100, 0.01)
        adapter._record_failure()

        # 2 successes out of 3 total = 66.67%
        assert pytest.approx(adapter.get_success_rate(), 0.1) == 66.67

    def test_get_average_latency(self):
        """Test average latency calculation."""
        adapter = ConcreteAdapter()

        # No successes yet
        assert adapter.get_average_latency() == 0.0

        # Record successes with different latencies
        adapter._record_success(100, 0.01)
        adapter._record_success(200, 0.02)

        # Average: (100 + 200) / 2 = 150
        assert adapter.get_average_latency() == 150.0

    def test_reset_metrics(self):
        """Test metrics reset."""
        adapter = ConcreteAdapter()

        # Record some metrics
        adapter._record_success(100, 0.01)
        adapter._record_failure()

        # Reset
        adapter.reset_metrics()

        assert adapter._success_count == 0
        assert adapter._failure_count == 0
        assert adapter._total_latency_ms == 0
        assert adapter._total_cost_usd == 0.0
        assert adapter._consecutive_failures == 0
        assert adapter._circuit_breaker_open is False

    def test_is_healthy_when_enabled_and_good_success_rate(self):
        """Test is_healthy returns True for healthy adapter."""
        adapter = ConcreteAdapter(enabled=True)

        # Record good success rate
        for _ in range(20):
            adapter._record_success(100, 0.01)

        assert adapter.is_healthy() is True

    def test_is_healthy_when_disabled(self):
        """Test is_healthy returns False when disabled."""
        adapter = ConcreteAdapter(enabled=False)

        assert adapter.is_healthy() is False

    def test_is_healthy_when_circuit_breaker_open(self):
        """Test is_healthy returns False when circuit breaker open."""
        adapter = ConcreteAdapter(circuit_breaker_threshold=2)

        # Open circuit breaker
        adapter._record_failure()
        adapter._record_failure()

        assert adapter.is_healthy() is False

    def test_is_healthy_with_low_success_rate(self):
        """Test is_healthy returns False with low success rate."""
        adapter = ConcreteAdapter()

        # Record poor success rate (5 successes, 15 failures = 25%)
        for _ in range(5):
            adapter._record_success(100, 0.01)
        for _ in range(15):
            adapter._record_failure()

        assert adapter.is_healthy() is False

    def test_is_healthy_ignores_low_success_rate_with_insufficient_data(self):
        """Test is_healthy ignores success rate with < 10 executions."""
        adapter = ConcreteAdapter()

        # Record poor success rate but insufficient data
        adapter._record_success(100, 0.01)
        adapter._record_failure()
        adapter._record_failure()

        # Only 3 executions, threshold is 10
        assert adapter.is_healthy() is True

    def test_create_error_response(self):
        """Test creating standardized error response."""
        adapter = ConcreteAdapter()

        response = adapter._create_error_response(
            error="Test error",
            status="error",
            latency_ms=100,
            model="test-model",
        )

        assert response.status == "error"
        assert response.error == "Test error"
        assert response.latency_ms == 100
        assert response.adapter_name == "TestAdapter"
        assert response.model_used == "test-model"

    def test_repr(self):
        """Test string representation."""
        adapter = ConcreteAdapter()

        adapter._record_success(100, 0.01)

        repr_str = repr(adapter)

        assert "ConcreteAdapter" in repr_str
        assert "name=TestAdapter" in repr_str
        assert "tier=API" in repr_str
        assert "reliability=1.0" in repr_str
        assert "success_rate=100.0%" in repr_str

    def test_execute_abstract_method(self):
        """Test execute is abstract and must be implemented."""
        # ConcreteAdapter implements it, so no error
        adapter = ConcreteAdapter()
        response = adapter.execute("test prompt")

        assert response is not None

    def test_circuit_breaker_without_timestamp(self):
        """Test circuit breaker handles missing timestamp gracefully."""
        adapter = ConcreteAdapter()

        # Manually set circuit breaker without timestamp
        adapter._circuit_breaker_open = True
        adapter._circuit_breaker_open_time = None

        # Should close circuit breaker and reset
        is_open = adapter._check_circuit_breaker()

        assert is_open is False
        assert adapter._circuit_breaker_open is False
        assert adapter._consecutive_failures == 0
