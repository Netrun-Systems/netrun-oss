"""
Netrun LLM - Three-Tier Cognition System

Implements tiered response generation for optimal latency:
    - Fast Ack (<100ms): Quick acknowledgment using local/cached responses
    - RAG Response (<2s): Knowledge-enhanced response using retrieval
    - Deep Insight (<5s): Full LLM reasoning for complex queries

This pattern enables:
    - Immediate user feedback while full response processes
    - Progressive enhancement of responses
    - Graceful degradation under load
    - Optimal UX for chat/assistant interfaces

Example:
    >>> cognition = ThreeTierCognition()
    >>> async for tier_response in cognition.stream_response("Explain quantum computing"):
    ...     print(f"[{tier_response.tier.name}] {tier_response.content}")

Timing Targets:
    - FAST_ACK: <100ms (cached/template responses)
    - RAG: <2000ms (retrieval-augmented generation)
    - DEEP: <5000ms (full LLM reasoning)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Dict,
    Any,
    Optional,
    List,
    AsyncGenerator,
    Callable,
    Awaitable,
    Union,
)

from netrun.llm.adapters.base import BaseLLMAdapter, LLMResponse
from netrun.llm.chain import LLMFallbackChain
from netrun.llm.exceptions import CognitionTimeoutError


logger = logging.getLogger(__name__)


class CognitionTier(Enum):
    """
    Cognition tier levels with target latencies.

    FAST_ACK: Immediate acknowledgment (<100ms)
        - Pre-computed responses
        - Template matching
        - Intent classification only

    RAG: Retrieval-augmented response (<2s)
        - Vector search + local model
        - Cached knowledge lookup
        - Context injection

    DEEP: Full LLM reasoning (<5s)
        - Complete chain execution
        - Complex reasoning
        - Multi-step analysis
    """

    FAST_ACK = auto()  # <100ms
    RAG = auto()  # <2000ms
    DEEP = auto()  # <5000ms


# Target latencies in milliseconds
TIER_LATENCY_TARGETS = {
    CognitionTier.FAST_ACK: 100,
    CognitionTier.RAG: 2000,
    CognitionTier.DEEP: 5000,
}


@dataclass
class TierResponse:
    """
    Response from a cognition tier.

    Attributes:
        tier: Which tier generated this response
        content: Response content
        latency_ms: Actual latency in milliseconds
        is_final: Whether this is the final response
        confidence: Confidence score (0.0-1.0)
        metadata: Additional tier-specific metadata
    """

    tier: CognitionTier
    content: str
    latency_ms: int
    is_final: bool = False
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def met_target(self) -> bool:
        """Check if response met tier's latency target."""
        target = TIER_LATENCY_TARGETS.get(self.tier, 5000)
        return self.latency_ms <= target


@dataclass
class CognitionMetrics:
    """Metrics tracking for three-tier cognition system."""

    total_requests: int = 0
    fast_ack_count: int = 0
    rag_count: int = 0
    deep_count: int = 0
    fast_ack_avg_latency: float = 0.0
    rag_avg_latency: float = 0.0
    deep_avg_latency: float = 0.0
    tier_success_rate: Dict[CognitionTier, float] = field(default_factory=dict)


# Type alias for RAG retrieval function
RAGRetrievalFunc = Callable[[str], Awaitable[List[str]]]


class ThreeTierCognition:
    """
    Three-Tier Cognition System for optimal response latency.

    Implements progressive response generation:
    1. Fast Ack (<100ms): Immediate acknowledgment
    2. RAG Response (<2s): Knowledge-enhanced response
    3. Deep Insight (<5s): Full LLM reasoning

    The system can operate in streaming mode (yield responses as available)
    or blocking mode (return best response within timeout).

    Example (Streaming):
        >>> cognition = ThreeTierCognition()
        >>> async for response in cognition.stream_response("What is AI?"):
        ...     if response.tier == CognitionTier.FAST_ACK:
        ...         print(f"[Thinking...] {response.content}")
        ...     elif response.tier == CognitionTier.DEEP:
        ...         print(f"[Answer] {response.content}")

    Example (Blocking):
        >>> cognition = ThreeTierCognition()
        >>> response = await cognition.execute("Explain machine learning")
        >>> print(response.content)  # Best response within timeout
    """

    def __init__(
        self,
        llm_chain: Optional[LLMFallbackChain] = None,
        fast_ack_templates: Optional[Dict[str, str]] = None,
        rag_retrieval: Optional[RAGRetrievalFunc] = None,
        rag_adapter: Optional[BaseLLMAdapter] = None,
        enable_fast_ack: bool = True,
        enable_rag: bool = True,
        fast_ack_timeout_ms: int = 100,
        rag_timeout_ms: int = 2000,
        deep_timeout_ms: int = 5000,
    ):
        """
        Initialize Three-Tier Cognition System.

        Args:
            llm_chain: LLM fallback chain for deep reasoning (creates default if None)
            fast_ack_templates: Template responses for fast acknowledgment
            rag_retrieval: Async function for RAG document retrieval
            rag_adapter: Adapter for RAG tier (defaults to Ollama for speed)
            enable_fast_ack: Enable fast acknowledgment tier
            enable_rag: Enable RAG tier
            fast_ack_timeout_ms: Timeout for fast ack tier
            rag_timeout_ms: Timeout for RAG tier
            deep_timeout_ms: Timeout for deep tier
        """
        # LLM chain for deep reasoning
        self.llm_chain = llm_chain or LLMFallbackChain()

        # Fast ack configuration
        self.enable_fast_ack = enable_fast_ack
        self.fast_ack_timeout_ms = fast_ack_timeout_ms
        self.fast_ack_templates = fast_ack_templates or self._default_templates()

        # RAG configuration
        self.enable_rag = enable_rag
        self.rag_timeout_ms = rag_timeout_ms
        self.rag_retrieval = rag_retrieval
        self.rag_adapter = rag_adapter

        # Deep tier configuration
        self.deep_timeout_ms = deep_timeout_ms

        # Metrics tracking
        self.metrics = CognitionMetrics()

        logger.info(
            f"ThreeTierCognition initialized: "
            f"fast_ack={enable_fast_ack}, rag={enable_rag}, "
            f"timeouts=({fast_ack_timeout_ms}, {rag_timeout_ms}, {deep_timeout_ms})ms"
        )

    def _default_templates(self) -> Dict[str, str]:
        """Default fast ack templates based on intent patterns."""
        return {
            "greeting": "Hello! How can I help you today?",
            "thanks": "You're welcome! Let me know if you need anything else.",
            "help": "I'd be happy to help. Let me think about that...",
            "question": "Good question! Let me find the best answer for you...",
            "code": "I'll analyze that code for you. One moment...",
            "explain": "Let me break that down for you...",
            "default": "Let me think about that for a moment...",
        }

    async def stream_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[TierResponse, None]:
        """
        Stream responses through all tiers as they become available.

        Yields responses progressively:
        1. Fast ack immediately (<100ms)
        2. RAG response when ready (<2s)
        3. Deep response when ready (<5s)

        Args:
            prompt: User prompt/query
            context: Optional execution context

        Yields:
            TierResponse objects as each tier completes
        """
        self.metrics.total_requests += 1
        context = context or {}

        # Tier 1: Fast Acknowledgment
        if self.enable_fast_ack:
            start = time.time()
            try:
                fast_response = await asyncio.wait_for(
                    self._generate_fast_ack(prompt, context),
                    timeout=self.fast_ack_timeout_ms / 1000,
                )
                latency_ms = int((time.time() - start) * 1000)

                self.metrics.fast_ack_count += 1

                yield TierResponse(
                    tier=CognitionTier.FAST_ACK,
                    content=fast_response,
                    latency_ms=latency_ms,
                    is_final=False,
                    confidence=0.3,  # Low confidence - just acknowledgment
                    metadata={"intent": self._detect_intent(prompt)},
                )
            except asyncio.TimeoutError:
                logger.debug("Fast ack tier timed out")
            except Exception as e:
                logger.warning(f"Fast ack tier failed: {e}")

        # Tier 2: RAG Response
        if self.enable_rag and self.rag_retrieval:
            start = time.time()
            try:
                rag_response = await asyncio.wait_for(
                    self._generate_rag_response(prompt, context),
                    timeout=self.rag_timeout_ms / 1000,
                )
                latency_ms = int((time.time() - start) * 1000)

                if rag_response:
                    self.metrics.rag_count += 1

                    yield TierResponse(
                        tier=CognitionTier.RAG,
                        content=rag_response,
                        latency_ms=latency_ms,
                        is_final=False,
                        confidence=0.7,  # Medium confidence - has context
                        metadata={"rag_enhanced": True},
                    )
            except asyncio.TimeoutError:
                logger.debug("RAG tier timed out")
            except Exception as e:
                logger.warning(f"RAG tier failed: {e}")

        # Tier 3: Deep Insight
        start = time.time()
        try:
            deep_response = await asyncio.wait_for(
                self._generate_deep_response(prompt, context),
                timeout=self.deep_timeout_ms / 1000,
            )
            latency_ms = int((time.time() - start) * 1000)

            self.metrics.deep_count += 1

            yield TierResponse(
                tier=CognitionTier.DEEP,
                content=deep_response.content or "",
                latency_ms=latency_ms,
                is_final=True,
                confidence=1.0,  # High confidence - full reasoning
                metadata={
                    "adapter": deep_response.adapter_name,
                    "model": deep_response.model_used,
                    "cost_usd": deep_response.cost_usd,
                    "tokens": deep_response.total_tokens,
                },
            )
        except asyncio.TimeoutError:
            logger.warning("Deep tier timed out")
            yield TierResponse(
                tier=CognitionTier.DEEP,
                content="I apologize, but I wasn't able to generate a complete response in time. Please try again or rephrase your question.",
                latency_ms=self.deep_timeout_ms,
                is_final=True,
                confidence=0.1,
                metadata={"timeout": True},
            )
        except Exception as e:
            logger.error(f"Deep tier failed: {e}")
            yield TierResponse(
                tier=CognitionTier.DEEP,
                content=f"An error occurred while processing your request: {str(e)}",
                latency_ms=int((time.time() - start) * 1000),
                is_final=True,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    async def execute(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.5,
    ) -> TierResponse:
        """
        Execute and return best response within timeout.

        Runs all tiers and returns the highest confidence response
        that meets minimum confidence threshold.

        Args:
            prompt: User prompt/query
            context: Optional execution context
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            Best TierResponse meeting confidence threshold
        """
        responses: List[TierResponse] = []

        async for response in self.stream_response(prompt, context):
            responses.append(response)

        # Filter by minimum confidence
        valid_responses = [r for r in responses if r.confidence >= min_confidence]

        if not valid_responses:
            # Return last response even if below threshold
            return responses[-1] if responses else TierResponse(
                tier=CognitionTier.DEEP,
                content="Unable to generate response",
                latency_ms=0,
                is_final=True,
                confidence=0.0,
            )

        # Return highest confidence response
        return max(valid_responses, key=lambda r: r.confidence)

    async def execute_sync(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TierResponse:
        """
        Execute synchronously (blocking) - returns final response only.

        Skips intermediate tiers and returns only the deep response.
        Useful when you don't need streaming/progressive updates.

        Args:
            prompt: User prompt/query
            context: Optional execution context

        Returns:
            Final TierResponse from deep tier
        """
        start = time.time()

        try:
            response = await asyncio.wait_for(
                self._generate_deep_response(prompt, context),
                timeout=self.deep_timeout_ms / 1000,
            )
            latency_ms = int((time.time() - start) * 1000)

            return TierResponse(
                tier=CognitionTier.DEEP,
                content=response.content or "",
                latency_ms=latency_ms,
                is_final=True,
                confidence=1.0,
                metadata={
                    "adapter": response.adapter_name,
                    "model": response.model_used,
                    "cost_usd": response.cost_usd,
                },
            )

        except asyncio.TimeoutError:
            raise CognitionTimeoutError(
                message="Deep cognition tier timed out",
                tier_name="DEEP",
                target_latency_ms=self.deep_timeout_ms,
                actual_latency_ms=int((time.time() - start) * 1000),
            )

    async def _generate_fast_ack(
        self, prompt: str, context: Dict[str, Any]
    ) -> str:
        """Generate fast acknowledgment response."""
        intent = self._detect_intent(prompt)
        return self.fast_ack_templates.get(
            intent, self.fast_ack_templates.get("default", "Processing...")
        )

    def _detect_intent(self, prompt: str) -> str:
        """Simple intent detection for fast ack templates."""
        prompt_lower = prompt.lower().strip()
        words = set(prompt_lower.split())

        # Code patterns - check first (more specific)
        if any(w in prompt_lower for w in ["code", "function", "class", "bug", "error"]):
            return "code"

        # Greeting patterns - use word boundaries to avoid false matches
        greeting_words = {"hello", "hi", "hey"}
        if words & greeting_words or "good morning" in prompt_lower:
            return "greeting"

        # Thanks patterns
        if any(w in prompt_lower for w in ["thank", "thanks", "appreciate"]):
            return "thanks"

        # Help patterns
        if any(w in prompt_lower for w in ["help", "assist", "support"]):
            return "help"

        # Explanation patterns
        if any(w in prompt_lower for w in ["explain", "what is", "how does", "why"]):
            return "explain"

        # Question patterns
        if prompt_lower.endswith("?"):
            return "question"

        return "default"

    async def _generate_rag_response(
        self, prompt: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate RAG-enhanced response."""
        if not self.rag_retrieval:
            return None

        # Retrieve relevant documents
        documents = await self.rag_retrieval(prompt)

        if not documents:
            return None

        # Build context from retrieved documents
        rag_context = "\n".join(documents[:3])  # Top 3 documents

        # Use RAG adapter or fast local model
        adapter = self.rag_adapter
        if not adapter:
            # Try to use Ollama for fast local RAG
            try:
                from netrun.llm.adapters.ollama import OllamaAdapter

                adapter = OllamaAdapter()
                if not adapter.check_availability():
                    return None
            except Exception:
                return None

        # Generate response with context
        rag_prompt = f"""Based on the following context, answer the question.

Context:
{rag_context}

Question: {prompt}

Answer:"""

        response = await adapter.execute_async(
            rag_prompt, {"max_tokens": 512, "temperature": 0.7}
        )

        return response.content if response.is_success else None

    async def _generate_deep_response(
        self, prompt: str, context: Dict[str, Any]
    ) -> LLMResponse:
        """Generate deep response using full LLM chain."""
        return await self.llm_chain.execute_async(prompt, context)

    def get_metrics(self) -> Dict[str, Any]:
        """Get cognition system metrics."""
        return {
            "total_requests": self.metrics.total_requests,
            "fast_ack_count": self.metrics.fast_ack_count,
            "rag_count": self.metrics.rag_count,
            "deep_count": self.metrics.deep_count,
            "tier_distribution": {
                "fast_ack": (
                    self.metrics.fast_ack_count / max(self.metrics.total_requests, 1)
                )
                * 100,
                "rag": (self.metrics.rag_count / max(self.metrics.total_requests, 1))
                * 100,
                "deep": (self.metrics.deep_count / max(self.metrics.total_requests, 1))
                * 100,
            },
            "timeouts": {
                "fast_ack_ms": self.fast_ack_timeout_ms,
                "rag_ms": self.rag_timeout_ms,
                "deep_ms": self.deep_timeout_ms,
            },
            "enabled_tiers": {
                "fast_ack": self.enable_fast_ack,
                "rag": self.enable_rag,
            },
        }

    def reset_metrics(self) -> None:
        """Reset cognition metrics."""
        self.metrics = CognitionMetrics()
        self.llm_chain.reset_metrics()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ThreeTierCognition("
            f"fast_ack={self.enable_fast_ack}, "
            f"rag={self.enable_rag}, "
            f"timeouts=({self.fast_ack_timeout_ms}, {self.rag_timeout_ms}, {self.deep_timeout_ms})ms"
            f")"
        )
