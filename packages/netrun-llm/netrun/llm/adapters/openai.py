"""
Netrun LLM - OpenAI Adapter

Tier 1 (API) integration with OpenAI's GPT service.
Supports GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and more.

Pricing (per million tokens, 2025):
    - GPT-4: $30 input / $60 output
    - GPT-4 Turbo: $10 input / $30 output
    - GPT-3.5 Turbo: $0.50 input / $1.50 output

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key
    OPENAI_DEFAULT_MODEL: Default model (gpt-4-turbo)
    OPENAI_MAX_TOKENS: Default max tokens (4096)
    OPENAI_TIMEOUT: Request timeout in seconds (30)
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional

from netrun.llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun.llm.exceptions import AdapterUnavailableError


# Pricing constants (USD per million tokens, 2025)
OPENAI_PRICING = {
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-16k": {"input": 0.50, "output": 1.50},
}

DEFAULT_MODEL = "gpt-4-turbo"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 30


class OpenAIAdapter(BaseLLMAdapter):
    """
    OpenAI GPT API adapter with circuit breaker protection.

    Features:
        - Tier 1 (API) reliability (highest)
        - Support for GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and more
        - Circuit breaker protection
        - Automatic retry with exponential backoff
        - Cost tracking and estimation
        - Async and sync execution support

    Example:
        >>> adapter = OpenAIAdapter()
        >>> response = adapter.execute("Write a Python function to sort a list")
        >>> print(response.content)
        >>> print(f"Cost: ${response.cost_usd:.6f}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key (defaults to {{OPENAI_API_KEY}} placeholder)
            default_model: Default model to use
            max_tokens: Default max tokens for responses
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to BaseLLMAdapter
        """
        super().__init__(
            adapter_name="OpenAI-GPT",
            tier=AdapterTier.API,
            reliability_score=1.0,
            **kwargs,
        )

        # API key (resolve placeholder from environment)
        self._api_key_placeholder = api_key or "{{OPENAI_API_KEY}}"
        self._api_key: Optional[str] = None

        # Configuration
        self.default_model = default_model or os.getenv(
            "OPENAI_DEFAULT_MODEL", DEFAULT_MODEL
        )
        self.max_tokens = max_tokens or int(
            os.getenv("OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        )
        self.timeout = timeout or int(os.getenv("OPENAI_TIMEOUT", str(DEFAULT_TIMEOUT)))

        # OpenAI client (lazy initialization)
        self._client = None

    def _get_api_key(self) -> Optional[str]:
        """Resolve API key from placeholder or environment."""
        if self._api_key is None:
            if self._api_key_placeholder.startswith("{{"):
                var_name = self._api_key_placeholder[2:-2]
                self._api_key = os.getenv(var_name)
            else:
                self._api_key = self._api_key_placeholder
        return self._api_key

    def _get_client(self):
        """Get or create OpenAI client (lazy initialization)."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package not installed. Install with: pip install openai"
                )

            api_key = self._get_api_key()
            if not api_key:
                raise AdapterUnavailableError(
                    message="OpenAI API key not configured",
                    adapter_name=self.adapter_name,
                    reason="Set OPENAI_API_KEY environment variable",
                )

            self._client = OpenAI(api_key=api_key, timeout=self.timeout)

        return self._client

    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt using OpenAI API (synchronous).

        Args:
            prompt: The prompt/instruction to send to GPT
            context: Optional context with parameters:
                - model (str): Override default model
                - max_tokens (int): Override default max tokens
                - temperature (float): Sampling temperature (0.0-2.0)
                - system (str): System prompt for context
                - timeout (int): Override default timeout

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
        system_prompt = context.get("system", "You are a helpful assistant.")
        timeout = context.get("timeout", self.timeout)

        start_time = time.time()

        try:
            client = self._get_client()

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            # Make API request
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response
            content = response.choices[0].message.content
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens

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
                    "finish_reason": response.choices[0].finish_reason,
                    "model_version": response.model,
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
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
            elif "timeout" in error_str:
                return LLMResponse(
                    status="timeout",
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
        Execute prompt using OpenAI API (asynchronous).

        For true async, use openai's AsyncOpenAI client.
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
        system_prompt = context.get("system", "You are a helpful assistant.")

        # Estimate tokens
        estimated_input = (len(prompt) + len(system_prompt)) / 4
        estimated_output = max_tokens

        return self._calculate_cost(model, estimated_input, estimated_output)

    def check_availability(self) -> bool:
        """Check if OpenAI API is available and healthy."""
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
            "timeout": self.timeout,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self.get_success_rate(),
            "avg_latency_ms": self.get_average_latency(),
            "total_cost_usd": self._total_cost_usd,
            "circuit_breaker_open": self._circuit_breaker_open,
            "consecutive_failures": self._consecutive_failures,
            "supported_models": list(OPENAI_PRICING.keys()),
            "has_api_key": bool(self._get_api_key()),
        }

    def _calculate_cost(
        self, model: str, input_tokens: float, output_tokens: float
    ) -> float:
        """Calculate cost based on token usage and model pricing."""
        if model not in OPENAI_PRICING:
            model = DEFAULT_MODEL

        pricing = OPENAI_PRICING[model]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
