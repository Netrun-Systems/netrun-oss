"""
Tests for LLMFallbackChain.

Tests cover:
    - Chain initialization with default and custom adapters
    - Automatic failover on adapter failures
    - Circuit breaker integration
    - Metrics tracking
    - Async execution
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional

from netrun_llm.chain import (
    LLMFallbackChain,
    create_default_chain,
    create_cost_optimized_chain,
    create_quality_chain,
)
from netrun_llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun_llm.exceptions import AllAdaptersFailedError


class MockAdapter(BaseLLMAdapter):
    """Mock adapter for testing."""

    def __init__(
        self,
        name: str = "MockAdapter",
        should_fail: bool = False,
        is_available: bool = True,
        response_content: str = "Mock response",
        cost: float = 0.001,
    ):
        super().__init__(
            adapter_name=name,
            tier=AdapterTier.API,
            reliability_score=1.0,
        )
        self.should_fail = should_fail
        self._is_available = is_available
        self.response_content = response_content
        self.cost = cost
        self.call_count = 0

    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        self.call_count += 1

        if self.should_fail:
            self._record_failure()
            return LLMResponse(
                status="error",
                error="Mock failure",
                adapter_name=self.adapter_name,
                latency_ms=100,
            )

        self._record_success(100, self.cost)
        return LLMResponse(
            status="success",
            content=self.response_content,
            cost_usd=self.cost,
            latency_ms=100,
            adapter_name=self.adapter_name,
            model_used="mock-model",
            tokens_input=50,
            tokens_output=100,
        )

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        return self.execute(prompt, context)

    def estimate_cost(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        return self.cost

    def check_availability(self) -> bool:
        return self._is_available

    def get_metadata(self) -> Dict[str, Any]:
        return {"name": self.adapter_name, "available": self._is_available}


class TestLLMFallbackChain:
    """Test suite for LLMFallbackChain."""

    def test_chain_initialization_with_adapters(self):
        """Test chain initializes with provided adapters."""
        adapters = [
            MockAdapter("Primary"),
            MockAdapter("Secondary"),
        ]
        chain = LLMFallbackChain(adapters=adapters)

        assert len(chain.adapters) == 2
        assert chain.adapters[0].adapter_name == "Primary"
        assert chain.adapters[1].adapter_name == "Secondary"

    def test_chain_executes_primary_on_success(self):
        """Test chain uses primary adapter when it succeeds."""
        primary = MockAdapter("Primary", response_content="Primary response")
        secondary = MockAdapter("Secondary", response_content="Secondary response")
        chain = LLMFallbackChain(adapters=[primary, secondary])

        response = chain.execute("Test prompt")

        assert response.is_success
        assert response.content == "Primary response"
        assert response.adapter_name == "Primary"
        assert primary.call_count == 1
        assert secondary.call_count == 0

    def test_chain_falls_back_on_primary_failure(self):
        """Test chain falls back to secondary when primary fails."""
        primary = MockAdapter("Primary", should_fail=True)
        secondary = MockAdapter("Secondary", response_content="Secondary response")
        chain = LLMFallbackChain(adapters=[primary, secondary])

        response = chain.execute("Test prompt")

        assert response.is_success
        assert response.content == "Secondary response"
        assert response.adapter_name == "Secondary"
        assert primary.call_count == 1
        assert secondary.call_count == 1
        assert response.metadata.get("fallback_attempts") == 1

    def test_chain_falls_back_on_unavailable_adapter(self):
        """Test chain skips unavailable adapters."""
        primary = MockAdapter("Primary", is_available=False)
        secondary = MockAdapter("Secondary", response_content="Secondary response")
        chain = LLMFallbackChain(adapters=[primary, secondary])

        response = chain.execute("Test prompt")

        assert response.is_success
        assert response.adapter_name == "Secondary"
        assert primary.call_count == 0  # Never called because unavailable

    def test_chain_raises_when_all_fail(self):
        """Test chain raises AllAdaptersFailedError when all adapters fail."""
        adapters = [
            MockAdapter("Primary", should_fail=True),
            MockAdapter("Secondary", should_fail=True),
        ]
        chain = LLMFallbackChain(adapters=adapters)

        with pytest.raises(AllAdaptersFailedError) as exc_info:
            chain.execute("Test prompt")

        assert "Primary" in exc_info.value.failed_adapters
        assert "Secondary" in exc_info.value.failed_adapters

    def test_chain_metrics_tracking(self):
        """Test chain tracks metrics correctly."""
        primary = MockAdapter("Primary", cost=0.001)
        secondary = MockAdapter("Secondary", cost=0.002)
        chain = LLMFallbackChain(adapters=[primary, secondary])

        # Execute multiple requests
        chain.execute("Prompt 1")
        chain.execute("Prompt 2")

        metrics = chain.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["successful_requests"] == 2
        assert metrics["adapter_usage"]["Primary"] == 2
        assert metrics["total_cost_usd"] == 0.002  # 2 * 0.001

    def test_chain_tracks_fallback_triggers(self):
        """Test chain tracks fallback triggers."""
        primary = MockAdapter("Primary", should_fail=True)
        secondary = MockAdapter("Secondary")
        chain = LLMFallbackChain(adapters=[primary, secondary])

        chain.execute("Test")

        metrics = chain.get_metrics()
        assert metrics["fallback_triggers"] == 1

    def test_chain_add_adapter(self):
        """Test adding adapter to chain."""
        chain = LLMFallbackChain(adapters=[MockAdapter("Primary")])
        chain.add_adapter(MockAdapter("Secondary"))

        assert len(chain.adapters) == 2
        assert chain.adapters[1].adapter_name == "Secondary"

    def test_chain_add_adapter_at_position(self):
        """Test adding adapter at specific position."""
        chain = LLMFallbackChain(adapters=[MockAdapter("First"), MockAdapter("Third")])
        chain.add_adapter(MockAdapter("Second"), position=1)

        assert len(chain.adapters) == 3
        assert chain.adapters[1].adapter_name == "Second"

    def test_chain_remove_adapter(self):
        """Test removing adapter from chain."""
        chain = LLMFallbackChain(
            adapters=[MockAdapter("Primary"), MockAdapter("Secondary")]
        )
        removed = chain.remove_adapter("Primary")

        assert removed is True
        assert len(chain.adapters) == 1
        assert chain.adapters[0].adapter_name == "Secondary"

    def test_chain_remove_nonexistent_adapter(self):
        """Test removing adapter that doesn't exist."""
        chain = LLMFallbackChain(adapters=[MockAdapter("Primary")])
        removed = chain.remove_adapter("NonExistent")

        assert removed is False
        assert len(chain.adapters) == 1

    def test_chain_get_healthy_adapters(self):
        """Test getting list of healthy adapters."""
        adapters = [
            MockAdapter("Healthy1"),
            MockAdapter("Unhealthy", is_available=False),
            MockAdapter("Healthy2"),
        ]
        chain = LLMFallbackChain(adapters=adapters)

        healthy = chain.get_healthy_adapters()

        assert len(healthy) == 2
        assert all(a.adapter_name in ["Healthy1", "Healthy2"] for a in healthy)

    def test_chain_estimate_cost(self):
        """Test cost estimation uses primary adapter."""
        primary = MockAdapter("Primary", cost=0.01)
        secondary = MockAdapter("Secondary", cost=0.02)
        chain = LLMFallbackChain(adapters=[primary, secondary])

        cost = chain.estimate_cost("Test prompt")

        assert cost == 0.01

    def test_chain_reset_metrics(self):
        """Test metrics reset."""
        chain = LLMFallbackChain(adapters=[MockAdapter("Primary")])
        chain.execute("Test")
        chain.reset_metrics()

        metrics = chain.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0

    @pytest.mark.asyncio
    async def test_chain_async_execution(self):
        """Test async execution."""
        primary = MockAdapter("Primary", response_content="Async response")
        chain = LLMFallbackChain(adapters=[primary])

        response = await chain.execute_async("Test prompt")

        assert response.is_success
        assert response.content == "Async response"

    @pytest.mark.asyncio
    async def test_chain_async_fallback(self):
        """Test async execution with fallback."""
        primary = MockAdapter("Primary", should_fail=True)
        secondary = MockAdapter("Secondary", response_content="Fallback response")
        chain = LLMFallbackChain(adapters=[primary, secondary])

        response = await chain.execute_async("Test prompt")

        assert response.is_success
        assert response.content == "Fallback response"
        assert response.metadata.get("fallback_attempts") == 1


class TestChainFactories:
    """Test factory functions for creating chains."""

    def test_create_default_chain(self):
        """Test default chain creation."""
        # Skip if packages not installed
        try:
            chain = create_default_chain()
            assert len(chain.adapters) == 3
        except ImportError:
            pytest.skip("Required packages not installed")

    def test_create_cost_optimized_chain(self):
        """Test cost-optimized chain creation."""
        try:
            chain = create_cost_optimized_chain()
            assert len(chain.adapters) == 3
            # First adapter should be Ollama (free)
            assert "Ollama" in chain.adapters[0].adapter_name
        except ImportError:
            pytest.skip("Required packages not installed")

    def test_create_quality_chain(self):
        """Test quality-focused chain creation."""
        try:
            chain = create_quality_chain()
            assert len(chain.adapters) == 3
        except ImportError:
            pytest.skip("Required packages not installed")
