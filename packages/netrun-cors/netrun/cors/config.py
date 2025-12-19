"""
CORS configuration settings using Pydantic BaseSettings.

Provides type-safe configuration for CORS middleware with environment variable support.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CORSConfig(BaseSettings):
    """
    CORS configuration settings with environment variable support.

    Environment variables can override defaults:
        CORS_ORIGINS="https://app.example.com,https://www.example.com"
        CORS_ALLOW_CREDENTIALS="true"
        CORS_ALLOW_METHODS="GET,POST,PUT,DELETE"
        CORS_ALLOW_HEADERS="Authorization,Content-Type"
        CORS_EXPOSE_HEADERS="X-Request-ID,X-Process-Time"
        CORS_MAX_AGE="3600"

    Example:
        >>> config = CORSConfig()
        >>> config.CORS_ORIGINS
        ['http://localhost:3000']
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    """List of allowed origins. Supports comma-separated env var."""

    CORS_ALLOW_CREDENTIALS: bool = True
    """Allow credentials (cookies, authorization headers) in CORS requests."""

    CORS_ALLOW_METHODS: List[str] = ["*"]
    """Allowed HTTP methods. Use ['*'] for all methods."""

    CORS_ALLOW_HEADERS: List[str] = ["*"]
    """Allowed HTTP headers. Use ['*'] for all headers."""

    CORS_EXPOSE_HEADERS: List[str] = ["X-Request-ID", "X-Process-Time"]
    """Headers exposed to browser in CORS response."""

    CORS_MAX_AGE: int = 3600
    """Preflight cache duration in seconds (default: 1 hour)."""

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", "CORS_EXPOSE_HEADERS", mode="before")
    @classmethod
    def parse_comma_separated(cls, v):
        """Parse comma-separated string values into lists."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
