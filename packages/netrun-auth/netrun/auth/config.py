"""
Netrun Authentication - Configuration
======================================

Configuration settings for authentication module using Pydantic Settings.

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

from datetime import timedelta
from typing import Optional, List
from pathlib import Path
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    """
    Authentication configuration settings.

    Loads from environment variables with NETRUN_AUTH_ prefix.
    """
    model_config = SettingsConfigDict(
        env_prefix="NETRUN_AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # JWT Configuration
    jwt_algorithm: str = Field(
        default="RS256",
        description="JWT signing algorithm (RS256 recommended)"
    )
    jwt_issuer: str = Field(
        default="netrun-auth",
        description="JWT issuer claim"
    )
    jwt_audience: str = Field(
        default="netrun-api",
        description="JWT audience claim"
    )
    access_token_expiry_minutes: int = Field(
        default=15,
        description="Access token expiry in minutes"
    )
    refresh_token_expiry_days: int = Field(
        default=30,
        description="Refresh token expiry in days"
    )

    # Key Management
    jwt_private_key_path: Optional[str] = Field(
        default=None,
        description="Path to RSA private key PEM file"
    )
    jwt_public_key_path: Optional[str] = Field(
        default=None,
        description="Path to RSA public key PEM file"
    )
    jwt_private_key: Optional[str] = Field(
        default=None,
        description="RSA private key content (alternative to file path)"
    )
    jwt_public_key: Optional[str] = Field(
        default=None,
        description="RSA public key content (alternative to file path)"
    )

    # Azure Key Vault (Optional)
    azure_key_vault_url: Optional[str] = Field(
        default=None,
        description="Azure Key Vault URL for key rotation"
    )
    azure_key_vault_secret_name: str = Field(
        default="netrun-jwt-private-key",
        description="Azure Key Vault secret name for private key"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for token blacklist and rate limiting"
    )
    redis_key_prefix: str = Field(
        default="netrun:auth:",
        description="Redis key prefix for namespacing"
    )
    redis_ttl_buffer_seconds: int = Field(
        default=300,
        description="TTL buffer for Redis keys (5 minutes)"
    )

    # Password Configuration
    password_min_length: int = Field(
        default=12,
        description="Minimum password length"
    )
    password_require_uppercase: bool = Field(
        default=True,
        description="Require uppercase letters in password"
    )
    password_require_lowercase: bool = Field(
        default=True,
        description="Require lowercase letters in password"
    )
    password_require_digits: bool = Field(
        default=True,
        description="Require digits in password"
    )
    password_require_special: bool = Field(
        default=True,
        description="Require special characters in password"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_default_requests: int = Field(
        default=100,
        description="Default requests per window"
    )
    rate_limit_default_window_seconds: int = Field(
        default=900,
        description="Default rate limit window (15 minutes)"
    )

    # Brute Force Protection
    brute_force_protection_enabled: bool = Field(
        default=True,
        description="Enable brute force protection"
    )
    brute_force_max_attempts: int = Field(
        default=5,
        description="Max failed login attempts before lockout"
    )
    brute_force_lockout_minutes: int = Field(
        default=15,
        description="Lockout duration after max attempts"
    )

    # Middleware Configuration
    exempt_paths: List[str] = Field(
        default_factory=lambda: [
            "/health",
            "/health/ready",
            "/health/live",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/oauth",
            "/auth/callback"
        ],
        description="Paths exempt from authentication"
    )

    # Audit Logging
    audit_log_enabled: bool = Field(
        default=True,
        description="Enable audit logging"
    )
    audit_log_retention_days: int = Field(
        default=90,
        description="Audit log retention period"
    )

    # Session Configuration
    session_max_duration_hours: int = Field(
        default=720,
        description="Maximum session duration (30 days)"
    )
    session_idle_timeout_minutes: int = Field(
        default=120,
        description="Session idle timeout (2 hours)"
    )

    @validator("jwt_algorithm")
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm is secure."""
        allowed_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        if v not in allowed_algorithms:
            raise ValueError(
                f"JWT algorithm must be one of {allowed_algorithms}. "
                f"Symmetric algorithms (HS256, HS384, HS512) are not recommended for production."
            )
        return v

    @validator("redis_url")
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must start with redis:// or rediss://")
        return v

    @validator("access_token_expiry_minutes")
    def validate_access_token_expiry(cls, v: int) -> int:
        """Validate access token expiry is reasonable."""
        if v < 1:
            raise ValueError("Access token expiry must be at least 1 minute")
        if v > 120:
            raise ValueError(
                "Access token expiry should not exceed 2 hours for security. "
                "Use refresh tokens for longer sessions."
            )
        return v

    @validator("refresh_token_expiry_days")
    def validate_refresh_token_expiry(cls, v: int) -> int:
        """Validate refresh token expiry is reasonable."""
        if v < 1:
            raise ValueError("Refresh token expiry must be at least 1 day")
        if v > 90:
            raise ValueError(
                "Refresh token expiry should not exceed 90 days for security. "
                "Consider shorter expiry with re-authentication."
            )
        return v

    def get_access_token_expiry(self) -> timedelta:
        """Get access token expiry as timedelta."""
        return timedelta(minutes=self.access_token_expiry_minutes)

    def get_refresh_token_expiry(self) -> timedelta:
        """Get refresh token expiry as timedelta."""
        return timedelta(days=self.refresh_token_expiry_days)

    def get_rate_limit_window(self) -> timedelta:
        """Get rate limit window as timedelta."""
        return timedelta(seconds=self.rate_limit_default_window_seconds)

    def get_brute_force_lockout(self) -> timedelta:
        """Get brute force lockout duration as timedelta."""
        return timedelta(minutes=self.brute_force_lockout_minutes)

    def load_private_key(self) -> str:
        """
        Load RSA private key from file or environment.

        Returns:
            RSA private key in PEM format

        Raises:
            ValueError: If no private key source configured
        """
        if self.jwt_private_key:
            return self.jwt_private_key

        if self.jwt_private_key_path:
            key_path = Path(self.jwt_private_key_path)
            if not key_path.exists():
                raise ValueError(f"Private key file not found: {key_path}")
            return key_path.read_text()

        raise ValueError(
            "No JWT private key configured. Set NETRUN_AUTH_JWT_PRIVATE_KEY or "
            "NETRUN_AUTH_JWT_PRIVATE_KEY_PATH environment variable."
        )

    def load_public_key(self) -> str:
        """
        Load RSA public key from file or environment.

        Returns:
            RSA public key in PEM format

        Raises:
            ValueError: If no public key source configured
        """
        if self.jwt_public_key:
            return self.jwt_public_key

        if self.jwt_public_key_path:
            key_path = Path(self.jwt_public_key_path)
            if not key_path.exists():
                raise ValueError(f"Public key file not found: {key_path}")
            return key_path.read_text()

        raise ValueError(
            "No JWT public key configured. Set NETRUN_AUTH_JWT_PUBLIC_KEY or "
            "NETRUN_AUTH_JWT_PUBLIC_KEY_PATH environment variable."
        )
