"""
Tests for LLM Policy Enforcement.

Tests cover:
    - Provider policy configuration and validation
    - Tenant policy configuration
    - Policy enforcement (models, tokens, costs, budgets)
    - Rate limiting (RPM and TPM)
    - Cost estimation
    - Usage tracking and reporting
    - Budget management (daily/monthly)
    - Fallback to local models
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from netrun.llm.policies import (
    ProviderPolicy,
    TenantPolicy,
    PolicyEnforcer,
    UsageRecord,
    CostTier,
    MODEL_COSTS,
    MODEL_COST_TIERS,
    PolicyViolationError,
    ProviderDisabledError,
    BudgetExceededError,
    RateLimitExceededError,
    FallbackToLocalError,
)


class TestProviderPolicy:
    """Tests for ProviderPolicy configuration."""

    def test_default_provider_policy(self):
        """Test default provider policy settings."""
        policy = ProviderPolicy(provider="openai")

        assert policy.provider == "openai"
        assert policy.allowed_models == []  # Empty = all allowed
        assert policy.denied_models == []
        assert policy.max_tokens_per_request == 4096
        assert policy.max_cost_per_request == 1.0
        assert policy.rate_limit_rpm == 60
        assert policy.rate_limit_tpm == 100000
        assert policy.cost_tier_limit is None
        assert policy.require_reason is False
        assert policy.enabled is True

    def test_custom_provider_policy(self):
        """Test custom provider policy configuration."""
        policy = ProviderPolicy(
            provider="anthropic",
            allowed_models=["claude-3-haiku", "claude-3-5-sonnet"],
            max_tokens_per_request=8192,
            max_cost_per_request=0.50,
            rate_limit_rpm=30,
            cost_tier_limit=CostTier.MEDIUM,
            require_reason=True,
        )

        assert policy.provider == "anthropic"
        assert policy.allowed_models == ["claude-3-haiku", "claude-3-5-sonnet"]
        assert policy.max_tokens_per_request == 8192
        assert policy.max_cost_per_request == 0.50
        assert policy.rate_limit_rpm == 30
        assert policy.cost_tier_limit == CostTier.MEDIUM
        assert policy.require_reason is True

    def test_denied_models(self):
        """Test denied models configuration."""
        policy = ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini", "gpt-4o", "gpt-4"],
            denied_models=["gpt-4"],  # Explicitly deny expensive model
        )

        assert "gpt-4" in policy.denied_models
        assert "gpt-4o-mini" not in policy.denied_models

    def test_disabled_provider(self):
        """Test disabled provider configuration."""
        policy = ProviderPolicy(
            provider="bedrock",
            enabled=False,
        )

        assert policy.enabled is False


class TestTenantPolicy:
    """Tests for TenantPolicy configuration."""

    def test_default_tenant_policy(self):
        """Test default tenant policy settings."""
        policy = TenantPolicy(tenant_id="test-tenant")

        assert policy.tenant_id == "test-tenant"
        assert policy.monthly_budget_usd == 100.0
        assert policy.daily_budget_usd is None
        assert policy.provider_policies == {}
        assert policy.default_provider == "openai"
        assert policy.fallback_to_local is True
        assert policy.track_usage is True
        assert policy.alert_threshold_pct == 80.0

    def test_custom_tenant_policy(self):
        """Test custom tenant policy configuration."""
        openai_policy = ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini"],
            max_cost_per_request=0.05,
        )

        policy = TenantPolicy(
            tenant_id="acme-corp",
            monthly_budget_usd=500.0,
            daily_budget_usd=20.0,
            provider_policies={"openai": openai_policy},
            default_provider="anthropic",
            fallback_to_local=False,
            alert_threshold_pct=90.0,
        )

        assert policy.tenant_id == "acme-corp"
        assert policy.monthly_budget_usd == 500.0
        assert policy.daily_budget_usd == 20.0
        assert "openai" in policy.provider_policies
        assert policy.default_provider == "anthropic"
        assert policy.fallback_to_local is False
        assert policy.alert_threshold_pct == 90.0

    def test_tenant_id_validation(self):
        """Test tenant_id validation."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            TenantPolicy(tenant_id="")

        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            TenantPolicy(tenant_id="   ")


class TestPolicyEnforcer:
    """Tests for PolicyEnforcer validation and tracking."""

    def test_basic_validation_success(self):
        """Test successful validation with basic policy."""
        policy = TenantPolicy(
            tenant_id="test",
            monthly_budget_usd=100.0,
        )
        enforcer = PolicyEnforcer(policy)

        # Should not raise
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )

    def test_denied_model_validation(self):
        """Test validation fails for denied models."""
        openai_policy = ProviderPolicy(
            provider="openai",
            denied_models=["gpt-4"],
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        with pytest.raises(PolicyViolationError, match="explicitly denied"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4",
                estimated_tokens=1000,
            )

    def test_allowed_models_validation(self):
        """Test validation with allowed models list."""
        openai_policy = ProviderPolicy(
            provider="openai",
            allowed_models=["gpt-4o-mini", "gpt-4o"],
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # Allowed model should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )

        # Disallowed model should fail
        with pytest.raises(PolicyViolationError, match="not in allowed list"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4-turbo",
                estimated_tokens=1000,
            )

    def test_token_limit_validation(self):
        """Test token limit enforcement."""
        openai_policy = ProviderPolicy(
            provider="openai",
            max_tokens_per_request=2000,
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # Within limit
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1500,
        )

        # Exceeds limit
        with pytest.raises(PolicyViolationError, match="exceeds limit"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=3000,
            )

    def test_cost_per_request_limit(self):
        """Test per-request cost limit enforcement."""
        openai_policy = ProviderPolicy(
            provider="openai",
            max_cost_per_request=0.01,  # Very low limit
            max_tokens_per_request=100000,  # High token limit so cost check triggers first
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # Small request should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=500,
        )

        # Large request should fail on cost (not token limit)
        # gpt-4o-mini: $0.00015/1K input + $0.0006/1K output = ~$0.000285/1K tokens
        # 50000 tokens = ~$0.014 which exceeds $0.01 limit
        with pytest.raises(PolicyViolationError, match="exceeds per-request limit"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=50000,
            )

    def test_cost_tier_limit(self):
        """Test cost tier limit enforcement."""
        openai_policy = ProviderPolicy(
            provider="openai",
            cost_tier_limit=CostTier.LOW,
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # Low tier model should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )

        # Medium tier model should fail
        with pytest.raises(PolicyViolationError, match="tier.*exceeds limit"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o",
                estimated_tokens=1000,
            )

    def test_monthly_budget_enforcement(self):
        """Test monthly budget enforcement."""
        policy = TenantPolicy(
            tenant_id="test",
            monthly_budget_usd=1.0,  # Very low budget
            fallback_to_local=False,
        )
        enforcer = PolicyEnforcer(policy)

        # First request should pass
        enforcer.validate_request(
            provider="anthropic",
            model="claude-3-opus",  # Expensive model for meaningful cost
            estimated_tokens=1000,
        )

        # Record high usage (just under budget)
        enforcer.record_usage(
            provider="anthropic",
            model="claude-3-opus",
            tokens_input=500,
            tokens_output=500,
            cost_usd=0.95,  # $0.95 recorded
            latency_ms=1000,
            success=True,
        )

        # Next request should fail (would exceed $1.00 budget)
        # claude-3-opus: $0.015/1K input + $0.075/1K output = ~$0.033/1K tokens
        # 2000 tokens = ~$0.066 estimated, $0.95 + $0.066 > $1.00
        with pytest.raises(BudgetExceededError, match="Monthly budget"):
            enforcer.validate_request(
                provider="anthropic",
                model="claude-3-opus",
                estimated_tokens=2000,
            )

    def test_daily_budget_enforcement(self):
        """Test daily budget enforcement."""
        policy = TenantPolicy(
            tenant_id="test",
            monthly_budget_usd=100.0,
            daily_budget_usd=1.0,  # Very low daily budget
            fallback_to_local=False,
        )
        enforcer = PolicyEnforcer(policy)

        # Record high daily usage (just under daily budget)
        enforcer.record_usage(
            provider="anthropic",
            model="claude-3-opus",
            tokens_input=500,
            tokens_output=500,
            cost_usd=0.95,  # $0.95 recorded
            latency_ms=1000,
            success=True,
        )

        # Next request should fail (would exceed daily budget)
        # claude-3-opus: ~$0.066 for 2000 tokens, $0.95 + $0.066 > $1.00
        with pytest.raises(BudgetExceededError, match="Daily budget"):
            enforcer.validate_request(
                provider="anthropic",
                model="claude-3-opus",
                estimated_tokens=2000,
            )

    def test_fallback_to_local(self):
        """Test fallback to local when budget exceeded."""
        policy = TenantPolicy(
            tenant_id="test",
            monthly_budget_usd=1.0,
            fallback_to_local=True,  # Enable fallback
        )
        enforcer = PolicyEnforcer(policy)

        # Record high usage (just under budget)
        enforcer.record_usage(
            provider="anthropic",
            model="claude-3-opus",
            tokens_input=500,
            tokens_output=500,
            cost_usd=0.95,  # $0.95 recorded
            latency_ms=1000,
            success=True,
        )

        # Should raise FallbackToLocalError (not BudgetExceededError)
        # because fallback_to_local=True
        # claude-3-opus: ~$0.066 for 2000 tokens, $0.95 + $0.066 > $1.00
        with pytest.raises(FallbackToLocalError, match="Fallback to local"):
            enforcer.validate_request(
                provider="anthropic",
                model="claude-3-opus",
                estimated_tokens=2000,
            )

    def test_disabled_provider(self):
        """Test disabled provider enforcement."""
        openai_policy = ProviderPolicy(
            provider="openai",
            enabled=False,
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        with pytest.raises(ProviderDisabledError, match="disabled"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=1000,
            )

    def test_require_reason(self):
        """Test reason requirement enforcement."""
        openai_policy = ProviderPolicy(
            provider="openai",
            require_reason=True,
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # Without reason should fail
        with pytest.raises(PolicyViolationError, match="Reason required"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=1000,
            )

        # With reason should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
            reason="Customer support chatbot",
        )

    def test_rate_limit_rpm(self):
        """Test requests per minute rate limiting."""
        openai_policy = ProviderPolicy(
            provider="openai",
            rate_limit_rpm=2,  # Very low limit for testing
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # First two requests should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=100,
        )
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=100,
        )

        # Third request should fail
        with pytest.raises(RateLimitExceededError, match="Rate limit exceeded"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=100,
            )

    def test_rate_limit_tpm(self):
        """Test tokens per minute rate limiting."""
        openai_policy = ProviderPolicy(
            provider="openai",
            rate_limit_tpm=1000,  # Low limit for testing
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # First request (500 tokens) should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=500,
        )

        # Second request (400 tokens) should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=400,
        )

        # Third request (200 tokens) should fail (would exceed 1000)
        with pytest.raises(RateLimitExceededError, match="Token rate limit exceeded"):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=200,
            )


class TestCostEstimation:
    """Tests for cost estimation."""

    def test_cost_estimation_gpt4o_mini(self):
        """Test cost estimation for GPT-4o-mini."""
        policy = TenantPolicy(tenant_id="test")
        enforcer = PolicyEnforcer(policy)

        # 1000 tokens: 700 input, 300 output
        cost = enforcer.estimate_cost("gpt-4o-mini", 1000, input_ratio=0.7)

        input_cost, output_cost = MODEL_COSTS["gpt-4o-mini"]
        expected = (700 * input_cost + 300 * output_cost) / 1000

        assert abs(cost - expected) < 0.0001

    def test_cost_estimation_claude_sonnet(self):
        """Test cost estimation for Claude Sonnet."""
        policy = TenantPolicy(tenant_id="test")
        enforcer = PolicyEnforcer(policy)

        cost = enforcer.estimate_cost("claude-3-5-sonnet", 2000, input_ratio=0.6)

        input_cost, output_cost = MODEL_COSTS["claude-3-5-sonnet"]
        expected = (1200 * input_cost + 800 * output_cost) / 1000

        assert abs(cost - expected) < 0.0001

    def test_cost_estimation_unknown_model(self):
        """Test cost estimation for unknown model (assumed free)."""
        policy = TenantPolicy(tenant_id="test")
        enforcer = PolicyEnforcer(policy)

        cost = enforcer.estimate_cost("unknown-model", 1000)
        assert cost == 0.0

    def test_cost_estimation_local_model(self):
        """Test cost estimation for local model (free)."""
        policy = TenantPolicy(tenant_id="test")
        enforcer = PolicyEnforcer(policy)

        cost = enforcer.estimate_cost("llama3", 10000)
        assert cost == 0.0


class TestUsageTracking:
    """Tests for usage tracking and reporting."""

    def test_record_usage(self):
        """Test usage recording."""
        policy = TenantPolicy(tenant_id="test", track_usage=True)
        enforcer = PolicyEnforcer(policy)

        enforcer.record_usage(
            provider="openai",
            model="gpt-4o-mini",
            tokens_input=500,
            tokens_output=300,
            cost_usd=0.0005,
            latency_ms=1200,
            success=True,
            reason="Test request",
        )

        assert len(enforcer.usage_records) == 1
        record = enforcer.usage_records[0]

        assert record.tenant_id == "test"
        assert record.provider == "openai"
        assert record.model == "gpt-4o-mini"
        assert record.tokens_input == 500
        assert record.tokens_output == 300
        assert record.tokens_total == 800
        assert record.cost_usd == 0.0005
        assert record.latency_ms == 1200
        assert record.success is True
        assert record.reason == "Test request"

    def test_usage_tracking_disabled(self):
        """Test usage tracking can be disabled."""
        policy = TenantPolicy(tenant_id="test", track_usage=False)
        enforcer = PolicyEnforcer(policy)

        enforcer.record_usage(
            provider="openai",
            model="gpt-4o-mini",
            tokens_input=500,
            tokens_output=300,
            cost_usd=0.0005,
            latency_ms=1200,
            success=True,
        )

        assert len(enforcer.usage_records) == 0

    def test_usage_report_empty(self):
        """Test usage report with no records."""
        policy = TenantPolicy(tenant_id="test")
        enforcer = PolicyEnforcer(policy)

        report = enforcer.get_usage_report(days=30)

        assert report["tenant_id"] == "test"
        assert report["period_days"] == 30
        assert report["total_requests"] == 0
        assert report["total_cost_usd"] == 0.0
        assert report["total_tokens"] == 0
        assert report["by_provider"] == {}
        assert report["by_model"] == {}

    def test_usage_report_with_data(self):
        """Test usage report with multiple records."""
        policy = TenantPolicy(tenant_id="test", monthly_budget_usd=100.0)
        enforcer = PolicyEnforcer(policy)

        # Record multiple requests
        enforcer.record_usage(
            provider="openai",
            model="gpt-4o-mini",
            tokens_input=500,
            tokens_output=300,
            cost_usd=0.001,
            latency_ms=1000,
            success=True,
        )
        enforcer.record_usage(
            provider="openai",
            model="gpt-4o",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.010,
            latency_ms=2000,
            success=True,
        )
        enforcer.record_usage(
            provider="anthropic",
            model="claude-3-5-sonnet",
            tokens_input=800,
            tokens_output=400,
            cost_usd=0.008,
            latency_ms=1500,
            success=True,
        )

        report = enforcer.get_usage_report(days=30)

        assert report["total_requests"] == 3
        assert report["total_cost_usd"] == 0.019
        assert report["total_tokens"] == 3500

        # Check by provider
        assert "openai" in report["by_provider"]
        assert report["by_provider"]["openai"]["requests"] == 2
        assert report["by_provider"]["openai"]["cost_usd"] == 0.011

        assert "anthropic" in report["by_provider"]
        assert report["by_provider"]["anthropic"]["requests"] == 1
        assert report["by_provider"]["anthropic"]["cost_usd"] == 0.008

        # Check by model
        assert "gpt-4o-mini" in report["by_model"]
        assert report["by_model"]["gpt-4o-mini"]["requests"] == 1
        assert report["by_model"]["gpt-4o"]["requests"] == 1
        assert report["by_model"]["claude-3-5-sonnet"]["requests"] == 1

        # Check budget remaining
        assert report["budget_remaining_usd"] == pytest.approx(99.981)
        assert report["budget_used_pct"] == pytest.approx(0.019)

    def test_daily_budget_reset(self):
        """Test daily budget resets at midnight."""
        policy = TenantPolicy(
            tenant_id="test",
            monthly_budget_usd=100.0,
            daily_budget_usd=10.0,
        )
        enforcer = PolicyEnforcer(policy)

        # Record usage today
        enforcer.record_usage(
            provider="openai",
            model="gpt-4o-mini",
            tokens_input=500,
            tokens_output=300,
            cost_usd=5.0,
            latency_ms=1000,
            success=True,
        )

        assert enforcer._daily_spend == 5.0

        # Simulate day change
        enforcer._last_daily_reset = (datetime.utcnow() - timedelta(days=1)).date()
        enforcer._reset_daily_budget_if_needed()

        assert enforcer._daily_spend == 0.0

    def test_monthly_budget_reset(self):
        """Test manual monthly budget reset."""
        policy = TenantPolicy(tenant_id="test", monthly_budget_usd=100.0)
        enforcer = PolicyEnforcer(policy)

        # Record usage
        enforcer.record_usage(
            provider="openai",
            model="gpt-4o-mini",
            tokens_input=500,
            tokens_output=300,
            cost_usd=50.0,
            latency_ms=1000,
            success=True,
        )

        assert enforcer._monthly_spend == 50.0

        # Reset monthly budget
        enforcer.reset_monthly_budget()

        assert enforcer._monthly_spend == 0.0


class TestCostTiers:
    """Tests for cost tier classification."""

    def test_model_cost_tiers(self):
        """Test model to cost tier mappings."""
        assert MODEL_COST_TIERS["llama3"] == CostTier.FREE
        assert MODEL_COST_TIERS["gpt-4o-mini"] == CostTier.LOW
        assert MODEL_COST_TIERS["claude-3-5-sonnet"] == CostTier.MEDIUM
        assert MODEL_COST_TIERS["gpt-4"] == CostTier.HIGH
        assert MODEL_COST_TIERS["o1-preview"] == CostTier.PREMIUM

    def test_cost_tier_enforcement(self):
        """Test cost tier limit enforcement."""
        openai_policy = ProviderPolicy(
            provider="openai",
            cost_tier_limit=CostTier.LOW,
        )
        policy = TenantPolicy(
            tenant_id="test",
            provider_policies={"openai": openai_policy},
        )
        enforcer = PolicyEnforcer(policy)

        # LOW tier should pass
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )

        # MEDIUM tier should fail
        with pytest.raises(PolicyViolationError):
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o",
                estimated_tokens=1000,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
