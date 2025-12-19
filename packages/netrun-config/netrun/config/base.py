"""
Base configuration class for Netrun Systems projects.

Provides a standardized configuration foundation with common patterns
extracted from analysis of 12 portfolio projects.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .validators import (
    validate_environment,
    validate_secret_key,
    parse_cors_origins,
    validate_log_level,
    validate_positive_int,
)

# Optional netrun-logging integration
_use_netrun_logging = False
try:
    from netrun.logging import get_logger

    _use_netrun_logging = True
except ImportError:
    # Fallback to legacy import for backwards compatibility
    try:
        from netrun_logging import get_logger

        _use_netrun_logging = True
    except ImportError:
        import logging

        def get_logger(name: str, **kwargs):
            """Fallback to standard logging if netrun-logging not available."""
            return logging.getLogger(name)


# Initialize logger with optional netrun-logging
logger = get_logger(__name__)


class BaseConfig(BaseSettings):
    """
    Base configuration class for all Netrun Systems projects.

    Features:
    - Automatic .env file loading
    - Environment validation (development, staging, production, testing)
    - Secret key validation (32-char minimum)
    - CORS parsing (string → list)
    - Property methods (is_production, is_development, is_staging)
    - Caching via get_settings() factory

    Example:
        >>> from netrun.config import BaseConfig, Field
        >>>
        >>> class MyAppSettings(BaseConfig):
        ...     app_name: str = Field(default="MyApp")
        ...     custom_api_key: str = Field(..., env="CUSTOM_API_KEY")
        >>>
        >>> settings = get_settings(MyAppSettings)
        >>> print(settings.app_name)
        MyApp
    """

    # Pydantic v2 model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # ========================================================================
    # Core Application Configuration
    # ========================================================================

    app_name: str = Field(default="Netrun Application", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_environment: str = Field(default="development", env="APP_ENVIRONMENT")
    app_debug: bool = Field(default=False, env="APP_DEBUG")

    # ========================================================================
    # Security Configuration
    # ========================================================================

    app_secret_key: Optional[str] = Field(default=None, env="APP_SECRET_KEY")
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=15, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")

    # ========================================================================
    # CORS Configuration
    # ========================================================================

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")

    # ========================================================================
    # Database Configuration
    # ========================================================================

    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")

    # ========================================================================
    # Redis Configuration
    # ========================================================================

    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # ========================================================================
    # Logging Configuration
    # ========================================================================

    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # ========================================================================
    # Monitoring Configuration
    # ========================================================================

    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # ========================================================================
    # Azure Configuration
    # ========================================================================

    azure_subscription_id: Optional[str] = Field(
        default=None, env="AZURE_SUBSCRIPTION_ID"
    )
    azure_tenant_id: Optional[str] = Field(default=None, env="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, env="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, env="AZURE_CLIENT_SECRET")

    # ========================================================================
    # Validators (Applied to ALL Subclasses)
    # ========================================================================

    @field_validator("app_environment")
    @classmethod
    def _validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values."""
        return validate_environment(v)

    @field_validator("app_secret_key", "jwt_secret_key", "encryption_key")
    @classmethod
    def _validate_secret_keys(cls, v: Optional[str]) -> Optional[str]:
        """Validate secret keys are sufficiently long (32+ chars)."""
        return validate_secret_key(v)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        return parse_cors_origins(v)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        return validate_log_level(v)

    @field_validator("database_pool_size", "database_max_overflow")
    @classmethod
    def _validate_pool_settings(cls, v: int) -> int:
        """Validate database pool settings are positive."""
        return validate_positive_int(v)

    # ========================================================================
    # Property Methods (Computed Values)
    # ========================================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_environment == "development"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.app_environment == "staging"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app_environment == "testing"

    @property
    def database_url_async(self) -> Optional[str]:
        """Get async database URL (postgresql → postgresql+asyncpg)."""
        if self.database_url and self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def redis_url_full(self) -> str:
        """Get full Redis URL with authentication."""
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(maxsize=128)
def get_settings(settings_class: type[BaseConfig] = BaseConfig) -> BaseConfig:
    """
    Factory function to create cached settings instance.

    Args:
        settings_class: Settings class to instantiate (default: BaseConfig)

    Returns:
        Cached settings instance

    Example:
        >>> from netrun.config import BaseConfig, get_settings
        >>> settings = get_settings()
        >>> print(settings.app_environment)
        development
    """
    logger.debug(f"Loading settings: {settings_class.__name__}")
    settings = settings_class()
    logger.info(
        f"Settings loaded: {settings.app_name} ({settings.app_environment} environment)"
    )
    return settings


def reload_settings(settings_class: type[BaseConfig] = BaseConfig):
    """
    Reload settings by clearing cache (useful for testing).

    Args:
        settings_class: Settings class to reload

    Example:
        >>> from netrun.config import reload_settings
        >>> reload_settings()  # Clears cache, reloads from env
    """
    logger.info(f"Reloading settings: {settings_class.__name__}")
    get_settings.cache_clear()
    return get_settings(settings_class)
