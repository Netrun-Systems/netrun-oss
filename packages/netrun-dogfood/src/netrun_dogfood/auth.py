"""
MSAL Authentication for Netrun Dogfood MCP Server.

Provides unified authentication to all Netrun Systems products
using Azure AD Client Credentials flow.

Author: Netrun Systems
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

from netrun_auth.integrations.azure_ad import AzureADClient, AzureADConfig
from netrun_auth.core.exceptions import AuthenticationError

from netrun_dogfood.config import DogfoodConfig, get_config

logger = logging.getLogger(__name__)


class DogfoodAuth:
    """Unified authentication for all Netrun Systems products.

    Uses Azure AD Client Credentials flow for service-to-service
    authentication. Manages token caching and auto-refresh.
    """

    def __init__(self, config: Optional[DogfoodConfig] = None):
        """Initialize authentication client.

        Args:
            config: Optional configuration (uses global config if None)
        """
        self.config = config or get_config()

        # Initialize Azure AD client
        azure_config = AzureADConfig(
            tenant_id=self.config.azure_tenant_id,
            client_id=self.config.azure_client_id,
            client_secret=self.config.azure_client_secret,
        )
        self._azure_client = AzureADClient(azure_config)

        # Token cache: {scope: (token, expiry)}
        self._token_cache: Dict[str, tuple[str, datetime]] = {}

        # Default scopes for each product
        self._product_scopes = {
            "intirkon": [f"{self.config.azure_client_id}/.default"],
            "charlotte": [f"{self.config.azure_client_id}/.default"],
            "meridian": [f"{self.config.azure_client_id}/.default"],
            "netrunsite": [f"{self.config.azure_client_id}/.default"],
            "securevault": [f"{self.config.azure_client_id}/.default"],
        }

    async def get_token(self, product: str) -> str:
        """Get access token for a specific product.

        Tokens are cached and auto-refreshed 5 minutes before expiry.

        Args:
            product: Product name (intirkon, charlotte, meridian, netrunsite, securevault)

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If token acquisition fails
        """
        cache_key = product.lower()

        # Check cache
        if cache_key in self._token_cache:
            token, expiry = self._token_cache[cache_key]
            # Refresh if expires within 5 minutes
            if datetime.now(timezone.utc) < expiry - timedelta(minutes=5):
                return token

        # Get new token
        scopes = self._product_scopes.get(cache_key, [f"{self.config.azure_client_id}/.default"])

        try:
            result = await self._azure_client.get_client_credentials_token(scopes=scopes)

            token = result["access_token"]
            expires_in = result.get("expires_in", 3600)
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Cache token
            self._token_cache[cache_key] = (token, expiry)

            logger.debug(f"Acquired new token for {product}, expires in {expires_in}s")
            return token

        except Exception as e:
            logger.error(f"Failed to acquire token for {product}: {e}")
            raise AuthenticationError(f"Failed to authenticate to {product}: {e}")

    async def get_auth_headers(self, product: str) -> Dict[str, str]:
        """Get authorization headers for API requests.

        Args:
            product: Product name

        Returns:
            Dict with Authorization header
        """
        # Meridian uses API key authentication instead of Azure AD
        if product.lower() == "meridian" and self.config.meridian_api_key:
            return {
                "Authorization": f"Bearer {self.config.meridian_api_key}",
                "Content-Type": "application/json",
            }

        token = await self.get_token(product)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def clear_cache(self) -> None:
        """Clear all cached tokens."""
        self._token_cache.clear()
        logger.info("Token cache cleared")

    @property
    def is_configured(self) -> bool:
        """Check if authentication is properly configured.

        Returns:
            True if all required credentials are set
        """
        return bool(
            self.config.azure_tenant_id and
            self.config.azure_client_id and
            self.config.azure_client_secret
        )


# Global auth instance
_auth: Optional[DogfoodAuth] = None


def get_auth() -> DogfoodAuth:
    """Get or create the global authentication instance.

    Returns:
        DogfoodAuth: Authentication instance
    """
    global _auth
    if _auth is None:
        _auth = DogfoodAuth()
    return _auth


def initialize_auth(config: Optional[DogfoodConfig] = None) -> DogfoodAuth:
    """Initialize authentication with optional configuration.

    Args:
        config: Optional configuration

    Returns:
        DogfoodAuth: Initialized authentication instance
    """
    global _auth
    _auth = DogfoodAuth(config)
    return _auth
