"""
Comprehensive tests for LLM configuration management.

Tests cover:
    - Placeholder resolution
    - Configuration initialization
    - Environment variable resolution
    - Configuration validation
    - API key getters
"""

import pytest
import os
from netrun.llm.config import (
    resolve_placeholder,
    PLACEHOLDER_PATTERN,
    LLMConfig,
)


class TestPlaceholderResolution:
    """Test placeholder pattern resolution."""

    def test_resolve_placeholder_with_env_var(self, monkeypatch):
        """Test resolving placeholder from environment variable."""
        monkeypatch.setenv("MY_API_KEY", "sk-12345")

        result = resolve_placeholder("{{MY_API_KEY}}")

        assert result == "sk-12345"

    def test_resolve_placeholder_without_env_var(self, monkeypatch):
        """Test resolving placeholder when env var not set."""
        monkeypatch.delenv("MY_API_KEY", raising=False)

        result = resolve_placeholder("{{MY_API_KEY}}")

        assert result is None

    def test_resolve_placeholder_with_direct_value(self):
        """Test passing through non-placeholder values."""
        result = resolve_placeholder("direct-value")

        assert result == "direct-value"

    def test_resolve_placeholder_with_none(self):
        """Test handling None value."""
        result = resolve_placeholder(None)

        assert result is None

    def test_placeholder_pattern_matches_valid(self):
        """Test placeholder pattern matches valid placeholders."""
        assert PLACEHOLDER_PATTERN.match("{{API_KEY}}") is not None
        assert PLACEHOLDER_PATTERN.match("{{MY_SECRET_123}}") is not None
        assert PLACEHOLDER_PATTERN.match("{{ANTHROPIC_API_KEY}}") is not None

    def test_placeholder_pattern_rejects_invalid(self):
        """Test placeholder pattern rejects invalid patterns."""
        assert PLACEHOLDER_PATTERN.match("{{api_key}}") is None  # lowercase
        assert PLACEHOLDER_PATTERN.match("{{123_KEY}}") is None  # starts with number
        assert PLACEHOLDER_PATTERN.match("{API_KEY}") is None  # single braces
        assert PLACEHOLDER_PATTERN.match("API_KEY") is None  # no braces


class TestLLMConfigInitialization:
    """Test LLMConfig initialization."""

    def test_default_initialization(self):
        """Test config initializes with default values."""
        config = LLMConfig()

        assert config.anthropic_api_key == "{{ANTHROPIC_API_KEY}}"
        assert config.openai_api_key == "{{OPENAI_API_KEY}}"
        assert config.ollama_host == "{{OLLAMA_HOST}}"
        assert config.default_model_claude == "claude-sonnet-4-5-20250929"
        assert config.default_model_openai == "gpt-4-turbo"
        assert config.default_model_ollama == "llama3"
        assert config.default_max_tokens == 4096
        assert config.default_temperature == 1.0
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_cooldown == 300
        assert config.request_timeout == 30

    def test_initialization_with_custom_values(self):
        """Test config initialization with custom values."""
        config = LLMConfig(
            anthropic_api_key="custom-claude-key",
            openai_api_key="custom-openai-key",
            default_model_claude="claude-3-opus-20240229",
            default_max_tokens=8000,
            default_temperature=0.7,
            circuit_breaker_threshold=10,
        )

        assert config.anthropic_api_key == "custom-claude-key"
        assert config.openai_api_key == "custom-openai-key"
        assert config.default_model_claude == "claude-3-opus-20240229"
        assert config.default_max_tokens == 8000
        assert config.default_temperature == 0.7
        assert config.circuit_breaker_threshold == 10

    def test_custom_settings_field(self):
        """Test custom_settings field for adapter-specific config."""
        config = LLMConfig(
            custom_settings={"custom_adapter": {"param1": "value1"}}
        )

        assert "custom_adapter" in config.custom_settings
        assert config.custom_settings["custom_adapter"]["param1"] == "value1"


class TestLLMConfigAPIKeyGetters:
    """Test API key getter methods."""

    def test_get_anthropic_api_key(self, monkeypatch):
        """Test getting resolved Anthropic API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-claude-12345")

        config = LLMConfig()
        api_key = config.get_anthropic_api_key()

        assert api_key == "sk-claude-12345"

    def test_get_openai_api_key(self, monkeypatch):
        """Test getting resolved OpenAI API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-12345")

        config = LLMConfig()
        api_key = config.get_openai_api_key()

        assert api_key == "sk-openai-12345"

    def test_get_ollama_host_with_env_var(self, monkeypatch):
        """Test getting Ollama host from environment."""
        monkeypatch.setenv("OLLAMA_HOST", "http://custom-ollama:11434")

        config = LLMConfig()
        host = config.get_ollama_host()

        assert host == "http://custom-ollama:11434"

    def test_get_ollama_host_default_when_not_set(self, monkeypatch):
        """Test Ollama host defaults to localhost."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)

        config = LLMConfig()
        host = config.get_ollama_host()

        assert host == "http://localhost:11434"

    def test_get_azure_openai_endpoint(self, monkeypatch):
        """Test getting Azure OpenAI endpoint."""
        monkeypatch.setenv(
            "AZURE_OPENAI_ENDPOINT", "https://my-azure.openai.azure.com"
        )

        config = LLMConfig()
        endpoint = config.get_azure_openai_endpoint()

        assert endpoint == "https://my-azure.openai.azure.com"

    def test_get_azure_openai_key(self, monkeypatch):
        """Test getting Azure OpenAI key."""
        monkeypatch.setenv("AZURE_OPENAI_KEY", "azure-key-12345")

        config = LLMConfig()
        key = config.get_azure_openai_key()

        assert key == "azure-key-12345"


class TestLLMConfigFromEnv:
    """Test creating config from environment variables."""

    def test_from_env_with_defaults(self):
        """Test from_env uses default values when env vars not set."""
        config = LLMConfig.from_env()

        assert config.anthropic_api_key == "{{ANTHROPIC_API_KEY}}"
        assert config.openai_api_key == "{{OPENAI_API_KEY}}"
        assert config.default_model_claude == "claude-sonnet-4-5-20250929"
        assert config.default_model_openai == "gpt-4-turbo"

    def test_from_env_with_custom_env_vars(self, monkeypatch):
        """Test from_env reads custom values from environment."""
        monkeypatch.setenv("LLM_DEFAULT_MODEL_CLAUDE", "claude-3-haiku-20240307")
        monkeypatch.setenv("LLM_DEFAULT_MODEL_OPENAI", "gpt-4o")
        monkeypatch.setenv("LLM_DEFAULT_MODEL_OLLAMA", "codellama")
        monkeypatch.setenv("LLM_DEFAULT_MAX_TOKENS", "2048")
        monkeypatch.setenv("LLM_DEFAULT_TEMPERATURE", "0.5")
        monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "60")
        monkeypatch.setenv("LLM_MAX_RETRIES", "5")

        config = LLMConfig.from_env()

        assert config.default_model_claude == "claude-3-haiku-20240307"
        assert config.default_model_openai == "gpt-4o"
        assert config.default_model_ollama == "codellama"
        assert config.default_max_tokens == 2048
        assert config.default_temperature == 0.5
        assert config.request_timeout == 60
        assert config.max_retries == 5


class TestLLMConfigValidation:
    """Test configuration validation."""

    def test_validation_with_claude_configured(self, monkeypatch):
        """Test validation passes with Claude API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-12345")

        config = LLMConfig()
        issues = config.validate()

        assert len(issues) == 0

    def test_validation_with_openai_configured(self, monkeypatch):
        """Test validation passes with OpenAI API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-12345")

        config = LLMConfig()
        issues = config.validate()

        assert len(issues) == 0

    def test_validation_with_ollama_configured(self, monkeypatch):
        """Test validation passes with Ollama host."""
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")

        config = LLMConfig()
        issues = config.validate()

        assert len(issues) == 0

    def test_validation_with_azure_configured(self, monkeypatch):
        """Test validation passes with Azure OpenAI."""
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://my-azure.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_KEY", "azure-key-12345")

        config = LLMConfig()
        issues = config.validate()

        assert len(issues) == 0

    def test_validation_without_providers(self, monkeypatch):
        """Test validation passes when Ollama defaults to localhost."""
        # Clear all provider env vars
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)

        config = LLMConfig(
            anthropic_api_key=None,
            openai_api_key=None,
            ollama_host=None,
            azure_openai_endpoint=None,
            azure_openai_key=None,
        )
        issues = config.validate()

        # Validation should pass because Ollama defaults to localhost
        # This is intentional behavior - local Ollama is a valid default
        assert len(issues) == 0

    def test_validation_invalid_max_tokens(self):
        """Test validation detects invalid max_tokens."""
        config = LLMConfig(default_max_tokens=0)
        issues = config.validate()

        assert any("default_max_tokens must be positive" in issue for issue in issues)

    def test_validation_invalid_temperature(self):
        """Test validation detects invalid temperature."""
        config = LLMConfig(default_temperature=3.0)
        issues = config.validate()

        assert any(
            "default_temperature must be between 0.0 and 2.0" in issue
            for issue in issues
        )

    def test_validation_invalid_circuit_breaker_threshold(self):
        """Test validation detects invalid circuit breaker threshold."""
        config = LLMConfig(circuit_breaker_threshold=0)
        issues = config.validate()

        assert any(
            "circuit_breaker_threshold must be at least 1" in issue
            for issue in issues
        )

    def test_validation_invalid_timeout(self):
        """Test validation detects invalid timeout."""
        config = LLMConfig(request_timeout=0)
        issues = config.validate()

        assert any(
            "request_timeout must be at least 1 second" in issue
            for issue in issues
        )

    def test_validation_multiple_issues(self):
        """Test validation returns all issues."""
        config = LLMConfig(
            default_max_tokens=-1,
            default_temperature=5.0,
            circuit_breaker_threshold=0,
        )
        issues = config.validate()

        # Should have at least 3 issues
        assert len(issues) >= 3
