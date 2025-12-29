"""
Environment and configuration validators for Netrun Systems applications.

This module provides validators for environment-specific settings like
environment names, log levels, and provider selections.
"""

from typing import List, Optional
from .validators import validate_enum_value


def validate_environment(
    v: str,
    allowed: Optional[List[str]] = None,
) -> str:
    """
    Validate application environment.

    Args:
        v: The environment value to validate
        allowed: Optional list of allowed environments (defaults to standard environments)

    Returns:
        str: The validated environment (normalized to lowercase)

    Raises:
        ValueError: If environment is not in allowed list

    Example:
        >>> validate_environment("production")
        'production'
        >>> validate_environment("DEVELOPMENT")
        'development'
        >>> validate_environment("local", allowed=["local", "dev", "prod"])
        'local'
    """
    if allowed is None:
        allowed = ["development", "staging", "production", "testing"]

    return validate_enum_value(v, allowed, "environment", case_sensitive=False)


def validate_log_level(
    v: str,
    allowed: Optional[List[str]] = None,
) -> str:
    """
    Validate log level.

    Args:
        v: The log level to validate
        allowed: Optional list of allowed log levels (defaults to Python logging levels)

    Returns:
        str: The validated log level (normalized to uppercase)

    Raises:
        ValueError: If log level is not in allowed list

    Example:
        >>> validate_log_level("info")
        'INFO'
        >>> validate_log_level("DEBUG")
        'DEBUG'
    """
    if allowed is None:
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # Normalize to uppercase for log levels
    str_value = str(v).strip().upper()
    lower_allowed = {val.lower(): val for val in allowed}

    if str_value.lower() not in lower_allowed:
        raise ValueError(
            f"log_level must be one of: {', '.join(allowed)}. Got: {v}"
        )

    return str_value


def validate_provider(
    v: str,
    allowed: List[str],
    provider_type: str = "provider",
) -> str:
    """
    Validate provider selection (generic provider validator).

    Args:
        v: The provider value to validate
        allowed: List of allowed providers
        provider_type: Type of provider (for error messages, e.g., "LLM", "voice")

    Returns:
        str: The validated provider (normalized to lowercase)

    Raises:
        ValueError: If provider is not in allowed list

    Example:
        >>> validate_provider("openai", ["local", "openai", "azure_openai"], "LLM")
        'openai'
        >>> validate_provider("AZURE", ["azure", "local"], "voice")
        'azure'
    """
    return validate_enum_value(v, allowed, f"{provider_type} provider", case_sensitive=False)


def validate_llm_provider(v: str) -> str:
    """
    Validate LLM provider selection.

    Args:
        v: The LLM provider to validate

    Returns:
        str: The validated LLM provider

    Raises:
        ValueError: If LLM provider is not in allowed list

    Example:
        >>> validate_llm_provider("openai")
        'openai'
        >>> validate_llm_provider("AZURE_OPENAI")
        'azure_openai'
    """
    allowed = ["local", "openai", "azure_openai", "anthropic", "ollama"]
    return validate_provider(v, allowed, "LLM")


def validate_voice_provider(v: str) -> str:
    """
    Validate voice provider selection.

    Args:
        v: The voice provider to validate

    Returns:
        str: The validated voice provider

    Raises:
        ValueError: If voice provider is not in allowed list

    Example:
        >>> validate_voice_provider("azure")
        'azure'
        >>> validate_voice_provider("WHISPER")
        'whisper'
    """
    allowed = ["azure", "local", "whisper", "elevenlabs"]
    return validate_provider(v, allowed, "voice")


def validate_database_provider(v: str) -> str:
    """
    Validate database provider selection.

    Args:
        v: The database provider to validate

    Returns:
        str: The validated database provider

    Raises:
        ValueError: If database provider is not in allowed list

    Example:
        >>> validate_database_provider("postgresql")
        'postgresql'
        >>> validate_database_provider("MYSQL")
        'mysql'
    """
    allowed = ["postgresql", "mysql", "sqlite", "mssql", "mongodb"]
    return validate_provider(v, allowed, "database")


def validate_cloud_provider(v: str) -> str:
    """
    Validate cloud provider selection.

    Args:
        v: The cloud provider to validate

    Returns:
        str: The validated cloud provider

    Raises:
        ValueError: If cloud provider is not in allowed list

    Example:
        >>> validate_cloud_provider("azure")
        'azure'
        >>> validate_cloud_provider("AWS")
        'aws'
    """
    allowed = ["azure", "aws", "gcp", "local"]
    return validate_provider(v, allowed, "cloud")
