"""
Basic usage example for netrun-config.

Demonstrates simple .env configuration with validation.
"""

from netrun_config import BaseConfig, Field, get_settings


class MyAppSettings(BaseConfig):
    """Custom application settings."""

    # Override default app name
    app_name: str = Field(default="MyAwesomeApp", env="APP_NAME")

    # Add custom fields
    api_timeout: int = Field(default=30, env="API_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")


def main():
    """Load and display settings."""
    # Get settings (cached singleton)
    settings = get_settings(MyAppSettings)

    print("Application Settings")
    print("=" * 50)
    print(f"App Name: {settings.app_name}")
    print(f"Version: {settings.app_version}")
    print(f"Environment: {settings.app_environment}")
    print(f"Debug Mode: {settings.app_debug}")
    print(f"API Timeout: {settings.api_timeout}s")
    print(f"Max Retries: {settings.max_retries}")
    print()

    # Use property methods
    print("Environment Checks")
    print("=" * 50)
    print(f"Is Production: {settings.is_production}")
    print(f"Is Development: {settings.is_development}")
    print(f"Is Staging: {settings.is_staging}")
    print()

    # Database configuration
    if settings.database_url:
        print("Database Configuration")
        print("=" * 50)
        print(f"Database URL: {settings.database_url}")
        print(f"Async URL: {settings.database_url_async}")
        print(f"Pool Size: {settings.database_pool_size}")
        print()

    # Redis configuration
    print("Redis Configuration")
    print("=" * 50)
    print(f"Redis URL: {settings.redis_url_full}")
    print()


if __name__ == "__main__":
    main()
