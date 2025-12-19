"""
Configuration for Netrun Dogfood MCP Server.

Loads configuration from environment variables with sensible defaults
for all Netrun Systems product API endpoints.

Supports Azure Key Vault for credential management via DefaultAzureCredential.

Author: Netrun Systems
Version: 1.0.1
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class DogfoodConfig(BaseSettings):
    """Dogfood MCP Server configuration.

    All settings can be overridden via environment variables.

    Key Vault Integration:
        Set AZURE_KEYVAULT_URL and USE_KEYVAULT_AUTH=true to load
        credentials from Azure Key Vault using DefaultAzureCredential.
        Secrets expected: dogfood-tenant-id, dogfood-client-id, dogfood-client-secret
    """

    # Azure Key Vault Configuration
    azure_keyvault_url: Optional[str] = Field(
        default=None,
        description="Azure Key Vault URL (e.g., https://netrun-keyvault.vault.azure.net)"
    )
    use_keyvault_auth: bool = Field(
        default=False,
        description="Use Key Vault for credential loading"
    )

    # Azure AD / MSAL Configuration (loaded from Key Vault or env vars)
    azure_tenant_id: str = Field(
        default="",
        description="Azure AD tenant ID for Netrun Systems"
    )
    azure_client_id: str = Field(
        default="",
        description="Service principal client ID for dogfood access"
    )
    azure_client_secret: str = Field(
        default="",
        description="Service principal client secret"
    )

    def load_keyvault_credentials(self) -> None:
        """Load credentials from Azure Key Vault if configured.

        Uses DefaultAzureCredential which supports:
        - Managed Identity (in Azure)
        - Azure CLI credentials (local dev)
        - Environment variables (CI/CD)
        """
        if not self.use_keyvault_auth or not self.azure_keyvault_url:
            return

        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=self.azure_keyvault_url, credential=credential)

            # Load credentials from Key Vault (using existing Netrun secret names)
            secrets_map = {
                "AZURE-AD-TENANT-ID": "azure_tenant_id",
                "AZURE-AD-CLIENT-ID": "azure_client_id",
                "AZURE-AD-CLIENT-SECRET": "azure_client_secret",
            }

            for secret_name, attr_name in secrets_map.items():
                try:
                    secret = client.get_secret(secret_name)
                    if secret.value:
                        setattr(self, attr_name, secret.value)
                        logger.info(f"Loaded {secret_name} from Key Vault")
                except Exception as e:
                    logger.warning(f"Failed to load {secret_name} from Key Vault: {e}")

        except ImportError:
            logger.warning("Azure SDK not installed. Run: pip install azure-identity azure-keyvault-secrets")
        except Exception as e:
            logger.error(f"Key Vault initialization failed: {e}")

    # Intirkon API (Cloud Management)
    intirkon_api_url: str = Field(
        default="https://intirkon-prod-api.azurewebsites.net/api",
        description="Intirkon API base URL"
    )
    intirkon_enabled: bool = Field(
        default=True,
        description="Enable Intirkon tools"
    )

    # Charlotte API (AI Orchestration)
    charlotte_api_url: str = Field(
        default="https://charlotte.netrunsystems.com/api/v1",
        description="Charlotte API base URL"
    )
    charlotte_enabled: bool = Field(
        default=True,
        description="Enable Charlotte tools"
    )

    # Meridian API (Document Publishing)
    meridian_api_url: str = Field(
        default="https://meridian-backend-prod.blackrock-7921664c.eastus2.azurecontainerapps.io/api",
        description="Meridian API base URL"
    )
    meridian_api_key: Optional[str] = Field(
        default=None,
        description="Meridian API key for M2M authentication (mk_... format)"
    )
    meridian_enabled: bool = Field(
        default=True,
        description="Enable Meridian tools"
    )

    # NetrunSite API (Website/Blog)
    netrunsite_api_url: str = Field(
        default="https://netrunsystems.com/api",
        description="NetrunSite API base URL"
    )
    netrunsite_enabled: bool = Field(
        default=True,
        description="Enable NetrunSite tools"
    )

    # SecureVault API (Password Management)
    securevault_api_url: str = Field(
        default="http://127.0.0.1:8437/api/v1",
        description="SecureVault API base URL (local daemon)"
    )
    securevault_enabled: bool = Field(
        default=True,
        description="Enable SecureVault tools"
    )

    # General Settings
    request_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Global config instance
_config: Optional[DogfoodConfig] = None


def get_config() -> DogfoodConfig:
    """Get or create the global configuration instance.

    Automatically loads credentials from Key Vault if configured.

    Returns:
        DogfoodConfig: Configuration instance
    """
    global _config
    if _config is None:
        _config = DogfoodConfig()
        _config.load_keyvault_credentials()
    return _config


def initialize_config(**overrides) -> DogfoodConfig:
    """Initialize configuration with optional overrides.

    Automatically loads credentials from Key Vault if configured.

    Args:
        **overrides: Configuration values to override

    Returns:
        DogfoodConfig: Initialized configuration
    """
    global _config
    _config = DogfoodConfig(**overrides)
    _config.load_keyvault_credentials()
    return _config
