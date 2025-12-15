"""
Reusable validators for netrun-config.

Common validation functions extracted from analysis of 12 Netrun Systems projects.
"""

from typing import Any, Optional


def validate_environment(v: str) -> str:
    """
    Validate environment is one of allowed values.

    Args:
        v: Environment string to validate

    Returns:
        Validated environment string

    Raises:
        ValueError: If environment is not in allowed list
    """
    allowed = ["development", "staging", "production", "testing"]
    if v not in allowed:
        raise ValueError(f"Environment must be one of: {allowed}")
    return v


def validate_secret_key(v: Optional[str]) -> Optional[str]:
    """
    Validate secret keys are sufficiently long (32+ characters).

    Args:
        v: Secret key to validate

    Returns:
        Validated secret key

    Raises:
        ValueError: If secret key is less than 32 characters
    """
    if v is not None and len(v) < 32:
        raise ValueError("Secret keys must be at least 32 characters long")
    return v


def parse_cors_origins(v: Any) -> list[str]:
    """
    Parse CORS origins from comma-separated string or list.

    Args:
        v: CORS origins as string or list

    Returns:
        List of origin URLs

    Examples:
        >>> parse_cors_origins("http://localhost:3000,http://example.com")
        ['http://localhost:3000', 'http://example.com']
        >>> parse_cors_origins(["http://localhost:3000"])
        ['http://localhost:3000']
    """
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    return v if v else []


def validate_log_level(v: str) -> str:
    """
    Validate log level is one of allowed values.

    Args:
        v: Log level string to validate

    Returns:
        Validated log level (uppercase)

    Raises:
        ValueError: If log level is not valid
    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    v_upper = v.upper()
    if v_upper not in valid_levels:
        raise ValueError(f"Log level must be one of: {valid_levels}")
    return v_upper


def validate_database_url(v: Optional[str]) -> Optional[str]:
    """
    Validate database URL format.

    Args:
        v: Database URL to validate

    Returns:
        Validated database URL

    Raises:
        ValueError: If URL format is invalid
    """
    if v is None:
        return v

    # Basic validation - check for scheme
    if "://" not in v:
        raise ValueError("Database URL must include scheme (e.g., postgresql://)")

    return v


def validate_positive_int(v: int) -> int:
    """
    Validate integer is positive (greater than 0).

    Args:
        v: Integer to validate

    Returns:
        Validated integer

    Raises:
        ValueError: If integer is not positive
    """
    if v < 1:
        raise ValueError("Value must be at least 1")
    return v
