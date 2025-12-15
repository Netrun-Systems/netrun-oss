"""
Tests for ThreeTierCognition System.

Tests cover:
    - Tier response generation
    - Latency targets
    - Streaming responses
    - Intent detection
    - Metrics tracking
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List

from netrun_llm.cognition import (
    ThreeTierCognition,
    CognitionTier,
    TierResponse,
    TIER_LATENCY_TARGETS,
)
from netrun_llm.chain import LLMFallbackChain
from netrun_llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse


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


class TestCognitionTier:
    """Test CognitionTier enum."""

    def test_tier_values(self):
        """Test tier enum values exist."""
        assert CognitionTier.FAST_ACK is not None
        assert CognitionTier.RAG is not None
        assert CognitionTier.DEEP is not None

    def test_latency_targets_defined(self):
        """Test latency targets are defined for all tiers."""
        assert CognitionTier.FAST_ACK in TIER_LATENCY_TARGETS
        assert CognitionTier.RAG in TIER_LATENCY_TARGETS
        assert CognitionTier.DEEP in TIER_LATENCY_TARGETS

    def test_latency_target_values(self):
        """Test latency targets have expected values."""
        assert TIER_LATENCY_TARGETS[CognitionTier.FAST_ACK] == 100
        assert TIER_LATENCY_TARGETS[CognitionTier.RAG] == 2000
        assert TIER_LATENCY_TARGETS[CognitionTier.DEEP] == 5000


class TestTierResponse:
    """Test TierResponse dataclass."""

    def test_tier_response_creation(self):
        """Test creating TierResponse."""
        response = TierResponse(
            tier=CognitionTier.FAST_ACK,
            content="Test content",
            latency_ms=50,
            is_final=False,
            confidence=0.3,
        )

        assert response.tier == CognitionTier.FAST_ACK
        assert response.content == "Test content"
        assert response.latency_ms == 50
        assert response.is_final is False
        assert response.confidence == 0.3

    def test_met_target_within_limit(self):
        """Test met_target when within limit."""
        response = TierResponse(
            tier=CognitionTier.FAST_ACK,
            content="Test",
            latency_ms=50,  # Under 100ms target
        )
        assert response.met_target is True

    def test_met_target_exceeds_limit(self):
        """Test met_target when exceeding limit."""
        response = TierResponse(
            tier=CognitionTier.FAST_ACK,
            content="Test",
            latency_ms=150,  # Over 100ms target
        )
        assert response.met_target is False


class TestThreeTierCognition:
    """Test ThreeTierCognition system."""

    @pytest.fixture
    def mock_chain(self):
        """Create mock chain for testing."""
        return MockChain()

    @pytest.fixture
    def cognition(self, mock_chain):
        """Create cognition system with mock chain."""
        return ThreeTierCognition(
            llm_chain=mock_chain,
            enable_fast_ack=True,
            enable_rag=False,  # Disable RAG for simpler testing
            fast_ack_timeout_ms=100,
            rag_timeout_ms=2000,
            deep_timeout_ms=5000,
        )

    def test_initialization(self, cognition):
        """Test cognition system initialization."""
        assert cognition.enable_fast_ack is True
        assert cognition.enable_rag is False
        assert cognition.fast_ack_timeout_ms == 100
        assert cognition.deep_timeout_ms == 5000

    def test_default_templates_exist(self, cognition):
        """Test default fast ack templates are created."""
        assert "greeting" in cognition.fast_ack_templates
        assert "help" in cognition.fast_ack_templates
        assert "code" in cognition.fast_ack_templates
        assert "default" in cognition.fast_ack_templates

    @pytest.mark.asyncio
    async def test_stream_response_yields_fast_ack(self, cognition):
        """Test stream_response yields fast ack tier."""
        responses = []
        async for response in cognition.stream_response("Hello"):
            responses.append(response)

        # Should have fast ack and deep response
        tiers = [r.tier for r in responses]
        assert CognitionTier.FAST_ACK in tiers
        assert CognitionTier.DEEP in tiers

    @pytest.mark.asyncio
    async def test_stream_response_fast_ack_not_final(self, cognition):
        """Test fast ack is marked as not final."""
        async for response in cognition.stream_response("Test"):
            if response.tier == CognitionTier.FAST_ACK:
                assert response.is_final is False
                break

    @pytest.mark.asyncio
    async def test_stream_response_deep_is_final(self, cognition):
        """Test deep response is marked as final."""
        responses = []
        async for response in cognition.stream_response("Test"):
            responses.append(response)

        deep_responses = [r for r in responses if r.tier == CognitionTier.DEEP]
        assert len(deep_responses) == 1
        assert deep_responses[0].is_final is True

    @pytest.mark.asyncio
    async def test_execute_returns_best_response(self, cognition):
        """Test execute returns highest confidence response."""
        response = await cognition.execute("Test prompt")

        # Should return deep response (highest confidence)
        assert response.tier == CognitionTier.DEEP
        assert response.confidence == 1.0

    @pytest.mark.asyncio
    async def test_execute_with_min_confidence(self, cognition):
        """Test execute respects min_confidence threshold."""
        response = await cognition.execute("Test", min_confidence=0.9)

        # Only deep tier meets 0.9 threshold
        assert response.tier == CognitionTier.DEEP

    @pytest.mark.asyncio
    async def test_execute_sync_skips_intermediate_tiers(self, mock_chain):
        """Test execute_sync goes directly to deep tier."""
        cognition = ThreeTierCognition(
            llm_chain=mock_chain,
            enable_fast_ack=True,
            enable_rag=False,
        )

        response = await cognition.execute_sync("Test")

        assert response.tier == CognitionTier.DEEP
        assert response.is_final is True

    def test_intent_detection_greeting(self, cognition):
        """Test intent detection for greetings."""
        assert cognition._detect_intent("Hello there!") == "greeting"
        assert cognition._detect_intent("Hi friend") == "greeting"
        assert cognition._detect_intent("hey") == "greeting"

    def test_intent_detection_thanks(self, cognition):
        """Test intent detection for thanks."""
        assert cognition._detect_intent("Thank you!") == "thanks"
        assert cognition._detect_intent("I appreciate your help") == "thanks"

    def test_intent_detection_code(self, cognition):
        """Test intent detection for code-related queries."""
        assert cognition._detect_intent("Fix this bug in my code") == "code"
        assert cognition._detect_intent("Write a function to sort") == "code"

    def test_intent_detection_question(self, cognition):
        """Test intent detection for questions."""
        assert cognition._detect_intent("Is this correct?") == "question"

    def test_intent_detection_default(self, cognition):
        """Test intent detection falls back to default."""
        assert cognition._detect_intent("Random statement here") == "default"

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, cognition):
        """Test metrics are tracked correctly."""
        async for _ in cognition.stream_response("Test"):
            pass

        metrics = cognition.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["fast_ack_count"] == 1
        assert metrics["deep_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_reset(self, cognition):
        """Test metrics can be reset."""
        async for _ in cognition.stream_response("Test"):
            pass

        cognition.reset_metrics()
        metrics = cognition.get_metrics()

        assert metrics["total_requests"] == 0
        assert metrics["fast_ack_count"] == 0

    @pytest.mark.asyncio
    async def test_disabled_fast_ack(self, mock_chain):
        """Test with fast ack disabled."""
        cognition = ThreeTierCognition(
            llm_chain=mock_chain,
            enable_fast_ack=False,
            enable_rag=False,
        )

        responses = []
        async for response in cognition.stream_response("Test"):
            responses.append(response)

        tiers = [r.tier for r in responses]
        assert CognitionTier.FAST_ACK not in tiers
        assert CognitionTier.DEEP in tiers

    @pytest.mark.asyncio
    async def test_deep_timeout_handling(self):
        """Test timeout handling for deep tier."""
        slow_chain = MockChain(delay=10.0)  # Very slow
        cognition = ThreeTierCognition(
            llm_chain=slow_chain,
            enable_fast_ack=False,
            enable_rag=False,
            deep_timeout_ms=100,  # Short timeout
        )

        responses = []
        async for response in cognition.stream_response("Test"):
            responses.append(response)

        # Should get timeout response
        deep_response = [r for r in responses if r.tier == CognitionTier.DEEP][0]
        assert deep_response.metadata.get("timeout") is True
        assert deep_response.confidence < 0.5


class TestCognitionWithRAG:
    """Test cognition system with RAG enabled."""

    @pytest.mark.asyncio
    async def test_rag_integration(self):
        """Test RAG tier when retrieval function provided."""
        mock_chain = MockChain()

        async def mock_retrieval(query: str) -> List[str]:
            return ["Document 1 content", "Document 2 content"]

        # Create a mock RAG adapter
        class MockRAGAdapter(BaseLLMAdapter):
            def __init__(self):
                super().__init__("MockRAG", AdapterTier.LOCAL)

            def execute(self, prompt, context=None):
                return LLMResponse(
                    status="success",
                    content="RAG enhanced response",
                    latency_ms=500,
                    adapter_name="MockRAG",
                )

            async def execute_async(self, prompt, context=None):
                return self.execute(prompt, context)

            def estimate_cost(self, prompt, context=None):
                return 0.0

            def check_availability(self):
                return True

            def get_metadata(self):
                return {}

        cognition = ThreeTierCognition(
            llm_chain=mock_chain,
            enable_fast_ack=True,
            enable_rag=True,
            rag_retrieval=mock_retrieval,
            rag_adapter=MockRAGAdapter(),
        )

        responses = []
        async for response in cognition.stream_response("Test query"):
            responses.append(response)

        tiers = [r.tier for r in responses]
        assert CognitionTier.RAG in tiers

    @pytest.mark.asyncio
    async def test_rag_without_retrieval_function(self):
        """Test RAG tier skipped when no retrieval function."""
        mock_chain = MockChain()
        cognition = ThreeTierCognition(
            llm_chain=mock_chain,
            enable_fast_ack=False,
            enable_rag=True,  # Enabled but no retrieval function
            rag_retrieval=None,
        )

        responses = []
        async for response in cognition.stream_response("Test"):
            responses.append(response)

        tiers = [r.tier for r in responses]
        assert CognitionTier.RAG not in tiers
