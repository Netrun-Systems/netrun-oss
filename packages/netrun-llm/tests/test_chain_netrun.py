"""
Tests for LLMFallbackChain using netrun.llm imports.

This test file uses the NEW netrun.llm namespace (not netrun_llm deprecated namespace).
Tests cover chain execution, fallback logic, and metrics.
"""

import pytest
from unittest.mock import Mock
from typing import Dict, Any, Optional

from netrun.llm.chain import (
    LLMFallbackChain,
    ChainMetrics,
    create_default_chain,
    create_cost_optimized_chain,
    create_quality_chain,
)
from netrun.llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun.llm.exceptions import AllAdaptersFailedError


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


class TestChainBasics:
    """Test basic chain functionality."""

    def test_chain_executes_successfully(self):
        """Test chain executes with single adapter."""
        adapter = MockAdapter("TestAdapter", response_content="Success!")
        chain = LLMFallbackChain(adapters=[adapter])

        response = chain.execute("Test prompt")

        assert response.is_success
        assert response.content == "Success!"

    def test_chain_falls_back_on_failure(self):
        """Test chain falls back to secondary on primary failure."""
        primary = MockAdapter("Primary", should_fail=True)
        secondary = MockAdapter("Secondary", response_content="Fallback success")
        chain = LLMFallbackChain(adapters=[primary, secondary])

        response = chain.execute("Test")

        assert response.is_success
        assert response.adapter_name == "Secondary"

    def test_metrics_are_tracked(self):
        """Test metrics tracking."""
        adapter = MockAdapter("TestAdapter", cost=0.005)
        chain = LLMFallbackChain(adapters=[adapter])

        chain.execute("Test 1")
        chain.execute("Test 2")

        metrics = chain.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["successful_requests"] == 2
        assert metrics["total_cost_usd"] == 0.010


class TestChainMetricsProperties:
    """Test ChainMetrics dataclass properties."""

    def test_success_rate_zero_requests(self):
        """Test success rate with zero requests."""
        metrics = ChainMetrics()
        assert metrics.success_rate == 100.0

    def test_success_rate_with_data(self):
        """Test success rate calculation."""
        metrics = ChainMetrics()
        metrics.total_requests = 10
        metrics.successful_requests = 7
        assert metrics.success_rate == 70.0

    def test_average_latency_zero_requests(self):
        """Test average latency with zero requests."""
        metrics = ChainMetrics()
        assert metrics.average_latency_ms == 0.0

    def test_average_latency_with_data(self):
        """Test average latency calculation."""
        metrics = ChainMetrics()
        metrics.successful_requests = 5
        metrics.total_latency_ms = 1000
        assert metrics.average_latency_ms == 200.0

    def test_fallback_rate_zero_requests(self):
        """Test fallback rate with zero requests."""
        metrics = ChainMetrics()
        assert metrics.fallback_rate == 0.0

    def test_fallback_rate_with_data(self):
        """Test fallback rate calculation."""
        metrics = ChainMetrics()
        metrics.total_requests = 20
        metrics.fallback_triggers = 3
        assert metrics.fallback_rate == 15.0


class TestChainFactoryFunctions:
    """Test factory functions."""

    def test_create_default_chain(self):
        """Test default chain creation."""
        try:
            chain = create_default_chain()
            assert len(chain.adapters) >= 1
        except ImportError:
            pytest.skip("Required packages not installed")

    def test_create_cost_optimized_chain(self):
        """Test cost-optimized chain."""
        try:
            chain = create_cost_optimized_chain()
            assert len(chain.adapters) >= 1
        except ImportError:
            pytest.skip("Required packages not installed")

    def test_create_quality_chain(self):
        """Test quality-focused chain."""
        try:
            chain = create_quality_chain()
            assert len(chain.adapters) >= 1
        except ImportError:
            pytest.skip("Required packages not installed")
