"""
Netrun LLM - Ollama Adapter

Tier 2 (LOCAL) integration with Ollama for local LLM execution.
Provides free fallback using local compute resources.

Supported Models:
    - llama3 (8B, recommended for general tasks)
    - llama3.1 (8B, improved reasoning)
    - codellama (7B/13B, code generation)
    - mistral (7B, efficient general purpose)
    - phi-3 (3.8B, small but capable)

Environment Variables:
    OLLAMA_HOST: Ollama server host (http://localhost:11434)
    OLLAMA_DEFAULT_MODEL: Default model (llama3)
    OLLAMA_MAX_TOKENS: Default max tokens (2048)
    OLLAMA_TIMEOUT: Request timeout in seconds (60)

Pricing:
    - Cost: $0.00 (local compute, no API charges)
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional, List

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from netrun_llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse


# Known model metadata
KNOWN_MODELS = {
    "llama3": {"size": "8B", "use_case": "general purpose"},
    "llama3.1": {"size": "8B", "use_case": "improved reasoning"},
    "llama3.2": {"size": "3B", "use_case": "fast general purpose"},
    "codellama": {"size": "7B/13B", "use_case": "code generation"},
    "mistral": {"size": "7B", "use_case": "efficient general purpose"},
    "phi-3": {"size": "3.8B", "use_case": "small but capable"},
    "gemma2": {"size": "9B", "use_case": "Google's open model"},
    "qwen2": {"size": "7B", "use_case": "multilingual"},
}

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TIMEOUT = 60
DEFAULT_TEMPERATURE = 0.7


class OllamaAdapter(BaseLLMAdapter):
    """
    Ollama local LLM adapter with multi-endpoint fallback.

    Features:
        - Tier 2 (LOCAL) reliability (hardware dependent)
        - Multi-endpoint fallback support
        - Zero API cost (local compute)
        - Circuit breaker protection
        - Model availability checking

    Example:
        >>> adapter = OllamaAdapter()
        >>> if adapter.check_availability():
        ...     response = adapter.execute("Write a Python hello world")
        ...     print(response.content)
        ...     print(f"Cost: ${response.cost_usd:.6f}")  # Always $0.00
    """

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        fallback_hosts: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize Ollama adapter.

        Args:
            host: Ollama server host (defaults to {{OLLAMA_HOST}} placeholder)
            model: Default model to use
            max_tokens: Default max tokens for responses
            timeout: Request timeout in seconds
            fallback_hosts: List of fallback Ollama hosts
            **kwargs: Additional arguments passed to BaseLLMAdapter
        """
        # Configuration
        self.model = model or os.getenv("OLLAMA_DEFAULT_MODEL", DEFAULT_MODEL)

        super().__init__(
            adapter_name=f"Ollama-{self.model}",
            tier=AdapterTier.LOCAL,
            reliability_score=0.8,  # Lower than API tier (hardware dependent)
            **kwargs,
        )

        # Host configuration
        self._host_placeholder = host or "{{OLLAMA_HOST}}"
        self._resolved_host: Optional[str] = None

        # Build fallback host list
        self.fallback_hosts: List[str] = []
        if fallback_hosts:
            self.fallback_hosts.extend(fallback_hosts)

        # Add environment variable host
        env_host = os.getenv("OLLAMA_HOST")
        if env_host and env_host not in self.fallback_hosts:
            self.fallback_hosts.append(env_host)

        # Add default localhost
        if DEFAULT_HOST not in self.fallback_hosts:
            self.fallback_hosts.append(DEFAULT_HOST)

        self.max_tokens = max_tokens or int(
            os.getenv("OLLAMA_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        )
        self.timeout = timeout or int(os.getenv("OLLAMA_TIMEOUT", str(DEFAULT_TIMEOUT)))

        # Active host (set on first successful connection)
        self.active_host: Optional[str] = None

    def _get_host(self) -> str:
        """Resolve host from placeholder or environment."""
        if self._resolved_host is None:
            if self._host_placeholder.startswith("{{"):
                var_name = self._host_placeholder[2:-2]
                self._resolved_host = os.getenv(var_name)
            else:
                self._resolved_host = self._host_placeholder

        return self._resolved_host or DEFAULT_HOST

    def _get_hosts_to_try(self) -> List[str]:
        """Get ordered list of hosts to try."""
        hosts = []

        # Add resolved host first
        resolved = self._get_host()
        if resolved:
            hosts.append(resolved)

        # Add fallbacks
        for host in self.fallback_hosts:
            if host not in hosts:
                hosts.append(host)

        # If active host is known, move it to front
        if self.active_host and self.active_host in hosts:
            hosts.remove(self.active_host)
            hosts.insert(0, self.active_host)

        return hosts

    def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Execute prompt using Ollama API (synchronous).

        Args:
            prompt: The prompt/instruction to send to model
            context: Optional context with parameters:
                - model (str): Override default model
                - max_tokens (int): Override default max tokens
                - temperature (float): Sampling temperature (0.0-1.0)
                - host (str): Override host URL

        Returns:
            LLMResponse with status, content, cost ($0.00), latency
        """
        if requests is None:
            return self._create_error_response(
                error="requests package not installed. Install with: pip install requests"
            )

        # Check circuit breaker
        if self._check_circuit_breaker():
            return self._create_error_response(
                error="Circuit breaker open. Service unavailable for cooldown period.",
                status="error",
            )

        # Extract context parameters
        context = context or {}
        model = context.get("model", self.model)
        max_tokens = context.get("max_tokens", self.max_tokens)
        temperature = context.get("temperature", DEFAULT_TEMPERATURE)
        host_override = context.get("host")

        start_time = time.time()

        # Determine hosts to try
        hosts_to_try = [host_override] if host_override else self._get_hosts_to_try()

        last_error = None

        for host in hosts_to_try:
            if not host:
                continue

            try:
                response_data = self._call_ollama(
                    host=host,
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Extract response
                content = response_data.get("response", "")

                # Estimate tokens (Ollama doesn't always return exact counts)
                tokens_input = len(prompt) // 4
                tokens_output = len(content) // 4

                # Cost is always $0.00 for local models
                cost_usd = 0.0

                # Record success
                self._record_success(latency_ms, cost_usd)

                # Update active host
                self.active_host = host

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
                        "host": host,
                        "model": response_data.get("model", model),
                        "done": response_data.get("done", True),
                        "total_duration_ns": response_data.get("total_duration", 0),
                        "eval_count": response_data.get("eval_count", 0),
                    },
                )

            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error at {host}: {e}"
                continue

            except requests.exceptions.Timeout as e:
                last_error = f"Timeout at {host}: {e}"
                continue

            except Exception as e:
                last_error = f"Error at {host}: {e}"
                continue

        # All hosts failed
        self._record_failure()
        latency_ms = int((time.time() - start_time) * 1000)

        return LLMResponse(
            status="error",
            error=f"All Ollama endpoints failed. Last error: {last_error}",
            cost_usd=0.0,
            latency_ms=latency_ms,
            adapter_name=self.adapter_name,
            model_used=model,
            metadata={
                "hosts_tried": len(hosts_to_try),
                "fallback_hosts": self.fallback_hosts,
            },
        )

    def _call_ollama(
        self,
        host: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Call Ollama API at specified host."""
        endpoint = f"{host}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = requests.post(endpoint, json=payload, timeout=self.timeout)

        if response.status_code == 404:
            raise ValueError(
                f"Model '{model}' not found at {host}. "
                f"Install it with: ollama pull {model}"
            )

        response.raise_for_status()
        return response.json()

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Execute prompt using Ollama API (asynchronous)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, prompt, context)

    def estimate_cost(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Estimate cost - always $0.00 for local models."""
        return 0.0

    def check_availability(self) -> bool:
        """Check if any Ollama endpoint is reachable with the model installed."""
        if requests is None:
            return False

        if not self.is_healthy():
            return False

        for host in self._get_hosts_to_try():
            if not host:
                continue

            try:
                # Check if Ollama is running
                response = requests.get(f"{host}/api/tags", timeout=2)

                if response.status_code == 200:
                    # Check if model is available
                    if self._check_model_available(host):
                        self.active_host = host
                        return True

            except Exception:
                continue

        return False

    def _check_model_available(self, host: str) -> bool:
        """Check if model is installed at host."""
        try:
            response = requests.get(f"{host}/api/tags", timeout=2)

            if response.status_code != 200:
                return False

            data = response.json()
            models = data.get("models", [])

            for installed_model in models:
                model_name = installed_model.get("name", "")
                if model_name.startswith(self.model):
                    return True

            return False

        except Exception:
            return False

    def list_available_models(self, host: Optional[str] = None) -> List[str]:
        """List all models available at Ollama endpoint."""
        if requests is None:
            return []

        endpoint = host or self.active_host or self._get_host()

        try:
            response = requests.get(f"{endpoint}/api/tags", timeout=2)

            if response.status_code != 200:
                return []

            data = response.json()
            models = data.get("models", [])

            return [m.get("name", "") for m in models]

        except Exception:
            return []

    def get_metadata(self) -> Dict[str, Any]:
        """Return adapter configuration and status."""
        return {
            "name": self.adapter_name,
            "tier": self.tier.name,
            "tier_value": self.tier.value,
            "reliability_score": self.reliability_score,
            "enabled": self.enabled,
            "model": self.model,
            "active_host": self.active_host,
            "fallback_hosts": self.fallback_hosts,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self.get_success_rate(),
            "avg_latency_ms": self.get_average_latency(),
            "total_cost_usd": self._total_cost_usd,  # Always 0.0
            "circuit_breaker_open": self._circuit_breaker_open,
            "consecutive_failures": self._consecutive_failures,
            "known_models": list(KNOWN_MODELS.keys()),
            "model_info": KNOWN_MODELS.get(
                self.model, {"size": "unknown", "use_case": "unknown"}
            ),
        }
