"""
Azure Key Vault integration example for netrun-config.

Demonstrates hybrid configuration with Key Vault for production secrets
and environment variables for local development.
"""

from typing import Optional

from netrun_config import BaseConfig, Field, KeyVaultMixin, get_settings


class ProductionSettings(BaseConfig, KeyVaultMixin):
    """Settings with Azure Key Vault integration."""

    # Key Vault URL (required for production)
    KEY_VAULT_URL: Optional[str] = Field(default=None, env="KEY_VAULT_URL")

    # Database configuration
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_password: Optional[str] = Field(default=None, env="DATABASE_PASSWORD")

    # API keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    stripe_api_key: Optional[str] = Field(default=None, env="STRIPE_API_KEY")

    @property
    def database_url_resolved(self) -> Optional[str]:
        """
        Get database URL, preferring Key Vault in production.

        Priority:
        1. Key Vault (production only)
        2. Environment variable
        """
        if self.is_production and self.KEY_VAULT_URL:
            vault_url = self.get_keyvault_secret("database-url")
            if vault_url:
                return vault_url

        return self.database_url

    @property
    def openai_api_key_resolved(self) -> Optional[str]:
        """
        Get OpenAI API key, preferring Key Vault in production.

        Priority:
        1. Key Vault (production only)
        2. Environment variable
        """
        if self.is_production and self.KEY_VAULT_URL:
            vault_key = self.get_keyvault_secret("openai-api-key")
            if vault_key:
                return vault_key

        return self.openai_api_key

    @property
    def stripe_api_key_resolved(self) -> Optional[str]:
        """
        Get Stripe API key, preferring Key Vault in production.

        Priority:
        1. Key Vault (production only)
        2. Environment variable
        """
        if self.is_production and self.KEY_VAULT_URL:
            vault_key = self.get_keyvault_secret("stripe-api-key")
            if vault_key:
                return vault_key

        return self.stripe_api_key


def main():
    """Demonstrate Key Vault integration."""
    settings = get_settings(ProductionSettings)

    print("Application Settings (with Key Vault)")
    print("=" * 50)
    print(f"Environment: {settings.app_environment}")
    print(f"Key Vault Enabled: {settings._kv_enabled}")
    print()

    # Demonstrate secret resolution
    print("Secret Resolution")
    print("=" * 50)

    if settings.is_production:
        print("Production Mode:")
        print("  - Secrets loaded from Azure Key Vault")
        print("  - Fallback to environment variables if unavailable")
    else:
        print("Development Mode:")
        print("  - Secrets loaded from .env file")
        print("  - Key Vault integration optional")

    print()

    # Show resolved values (masked for security)
    if settings.database_url_resolved:
        print(f"Database URL: {'*' * 20} (resolved)")

    if settings.openai_api_key_resolved:
        print(f"OpenAI API Key: {'*' * 20} (resolved)")

    if settings.stripe_api_key_resolved:
        print(f"Stripe API Key: {'*' * 20} (resolved)")


if __name__ == "__main__":
    main()
