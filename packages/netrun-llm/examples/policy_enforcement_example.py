"""
LLM Policy Enforcement - Integration Examples

This example demonstrates how to use the policy enforcement system to control
LLM usage, costs, and rate limits in multi-tenant applications.

Examples:
    - Basic policy configuration
    - Cost-conscious tenant policies
    - Budget enforcement with fallback
    - Rate limiting
    - Usage tracking and reporting

Author: Netrun Systems
"""

import asyncio
from netrun.llm import (
    TenantPolicy,
    ProviderPolicy,
    PolicyEnforcer,
    CostTier,
    PolicyViolationError,
    BudgetExceededError,
    FallbackToLocalError,
    LLMFallbackChain,
    ClaudeAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    LLMConfig,
)


def example_basic_policy():
    """Example 1: Basic policy configuration."""
    print("\n=== Example 1: Basic Policy Configuration ===\n")

    # Create a simple policy for a tenant
    policy = TenantPolicy(
        tenant_id="startup-corp",
        monthly_budget_usd=50.0,
        provider_policies={
            "openai": ProviderPolicy(
                provider="openai",
                allowed_models=["gpt-4o-mini", "gpt-4o"],
                max_tokens_per_request=4096,
                max_cost_per_request=0.10,
            ),
        },
    )

    # Create enforcer
    enforcer = PolicyEnforcer(policy)

    # Validate a request
    try:
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=2000,
        )
        print("✓ Request validated successfully")
    except PolicyViolationError as e:
        print(f"✗ Policy violation: {e}")


def example_cost_conscious_policy():
    """Example 2: Cost-conscious policy with tier limits."""
    print("\n=== Example 2: Cost-Conscious Policy ===\n")

    # Restrict to low-cost models only
    policy = TenantPolicy(
        tenant_id="budget-startup",
        monthly_budget_usd=20.0,
        daily_budget_usd=2.0,
        provider_policies={
            "openai": ProviderPolicy(
                provider="openai",
                cost_tier_limit=CostTier.LOW,  # Only LOW tier models
                max_cost_per_request=0.01,
            ),
            "anthropic": ProviderPolicy(
                provider="anthropic",
                cost_tier_limit=CostTier.LOW,
                max_cost_per_request=0.01,
            ),
        },
        fallback_to_local=True,
    )

    enforcer = PolicyEnforcer(policy)

    # Try a low-cost model (should pass)
    try:
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )
        print("✓ Low-cost model (gpt-4o-mini) allowed")
    except PolicyViolationError as e:
        print(f"✗ {e}")

    # Try a high-cost model (should fail)
    try:
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o",
            estimated_tokens=1000,
        )
        print("✓ High-cost model (gpt-4o) allowed")
    except PolicyViolationError as e:
        print(f"✗ High-cost model rejected: {e}")


def example_budget_enforcement():
    """Example 3: Budget enforcement with fallback."""
    print("\n=== Example 3: Budget Enforcement with Fallback ===\n")

    policy = TenantPolicy(
        tenant_id="test-corp",
        monthly_budget_usd=1.0,  # Very low budget for testing
        fallback_to_local=True,
    )

    enforcer = PolicyEnforcer(policy)

    # Simulate high usage
    enforcer.record_usage(
        provider="openai",
        model="gpt-4o-mini",
        tokens_input=5000,
        tokens_output=3000,
        cost_usd=0.95,
        latency_ms=1200,
        success=True,
    )

    print(f"Current spend: ${enforcer._monthly_spend:.2f}")

    # Try another request (should trigger fallback)
    try:
        enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )
        print("✓ Request allowed")
    except FallbackToLocalError as e:
        print(f"✓ Budget limit reached, fallback recommended: {e}")
    except BudgetExceededError as e:
        print(f"✗ Budget exceeded: {e}")


def example_rate_limiting():
    """Example 4: Rate limiting."""
    print("\n=== Example 4: Rate Limiting ===\n")

    policy = TenantPolicy(
        tenant_id="api-service",
        provider_policies={
            "openai": ProviderPolicy(
                provider="openai",
                rate_limit_rpm=3,  # 3 requests per minute
                rate_limit_tpm=5000,  # 5000 tokens per minute
            ),
        },
    )

    enforcer = PolicyEnforcer(policy)

    # Make several requests
    for i in range(5):
        try:
            enforcer.validate_request(
                provider="openai",
                model="gpt-4o-mini",
                estimated_tokens=500,
            )
            print(f"✓ Request {i+1} allowed")
        except PolicyViolationError as e:
            print(f"✗ Request {i+1} blocked: {e}")


def example_usage_tracking():
    """Example 5: Usage tracking and reporting."""
    print("\n=== Example 5: Usage Tracking and Reporting ===\n")

    policy = TenantPolicy(
        tenant_id="analytics-corp",
        monthly_budget_usd=100.0,
        track_usage=True,
    )

    enforcer = PolicyEnforcer(policy)

    # Record several requests
    enforcer.record_usage(
        provider="openai",
        model="gpt-4o-mini",
        tokens_input=500,
        tokens_output=300,
        cost_usd=0.0005,
        latency_ms=800,
        success=True,
        reason="Customer support chatbot",
    )

    enforcer.record_usage(
        provider="openai",
        model="gpt-4o",
        tokens_input=1000,
        tokens_output=600,
        cost_usd=0.008,
        latency_ms=1500,
        success=True,
        reason="Document analysis",
    )

    enforcer.record_usage(
        provider="anthropic",
        model="claude-3-5-sonnet",
        tokens_input=800,
        tokens_output=500,
        cost_usd=0.007,
        latency_ms=1200,
        success=True,
        reason="Content generation",
    )

    # Get usage report
    report = enforcer.get_usage_report(days=30)

    print(f"Total requests: {report['total_requests']}")
    print(f"Total cost: ${report['total_cost_usd']:.4f}")
    print(f"Total tokens: {report['total_tokens']}")
    print(f"Budget remaining: ${report['budget_remaining_usd']:.2f}")
    print(f"Budget used: {report['budget_used_pct']:.2f}%")

    print("\nBy Provider:")
    for provider, stats in report['by_provider'].items():
        print(f"  {provider}: {stats['requests']} requests, ${stats['cost_usd']:.4f}")

    print("\nBy Model:")
    for model, stats in report['by_model'].items():
        print(f"  {model}: {stats['requests']} requests, ${stats['cost_usd']:.4f}")


async def example_integration_with_fallback_chain():
    """Example 6: Integration with LLMFallbackChain."""
    print("\n=== Example 6: Integration with Fallback Chain ===\n")

    # Create policy
    policy = TenantPolicy(
        tenant_id="production-app",
        monthly_budget_usd=200.0,
        provider_policies={
            "anthropic": ProviderPolicy(
                provider="anthropic",
                allowed_models=["claude-3-5-sonnet"],
                max_cost_per_request=0.50,
            ),
            "openai": ProviderPolicy(
                provider="openai",
                allowed_models=["gpt-4o", "gpt-4o-mini"],
                max_cost_per_request=0.30,
            ),
            "ollama": ProviderPolicy(
                provider="ollama",
                allowed_models=["llama3"],
            ),
        },
        fallback_to_local=True,
    )

    enforcer = PolicyEnforcer(policy)

    # Create LLM config
    config = LLMConfig.from_env()

    # Create fallback chain with policy-compliant adapters
    chain = LLMFallbackChain(
        adapters=[
            ClaudeAdapter(
                config=config,
                adapter_name="claude-primary",
                model="claude-3-5-sonnet",
            ),
            OpenAIAdapter(
                config=config,
                adapter_name="openai-fallback",
                model="gpt-4o-mini",
            ),
            OllamaAdapter(
                config=config,
                adapter_name="ollama-local",
                model="llama3",
            ),
        ]
    )

    # Validate request before execution
    try:
        # Estimate tokens (rough approximation)
        prompt = "Explain the benefits of policy enforcement in LLM applications."
        estimated_tokens = len(prompt.split()) * 1.3 * 2  # Input + output estimate

        enforcer.validate_request(
            provider="anthropic",
            model="claude-3-5-sonnet",
            estimated_tokens=int(estimated_tokens),
            reason="User documentation query",
        )

        # Execute request (in real app)
        # response = await chain.execute_async(prompt)

        # Record usage after execution
        enforcer.record_usage(
            provider="anthropic",
            model="claude-3-5-sonnet",
            tokens_input=20,
            tokens_output=150,
            cost_usd=0.0027,
            latency_ms=1100,
            success=True,
            reason="User documentation query",
        )

        print("✓ Request validated, executed, and tracked successfully")

    except FallbackToLocalError as e:
        print(f"⚠ Falling back to local model: {e}")
        # In real app, retry with Ollama
    except PolicyViolationError as e:
        print(f"✗ Policy violation: {e}")


def example_multi_tenant_isolation():
    """Example 7: Multi-tenant isolation."""
    print("\n=== Example 7: Multi-Tenant Isolation ===\n")

    # Tenant 1: Enterprise customer with high budget
    enterprise_policy = TenantPolicy(
        tenant_id="enterprise-customer",
        monthly_budget_usd=10000.0,
        provider_policies={
            "anthropic": ProviderPolicy(
                provider="anthropic",
                allowed_models=["claude-3-opus", "claude-3-5-sonnet"],
                max_cost_per_request=5.0,
            ),
        },
    )

    # Tenant 2: Startup with limited budget
    startup_policy = TenantPolicy(
        tenant_id="startup-customer",
        monthly_budget_usd=50.0,
        daily_budget_usd=5.0,
        provider_policies={
            "openai": ProviderPolicy(
                provider="openai",
                allowed_models=["gpt-4o-mini"],
                cost_tier_limit=CostTier.LOW,
            ),
        },
        fallback_to_local=True,
    )

    # Create separate enforcers
    enterprise_enforcer = PolicyEnforcer(enterprise_policy)
    startup_enforcer = PolicyEnforcer(startup_policy)

    # Enterprise can use expensive models
    try:
        enterprise_enforcer.validate_request(
            provider="anthropic",
            model="claude-3-opus",
            estimated_tokens=5000,
        )
        print("✓ Enterprise: High-cost model allowed")
    except PolicyViolationError as e:
        print(f"✗ Enterprise: {e}")

    # Startup restricted to low-cost models
    try:
        startup_enforcer.validate_request(
            provider="openai",
            model="gpt-4o",
            estimated_tokens=1000,
        )
        print("✓ Startup: High-cost model allowed")
    except PolicyViolationError as e:
        print(f"✗ Startup: {e}")

    # Startup can use budget models
    try:
        startup_enforcer.validate_request(
            provider="openai",
            model="gpt-4o-mini",
            estimated_tokens=1000,
        )
        print("✓ Startup: Low-cost model allowed")
    except PolicyViolationError as e:
        print(f"✗ Startup: {e}")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("LLM Policy Enforcement - Integration Examples")
    print("="*70)

    # Run synchronous examples
    example_basic_policy()
    example_cost_conscious_policy()
    example_budget_enforcement()
    example_rate_limiting()
    example_usage_tracking()
    example_multi_tenant_isolation()

    # Run async example
    asyncio.run(example_integration_with_fallback_chain())

    print("\n" + "="*70)
    print("Examples completed successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
