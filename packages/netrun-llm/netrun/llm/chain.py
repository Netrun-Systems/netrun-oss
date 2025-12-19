"""
Netrun LLM - Fallback Chain Implementation

Provides automatic failover between multiple LLM providers.
Default chain: Claude -> GPT-4 -> Llama3 (local)

The fallback chain automatically:
    - Routes to primary adapter (Claude for agentic tasks)
    - Falls back to secondary adapter on failure (GPT-4)
    - Falls back to tertiary/local adapter as last resort (Ollama)
    - Tracks metrics across all adapters

v1.1.0: Added netrun-logging integration for structured LLM operation logging

Example:
    >>> chain = LLMFallbackChain()
    >>> response = chain.execute("Analyze this code for bugs")
    >>> print(f"Handled by: {response.adapter_name}")
    >>> print(f"Fallbacks used: {response.metadata.get('fallback_attempts', 0)}")
"""

import logging
from typing import List, Optional, Dict, Any, Type
from dataclasses import dataclass, field

from netrun.llm.adapters.base import BaseLLMAdapter, LLMResponse
from netrun.llm.exceptions import AllAdaptersFailedError

# Optional netrun-logging integration
_use_netrun_logging = False
_logger = None

try:
    from netrun.logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    _logger = logging.getLogger(__name__)


def _log(level: str, message: str, **kwargs) -> None:
    """Log using netrun-logging if available, otherwise standard logging."""
    if _use_netrun_logging:
        log_method = getattr(_logger, level, _logger.info)
        log_method(message, **kwargs)
    else:
        log_method = getattr(_logger, level, _logger.info)
        log_method(f"{message} {kwargs}" if kwargs else message)


# Alias for backward compatibility
logger = _logger


@dataclass
class ChainMetrics:
    """Metrics tracking for fallback chain execution."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_triggers: int = 0
    adapter_usage: Dict[str, int] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    @property
    def fallback_rate(self) -> float:
        """Calculate percentage of requests requiring fallback."""
        if self.total_requests == 0:
            return 0.0
        return (self.fallback_triggers / self.total_requests) * 100.0


class LLMFallbackChain:
    """
    Multi-adapter fallback chain with automatic failover.

    Provides resilient LLM access by chaining multiple adapters
    with automatic failover on failures. Supports:
        - Configurable adapter chain (default: Claude -> GPT-4 -> Ollama)
        - Per-adapter circuit breakers
        - Comprehensive metrics tracking
        - Async and sync execution

    Default Chain:
        1. Claude (Anthropic) - Primary for agentic/complex tasks
        2. OpenAI GPT-4 - Secondary for general tasks
        3. Ollama Llama3 - Fallback for cost-free local execution

    Example:
        >>> from netrun_llm import LLMFallbackChain
        >>>
        >>> # Create default chain (Claude -> GPT-4 -> Ollama)
        >>> chain = LLMFallbackChain()
        >>>
        >>> # Execute with automatic fallback
        >>> response = chain.execute("Explain quantum computing")
        >>> print(response.content)
        >>>
        >>> # Check which adapter handled the request
        >>> print(f"Handled by: {response.adapter_name}")
    """

    def __init__(
        self,
        adapters: Optional[List[BaseLLMAdapter]] = None,
        stop_on_success: bool = True,
        log_fallbacks: bool = True,
    ):
        """
        Initialize fallback chain with adapters.

        Args:
            adapters: Ordered list of adapters (first = primary, last = fallback)
                     If None, creates default chain: Claude -> OpenAI -> Ollama
            stop_on_success: Stop trying adapters after first success (default: True)
            log_fallbacks: Log when fallback is triggered (default: True)
        """
        self.adapters: List[BaseLLMAdapter] = adapters or self._create_default_chain()
        self.stop_on_success = stop_on_success
        self.log_fallbacks = log_fallbacks

        # Metrics tracking
        self.metrics = ChainMetrics()

        # Initialize adapter usage counters
        for adapter in self.adapters:
            self.metrics.adapter_usage[adapter.adapter_name] = 0

        logger.info(
            f"LLMFallbackChain initialized with {len(self.adapters)} adapters: "
            f"{[a.adapter_name for a in self.adapters]}"
        )

    def _create_default_chain(self) -> List[BaseLLMAdapter]:
        """Create default fallback chain: Claude -> OpenAI -> Ollama."""
        from netrun.llm.adapters.claude import ClaudeAdapter
        from netrun.llm.adapters.openai import OpenAIAdapter
        from netrun.llm.adapters.ollama import OllamaAdapter

        return [
            ClaudeAdapter(),
            OpenAIAdapter(),
            OllamaAdapter(),
        ]

    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt with automatic fallback through adapter chain.

        Args:
            prompt: The prompt/instruction to send to LLM
            context: Optional context dictionary with parameters

        Returns:
            LLMResponse from first successful adapter

        Raises:
            AllAdaptersFailedError: If all adapters in chain fail
        """
        self.metrics.total_requests += 1
        errors: Dict[str, str] = {}
        failed_adapters: List[str] = []
        fallback_count = 0

        for i, adapter in enumerate(self.adapters):
            adapter_name = adapter.adapter_name

            # Check if adapter is healthy
            if not adapter.is_healthy():
                error_msg = "Adapter unhealthy (circuit breaker open or disabled)"
                errors[adapter_name] = error_msg

                if self.log_fallbacks and i > 0:
                    logger.warning(
                        f"Fallback triggered: {adapter_name} is unhealthy, "
                        f"trying next adapter"
                    )

                failed_adapters.append(adapter_name)
                continue

            # Check availability
            if not adapter.check_availability():
                error_msg = "Adapter unavailable"
                errors[adapter_name] = error_msg

                if self.log_fallbacks and i > 0:
                    logger.warning(
                        f"Fallback triggered: {adapter_name} is unavailable, "
                        f"trying next adapter"
                    )

                failed_adapters.append(adapter_name)
                continue

            # Attempt execution
            try:
                response = adapter.execute(prompt, context)

                if response.is_success:
                    # Success - update metrics and return
                    self.metrics.successful_requests += 1
                    self.metrics.adapter_usage[adapter_name] = (
                        self.metrics.adapter_usage.get(adapter_name, 0) + 1
                    )
                    self.metrics.total_cost_usd += response.cost_usd
                    self.metrics.total_latency_ms += response.latency_ms

                    if fallback_count > 0:
                        self.metrics.fallback_triggers += 1

                    # Add fallback info to metadata
                    response.metadata["fallback_attempts"] = fallback_count
                    response.metadata["failed_adapters"] = failed_adapters

                    logger.info(
                        f"Request succeeded on {adapter_name} "
                        f"(fallbacks: {fallback_count})"
                    )

                    return response

                else:
                    # Non-success response (rate_limited, error, timeout)
                    errors[adapter_name] = response.error or response.status
                    failed_adapters.append(adapter_name)
                    fallback_count += 1

                    if self.log_fallbacks:
                        logger.warning(
                            f"Fallback triggered: {adapter_name} returned "
                            f"status={response.status}, trying next adapter"
                        )

            except Exception as e:
                errors[adapter_name] = str(e)
                failed_adapters.append(adapter_name)
                fallback_count += 1

                if self.log_fallbacks:
                    logger.warning(
                        f"Fallback triggered: {adapter_name} raised exception: {e}"
                    )

        # All adapters failed
        self.metrics.failed_requests += 1
        self.metrics.fallback_triggers += 1

        logger.error(
            f"All adapters failed. Tried: {', '.join(failed_adapters)}. "
            f"Errors: {errors}"
        )

        raise AllAdaptersFailedError(
            message="All adapters in fallback chain failed",
            failed_adapters=failed_adapters,
            errors=errors,
        )

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt with automatic fallback (asynchronous).

        Args:
            prompt: The prompt/instruction to send to LLM
            context: Optional context dictionary with parameters

        Returns:
            LLMResponse from first successful adapter

        Raises:
            AllAdaptersFailedError: If all adapters in chain fail
        """
        self.metrics.total_requests += 1
        errors: Dict[str, str] = {}
        failed_adapters: List[str] = []
        fallback_count = 0

        for i, adapter in enumerate(self.adapters):
            adapter_name = adapter.adapter_name

            if not adapter.is_healthy() or not adapter.check_availability():
                errors[adapter_name] = "Adapter unavailable or unhealthy"
                failed_adapters.append(adapter_name)
                continue

            try:
                response = await adapter.execute_async(prompt, context)

                if response.is_success:
                    self.metrics.successful_requests += 1
                    self.metrics.adapter_usage[adapter_name] = (
                        self.metrics.adapter_usage.get(adapter_name, 0) + 1
                    )
                    self.metrics.total_cost_usd += response.cost_usd
                    self.metrics.total_latency_ms += response.latency_ms

                    if fallback_count > 0:
                        self.metrics.fallback_triggers += 1

                    response.metadata["fallback_attempts"] = fallback_count
                    response.metadata["failed_adapters"] = failed_adapters

                    return response

                else:
                    errors[adapter_name] = response.error or response.status
                    failed_adapters.append(adapter_name)
                    fallback_count += 1

            except Exception as e:
                errors[adapter_name] = str(e)
                failed_adapters.append(adapter_name)
                fallback_count += 1

        self.metrics.failed_requests += 1
        self.metrics.fallback_triggers += 1

        raise AllAdaptersFailedError(
            message="All adapters in fallback chain failed",
            failed_adapters=failed_adapters,
            errors=errors,
        )

    def add_adapter(self, adapter: BaseLLMAdapter, position: Optional[int] = None) -> None:
        """
        Add adapter to the chain.

        Args:
            adapter: Adapter to add
            position: Position in chain (None = append to end)
        """
        if position is None:
            self.adapters.append(adapter)
        else:
            self.adapters.insert(position, adapter)

        self.metrics.adapter_usage[adapter.adapter_name] = 0
        logger.info(f"Added adapter {adapter.adapter_name} to chain")

    def remove_adapter(self, adapter_name: str) -> bool:
        """
        Remove adapter from chain by name.

        Args:
            adapter_name: Name of adapter to remove

        Returns:
            True if adapter was found and removed
        """
        for i, adapter in enumerate(self.adapters):
            if adapter.adapter_name == adapter_name:
                self.adapters.pop(i)
                logger.info(f"Removed adapter {adapter_name} from chain")
                return True

        return False

    def get_adapter(self, adapter_name: str) -> Optional[BaseLLMAdapter]:
        """Get adapter by name."""
        for adapter in self.adapters:
            if adapter.adapter_name == adapter_name:
                return adapter
        return None

    def get_healthy_adapters(self) -> List[BaseLLMAdapter]:
        """Get list of currently healthy adapters."""
        return [a for a in self.adapters if a.is_healthy() and a.check_availability()]

    def estimate_cost(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Estimate cost using primary adapter's pricing.

        Args:
            prompt: The prompt/instruction
            context: Optional context with parameters

        Returns:
            Estimated cost in USD from primary adapter
        """
        if not self.adapters:
            return 0.0

        return self.adapters[0].estimate_cost(prompt, context)

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive chain metrics."""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "fallback_triggers": self.metrics.fallback_triggers,
            "fallback_rate": self.metrics.fallback_rate,
            "average_latency_ms": self.metrics.average_latency_ms,
            "total_cost_usd": self.metrics.total_cost_usd,
            "adapter_usage": self.metrics.adapter_usage,
            "adapters": [
                {
                    "name": a.adapter_name,
                    "tier": a.tier.name,
                    "healthy": a.is_healthy(),
                    "available": a.check_availability(),
                    "success_rate": a.get_success_rate(),
                }
                for a in self.adapters
            ],
        }

    def reset_metrics(self) -> None:
        """Reset all chain metrics."""
        self.metrics = ChainMetrics()
        for adapter in self.adapters:
            self.metrics.adapter_usage[adapter.adapter_name] = 0
            adapter.reset_metrics()

    def __repr__(self) -> str:
        """String representation for debugging."""
        adapter_names = [a.adapter_name for a in self.adapters]
        return (
            f"LLMFallbackChain("
            f"adapters={adapter_names}, "
            f"success_rate={self.metrics.success_rate:.1f}%"
            f")"
        )


# Convenience factory functions
def create_default_chain() -> LLMFallbackChain:
    """Create default fallback chain: Claude -> OpenAI -> Ollama."""
    return LLMFallbackChain()


def create_cost_optimized_chain() -> LLMFallbackChain:
    """Create cost-optimized chain: Ollama -> GPT-3.5 -> Claude."""
    from netrun.llm.adapters.claude import ClaudeAdapter
    from netrun.llm.adapters.openai import OpenAIAdapter
    from netrun.llm.adapters.ollama import OllamaAdapter

    return LLMFallbackChain(
        adapters=[
            OllamaAdapter(),  # Free local models first
            OpenAIAdapter(default_model="gpt-3.5-turbo"),  # Cheap API
            ClaudeAdapter(),  # Premium as fallback
        ]
    )


def create_quality_chain() -> LLMFallbackChain:
    """Create quality-focused chain: Claude Opus -> GPT-4 -> Claude Sonnet."""
    from netrun.llm.adapters.claude import ClaudeAdapter
    from netrun.llm.adapters.openai import OpenAIAdapter

    return LLMFallbackChain(
        adapters=[
            ClaudeAdapter(default_model="claude-3-opus-20240229"),
            OpenAIAdapter(default_model="gpt-4"),
            ClaudeAdapter(default_model="claude-sonnet-4-5-20250929"),
        ]
    )
