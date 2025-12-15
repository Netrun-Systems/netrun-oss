"""
Tests for Pydantic Settings Source integration.
"""

import pytest
from pydantic import Field
from pydantic_settings import BaseSettings

from netrun_config.multi_vault import VaultConfig
from netrun_config.settings_source import (
    AzureKeyVaultRefreshableSettingsSource,
    AzureKeyVaultSettingsSource,
)

# Mark all tests as requiring Azure SDK
pytestmark = pytest.mark.skipif(
    True, reason="Azure SDK integration tests require live Key Vault"
)


class TestAzureKeyVaultSettingsSource:
    """Test AzureKeyVaultSettingsSource functionality."""

    @pytest.fixture
    def settings_class(self):
        """Create a test settings class."""

        class TestSettings(BaseSettings):
            database_url: str = Field(
                default="sqlite:///test.db",
                json_schema_extra={"keyvault_secret": "database-url"},
            )
            api_key: str = Field(
                default="default-key",
                json_schema_extra={
                    "keyvault_secret": "api-key",
                    "keyvault_vault": "certificates",
                },
            )
            skip_field: str = Field(
                default="skip-value",
                json_schema_extra={"keyvault_skip": True},
            )

        return TestSettings

    @pytest.fixture
    def mock_multi_vault_client(self, mocker):
        """Mock MultiVaultClient."""
        mock_client = mocker.MagicMock()
        mock_client.get_secret.side_effect = lambda name, vault="default": {
            ("database-url", "default"): "postgresql://prod-db",
            ("api-key", "certificates"): "prod-api-key-123",
        }.get((name, vault))

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_client,
        )

        return mock_client

    def test_settings_source_initialization(self, settings_class):
        """Test initializing settings source."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/"),
            "certificates": VaultConfig(url="https://vault2.vault.azure.net/"),
        }

        source = AzureKeyVaultSettingsSource(
            settings_class, vaults=vaults, is_production=True
        )

        assert source.vaults == vaults
        assert source.is_production is True

    def test_get_field_value(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test getting field value from Key Vault."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultSettingsSource(settings_class, vaults=vaults)

        field_info = settings_class.model_fields["database_url"]
        value, key, is_complex = source.get_field_value(
            field_info, "database_url"
        )

        assert value == "postgresql://prod-db"
        assert key == "database_url"
        assert is_complex is False

    def test_get_field_value_custom_vault(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test getting field value from custom vault."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/"),
            "certificates": VaultConfig(url="https://vault2.vault.azure.net/"),
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultSettingsSource(settings_class, vaults=vaults)

        field_info = settings_class.model_fields["api_key"]
        value, key, is_complex = source.get_field_value(field_info, "api_key")

        assert value == "prod-api-key-123"
        assert key == "api_key"

    def test_skip_field(self, settings_class, mock_multi_vault_client, mocker):
        """Test skipping field marked with keyvault_skip."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultSettingsSource(settings_class, vaults=vaults)

        field_info = settings_class.model_fields["skip_field"]
        value, key, is_complex = source.get_field_value(
            field_info, "skip_field"
        )

        assert value is None  # Should be skipped
        assert key == "skip_field"

    def test_call_loads_all_secrets(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test __call__ loads all secrets."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/"),
            "certificates": VaultConfig(url="https://vault2.vault.azure.net/"),
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultSettingsSource(settings_class, vaults=vaults)
        values = source()

        assert "database_url" in values
        assert values["database_url"] == "postgresql://prod-db"
        assert "api_key" in values
        assert values["api_key"] == "prod-api-key-123"
        assert "skip_field" not in values  # Should be skipped

    def test_secret_name_transform(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test custom secret name transformation."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        # Custom transform: snake_case -> UPPER-KEBAB-CASE
        transform = lambda name: name.upper().replace("_", "-")

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultSettingsSource(
            settings_class, vaults=vaults, secret_name_transform=transform
        )

        # Test transform function was set
        assert source.secret_name_transform("test_field") == "TEST-FIELD"


class TestAzureKeyVaultRefreshableSettingsSource:
    """Test refreshable settings source with rotation detection."""

    @pytest.fixture
    def settings_class(self):
        """Create a test settings class."""

        class TestSettings(BaseSettings):
            database_url: str = Field(
                default="sqlite:///test.db",
                json_schema_extra={"keyvault_secret": "database-url"},
            )

        return TestSettings

    @pytest.fixture
    def mock_multi_vault_client(self, mocker):
        """Mock MultiVaultClient with rotation detection."""
        mock_client = mocker.MagicMock()
        mock_client.get_secret.return_value = "postgresql://prod-db"
        mock_client.refresh_if_rotated.return_value = "postgresql://prod-db-v2"
        mock_client.has_secret_rotated.return_value = False

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_client,
        )

        return mock_client

    def test_refreshable_source_initialization(self, settings_class):
        """Test initializing refreshable settings source."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        source = AzureKeyVaultRefreshableSettingsSource(
            settings_class, vaults=vaults, auto_refresh_on_rotation=True
        )

        assert source.auto_refresh_on_rotation is True

    def test_get_field_value_with_auto_refresh(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test getting field value with auto-refresh enabled."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultRefreshableSettingsSource(
            settings_class, vaults=vaults, auto_refresh_on_rotation=True
        )

        field_info = settings_class.model_fields["database_url"]
        value, key, is_complex = source.get_field_value(
            field_info, "database_url"
        )

        # Should use refresh_if_rotated when auto_refresh enabled
        mock_multi_vault_client.refresh_if_rotated.assert_called()
        assert value == "postgresql://prod-db-v2"

    def test_refresh_secrets(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test manually refreshing secrets."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultRefreshableSettingsSource(
            settings_class, vaults=vaults
        )

        source.refresh_secrets()
        mock_multi_vault_client.invalidate_cache.assert_called_with(vault=None)

        source.refresh_secrets(vault="default")
        mock_multi_vault_client.invalidate_cache.assert_called_with(
            vault="default"
        )

    def test_check_rotations(
        self, settings_class, mock_multi_vault_client, mocker
    ):
        """Test checking for rotated secrets."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/")
        }

        mocker.patch(
            "netrun_config.settings_source.MultiVaultClient",
            return_value=mock_multi_vault_client,
        )

        source = AzureKeyVaultRefreshableSettingsSource(
            settings_class, vaults=vaults
        )

        # Simulate rotation
        mock_multi_vault_client.has_secret_rotated.return_value = True

        rotated = source.check_rotations()
        assert "default" in rotated
        assert "database-url" in rotated["default"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
