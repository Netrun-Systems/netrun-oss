"""
Netrun LLM - Configuration Management

Centralized configuration with environment variable support and placeholder patterns.

Configuration Placeholders:
    Use {{VARIABLE_NAME}} pattern for API keys and sensitive configuration.
    These placeholders are replaced at runtime from environment variables.

Example:
    config = LLMConfig(
        anthropic_api_key="{{ANTHROPIC_API_KEY}}",
        openai_api_key="{{OPENAI_API_KEY}}",
    )
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


# Placeholder pattern: {{VARIABLE_NAME}}
PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")


def resolve_placeholder(value: Optional[str]) -> Optional[str]:
    """
    Resolve placeholder value from environment variable.

    Args:
        value: String value that may contain {{PLACEHOLDER}} pattern

    Returns:
        Resolved value from environment or original value if no placeholder

    Example:
        >>> os.environ["MY_API_KEY"] = "sk-12345"
        >>> resolve_placeholder("{{MY_API_KEY}}")
        'sk-12345'
    """
    if value is None:
        return None

    match = PLACEHOLDER_PATTERN.match(value)
    if match:
        env_var = match.group(1)
        return os.getenv(env_var)

    return value


@dataclass
class LLMConfig:
    """
    Configuration for LLM adapters and fallback chains.

    All API keys should use {{PLACEHOLDER}} syntax for security.
    Placeholders are resolved from environment variables at runtime.

    Attributes:
        anthropic_api_key: Anthropic/Claude API key (use {{ANTHROPIC_API_KEY}})
        openai_api_key: OpenAI API key (use {{OPENAI_API_KEY}})
        ollama_host: Ollama server host (use {{OLLAMA_HOST}} or default)
        azure_openai_endpoint: Azure OpenAI endpoint (use {{AZURE_OPENAI_ENDPOINT}})
        azure_openai_key: Azure OpenAI key (use {{AZURE_OPENAI_KEY}})
        default_model_claude: Default Claude model
        default_model_openai: Default OpenAI model
        default_model_ollama: Default Ollama model
        default_max_tokens: Default max tokens for responses
        default_temperature: Default sampling temperature
        circuit_breaker_threshold: Failures before circuit breaker opens
        circuit_breaker_cooldown: Cooldown period in seconds
        request_timeout: Default request timeout in seconds
    """

    # API Keys (use placeholders)
    anthropic_api_key: Optional[str] = "{{ANTHROPIC_API_KEY}}"
    openai_api_key: Optional[str] = "{{OPENAI_API_KEY}}"
    ollama_host: str = "{{OLLAMA_HOST}}"
    azure_openai_endpoint: Optional[str] = "{{AZURE_OPENAI_ENDPOINT}}"
    azure_openai_key: Optional[str] = "{{AZURE_OPENAI_KEY}}"

    # Default models
    default_model_claude: str = "claude-sonnet-4-5-20250929"
    default_model_openai: str = "gpt-4-turbo"
    default_model_ollama: str = "llama3"

    # Generation defaults
    default_max_tokens: int = 4096
    default_temperature: float = 1.0

    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown: int = 300  # 5 minutes

    # Request settings
    request_timeout: int = 30

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    # Cost tracking
    enable_cost_tracking: bool = True

    # Custom adapter settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def get_anthropic_api_key(self) -> Optional[str]:
        """Get resolved Anthropic API key from environment."""
        return resolve_placeholder(self.anthropic_api_key)

    def get_openai_api_key(self) -> Optional[str]:
        """Get resolved OpenAI API key from environment."""
        return resolve_placeholder(self.openai_api_key)

    def get_ollama_host(self) -> str:
        """Get resolved Ollama host, defaulting to localhost."""
        resolved = resolve_placeholder(self.ollama_host)
        return resolved or "http://localhost:11434"

    def get_azure_openai_endpoint(self) -> Optional[str]:
        """Get resolved Azure OpenAI endpoint."""
        return resolve_placeholder(self.azure_openai_endpoint)

    def get_azure_openai_key(self) -> Optional[str]:
        """Get resolved Azure OpenAI key."""
        return resolve_placeholder(self.azure_openai_key)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """
        Create configuration from environment variables.

        Environment Variables:
            ANTHROPIC_API_KEY: Anthropic/Claude API key
            OPENAI_API_KEY: OpenAI API key
            OLLAMA_HOST: Ollama server host
            AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint
            AZURE_OPENAI_KEY: Azure OpenAI key
            LLM_DEFAULT_MODEL_CLAUDE: Default Claude model
            LLM_DEFAULT_MODEL_OPENAI: Default OpenAI model
            LLM_DEFAULT_MODEL_OLLAMA: Default Ollama model
            LLM_DEFAULT_MAX_TOKENS: Default max tokens
            LLM_DEFAULT_TEMPERATURE: Default temperature
            LLM_REQUEST_TIMEOUT: Request timeout
            LLM_MAX_RETRIES: Max retries
        """
        return cls(
            anthropic_api_key="{{ANTHROPIC_API_KEY}}",
            openai_api_key="{{OPENAI_API_KEY}}",
            ollama_host="{{OLLAMA_HOST}}",
            azure_openai_endpoint="{{AZURE_OPENAI_ENDPOINT}}",
            azure_openai_key="{{AZURE_OPENAI_KEY}}",
            default_model_claude=os.getenv(
                "LLM_DEFAULT_MODEL_CLAUDE", "claude-sonnet-4-5-20250929"
            ),
            default_model_openai=os.getenv("LLM_DEFAULT_MODEL_OPENAI", "gpt-4-turbo"),
            default_model_ollama=os.getenv("LLM_DEFAULT_MODEL_OLLAMA", "llama3"),
            default_max_tokens=int(os.getenv("LLM_DEFAULT_MAX_TOKENS", "4096")),
            default_temperature=float(os.getenv("LLM_DEFAULT_TEMPERATURE", "1.0")),
            request_timeout=int(os.getenv("LLM_REQUEST_TIMEOUT", "30")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
        )

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Check if at least one API key is configured
        has_claude = bool(self.get_anthropic_api_key())
        has_openai = bool(self.get_openai_api_key())
        has_azure = bool(self.get_azure_openai_endpoint() and self.get_azure_openai_key())

        # Ollama doesn't need API key, just check if host is set
        has_ollama = bool(self.get_ollama_host())

        if not any([has_claude, has_openai, has_azure, has_ollama]):
            issues.append(
                "No LLM provider configured. Set at least one of: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, AZURE_OPENAI_*, or OLLAMA_HOST"
            )

        # Validate numeric ranges
        if self.default_max_tokens < 1:
            issues.append("default_max_tokens must be positive")

        if not (0.0 <= self.default_temperature <= 2.0):
            issues.append("default_temperature must be between 0.0 and 2.0")

        if self.circuit_breaker_threshold < 1:
            issues.append("circuit_breaker_threshold must be at least 1")

        if self.request_timeout < 1:
            issues.append("request_timeout must be at least 1 second")

        return issues
