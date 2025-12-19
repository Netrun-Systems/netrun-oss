"""
Pydantic Settings Source integration for Azure Key Vault.

Provides a custom SettingsSource that seamlessly integrates Key Vault secrets
with pydantic-settings v2, allowing automatic secret loading during settings
initialization.
"""

import logging
from typing import Any, Optional

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from .multi_vault import MultiVaultClient, VaultConfig

logger = logging.getLogger(__name__)


class AzureKeyVaultSettingsSource(PydanticBaseSettingsSource):
    """
    Pydantic Settings Source for Azure Key Vault.

    Integrates with pydantic-settings v2 to automatically load secrets from
    Azure Key Vault during settings initialization. Supports field-level
    vault routing and secret name customization.

    Features:
    - Automatic secret loading from Key Vault
    - Field-level vault selection via metadata
    - Secret name customization via Field metadata
    - Multi-vault support
    - TTL caching with rotation detection
    - Graceful fallback to environment variables

    Example:
        >>> from pydantic import Field
        >>> from pydantic_settings import BaseSettings, SettingsConfigDict
        >>> from netrun.config import AzureKeyVaultSettingsSource, VaultConfig
        >>>
        >>> class MySettings(BaseSettings):
        ...     model_config = SettingsConfigDict(env_prefix='APP_')
        ...
        ...     database_url: str = Field(
        ...         json_schema_extra={'keyvault_secret': 'database-url'}
        ...     )
        ...     api_key: str = Field(
        ...         json_schema_extra={
        ...             'keyvault_secret': 'api-key',
        ...             'keyvault_vault': 'certificates'
        ...         }
        ...     )
        ...
        ...     @classmethod
        ...     def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        ...         vaults = {
        ...             'default': VaultConfig(url="https://my-vault.vault.azure.net/"),
        ...             'certificates': VaultConfig(url="https://cert-vault.vault.azure.net/")
        ...         }
        ...         keyvault_source = AzureKeyVaultSettingsSource(
        ...             settings_cls,
        ...             vaults=vaults,
        ...             is_production=True
        ...         )
        ...         return (
        ...             init_settings,
        ...             keyvault_source,
        ...             env_settings,
        ...             dotenv_settings,
        ...             file_secret_settings,
        ...         )
        >>>
        >>> settings = MySettings()  # Automatically loads from Key Vault
    """

    def __init__(
        self,
        settings_cls: type,
        vaults: dict[str, VaultConfig],
        is_production: bool = False,
        secret_name_transform: Optional[callable] = None,
    ):
        """
        Initialize Key Vault settings source.

        Args:
            settings_cls: The settings class being initialized
            vaults: Dictionary mapping vault names to VaultConfig
            is_production: Whether running in production
            secret_name_transform: Optional function to transform field names to secret names
                                   (e.g., lambda name: name.replace('_', '-'))
        """
        super().__init__(settings_cls)
        self.vaults = vaults
        self.is_production = is_production
        self.secret_name_transform = secret_name_transform or (
            lambda name: name.replace("_", "-")
        )

        # Initialize multi-vault client
        try:
            self.client = MultiVaultClient(
                vaults=vaults, is_production=is_production
            )
            logger.info(
                f"🔐 Key Vault settings source initialized ({len(vaults)} vaults)"
            )
        except Exception as e:
            logger.error(f"❌ Key Vault settings source initialization failed: {e}")
            self.client = None

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """
        Get field value from Key Vault.

        Args:
            field: Pydantic field info
            field_name: Name of the field

        Returns:
            Tuple of (value, key, is_complex) for pydantic-settings
        """
        if self.client is None:
            # Key Vault disabled, return sentinel
            return None, field_name, False

        # Extract Key Vault metadata from field
        json_schema_extra = field.json_schema_extra or {}

        # Get secret name (from metadata or transform field name)
        secret_name = json_schema_extra.get(
            "keyvault_secret", self.secret_name_transform(field_name)
        )

        # Get vault name (from metadata or use 'default')
        vault_name = json_schema_extra.get("keyvault_vault", "default")

        # Skip Key Vault lookup if explicitly disabled for this field
        if json_schema_extra.get("keyvault_skip", False):
            return None, field_name, False

        # Fetch secret from Key Vault
        try:
            value = self.client.get_secret(secret_name, vault=vault_name)
            if value is not None:
                logger.debug(
                    f"✅ Loaded '{field_name}' from vault '{vault_name}' "
                    f"(secret: '{secret_name}')"
                )
                return value, field_name, False
            else:
                logger.debug(
                    f"⚠️ Secret '{secret_name}' not found in vault '{vault_name}'"
                )
                return None, field_name, False

        except Exception as e:
            logger.error(
                f"❌ Error loading '{field_name}' from Key Vault: {e}"
            )
            return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        """
        Load all secrets from Key Vault.

        Returns:
            Dictionary of field values loaded from Key Vault
        """
        d: dict[str, Any] = {}

        if self.client is None:
            return d

        # Iterate through all fields in settings class
        for field_name, field_info in self.settings_cls.model_fields.items():
            value, key, _ = self.get_field_value(field_info, field_name)
            if value is not None:
                d[key] = value

        logger.debug(f"Key Vault source loaded {len(d)} secrets")
        return d


class AzureKeyVaultRefreshableSettingsSource(AzureKeyVaultSettingsSource):
    """
    Refreshable Key Vault settings source with rotation detection.

    Extends AzureKeyVaultSettingsSource to support secret rotation detection
    and automatic refresh when secrets change.

    Features:
    - All features of AzureKeyVaultSettingsSource
    - Secret rotation detection
    - Automatic cache refresh on rotation
    - Manual refresh capability

    Example:
        >>> class MySettings(BaseSettings):
        ...     @classmethod
        ...     def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        ...         vaults = {
        ...             'default': VaultConfig(url="https://my-vault.vault.azure.net/")
        ...         }
        ...         keyvault_source = AzureKeyVaultRefreshableSettingsSource(
        ...             settings_cls,
        ...             vaults=vaults,
        ...             auto_refresh_on_rotation=True
        ...         )
        ...         return (init_settings, keyvault_source, env_settings, dotenv_settings, file_secret_settings)
        >>>
        >>> settings = MySettings()
        >>> # Later, to refresh secrets
        >>> keyvault_source.refresh_secrets()
    """

    def __init__(
        self,
        settings_cls: type,
        vaults: dict[str, VaultConfig],
        is_production: bool = False,
        secret_name_transform: Optional[callable] = None,
        auto_refresh_on_rotation: bool = False,
    ):
        """
        Initialize refreshable Key Vault settings source.

        Args:
            settings_cls: The settings class being initialized
            vaults: Dictionary mapping vault names to VaultConfig
            is_production: Whether running in production
            secret_name_transform: Optional function to transform field names
            auto_refresh_on_rotation: Automatically refresh on secret rotation
        """
        super().__init__(
            settings_cls, vaults, is_production, secret_name_transform
        )
        self.auto_refresh_on_rotation = auto_refresh_on_rotation

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """
        Get field value with rotation detection.

        Args:
            field: Pydantic field info
            field_name: Name of the field

        Returns:
            Tuple of (value, key, is_complex)
        """
        if self.client is None:
            return None, field_name, False

        # Extract metadata
        json_schema_extra = field.json_schema_extra or {}
        secret_name = json_schema_extra.get(
            "keyvault_secret", self.secret_name_transform(field_name)
        )
        vault_name = json_schema_extra.get("keyvault_vault", "default")

        if json_schema_extra.get("keyvault_skip", False):
            return None, field_name, False

        # Use refresh_if_rotated if auto-refresh enabled
        try:
            if self.auto_refresh_on_rotation:
                value = self.client.refresh_if_rotated(
                    secret_name, vault=vault_name
                )
            else:
                value = self.client.get_secret(secret_name, vault=vault_name)

            if value is not None:
                logger.debug(f"✅ Loaded '{field_name}' from vault '{vault_name}'")
                return value, field_name, False
            else:
                logger.debug(
                    f"⚠️ Secret '{secret_name}' not found in vault '{vault_name}'"
                )
                return None, field_name, False

        except Exception as e:
            logger.error(f"❌ Error loading '{field_name}' from Key Vault: {e}")
            return None, field_name, False

    def refresh_secrets(self, vault: Optional[str] = None) -> None:
        """
        Manually refresh all secrets (invalidate cache and reload).

        Args:
            vault: Vault name to refresh (optional, refreshes all vaults if None)
        """
        if self.client is None:
            logger.warning("Key Vault client not initialized")
            return

        logger.info(f"🔄 Refreshing secrets for vault: {vault or 'all vaults'}")
        self.client.invalidate_cache(vault=vault)

    def check_rotations(self) -> dict[str, list[str]]:
        """
        Check all configured secrets for rotation.

        Returns:
            Dictionary mapping vault names to lists of rotated secret names
        """
        if self.client is None:
            return {}

        rotated: dict[str, list[str]] = {}

        for field_name, field_info in self.settings_cls.model_fields.items():
            json_schema_extra = field_info.json_schema_extra or {}
            secret_name = json_schema_extra.get(
                "keyvault_secret", self.secret_name_transform(field_name)
            )
            vault_name = json_schema_extra.get("keyvault_vault", "default")

            if json_schema_extra.get("keyvault_skip", False):
                continue

            if self.client.has_secret_rotated(secret_name, vault=vault_name):
                if vault_name not in rotated:
                    rotated[vault_name] = []
                rotated[vault_name].append(secret_name)

        if rotated:
            logger.info(f"🔄 Detected rotated secrets: {rotated}")

        return rotated
