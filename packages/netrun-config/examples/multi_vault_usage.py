"""
Example: Multi-Vault Azure Key Vault Integration with TTL Caching

This example demonstrates the v1.1.0 features:
- Multi-vault support for different secret sources
- TTL-based caching with automatic expiration
- Secret rotation detection
- Pydantic Settings Source integration
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from netrun_config import (
    AzureKeyVaultRefreshableSettingsSource,
    MultiVaultClient,
    SecretCacheConfig,
    VaultConfig,
)


# ============================================================================
# Example 1: Direct Multi-Vault Client Usage
# ============================================================================


def example_multi_vault_client():
    """Example of using MultiVaultClient directly."""
    print("=" * 60)
    print("Example 1: Multi-Vault Client Usage")
    print("=" * 60)

    # Configure multiple vaults for different purposes
    vaults = {
        "default": VaultConfig(
            url="https://prod-vault.vault.azure.net/",
            cache_config=SecretCacheConfig(
                default_ttl_seconds=28800,  # 8 hours
                max_cache_size=500,
            ),
        ),
        "dev": VaultConfig(
            url="https://dev-vault.vault.azure.net/",
            cache_config=SecretCacheConfig(
                default_ttl_seconds=3600,  # 1 hour (shorter for dev)
                max_cache_size=100,
            ),
        ),
        "certificates": VaultConfig(
            url="https://cert-vault.vault.azure.net/",
            cache_config=SecretCacheConfig(
                default_ttl_seconds=86400,  # 24 hours (longer for certs)
                max_cache_size=50,
            ),
        ),
    }

    # Initialize multi-vault client
    client = MultiVaultClient(vaults, is_production=True)

    # Get secrets from different vaults
    db_url = client.get_secret("database-url")  # Uses 'default' vault
    api_key = client.get_secret("api-key", vault="dev")
    ssl_cert = client.get_secret("ssl-certificate", vault="certificates")

    print(f"Database URL: {db_url[:20]}..." if db_url else "Database URL: None")
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: None")
    print(
        f"SSL Certificate: {ssl_cert[:30]}..." if ssl_cert else "SSL Certificate: None"
    )

    # Check cache statistics
    stats = client.get_cache_stats()
    for vault_name, vault_stats in stats.items():
        print(f"\n{vault_name} vault cache stats:")
        print(f"  Total secrets: {vault_stats['total_secrets']}")
        print(f"  Valid secrets: {vault_stats['valid_secrets']}")
        print(f"  Cache utilization: {vault_stats['cache_utilization_pct']:.1f}%")

    # Check for secret rotation
    if client.has_secret_rotated("database-url"):
        print("\n⚠️ Database URL has been rotated!")
        refreshed_db_url = client.refresh_if_rotated("database-url")
        print(f"Refreshed database URL: {refreshed_db_url}")

    print()


# ============================================================================
# Example 2: Pydantic Settings Source Integration
# ============================================================================


class AppSettings(BaseSettings):
    """
    Application settings with Azure Key Vault integration.

    This example shows how to use the Pydantic Settings Source integration
    for automatic secret loading.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_", case_sensitive=False, extra="ignore"
    )

    # Basic settings
    app_name: str = Field(default="MyApp")
    app_environment: str = Field(default="production")

    # Secrets from 'default' vault
    database_url: str = Field(
        default="sqlite:///local.db",
        json_schema_extra={"keyvault_secret": "database-url"},
    )

    redis_url: str = Field(
        default="redis://localhost:6379",
        json_schema_extra={"keyvault_secret": "redis-url"},
    )

    # Secrets from 'dev' vault (for non-prod environments)
    dev_api_key: str = Field(
        default="dev-key",
        json_schema_extra={
            "keyvault_secret": "api-key",
            "keyvault_vault": "dev",
        },
    )

    # Secrets from 'certificates' vault
    ssl_certificate: str = Field(
        default="",
        json_schema_extra={
            "keyvault_secret": "ssl-certificate",
            "keyvault_vault": "certificates",
        },
    )

    # Skip Key Vault for this field
    local_config_path: str = Field(
        default="/etc/myapp/config.json",
        json_schema_extra={"keyvault_skip": True},
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Customize settings sources to include Key Vault."""
        # Configure vaults
        vaults = {
            "default": VaultConfig(url="https://prod-vault.vault.azure.net/"),
            "dev": VaultConfig(url="https://dev-vault.vault.azure.net/"),
            "certificates": VaultConfig(url="https://cert-vault.vault.azure.net/"),
        }

        # Create Key Vault settings source with auto-refresh
        keyvault_source = AzureKeyVaultRefreshableSettingsSource(
            settings_cls,
            vaults=vaults,
            is_production=True,
            auto_refresh_on_rotation=True,  # Automatically refresh rotated secrets
        )

        # Priority order: init > Key Vault > env > dotenv > file
        return (
            init_settings,
            keyvault_source,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


def example_pydantic_integration():
    """Example of Pydantic Settings Source integration."""
    print("=" * 60)
    print("Example 2: Pydantic Settings Source Integration")
    print("=" * 60)

    # Initialize settings (automatically loads from Key Vault)
    settings = AppSettings()

    print(f"App Name: {settings.app_name}")
    print(f"Environment: {settings.app_environment}")
    print(f"Database URL: {settings.database_url[:30]}...")
    print(f"Redis URL: {settings.redis_url[:30]}...")
    print(f"Local Config Path: {settings.local_config_path}")

    print()


# ============================================================================
# Example 3: Secret Rotation Detection
# ============================================================================


def example_rotation_detection():
    """Example of secret rotation detection."""
    print("=" * 60)
    print("Example 3: Secret Rotation Detection")
    print("=" * 60)

    vaults = {
        "default": VaultConfig(url="https://prod-vault.vault.azure.net/")
    }

    client = MultiVaultClient(vaults, is_production=True)

    # Get initial secret
    secret = client.get_secret("database-password")
    print(f"Initial secret version: {client.check_secret_version('database-password')}")

    # Simulate checking for rotation (would be done periodically)
    if client.has_secret_rotated("database-password"):
        print("🔄 Secret has been rotated! Refreshing...")
        new_secret = client.refresh_if_rotated("database-password")
        print(f"New secret version: {client.check_secret_version('database-password')}")
    else:
        print("✅ Secret has not been rotated, using cached value")

    # Manual cache invalidation if needed
    client.invalidate_cache(secret_name="database-password")
    print("Cache invalidated for database-password")

    print()


# ============================================================================
# Example 4: Cache Statistics and Monitoring
# ============================================================================


def example_cache_monitoring():
    """Example of monitoring cache statistics."""
    print("=" * 60)
    print("Example 4: Cache Statistics and Monitoring")
    print("=" * 60)

    vaults = {
        "default": VaultConfig(
            url="https://prod-vault.vault.azure.net/",
            cache_config=SecretCacheConfig(
                default_ttl_seconds=28800, max_cache_size=100
            ),
        ),
    }

    client = MultiVaultClient(vaults)

    # Fetch several secrets
    secrets = [
        "database-url",
        "redis-url",
        "api-key",
        "jwt-secret",
        "encryption-key",
    ]

    for secret_name in secrets:
        client.get_secret(secret_name)

    # Get cache statistics
    stats = client.get_cache_stats(vault="default")
    default_stats = stats["default"]

    print("Cache Statistics:")
    print(f"  Total secrets cached: {default_stats['total_secrets']}")
    print(f"  Valid secrets: {default_stats['valid_secrets']}")
    print(f"  Expired secrets: {default_stats['expired_secrets']}")
    print(f"  Cache utilization: {default_stats['cache_utilization_pct']:.1f}%")
    print(f"  Max cache size: {default_stats['max_cache_size']}")
    print(f"  TTL: {default_stats['default_ttl_seconds'] / 3600:.1f} hours")

    # List all configured vaults
    print(f"\nConfigured vaults: {', '.join(client.list_vaults())}")

    print()


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all examples."""
    print("\n🔐 netrun-config v1.1.0 - Multi-Vault Examples\n")

    try:
        example_multi_vault_client()
    except Exception as e:
        print(f"Example 1 error: {e}\n")

    try:
        example_pydantic_integration()
    except Exception as e:
        print(f"Example 2 error: {e}\n")

    try:
        example_rotation_detection()
    except Exception as e:
        print(f"Example 3 error: {e}\n")

    try:
        example_cache_monitoring()
    except Exception as e:
        print(f"Example 4 error: {e}\n")

    print("✅ Examples completed!")


if __name__ == "__main__":
    main()
