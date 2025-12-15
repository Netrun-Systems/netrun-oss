"""
Netrun LLM - Claude (Anthropic) Adapter

Tier 1 (API) integration with Anthropic's Claude AI service.
Supports Claude Sonnet 4.5, Claude 3.5 Sonnet, Claude 3 Opus, and more.

Pricing (per million tokens, 2025):
    - Sonnet 4.5/3.5: $3 input / $15 output
    - Opus 3: $15 input / $75 output
    - Sonnet 3: $3 input / $15 output

Environment Variables:
    ANTHROPIC_API_KEY: Your Anthropic API key
    CLAUDE_DEFAULT_MODEL: Default model (claude-sonnet-4-5-20250929)
    CLAUDE_MAX_TOKENS: Default max tokens (4096)
    CLAUDE_BASE_URL: Custom base URL (optional, for Azure Foundry)
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional

from netrun_llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun_llm.exceptions import (
    RateLimitError,
    AuthenticationError,
    AdapterUnavailableError,
)


# Pricing constants (USD per million tokens, 2025)
CLAUDE_PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 4096


class ClaudeAdapter(BaseLLMAdapter):
    """
    Anthropic Claude API adapter with circuit breaker protection.

    Features:
        - Tier 1 (API) reliability (highest)
        - Support for Claude 4.5 Sonnet, 3.5 Sonnet, 3 Opus, and more
        - Circuit breaker protection
        - Automatic retry with exponential backoff
        - Cost tracking and estimation
        - Async and sync execution support

    Example:
        >>> adapter = ClaudeAdapter()
        >>> response = adapter.execute("Explain quantum computing in 3 sentences")
        >>> print(response.content)
        >>> print(f"Cost: ${response.cost_usd:.6f}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize Claude adapter.

        Args:
            api_key: Anthropic API key (defaults to {{ANTHROPIC_API_KEY}} placeholder)
            default_model: Default model to use
            max_tokens: Default max tokens for responses
            base_url: Custom base URL (for Azure Foundry)
            **kwargs: Additional arguments passed to BaseLLMAdapter
        """
        super().__init__(
            adapter_name="Claude-Anthropic",
            tier=AdapterTier.API,
            reliability_score=1.0,
            **kwargs,
        )

        # API key (resolve placeholder from environment)
        self._api_key_placeholder = api_key or "{{ANTHROPIC_API_KEY}}"
        self._api_key: Optional[str] = None

        # Configuration
        self.default_model = default_model or os.getenv(
            "CLAUDE_DEFAULT_MODEL", DEFAULT_MODEL
        )
        self.max_tokens = max_tokens or int(
            os.getenv("CLAUDE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        )
        self.base_url = base_url or os.getenv("CLAUDE_BASE_URL")

        # Anthropic client (lazy initialization)
        self._client = None

    def _get_api_key(self) -> Optional[str]:
        """Resolve API key from placeholder or environment."""
        if self._api_key is None:
            if self._api_key_placeholder.startswith("{{"):
                # Extract variable name from {{VARIABLE_NAME}}
                var_name = self._api_key_placeholder[2:-2]
                self._api_key = os.getenv(var_name)
            else:
                self._api_key = self._api_key_placeholder
        return self._api_key

    def _get_client(self):
        """Get or create Anthropic client (lazy initialization)."""
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )

            api_key = self._get_api_key()
            if not api_key:
                raise AdapterUnavailableError(
                    message="Anthropic API key not configured",
                    adapter_name=self.adapter_name,
                    reason="Set ANTHROPIC_API_KEY environment variable",
                )

            client_kwargs = {"api_key": api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            self._client = Anthropic(**client_kwargs)

        return self._client

    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt using Claude API (synchronous).

        Args:
            prompt: The prompt/instruction to send to Claude
            context: Optional context with parameters:
                - model (str): Override default model
                - max_tokens (int): Override default max tokens
                - temperature (float): Sampling temperature (0.0-1.0)
                - system (str): System prompt for context

        Returns:
            LLMResponse with status, content, cost, latency
        """
        # Check circuit breaker
        if self._check_circuit_breaker():
            return self._create_error_response(
                error="Circuit breaker open. Service unavailable for cooldown period.",
                status="error",
            )

        # Extract context parameters
        context = context or {}
        model = context.get("model", self.default_model)
        max_tokens = context.get("max_tokens", self.max_tokens)
        temperature = context.get("temperature", 1.0)
        system_prompt = context.get("system")

        start_time = time.time()

        try:
            client = self._get_client()

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Prepare API request
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                request_params["system"] = system_prompt

            # Make API request
            response = client.messages.create(**request_params)

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response
            content = response.content[0].text
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens

            # Calculate cost
            cost_usd = self._calculate_cost(model, tokens_input, tokens_output)

            # Record success
            self._record_success(latency_ms, cost_usd)

            return LLMResponse(
                status="success",
                content=content,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                adapter_name=self.adapter_name,
                model_used=model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                metadata={
                    "stop_reason": response.stop_reason,
                    "model_version": response.model,
                },
            )

        except ImportError as e:
            return self._create_error_response(
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            self._record_failure()
            latency_ms = int((time.time() - start_time) * 1000)

            # Check for specific error types
            error_str = str(e).lower()
            if "rate" in error_str and "limit" in error_str:
                return LLMResponse(
                    status="rate_limited",
                    error=str(e),
                    adapter_name=self.adapter_name,
                    model_used=model,
                    latency_ms=latency_ms,
                )
            elif "auth" in error_str or "401" in error_str:
                return LLMResponse(
                    status="error",
                    error=f"Authentication failed: {e}",
                    adapter_name=self.adapter_name,
                    model_used=model,
                    latency_ms=latency_ms,
                )

            return self._create_error_response(
                error=str(e),
                model=model,
                latency_ms=latency_ms,
            )

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt using Claude API (asynchronous).

        For true async, use anthropic's AsyncAnthropic client.
        This implementation wraps sync execution in executor for compatibility.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, prompt, context)

    def estimate_cost(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Estimate cost (in USD) before executing prompt.

        Uses heuristic: 1 token ~= 4 characters for English text.
        """
        context = context or {}
        model = context.get("model", self.default_model)
        max_tokens = context.get("max_tokens", self.max_tokens)

        # Estimate tokens
        estimated_input = len(prompt) / 4
        estimated_output = max_tokens  # Assume full output

        return self._calculate_cost(model, estimated_input, estimated_output)

    def check_availability(self) -> bool:
        """Check if Claude API is available and healthy."""
        if not self.is_healthy():
            return False

        # Check if API key is configured
        api_key = self._get_api_key()
        return bool(api_key)

    def get_metadata(self) -> Dict[str, Any]:
        """Return adapter configuration and status."""
        return {
            "name": self.adapter_name,
            "tier": self.tier.name,
            "tier_value": self.tier.value,
            "reliability_score": self.reliability_score,
            "enabled": self.enabled,
            "default_model": self.default_model,
            "max_tokens": self.max_tokens,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self.get_success_rate(),
            "avg_latency_ms": self.get_average_latency(),
            "total_cost_usd": self._total_cost_usd,
            "circuit_breaker_open": self._circuit_breaker_open,
            "consecutive_failures": self._consecutive_failures,
            "supported_models": list(CLAUDE_PRICING.keys()),
            "has_api_key": bool(self._get_api_key()),
        }

    def _calculate_cost(
        self, model: str, input_tokens: float, output_tokens: float
    ) -> float:
        """Calculate cost based on token usage and model pricing."""
        if model not in CLAUDE_PRICING:
            model = DEFAULT_MODEL

        pricing = CLAUDE_PRICING[model]

        # Cost: (tokens / 1,000,000) * price_per_million
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
