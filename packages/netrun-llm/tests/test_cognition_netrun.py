"""
Tests for ThreeTierCognition using netrun.llm imports.

This test file uses the NEW netrun.llm namespace (not netrun_llm deprecated namespace).
Tests cover tier response generation, streaming, and latency targets.
"""

import pytest
import asyncio
from typing import Dict, Any, Optional

from netrun.llm.cognition import (
    ThreeTierCognition,
    CognitionTier,
    TierResponse,
    TIER_LATENCY_TARGETS,
)
from netrun.llm.chain import LLMFallbackChain
from netrun.llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse


class MockChain:
    """Mock LLMFallbackChain for testing."""

    def __init__(self, response_content: str = "Deep response", delay: float = 0.1):
        self.response_content = response_content
        self.delay = delay
        self.call_count = 0

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return LLMResponse(
            status="success",
            content=self.response_content,
            cost_usd=0.01,
            latency_ms=int(self.delay * 1000),
            adapter_name="MockAdapter",
            model_used="mock-model",
            tokens_input=100,
            tokens_output=200,
        )

    def reset_metrics(self):
        pass


class TestCognitionTierEnum:
    """Test CognitionTier enum."""

    def test_tier_values_exist(self):
        """Test tier values are defined."""
        assert CognitionTier.FAST_ACK is not None
        assert CognitionTier.RAG is not None
        assert CognitionTier.DEEP is not None

    def test_latency_targets_defined(self):
        """Test latency targets exist for all tiers."""
        assert CognitionTier.FAST_ACK in TIER_LATENCY_TARGETS
        assert CognitionTier.RAG in TIER_LATENCY_TARGETS
        assert CognitionTier.DEEP in TIER_LATENCY_TARGETS


class TestTierResponseClass:
    """Test TierResponse dataclass."""

    def test_tier_response_creation(self):
        """Test creating a tier response."""
        response = TierResponse(
            tier=CognitionTier.FAST_ACK,
            content="Quick ack",
            latency_ms=50,
            is_final=False,
            confidence=0.3,
        )

        assert response.tier == CognitionTier.FAST_ACK
        assert response.content == "Quick ack"
        assert response.latency_ms == 50
        assert response.is_final is False
        assert response.confidence == 0.3

    def test_met_target_property(self):
        """Test met_target property."""
        fast_response = TierResponse(
            tier=CognitionTier.FAST_ACK,
            content="Test",
            latency_ms=50,  # Under 100ms target
        )
        assert fast_response.met_target is True

        slow_response = TierResponse(
            tier=CognitionTier.FAST_ACK,
            content="Test",
            latency_ms=150,  # Over 100ms target
        )
        assert slow_response.met_target is False


class TestCognitionBasics:
    """Test basic cognition functionality."""

    @pytest.fixture
    def mock_chain(self):
        """Create mock chain."""
        return MockChain()

    @pytest.fixture
    def cognition(self, mock_chain):
        """Create cognition system."""
        return ThreeTierCognition(
            llm_chain=mock_chain,
            enable_fast_ack=True,
            enable_rag=False,
        )

    def test_initialization(self, cognition):
        """Test cognition system initializes."""
        assert cognition.enable_fast_ack is True
        assert cognition.enable_rag is False

    def test_default_templates_exist(self, cognition):
        """Test default fast ack templates."""
        assert "greeting" in cognition.fast_ack_templates
        assert "help" in cognition.fast_ack_templates
        assert "default" in cognition.fast_ack_templates

    @pytest.mark.asyncio
    async def test_stream_response_yields_tiers(self, cognition):
        """Test streaming yields multiple tier responses."""
        responses = []
        async for response in cognition.stream_response("Test prompt"):
            responses.append(response)

        # Should have at least fast ack and deep
        tiers = [r.tier for r in responses]
        assert CognitionTier.FAST_ACK in tiers
        assert CognitionTier.DEEP in tiers

    @pytest.mark.asyncio
    async def test_execute_returns_best_response(self, cognition):
        """Test execute returns highest confidence response."""
        response = await cognition.execute("Test")

        assert response.tier == CognitionTier.DEEP
        assert response.confidence == 1.0

    def test_intent_detection_greeting(self, cognition):
        """Test intent detection for greetings."""
        assert cognition._detect_intent("Hello there") == "greeting"
        assert cognition._detect_intent("Hi friend") == "greeting"

    def test_intent_detection_code(self, cognition):
        """Test intent detection for code queries."""
        assert cognition._detect_intent("Fix this bug") == "code"
        assert cognition._detect_intent("Write a function for sorting") == "code"

    def test_intent_detection_question(self, cognition):
        """Test intent detection for questions."""
        assert cognition._detect_intent("What is this?") == "explain"

    def test_get_metrics(self, cognition):
        """Test get_metrics returns metrics dict."""
        metrics = cognition.get_metrics()

        assert "total_requests" in metrics
        assert "fast_ack_count" in metrics
        assert "deep_count" in metrics
        assert "tier_distribution" in metrics

    def test_cognition_repr(self, cognition):
        """Test string representation."""
        repr_str = repr(cognition)

        assert "ThreeTierCognition" in repr_str
        assert "fast_ack=True" in repr_str
