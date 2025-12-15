"""
Netrun LLM - Base Adapter Interface

Abstract base class for all LLM service adapters. Provides consistent interface
for task execution, cost estimation, health monitoring, and circuit breaker protection.

All adapters must implement:
    - execute(): Process task and return result (sync)
    - execute_async(): Process task asynchronously
    - estimate_cost(): Calculate estimated cost before execution
    - check_availability(): Verify service is available and healthy
    - get_metadata(): Return adapter configuration and status
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional
import time


class AdapterTier(Enum):
    """
    Adapter reliability tiers based on integration method.

    API tier has highest reliability (direct HTTP API calls).
    LOCAL tier uses local compute (no network dependency but hardware dependent).
    CLI tier uses command-line interface (moderate reliability).
    GUI tier uses browser automation (lowest reliability).
    """

    API = 1  # Reliability: 1.0 (HTTP API integration)
    LOCAL = 2  # Reliability: 0.9 (Local model execution)
    CLI = 3  # Reliability: 0.7 (Command-line interface)
    GUI = 4  # Reliability: 0.4 (Browser automation)


@dataclass
class LLMResponse:
    """
    Standard response format for all LLM adapters.

    Provides comprehensive tracking of execution results including
    cost, latency, token usage, and metadata for analytics.

    Attributes:
        status: Response status ("success", "error", "timeout", "rate_limited")
        content: Generated text content (None if error)
        cost_usd: Actual or estimated cost in USD
        latency_ms: Execution time in milliseconds
        error: Error message if status != "success"
        adapter_name: Name of adapter that handled request
        model_used: Specific model/version used
        tokens_input: Input tokens consumed
        tokens_output: Output tokens generated
        metadata: Additional adapter-specific metadata
    """

    status: str  # "success", "error", "timeout", "rate_limited"
    content: Optional[str] = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    error: Optional[str] = None
    adapter_name: str = ""
    model_used: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.status == "success"

    @property
    def total_tokens(self) -> int:
        """Get total tokens used (input + output)."""
        return self.tokens_input + self.tokens_output

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for serialization."""
        return {
            "status": self.status,
            "content": self.content,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "adapter_name": self.adapter_name,
            "model_used": self.model_used,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "metadata": self.metadata,
        }


class BaseLLMAdapter(ABC):
    """
    Abstract base class for all LLM service adapters.

    Implements common functionality including:
    - Circuit breaker protection (opens after consecutive failures)
    - Performance metrics tracking (success rate, latency, cost)
    - Health monitoring with automatic recovery

    All adapters must implement the abstract methods to ensure
    consistent behavior across providers.
    """

    def __init__(
        self,
        adapter_name: str,
        tier: AdapterTier,
        reliability_score: float = 1.0,
        enabled: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_cooldown: int = 300,
    ):
        """
        Initialize base adapter with common configuration.

        Args:
            adapter_name: Unique identifier for this adapter
            tier: Reliability tier (API, LOCAL, CLI, GUI)
            reliability_score: Float 0.0-1.0 indicating reliability
            enabled: Whether adapter is active
            circuit_breaker_threshold: Failures before circuit breaker opens
            circuit_breaker_cooldown: Cooldown period in seconds
        """
        self.adapter_name = adapter_name
        self.tier = tier
        self.reliability_score = reliability_score
        self.enabled = enabled

        # Circuit breaker configuration
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_cooldown = circuit_breaker_cooldown

        # Performance tracking
        self._success_count = 0
        self._failure_count = 0
        self._total_latency_ms = 0
        self._total_cost_usd = 0.0

        # Circuit breaker state
        self._last_failure_time: Optional[float] = None
        self._consecutive_failures = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time: Optional[float] = None

    @abstractmethod
    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt using this adapter's LLM service (synchronous).

        Args:
            prompt: The prompt/instruction to send to the LLM
            context: Optional context dictionary with parameters:
                - model (str): Override default model
                - max_tokens (int): Override default max tokens
                - temperature (float): Sampling temperature (0.0-2.0)
                - system (str): System prompt for context

        Returns:
            LLMResponse with status, content, cost, latency, etc.

        Raises:
            NotImplementedError: If subclass doesn't implement
        """
        pass

    @abstractmethod
    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt using this adapter's LLM service (asynchronous).

        Args:
            prompt: The prompt/instruction to send to the LLM
            context: Optional context dictionary with parameters

        Returns:
            LLMResponse with status, content, cost, latency, etc.

        Raises:
            NotImplementedError: If subclass doesn't implement
        """
        pass

    @abstractmethod
    def estimate_cost(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Estimate cost (in USD) before executing prompt.

        Args:
            prompt: The prompt/instruction
            context: Optional context with parameters

        Returns:
            Estimated cost in USD (0.0 for free services)

        Raises:
            NotImplementedError: If subclass doesn't implement
        """
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """
        Check if adapter's service is available and healthy.

        Returns:
            True if service is reachable and operational

        Raises:
            NotImplementedError: If subclass doesn't implement
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Return adapter configuration and current status.

        Returns:
            Dictionary with adapter metadata:
            - name: Adapter name
            - tier: Reliability tier
            - reliability_score: Current reliability
            - enabled: Whether adapter is active
            - success_rate: % successful executions
            - avg_latency_ms: Average latency
            - total_cost_usd: Cumulative cost
            - circuit_breaker_open: Whether circuit breaker is active

        Raises:
            NotImplementedError: If subclass doesn't implement
        """
        pass

    # ========================================
    # Common Helper Methods
    # ========================================

    def _record_success(self, latency_ms: int, cost_usd: float) -> None:
        """Record successful execution for metrics tracking."""
        self._success_count += 1
        self._total_latency_ms += latency_ms
        self._total_cost_usd += cost_usd
        self._consecutive_failures = 0  # Reset failure counter

    def _record_failure(self) -> None:
        """Record failed execution and update circuit breaker state."""
        self._failure_count += 1
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        # Open circuit breaker after threshold failures
        if self._consecutive_failures >= self._circuit_breaker_threshold:
            self._circuit_breaker_open = True
            self._circuit_breaker_open_time = time.time()

    def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker should remain open.

        Returns:
            True if circuit breaker is open (should NOT use adapter)
        """
        if not self._circuit_breaker_open:
            return False

        # Handle case where circuit breaker opened without timestamp
        if self._circuit_breaker_open_time is None:
            self._circuit_breaker_open = False
            self._consecutive_failures = 0
            return False

        # Check if cooldown period has passed
        if time.time() - self._circuit_breaker_open_time > self._circuit_breaker_cooldown:
            # Close circuit breaker, reset counters
            self._circuit_breaker_open = False
            self._consecutive_failures = 0
            self._circuit_breaker_open_time = None
            return False

        return True  # Circuit breaker still open

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self._success_count + self._failure_count
        if total == 0:
            return 100.0  # No data yet, assume healthy
        return (self._success_count / total) * 100.0

    def get_average_latency(self) -> float:
        """Calculate average latency in milliseconds."""
        if self._success_count == 0:
            return 0.0
        return self._total_latency_ms / self._success_count

    def reset_metrics(self) -> None:
        """Reset performance metrics (for testing or periodic reset)."""
        self._success_count = 0
        self._failure_count = 0
        self._total_latency_ms = 0
        self._total_cost_usd = 0.0
        self._consecutive_failures = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time = None

    def is_healthy(self) -> bool:
        """
        Determine if adapter is healthy and should be used.

        Returns:
            True if enabled, available, and not circuit broken
        """
        if not self.enabled:
            return False

        if self._check_circuit_breaker():
            return False

        # Check success rate (unhealthy if <80% with sufficient data)
        if self._success_count + self._failure_count > 10:
            if self.get_success_rate() < 80.0:
                return False

        return True

    def _create_error_response(
        self,
        error: str,
        status: str = "error",
        latency_ms: int = 0,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """Create standardized error response."""
        return LLMResponse(
            status=status,
            error=error,
            adapter_name=self.adapter_name,
            model_used=model,
            latency_ms=latency_ms,
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.adapter_name}, "
            f"tier={self.tier.name}, "
            f"reliability={self.reliability_score}, "
            f"enabled={self.enabled}, "
            f"success_rate={self.get_success_rate():.1f}%"
            f")"
        )
