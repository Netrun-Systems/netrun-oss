"""
Netrun LLM - Provider Policies and Cost Control

LLM Provider Policies - Control model usage, costs, and rate limits.

Policies allow fine-grained control over:
- Which models can be used
- Maximum tokens per request
- Cost limits per request/tenant
- Rate limits per provider
- Budget management (daily/monthly)
- Cost tier restrictions

Features:
    - Per-provider policy configuration
    - Multi-tenant budget management
    - Real-time cost estimation
    - Automatic fallback to local models
    - Rate limiting (RPM/TPM)
    - Cost tier classification
    - Usage tracking and reporting

Example:
    # Define tenant policy
    tenant_policy = TenantPolicy(
        tenant_id="acme-corp",
        monthly_budget_usd=100.0,
        provider_policies={
            "openai": ProviderPolicy(
                provider="openai",
                allowed_models=["gpt-4o-mini"],
                max_cost_per_request=0.05,
            ),
        },
    )

    # Enforce policy before requests
    enforcer = PolicyEnforcer(tenant_policy)
    enforcer.validate_request(
        provider="openai",
        model="gpt-4o-mini",
        estimated_tokens=2000,
    )

Author: Netrun Systems
License: MIT
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Literal, Tuple
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from netrun.llm.exceptions import LLMError


class CostTier(str, Enum):
    """
    Cost tiers for model classification.

    Attributes:
        FREE: Local models (Ollama) - no API costs
        LOW: Budget models (GPT-4o-mini, Claude Haiku) - $0.0001-0.001/1K tokens
        MEDIUM: Standard models (GPT-4o, Claude Sonnet) - $0.001-0.01/1K tokens
        HIGH: Premium models (GPT-4, Claude Opus) - $0.01-0.1/1K tokens
        PREMIUM: Specialized models (O1, reasoning models) - $0.1+/1K tokens
    """
    FREE = "free"           # Local models (Ollama)
    LOW = "low"             # GPT-4o-mini, Claude Haiku
    MEDIUM = "medium"       # GPT-4o, Claude Sonnet
    HIGH = "high"           # GPT-4, Claude Opus
    PREMIUM = "premium"     # O1, specialized models


# Model cost per 1K tokens (input/output)
# Updated as of December 2025
MODEL_COSTS: Dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4": (0.03, 0.06),
    "o1-preview": (0.015, 0.06),
    "o1-mini": (0.003, 0.012),
    "gpt-3.5-turbo": (0.0005, 0.0015),

    # Anthropic
    "claude-3-haiku": (0.00025, 0.00125),
    "claude-3-5-haiku": (0.0008, 0.004),
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-opus": (0.015, 0.075),
    "claude-sonnet-4-5-20250929": (0.003, 0.015),  # Latest Sonnet
    "claude-opus-4-5-20251101": (0.015, 0.075),    # Latest Opus

    # Azure OpenAI (similar to OpenAI)
    "azure-gpt-4o-mini": (0.00015, 0.0006),
    "azure-gpt-4o": (0.0025, 0.01),
    "azure-gpt-4": (0.03, 0.06),

    # Local models (free)
    "llama3.2": (0.0, 0.0),
    "llama3": (0.0, 0.0),
    "mistral": (0.0, 0.0),
    "codellama": (0.0, 0.0),
    "phi3": (0.0, 0.0),
    "gemma": (0.0, 0.0),
}


# Model to cost tier mapping
MODEL_COST_TIERS: Dict[str, CostTier] = {
    # Free tier
    "llama3.2": CostTier.FREE,
    "llama3": CostTier.FREE,
    "mistral": CostTier.FREE,
    "codellama": CostTier.FREE,
    "phi3": CostTier.FREE,
    "gemma": CostTier.FREE,

    # Low tier
    "gpt-4o-mini": CostTier.LOW,
    "gpt-3.5-turbo": CostTier.LOW,
    "claude-3-haiku": CostTier.LOW,
    "claude-3-5-haiku": CostTier.LOW,
    "azure-gpt-4o-mini": CostTier.LOW,

    # Medium tier
    "gpt-4o": CostTier.MEDIUM,
    "claude-3-5-sonnet": CostTier.MEDIUM,
    "claude-3-sonnet": CostTier.MEDIUM,
    "claude-sonnet-4-5-20250929": CostTier.MEDIUM,
    "azure-gpt-4o": CostTier.MEDIUM,

    # High tier
    "gpt-4-turbo": CostTier.HIGH,
    "gpt-4": CostTier.HIGH,
    "claude-3-opus": CostTier.HIGH,
    "claude-opus-4-5-20251101": CostTier.HIGH,
    "azure-gpt-4": CostTier.HIGH,

    # Premium tier
    "o1-preview": CostTier.PREMIUM,
    "o1-mini": CostTier.PREMIUM,
}


class ProviderPolicy(BaseModel):
    """
    Policy configuration for an LLM provider.

    Controls model usage, token limits, costs, and rate limits per provider.

    Attributes:
        provider: Provider name (openai, anthropic, azure_openai, ollama, bedrock)
        allowed_models: List of allowed models. Empty list = all models allowed
        denied_models: Models explicitly denied. Takes precedence over allowed_models
        max_tokens_per_request: Maximum tokens (input + output) per request
        max_cost_per_request: Maximum USD cost per request (0 = unlimited)
        rate_limit_rpm: Requests per minute (0 = unlimited)
        rate_limit_tpm: Tokens per minute (0 = unlimited)
        cost_tier_limit: Maximum cost tier allowed (None = all tiers)
        require_reason: Require justification string for each request
        enabled: Whether this provider is enabled

    Example:
        policy = ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini", "gpt-4o"],
            max_tokens_per_request=4096,
            max_cost_per_request=0.10,
            rate_limit_rpm=60,
            cost_tier_limit=CostTier.MEDIUM,
        )
    """
    provider: Literal["openai", "anthropic", "azure_openai", "ollama", "bedrock"]
    allowed_models: list[str] = Field(
        default_factory=list,
        description="Models allowed for this provider. Empty = all allowed."
    )
    denied_models: list[str] = Field(
        default_factory=list,
        description="Models explicitly denied. Takes precedence over allowed."
    )
    max_tokens_per_request: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens (input + output) per request."
    )
    max_cost_per_request: float = Field(
        default=1.0,
        ge=0.0,
        description="Maximum USD cost per request. 0 = unlimited."
    )
    rate_limit_rpm: int = Field(
        default=60,
        ge=0,
        description="Requests per minute. 0 = unlimited."
    )
    rate_limit_tpm: int = Field(
        default=100000,
        ge=0,
        description="Tokens per minute. 0 = unlimited."
    )
    cost_tier_limit: Optional[CostTier] = Field(
        default=None,
        description="Maximum cost tier allowed. None = all tiers."
    )
    require_reason: bool = Field(
        default=False,
        description="Require a reason/justification for each request."
    )
    enabled: bool = Field(
        default=True,
        description="Whether this provider is enabled."
    )

    @field_validator('allowed_models', 'denied_models')
    @classmethod
    def validate_model_lists(cls, v):
        """Ensure model lists contain only strings."""
        if not all(isinstance(model, str) for model in v):
            raise ValueError("All model names must be strings")
        return v


class TenantPolicy(BaseModel):
    """
    Tenant-specific LLM usage policies.

    Controls budget limits, provider access, and default behavior per tenant.

    Attributes:
        tenant_id: Unique tenant identifier
        monthly_budget_usd: Monthly spending limit in USD
        daily_budget_usd: Daily spending limit (None = use monthly only)
        provider_policies: Per-provider policy overrides
        default_provider: Default provider when not specified
        fallback_to_local: Fall back to Ollama if budget exceeded
        track_usage: Enable usage tracking and reporting
        alert_threshold_pct: Alert when budget reaches this percentage

    Example:
        tenant_policy = TenantPolicy(
            tenant_id="acme-corp",
            monthly_budget_usd=100.0,
            daily_budget_usd=10.0,
            provider_policies={
                "openai": ProviderPolicy(
                    provider="openai",
                    allowed_models=["gpt-4o-mini"],
                    max_cost_per_request=0.05,
                ),
                "ollama": ProviderPolicy(
                    provider="ollama",
                    allowed_models=["llama3"],
                    max_tokens_per_request=8192,
                ),
            },
            fallback_to_local=True,
        )
    """
    tenant_id: str
    monthly_budget_usd: float = Field(
        default=100.0,
        ge=0.0,
        description="Monthly spending limit in USD."
    )
    daily_budget_usd: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Daily spending limit. None = use monthly only."
    )
    provider_policies: Dict[str, ProviderPolicy] = Field(
        default_factory=dict,
        description="Per-provider policy overrides."
    )
    default_provider: str = Field(
        default="openai",
        description="Default provider when not specified."
    )
    fallback_to_local: bool = Field(
        default=True,
        description="Fall back to Ollama if budget exceeded."
    )
    track_usage: bool = Field(
        default=True,
        description="Enable usage tracking and reporting."
    )
    alert_threshold_pct: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Alert when budget reaches this percentage."
    )

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        """Ensure tenant_id is not empty."""
        if not v or not v.strip():
            raise ValueError("tenant_id cannot be empty")
        return v.strip()


class UsageRecord(BaseModel):
    """
    Record of LLM usage for tracking and reporting.

    Attributes:
        timestamp: When the request was made
        tenant_id: Tenant identifier
        provider: Provider used
        model: Model used
        tokens_input: Input tokens consumed
        tokens_output: Output tokens consumed
        tokens_total: Total tokens (input + output)
        cost_usd: Cost in USD
        latency_ms: Response latency in milliseconds
        success: Whether request succeeded
        reason: Optional reason/justification provided
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str
    provider: str
    model: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    latency_ms: float
    success: bool
    reason: Optional[str] = None


class PolicyEnforcer:
    """
    Enforces LLM usage policies before requests are sent.

    Validates requests against provider and tenant policies, tracks usage,
    enforces budgets, and provides cost estimation.

    Attributes:
        policy: Tenant policy configuration
        usage_records: List of usage records for tracking

    Example:
        # Create enforcer with policy
        enforcer = PolicyEnforcer(tenant_policy)

        # Validate before making request
        try:
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o",
                estimated_tokens=2000,
                reason="Customer support chatbot",
            )
        except PolicyViolationError as e:
            logger.error(f"Policy violation: {e}")
            # Fall back to local model

        # Record usage after request completes
        enforcer.record_usage(
            provider="openai",
            model="gpt-4o",
            tokens_input=1500,
            tokens_output=500,
            cost_usd=0.0045,
            latency_ms=1200,
            success=True,
            reason="Customer support chatbot",
        )

        # Get usage report
        report = enforcer.get_usage_report(days=30)
    """

    def __init__(self, policy: TenantPolicy):
        """
        Initialize policy enforcer.

        Args:
            policy: Tenant policy configuration
        """
        self.policy = policy
        self.usage_records: list[UsageRecord] = []
        self._monthly_spend: float = 0.0
        self._daily_spend: float = 0.0
        self._last_daily_reset = datetime.utcnow().date()

        # Rate limiting state
        self._rate_limit_state: Dict[str, Dict[str, list[float]]] = {}

    def validate_request(
        self,
        provider: str,
        model: str,
        estimated_tokens: int,
        reason: Optional[str] = None,
    ) -> None:
        """
        Validate a request against policies.

        Args:
            provider: Provider name (openai, anthropic, etc.)
            model: Model identifier
            estimated_tokens: Estimated total tokens (input + output)
            reason: Optional justification for the request

        Raises:
            PolicyViolationError: If request violates policy
            ProviderDisabledError: If provider is disabled
            BudgetExceededError: If budget limit exceeded
            RateLimitExceededError: If rate limit exceeded
            FallbackToLocalError: If budget exceeded but fallback available
        """
        # Get provider policy (or create default)
        provider_policy = self.policy.provider_policies.get(
            provider,
            ProviderPolicy(provider=provider)  # type: ignore
        )

        # Check if provider is enabled
        if not provider_policy.enabled:
            raise ProviderDisabledError(
                f"Provider '{provider}' is disabled in policy."
            )

        # Check model allowed
        if provider_policy.denied_models and model in provider_policy.denied_models:
            raise PolicyViolationError(
                f"Model '{model}' is explicitly denied for provider '{provider}'."
            )

        if provider_policy.allowed_models and model not in provider_policy.allowed_models:
            raise PolicyViolationError(
                f"Model '{model}' not in allowed list for provider '{provider}': "
                f"{provider_policy.allowed_models}"
            )

        # Check cost tier limit
        if provider_policy.cost_tier_limit:
            model_tier = MODEL_COST_TIERS.get(model)
            if model_tier and self._tier_exceeds_limit(model_tier, provider_policy.cost_tier_limit):
                raise PolicyViolationError(
                    f"Model '{model}' tier ({model_tier.value}) exceeds limit "
                    f"({provider_policy.cost_tier_limit.value})."
                )

        # Check token limit
        if estimated_tokens > provider_policy.max_tokens_per_request:
            raise PolicyViolationError(
                f"Estimated tokens ({estimated_tokens}) exceeds limit "
                f"({provider_policy.max_tokens_per_request}) for provider '{provider}'."
            )

        # Check cost limit
        estimated_cost = self.estimate_cost(model, estimated_tokens)
        if provider_policy.max_cost_per_request > 0 and estimated_cost > provider_policy.max_cost_per_request:
            raise PolicyViolationError(
                f"Estimated cost (${estimated_cost:.4f}) exceeds per-request limit "
                f"(${provider_policy.max_cost_per_request:.4f})."
            )

        # Check daily budget
        self._reset_daily_budget_if_needed()
        if self.policy.daily_budget_usd and self._daily_spend + estimated_cost > self.policy.daily_budget_usd:
            if self.policy.fallback_to_local:
                raise FallbackToLocalError(
                    f"Daily budget (${self.policy.daily_budget_usd:.2f}) would be exceeded. "
                    f"Current spend: ${self._daily_spend:.2f}, estimated cost: ${estimated_cost:.4f}. "
                    f"Fallback to local model recommended."
                )
            raise BudgetExceededError(
                f"Daily budget (${self.policy.daily_budget_usd:.2f}) would be exceeded. "
                f"Current spend: ${self._daily_spend:.2f}, estimated cost: ${estimated_cost:.4f}."
            )

        # Check monthly budget
        if self._monthly_spend + estimated_cost > self.policy.monthly_budget_usd:
            if self.policy.fallback_to_local:
                raise FallbackToLocalError(
                    f"Monthly budget (${self.policy.monthly_budget_usd:.2f}) would be exceeded. "
                    f"Current spend: ${self._monthly_spend:.2f}, estimated cost: ${estimated_cost:.4f}. "
                    f"Fallback to local model recommended."
                )
            raise BudgetExceededError(
                f"Monthly budget (${self.policy.monthly_budget_usd:.2f}) would be exceeded. "
                f"Current spend: ${self._monthly_spend:.2f}, estimated cost: ${estimated_cost:.4f}."
            )

        # Check rate limits
        self._check_rate_limits(provider, provider_policy, estimated_tokens)

        # Check reason required
        if provider_policy.require_reason and not reason:
            raise PolicyViolationError(
                f"Reason required for requests to provider '{provider}'."
            )

    def estimate_cost(self, model: str, tokens: int, input_ratio: float = 0.7) -> float:
        """
        Estimate cost for a request.

        Args:
            model: Model identifier
            tokens: Total tokens (input + output)
            input_ratio: Ratio of input tokens to total (default 0.7 = 70% input, 30% output)

        Returns:
            Estimated cost in USD
        """
        if model not in MODEL_COSTS:
            return 0.0  # Unknown model, assume free (likely local)

        input_cost, output_cost = MODEL_COSTS[model]
        input_tokens = int(tokens * input_ratio)
        output_tokens = tokens - input_tokens

        return (input_tokens * input_cost + output_tokens * output_cost) / 1000

    def record_usage(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        latency_ms: float,
        success: bool,
        reason: Optional[str] = None,
    ) -> None:
        """
        Record actual usage after request completes.

        Args:
            provider: Provider used
            model: Model used
            tokens_input: Input tokens consumed
            tokens_output: Output tokens consumed
            cost_usd: Actual cost in USD
            latency_ms: Response latency in milliseconds
            success: Whether request succeeded
            reason: Optional justification provided
        """
        if not self.policy.track_usage:
            return

        record = UsageRecord(
            tenant_id=self.policy.tenant_id,
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            reason=reason,
        )

        self.usage_records.append(record)
        self._monthly_spend += cost_usd
        self._daily_spend += cost_usd

        # Check alert threshold
        if self.policy.monthly_budget_usd > 0:
            spend_pct = (self._monthly_spend / self.policy.monthly_budget_usd) * 100
            if spend_pct >= self.policy.alert_threshold_pct:
                # In production, this would trigger an alert/notification
                pass

    def get_usage_report(self, days: int = 30) -> Dict[str, any]:
        """
        Get usage report for the specified number of days.

        Args:
            days: Number of days to include in report

        Returns:
            Dictionary with usage statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_records = [r for r in self.usage_records if r.timestamp >= cutoff]

        if not recent_records:
            return {
                "tenant_id": self.policy.tenant_id,
                "period_days": days,
                "total_requests": 0,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "by_provider": {},
                "by_model": {},
            }

        # Aggregate statistics
        by_provider: Dict[str, Dict[str, any]] = {}
        by_model: Dict[str, Dict[str, any]] = {}

        for record in recent_records:
            # By provider
            if record.provider not in by_provider:
                by_provider[record.provider] = {
                    "requests": 0,
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "avg_latency_ms": 0.0,
                    "success_rate": 0.0,
                }
            by_provider[record.provider]["requests"] += 1
            by_provider[record.provider]["cost_usd"] += record.cost_usd
            by_provider[record.provider]["tokens"] += record.tokens_total

            # By model
            if record.model not in by_model:
                by_model[record.model] = {
                    "requests": 0,
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "avg_latency_ms": 0.0,
                }
            by_model[record.model]["requests"] += 1
            by_model[record.model]["cost_usd"] += record.cost_usd
            by_model[record.model]["tokens"] += record.tokens_total

        # Calculate averages
        for stats in by_provider.values():
            latencies = [r.latency_ms for r in recent_records]
            stats["avg_latency_ms"] = sum(latencies) / len(latencies)
            successes = sum(1 for r in recent_records if r.success)
            stats["success_rate"] = (successes / len(recent_records)) * 100

        for model, stats in by_model.items():
            model_records = [r for r in recent_records if r.model == model]
            latencies = [r.latency_ms for r in model_records]
            stats["avg_latency_ms"] = sum(latencies) / len(latencies)

        return {
            "tenant_id": self.policy.tenant_id,
            "period_days": days,
            "total_requests": len(recent_records),
            "total_cost_usd": sum(r.cost_usd for r in recent_records),
            "total_tokens": sum(r.tokens_total for r in recent_records),
            "by_provider": by_provider,
            "by_model": by_model,
            "budget_remaining_usd": max(0, self.policy.monthly_budget_usd - self._monthly_spend),
            "budget_used_pct": (self._monthly_spend / self.policy.monthly_budget_usd * 100)
                if self.policy.monthly_budget_usd > 0 else 0,
        }

    def reset_monthly_budget(self) -> None:
        """Reset monthly budget counter (call at start of billing period)."""
        self._monthly_spend = 0.0

    def _reset_daily_budget_if_needed(self) -> None:
        """Reset daily budget if new day."""
        current_date = datetime.utcnow().date()
        if current_date > self._last_daily_reset:
            self._daily_spend = 0.0
            self._last_daily_reset = current_date

    def _tier_exceeds_limit(self, model_tier: CostTier, limit_tier: CostTier) -> bool:
        """Check if model tier exceeds limit tier."""
        tier_order = [CostTier.FREE, CostTier.LOW, CostTier.MEDIUM, CostTier.HIGH, CostTier.PREMIUM]
        return tier_order.index(model_tier) > tier_order.index(limit_tier)

    def _check_rate_limits(
        self,
        provider: str,
        policy: ProviderPolicy,
        tokens: int,
    ) -> None:
        """
        Check rate limits for provider.

        Args:
            provider: Provider name
            policy: Provider policy
            tokens: Tokens for this request

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        if provider not in self._rate_limit_state:
            self._rate_limit_state[provider] = {
                "requests": [],  # List of timestamps
                "tokens": [],    # List of (timestamp, token_count) tuples
            }

        now = time.time()
        minute_ago = now - 60

        # Clean old entries
        state = self._rate_limit_state[provider]
        state["requests"] = [t for t in state["requests"] if t > minute_ago]
        state["tokens"] = [(ts, tc) for ts, tc in state["tokens"] if ts > minute_ago]

        # Check RPM limit
        if policy.rate_limit_rpm > 0 and len(state["requests"]) >= policy.rate_limit_rpm:
            raise RateLimitExceededError(
                f"Rate limit exceeded for provider '{provider}': "
                f"{len(state['requests'])} requests in last minute (limit: {policy.rate_limit_rpm} RPM)."
            )

        # Check TPM limit - sum only the token counts from tuples
        tokens_in_window = sum(tc for _, tc in state["tokens"])
        if policy.rate_limit_tpm > 0 and tokens_in_window + tokens > policy.rate_limit_tpm:
            raise RateLimitExceededError(
                f"Token rate limit exceeded for provider '{provider}': "
                f"{tokens_in_window + tokens} tokens would exceed limit ({policy.rate_limit_tpm} TPM)."
            )

        # Record this request
        state["requests"].append(now)
        state["tokens"].append((now, tokens))


def get_model_pricing(provider: str, model: str) -> Optional[Tuple[float, float]]:
    """
    Get pricing for a specific provider/model combination.

    Used by telemetry system for automatic cost calculation.

    Args:
        provider: Provider name (openai, anthropic, ollama, azure)
        model: Model identifier

    Returns:
        Tuple of (input_cost_per_1k_tokens, output_cost_per_1k_tokens) or None if not found

    Example:
        >>> get_model_pricing("openai", "gpt-4o")
        (0.0025, 0.01)
        >>> get_model_pricing("anthropic", "claude-sonnet-4-5-20250929")
        (0.003, 0.015)
    """
    # Normalize provider name
    provider_lower = provider.lower()

    # Try direct model lookup
    if model in MODEL_COSTS:
        return MODEL_COSTS[model]

    # Try with provider-specific prefixes
    for prefix in ["azure-", "claude-", "gpt-"]:
        prefixed_model = f"{prefix}{model}"
        if prefixed_model in MODEL_COSTS:
            return MODEL_COSTS[prefixed_model]

    # For ollama/local models, return free
    if provider_lower in ["ollama", "local"]:
        return (0.0, 0.0)

    # Unknown model
    return None


# Custom exceptions for policy enforcement

class PolicyViolationError(LLMError):
    """Raised when a request violates LLM usage policy."""

    def __init__(self, message: str):
        super().__init__(message=message)


class ProviderDisabledError(PolicyViolationError):
    """Raised when attempting to use a disabled provider."""
    pass


class BudgetExceededError(PolicyViolationError):
    """Raised when budget limit would be exceeded."""
    pass


class RateLimitExceededError(PolicyViolationError):
    """Raised when rate limit is exceeded."""
    pass


class FallbackToLocalError(Exception):
    """
    Raised when budget exceeded but local fallback is available.

    This is a special exception that signals the caller should retry
    with a local model (e.g., Ollama) instead of failing outright.
    """
    pass
