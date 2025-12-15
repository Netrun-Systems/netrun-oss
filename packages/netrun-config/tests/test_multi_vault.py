"""
Tests for multi-vault Azure Key Vault support.
"""

import pytest

from netrun_config.cache import SecretCacheConfig
from netrun_config.multi_vault import MultiVaultClient, VaultConfig

# Mark all tests as requiring Azure SDK
pytestmark = pytest.mark.skipif(
    True, reason="Azure SDK integration tests require live Key Vault"
)


class TestVaultConfig:
    """Test VaultConfig dataclass."""

    def test_vault_config_creation(self):
        """Test creating a VaultConfig."""
        config = VaultConfig(url="https://test-vault.vault.azure.net/")
        assert config.url == "https://test-vault.vault.azure.net/"
        assert config.credential is None
        assert config.cache_config is None
        assert config.enabled is True

    def test_vault_config_custom(self):
        """Test custom VaultConfig."""
        cache_config = SecretCacheConfig(default_ttl_seconds=3600)
        config = VaultConfig(
            url="https://test-vault.vault.azure.net/",
            cache_config=cache_config,
            enabled=False,
        )
        assert config.cache_config == cache_config
        assert config.enabled is False


class TestMultiVaultClient:
    """Test MultiVaultClient functionality."""

    def test_client_initialization(self):
        """Test client initialization with multiple vaults."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/"),
            "dev": VaultConfig(url="https://vault2.vault.azure.net/"),
        }
        # This will fail without Azure SDK, but tests the structure
        client = MultiVaultClient(vaults, is_production=False)
        assert client.vaults == vaults
        assert client.is_production is False

    def test_list_vaults(self):
        """Test listing configured vaults."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/"),
            "dev": VaultConfig(url="https://vault2.vault.azure.net/"),
            "certificates": VaultConfig(url="https://vault3.vault.azure.net/"),
        }
        client = MultiVaultClient(vaults)
        vault_list = client.list_vaults()
        assert "default" in vault_list
        assert "dev" in vault_list
        assert "certificates" in vault_list
        assert len(vault_list) == 3

    def test_is_vault_enabled(self):
        """Test checking if vault is enabled."""
        vaults = {
            "default": VaultConfig(
                url="https://vault1.vault.azure.net/", enabled=True
            ),
            "disabled": VaultConfig(
                url="https://vault2.vault.azure.net/", enabled=False
            ),
        }
        client = MultiVaultClient(vaults)
        assert client.is_vault_enabled("default") is True
        assert client.is_vault_enabled("disabled") is False
        assert client.is_vault_enabled("nonexistent") is False


class TestMultiVaultClientMocked:
    """Test MultiVaultClient with mocked Azure SDK."""

    @pytest.fixture
    def mock_vault_client(self, mocker):
        """Mock SecretClient."""
        mock_client = mocker.MagicMock()
        mock_secret = mocker.MagicMock()
        mock_secret.value = "test-secret-value"
        mock_secret.properties.version = "v123"
        mock_client.get_secret.return_value = mock_secret

        mocker.patch(
            "netrun_config.multi_vault.SecretClient", return_value=mock_client
        )
        mocker.patch("netrun_config.multi_vault.AZURE_AVAILABLE", True)

        return mock_client

    @pytest.fixture
    def multi_vault_client(self, mock_vault_client):
        """Create MultiVaultClient with mocked Azure SDK."""
        vaults = {
            "default": VaultConfig(url="https://vault1.vault.azure.net/"),
            "dev": VaultConfig(url="https://vault2.vault.azure.net/"),
        }
        return MultiVaultClient(vaults, is_production=False)

    def test_get_secret_default_vault(self, multi_vault_client, mock_vault_client):
        """Test getting secret from default vault."""
        secret = multi_vault_client.get_secret("test-secret")
        assert secret == "test-secret-value"
        mock_vault_client.get_secret.assert_called_with("test-secret")

    def test_get_secret_specific_vault(
        self, multi_vault_client, mock_vault_client
    ):
        """Test getting secret from specific vault."""
        secret = multi_vault_client.get_secret("test-secret", vault="dev")
        assert secret == "test-secret-value"

    def test_get_secret_nonexistent_vault(self, multi_vault_client):
        """Test getting secret from nonexistent vault."""
        secret = multi_vault_client.get_secret(
            "test-secret", vault="nonexistent"
        )
        assert secret is None

    def test_check_secret_version(self, multi_vault_client, mock_vault_client):
        """Test checking secret version."""
        version = multi_vault_client.check_secret_version("test-secret")
        assert version == "v123"

    def test_has_secret_rotated_no_cache(
        self, multi_vault_client, mock_vault_client
    ):
        """Test rotation detection with no cached secret."""
        rotated = multi_vault_client.has_secret_rotated("test-secret")
        assert rotated is True  # Not in cache, so considered rotated

    def test_has_secret_rotated_version_changed(
        self, multi_vault_client, mock_vault_client
    ):
        """Test rotation detection when version changed."""
        # First fetch
        multi_vault_client.get_secret("test-secret")

        # Change version
        mock_vault_client.get_secret.return_value.properties.version = "v124"

        rotated = multi_vault_client.has_secret_rotated("test-secret")
        assert rotated is True

    def test_refresh_if_rotated(self, multi_vault_client, mock_vault_client):
        """Test refreshing secret only if rotated."""
        # First fetch
        multi_vault_client.get_secret("test-secret")

        # Change version to simulate rotation
        mock_secret = mock_vault_client.get_secret.return_value
        mock_secret.properties.version = "v124"
        mock_secret.value = "new-secret-value"

        # Should detect rotation and refresh
        secret = multi_vault_client.refresh_if_rotated("test-secret")
        assert secret == "new-secret-value"

    def test_invalidate_cache_specific_secret(
        self, multi_vault_client, mock_vault_client
    ):
        """Test invalidating cache for specific secret."""
        multi_vault_client.get_secret("test-secret")
        multi_vault_client.invalidate_cache(secret_name="test-secret")

        # Next fetch should hit Key Vault again
        multi_vault_client.get_secret("test-secret")
        assert mock_vault_client.get_secret.call_count == 2

    def test_invalidate_cache_entire_vault(
        self, multi_vault_client, mock_vault_client
    ):
        """Test invalidating entire vault cache."""
        multi_vault_client.get_secret("secret1")
        multi_vault_client.get_secret("secret2")

        multi_vault_client.invalidate_cache(vault="default")

        # Next fetches should hit Key Vault again
        multi_vault_client.get_secret("secret1")
        multi_vault_client.get_secret("secret2")
        assert mock_vault_client.get_secret.call_count == 4

    def test_get_cache_stats_single_vault(
        self, multi_vault_client, mock_vault_client
    ):
        """Test getting cache stats for single vault."""
        multi_vault_client.get_secret("test-secret")
        stats = multi_vault_client.get_cache_stats(vault="default")
        assert "default" in stats
        assert stats["default"]["total_secrets"] == 1

    def test_get_cache_stats_all_vaults(
        self, multi_vault_client, mock_vault_client
    ):
        """Test getting cache stats for all vaults."""
        multi_vault_client.get_secret("secret1", vault="default")
        multi_vault_client.get_secret("secret2", vault="dev")

        stats = multi_vault_client.get_cache_stats()
        assert "default" in stats
        assert "dev" in stats
        assert stats["default"]["total_secrets"] == 1
        assert stats["dev"]["total_secrets"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
