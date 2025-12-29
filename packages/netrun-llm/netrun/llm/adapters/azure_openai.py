"""
Azure OpenAI Adapter for netrun-llm package

Provides multi-resource Azure OpenAI integration with automatic failover
and cloud credit utilization. Extracted from Charlotte production architecture.

Features:
    - Multi-resource failover (primary → secondary → tertiary)
    - Azure CLI authentication via DefaultAzureCredential
    - Cloud credit utilization (effectively free until credits exhausted)
    - Circuit breaker protection
    - Per-resource health tracking

Author: Netrun Systems
Version: 2.0.0
License: MIT
"""

import os
import time
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI, OpenAIError, RateLimitError, APIError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    AzureOpenAI = None
    DefaultAzureCredential = None

from .base import BaseLLMAdapter, AdapterTier, LLMResponse


@dataclass
class AzureResource:
    """Configuration for an Azure OpenAI resource"""
    name: str
    endpoint: str
    resource_group: str
    models: List[str]
    priority: int  # 1 = highest priority


class AzureOpenAIAdapter(BaseLLMAdapter):
    """
    Azure OpenAI adapter with multi-resource support and automatic failover.

    Features:
        - Cloud credit utilization (FREE until credits exhausted)
        - Multi-resource failover
        - Azure CLI authentication (DefaultAzureCredential)
        - Circuit breaker pattern for reliability
        - Per-resource health metrics

    Environment Variables:
        AZURE_OPENAI_API_VERSION: API version (default: 2024-02-15-preview)
        AZURE_OPENAI_DEFAULT_MODEL: Default model (default: gpt-4o)
        AZURE_OPENAI_TIMEOUT: Request timeout in seconds (default: 30)
        AZURE_OPENAI_RESOURCES: JSON array of custom resources (optional)

    Example:
        >>> adapter = AzureOpenAIAdapter()
        >>> result = adapter.execute("Explain REST APIs briefly")
        >>> print(result.content)
        >>> print(f"Effective savings: ${result.metadata['effective_cost_saved']:.4f}")
    """

    def __init__(
        self,
        resources: Optional[List[AzureResource]] = None,
        preferred_model: str = None,
        api_version: str = None,
        timeout: int = None
    ):
        """
        Initialize Azure OpenAI adapter.

        Args:
            resources: List of AzureResource configurations (default: uses built-in)
            preferred_model: Default model to use (default: gpt-4o)
            api_version: Azure OpenAI API version (default: 2024-02-15-preview)
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ImportError: If azure-identity or openai SDK not installed
        """
        if not AZURE_AVAILABLE:
            raise ImportError(
                "Azure OpenAI support requires additional packages. "
                "Install with: pip install 'netrun-llm[azure]'"
            )

        self.preferred_model = preferred_model or os.getenv(
            "AZURE_OPENAI_DEFAULT_MODEL", "gpt-4o"
        )
        self.api_version = api_version or os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
        )
        self.timeout = timeout or int(os.getenv("AZURE_OPENAI_TIMEOUT", "30"))

        super().__init__(
            adapter_name=f"AzureOpenAI-{self.preferred_model}",
            tier=AdapterTier.API,
            reliability_score=1.0  # Highest reliability (API tier)
        )

        # Configure resources (use provided or default)
        self.resources = resources or self._get_default_resources()

        # Initialize Azure authentication
        self.credential = None
        self.token_provider = None
        self.clients: Dict[str, AzureOpenAI] = {}

        # Per-resource health tracking
        self._resource_success_count: Dict[str, int] = {}
        self._resource_failure_count: Dict[str, int] = {}
        self._resource_last_used: Dict[str, float] = {}

        # Initialize clients for all resources
        self._initialize_clients()

    def _get_default_resources(self) -> List[AzureResource]:
        """Get default Azure OpenAI resources (Netrun infrastructure)"""
        # Check for custom resources in environment
        custom_resources_json = os.getenv("AZURE_OPENAI_RESOURCES")
        if custom_resources_json:
            import json
            resources_data = json.loads(custom_resources_json)
            return [AzureResource(**r) for r in resources_data]

        # Default Netrun resources (from Charlotte production)
        return [
            AzureResource(
                name="nrcharlotte",
                endpoint="https://nrcharlotte.openai.azure.com",
                resource_group="rg-Daniel-7272",
                models=["o3-mini", "gpt-4o"],
                priority=1  # HIGHEST CAPACITY
            ),
            AzureResource(
                name="wilbur-resource",
                endpoint="https://wilbur-resource.openai.azure.com",
                resource_group="Chatbot",
                models=["gpt-4.1", "gpt-4o", "gpt-4o-mini-transcribe"],
                priority=2
            ),
            AzureResource(
                name="oai-netrunmax-prod-eastus",
                endpoint="https://oai-netrunmax-prod-eastus.openai.azure.com",
                resource_group="rg-netrunmax-prod",
                models=["gpt-4-turbo", "text-embedding-ada-002"],
                priority=3
            )
        ]

    def _initialize_clients(self) -> None:
        """Initialize Azure OpenAI clients for all resources"""
        try:
            # Set up Azure authentication
            self.credential = DefaultAzureCredential()
            self.token_provider = get_bearer_token_provider(
                self.credential,
                "https://cognitiveservices.azure.com/.default"
            )

            # Create client for each resource
            for resource in self.resources:
                try:
                    client = AzureOpenAI(
                        azure_endpoint=resource.endpoint,
                        azure_ad_token_provider=self.token_provider,
                        api_version=self.api_version,
                        timeout=self.timeout
                    )
                    self.clients[resource.name] = client

                    # Initialize health tracking
                    self._resource_success_count[resource.name] = 0
                    self._resource_failure_count[resource.name] = 0
                    self._resource_last_used[resource.name] = 0.0

                except Exception as e:
                    # Log warning but continue (adapter can work with subset of resources)
                    pass

        except Exception as e:
            # Azure auth failed - disable adapter
            self.enabled = False

    def _verify_azure_auth(self) -> bool:
        """Verify Azure CLI is authenticated"""
        try:
            result = subprocess.run(
                ["az", "account", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_resource_for_model(self, model: str) -> Optional[AzureResource]:
        """Find the highest-priority resource that supports the requested model"""
        sorted_resources = sorted(self.resources, key=lambda r: r.priority)

        for resource in sorted_resources:
            if model in resource.models:
                return resource

        return None

    def _select_fallback_resource(self, failed_resources: List[str]) -> Optional[AzureResource]:
        """Select next available resource for failover"""
        sorted_resources = sorted(self.resources, key=lambda r: r.priority)

        for resource in sorted_resources:
            if resource.name not in failed_resources:
                return resource

        return None

    def _execute_with_resource(
        self,
        resource: AzureResource,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """Execute chat completion with specific resource"""
        start_time = time.time()

        try:
            client = self.clients.get(resource.name)
            if not client:
                return self._create_error_response(
                    f"No client initialized for {resource.name}",
                    latency_ms=0,
                    model=model
                )

            # Extract OpenAI parameters
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # Execute completion
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response data
            result_text = response.choices[0].message.content
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens

            # Update health metrics
            self._resource_success_count[resource.name] += 1
            self._resource_last_used[resource.name] = time.time()

            return LLMResponse(
                status="success",
                content=result_text,
                cost_usd=0.0,  # Cloud credits (FREE)
                latency_ms=latency_ms,
                adapter_name=self.adapter_name,
                model_used=model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                metadata={
                    "resource_name": resource.name,
                    "resource_group": resource.resource_group,
                    "endpoint": resource.endpoint,
                    "effective_cost_saved": self._calculate_effective_cost(
                        model, tokens_input, tokens_output
                    )
                }
            )

        except RateLimitError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._resource_failure_count[resource.name] += 1

            return self._create_error_response(
                f"Rate limit on {resource.name}: {str(e)}",
                status="rate_limited",
                latency_ms=latency_ms,
                model=model
            )

        except APIError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._resource_failure_count[resource.name] += 1

            return self._create_error_response(
                f"API error on {resource.name}: {str(e)}",
                latency_ms=latency_ms,
                model=model
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._resource_failure_count[resource.name] += 1

            return self._create_error_response(
                f"Unexpected error on {resource.name}: {str(e)}",
                latency_ms=latency_ms,
                model=model
            )

    def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """
        Execute prompt using Azure OpenAI with automatic failover.

        Args:
            prompt: The prompt/instruction to send
            context: Optional context with parameters:
                - model: Model name (default: self.preferred_model)
                - temperature: Temperature 0.0-1.0 (default: 0.7)
                - max_tokens: Max output tokens (default: 1000)
                - system: System message (optional)

        Returns:
            LLMResponse with status, content, cost, latency, etc.

        Example:
            >>> adapter = AzureOpenAIAdapter()
            >>> response = adapter.execute(
            ...     "Explain microservices in one paragraph",
            ...     context={"temperature": 0.5}
            ... )
            >>> print(response.content)
        """
        # Check circuit breaker
        if self._check_circuit_breaker():
            return self._create_error_response(
                "Circuit breaker open (too many failures)"
            )

        if not self.enabled:
            return self._create_error_response("Adapter is disabled")

        # Extract parameters from context
        context = context or {}
        model = context.get("model", self.preferred_model)
        system_prompt = context.get("system", "You are a helpful assistant.")

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": prompt})

        # Try primary resource first
        primary_resource = self._get_resource_for_model(model)
        failed_resources = []

        if primary_resource:
            result = self._execute_with_resource(
                primary_resource, model, messages, **context
            )

            if result.status == "success":
                self._record_success(result.latency_ms, result.cost_usd)
                return result
            else:
                failed_resources.append(primary_resource.name)

        # Try failover resources
        max_attempts = 3
        attempt = 1

        while attempt < max_attempts:
            fallback_resource = self._select_fallback_resource(failed_resources)

            if not fallback_resource:
                break  # No more resources to try

            # Use first available model on fallback resource
            fallback_model = fallback_resource.models[0]

            result = self._execute_with_resource(
                fallback_resource, fallback_model, messages, **context
            )

            if result.status == "success":
                self._record_success(result.latency_ms, result.cost_usd)
                return result
            else:
                failed_resources.append(fallback_resource.name)

            attempt += 1

        # All resources failed
        self._record_failure()

        return self._create_error_response(
            f"All Azure OpenAI resources failed after {len(failed_resources)} attempts"
        )

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Async execution - currently wraps sync implementation"""
        # For true async, would use AsyncAzureOpenAI client
        # For now, provide sync wrapper for compatibility
        return self.execute(prompt, context)

    def estimate_cost(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Estimate cost before executing prompt.

        Azure OpenAI uses cloud credits, so cost is $0.00 until credits exhausted.
        However, we track "effective cost" for ROI calculation.

        Args:
            prompt: The prompt/instruction
            context: Optional context with parameters

        Returns:
            Cost in USD (always 0.0 for cloud credits)
        """
        # Cloud credits = FREE
        return 0.0

    def _calculate_effective_cost(
        self, model: str, tokens_input: int, tokens_output: int
    ) -> float:
        """Calculate effective cost saved by using cloud credits (uses ChatGPT baseline)"""
        # Pricing per 1M tokens (ChatGPT baseline for comparison)
        pricing = {
            "o3-mini": {"input": 1.10, "output": 4.40},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4.1": {"input": 2.50, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-4o-mini-transcribe": {"input": 0.15, "output": 0.60},
        }

        model_pricing = pricing.get(model, {"input": 2.50, "output": 10.00})

        cost_input = (tokens_input / 1_000_000) * model_pricing["input"]
        cost_output = (tokens_output / 1_000_000) * model_pricing["output"]

        return cost_input + cost_output

    def check_availability(self) -> bool:
        """Check if adapter's service is available and healthy"""
        # Verify Azure CLI authentication
        if not self._verify_azure_auth():
            return False

        # Check circuit breaker
        if self._check_circuit_breaker():
            return False

        # Verify at least one client is initialized
        if not self.clients:
            return False

        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Return adapter configuration and current status"""
        # Calculate per-resource success rates
        resource_health = {}
        for resource in self.resources:
            success = self._resource_success_count.get(resource.name, 0)
            failure = self._resource_failure_count.get(resource.name, 0)
            total = success + failure

            success_rate = (success / total * 100) if total > 0 else 100.0
            last_used = self._resource_last_used.get(resource.name, 0.0)

            resource_health[resource.name] = {
                "success_count": success,
                "failure_count": failure,
                "success_rate": round(success_rate, 1),
                "last_used": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(last_used)
                ) if last_used > 0 else "Never",
                "models": resource.models,
                "priority": resource.priority
            }

        return {
            "name": self.adapter_name,
            "tier": self.tier.name,
            "reliability_score": self.reliability_score,
            "enabled": self.enabled,
            "preferred_model": self.preferred_model,
            "api_version": self.api_version,
            "success_rate": round(self.get_success_rate(), 1),
            "avg_latency_ms": round(self.get_average_latency(), 1),
            "total_cost_usd": round(self._total_cost_usd, 4),
            "circuit_breaker_open": self._circuit_breaker_open,
            "azure_authenticated": self._verify_azure_auth(),
            "clients_initialized": len(self.clients),
            "resource_health": resource_health,
            "total_requests": self._success_count + self._failure_count
        }
