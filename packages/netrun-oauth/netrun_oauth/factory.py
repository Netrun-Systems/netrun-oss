"""
OAuth Adapter Factory
Creates platform-specific OAuth adapters with credential injection

Part of: netrun-oauth v1.0.0
SDLC v2.2 Compliant - Extracted from Intirkast OAuth adapters
"""

import logging
from typing import Dict, List, Optional
import os

from .adapters import (
    BaseOAuthAdapter,
    MicrosoftAdapter,
    GoogleAdapter,
    SalesforceAdapter,
    HubSpotAdapter,
    QuickBooksAdapter,
    XeroAdapter,
    MetaAdapter,
    MailchimpAdapter,
    SlackAdapter,
    ZoomAdapter,
    DocuSignAdapter,
    DropboxAdapter,
)
from .exceptions import UnsupportedPlatformError, ConfigurationError

logger = logging.getLogger(__name__)


class OAuthAdapterFactory:
    """
    Factory for creating platform-specific OAuth adapters

    Features:
    - Automatic credential injection from environment variables
    - Support for placeholder-based configuration
    - Extensible adapter registry

    Credential Resolution Order:
    1. Azure Key Vault (if AZURE_KEY_VAULT_URL set)
    2. Environment variables (PLATFORM_CLIENT_ID, PLATFORM_CLIENT_SECRET)
    3. Placeholder values ({{OAUTH_CLIENT_ID}}, {{OAUTH_CLIENT_SECRET}})
    """

    _adapters: Dict[str, type[BaseOAuthAdapter]] = {
        "microsoft": MicrosoftAdapter,
        "google": GoogleAdapter,
        "salesforce": SalesforceAdapter,
        "hubspot": HubSpotAdapter,
        "quickbooks": QuickBooksAdapter,
        "xero": XeroAdapter,
        "meta": MetaAdapter,
        "facebook": MetaAdapter,  # Alias for Meta
        "instagram": MetaAdapter,  # Alias for Meta
        "mailchimp": MailchimpAdapter,
        "slack": SlackAdapter,
        "zoom": ZoomAdapter,
        "docusign": DocuSignAdapter,
        "dropbox": DropboxAdapter,
    }

    @classmethod
    def create(
        cls,
        platform: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        **kwargs
    ) -> BaseOAuthAdapter:
        """
        Create adapter instance for specified platform

        Args:
            platform: Platform name (microsoft, google, salesforce, etc.)
            client_id: Optional explicit client ID (overrides auto-resolution)
            client_secret: Optional explicit client secret (overrides auto-resolution)
            **kwargs: Additional platform-specific parameters

        Returns:
            Platform-specific adapter instance with credentials injected

        Raises:
            UnsupportedPlatformError: If platform not supported
            ConfigurationError: If credentials cannot be resolved

        Example:
            # Auto-resolve from environment
            adapter = OAuthAdapterFactory.create("microsoft")

            # Explicit credentials
            adapter = OAuthAdapterFactory.create(
                "google",
                client_id="YOUR_CLIENT_ID",
                client_secret="YOUR_CLIENT_SECRET"
            )
        """
        adapter_class = cls._adapters.get(platform.lower())
        if not adapter_class:
            raise UnsupportedPlatformError(
                f"Unsupported platform: {platform}. "
                f"Supported platforms: {', '.join(cls._adapters.keys())}"
            )

        # Resolve credentials
        if client_id and client_secret:
            # Explicit credentials provided
            credentials = {"client_id": client_id, "client_secret": client_secret}
        else:
            # Auto-resolve from environment or Key Vault
            credentials = cls._get_credentials_for_platform(platform.lower())

        # Create adapter instance
        try:
            return adapter_class(
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"],
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create {platform} adapter: {e}")
            raise ConfigurationError(f"Adapter creation failed: {str(e)}")

    @classmethod
    def _get_credentials_for_platform(cls, platform: str) -> Dict[str, str]:
        """
        Get OAuth credentials for specified platform

        Resolution order:
        1. Azure Key Vault (if configured)
        2. Environment variables
        3. Placeholder values

        Args:
            platform: Platform name (microsoft, google, etc.)

        Returns:
            Dictionary with client_id and client_secret

        Note:
            Placeholders use format: {{PLATFORM_CLIENT_ID}}
        """
        # Check Azure Key Vault first (if configured)
        key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        if key_vault_url:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient

                credential = DefaultAzureCredential()
                client = SecretClient(vault_url=key_vault_url, credential=credential)

                # Try to fetch secrets from Key Vault
                try:
                    client_id_secret = client.get_secret(f"{platform}-client-id")
                    client_secret_secret = client.get_secret(f"{platform}-client-secret")

                    logger.info(f"Loaded {platform} credentials from Azure Key Vault")
                    return {
                        "client_id": client_id_secret.value,
                        "client_secret": client_secret_secret.value,
                    }
                except Exception:
                    # Secret not found, fall through to env vars
                    pass
            except ImportError:
                logger.warning("Azure SDK not installed. Install: azure-identity azure-keyvault-secrets")
            except Exception as e:
                logger.warning(f"Failed to access Azure Key Vault: {e}")

        # Check environment variables
        platform_upper = platform.upper()
        client_id = os.getenv(f"{platform_upper}_CLIENT_ID")
        client_secret = os.getenv(f"{platform_upper}_CLIENT_SECRET")

        if client_id and client_secret:
            logger.info(f"Loaded {platform} credentials from environment variables")
            return {
                "client_id": client_id,
                "client_secret": client_secret,
            }

        # Fallback to placeholders (for development/testing)
        logger.warning(
            f"No credentials found for {platform}. Using placeholders. "
            "Set {PLATFORM}_CLIENT_ID and {PLATFORM}_CLIENT_SECRET environment variables."
        )
        return {
            "client_id": f"{{{{{platform_upper}_CLIENT_ID}}}}",
            "client_secret": f"{{{{{platform_upper}_CLIENT_SECRET}}}}",
        }

    @classmethod
    def list_platforms(cls) -> List[str]:
        """
        Get list of all supported platforms

        Returns:
            List of platform identifiers

        Example:
            platforms = OAuthAdapterFactory.list_platforms()
            # ['microsoft', 'google', 'salesforce', ...]
        """
        return sorted(set(cls._adapters.keys()))

    @classmethod
    def register_adapter(cls, platform: str, adapter_class: type[BaseOAuthAdapter]) -> None:
        """
        Register custom OAuth adapter

        Args:
            platform: Platform identifier (lowercase)
            adapter_class: Adapter class (must inherit from BaseOAuthAdapter)

        Raises:
            TypeError: If adapter_class doesn't inherit from BaseOAuthAdapter

        Example:
            class CustomAdapter(BaseOAuthAdapter):
                # ... implementation ...

            OAuthAdapterFactory.register_adapter("custom", CustomAdapter)
            adapter = OAuthAdapterFactory.create("custom")
        """
        if not issubclass(adapter_class, BaseOAuthAdapter):
            raise TypeError("Adapter class must inherit from BaseOAuthAdapter")

        cls._adapters[platform.lower()] = adapter_class
        logger.info(f"Registered custom adapter for platform: {platform}")
