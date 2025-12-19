"""
Tests for KeyVault integration.

Comprehensive test suite covering:
- Azure SDK unavailable fallback
- Secret retrieval and caching
- Credential selection (Managed Identity vs DefaultAzureCredential)
- Error handling and fallback behavior
- Integration patterns
"""

import os
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from netrun.config import BaseConfig, Field, KeyVaultMixin


class TestKeyVaultMixinWithoutAzure:
    """Tests for KeyVaultMixin when Azure SDK is not available."""

    def test_fallback_to_env_when_azure_unavailable(self, clean_env, mock_keyvault):
        """Test that Key Vault falls back to env vars when Azure SDK unavailable."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        clean_env.setenv("DATABASE_PASSWORD", "env_password")
        settings = TestSettings()

        # Should fall back to environment variable
        result = settings.get_keyvault_secret("database-password")
        assert result == "env_password"

    def test_keyvault_disabled_without_url(self, clean_env, mock_keyvault):
        """Test that Key Vault is disabled when URL is not set."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = None

        settings = TestSettings()
        # Access via property which triggers lazy initialization
        assert settings._kv_enabled is False


class TestKeyVaultMixinMocked:
    """Tests for KeyVaultMixin with mocked Azure SDK."""

    @pytest.fixture
    def mock_azure_sdk(self):
        """Mock Azure SDK components."""
        with patch("netrun_config.keyvault.AZURE_AVAILABLE", True), patch(
            "netrun_config.keyvault.SecretClient"
        ) as mock_client, patch(
            "netrun_config.keyvault.DefaultAzureCredential"
        ) as mock_credential:
            mock_secret = Mock()
            mock_secret.value = "keyvault_secret_value"
            mock_client.return_value.get_secret.return_value = mock_secret
            yield {
                "client": mock_client,
                "credential": mock_credential,
                "secret": mock_secret,
            }

    def test_keyvault_initialization(self, clean_env, mock_azure_sdk):
        """Test Key Vault client initialization."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        settings = TestSettings()
        # Access via property which triggers lazy initialization
        assert settings._kv_enabled is True
        mock_azure_sdk["client"].assert_called_once()

    def test_get_secret_from_keyvault(self, clean_env, mock_azure_sdk):
        """Test retrieving secret from Key Vault."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        settings = TestSettings()
        settings.clear_keyvault_cache()
        result = settings.get_keyvault_secret("test-secret")

        assert result == "keyvault_secret_value"
        mock_azure_sdk["client"].return_value.get_secret.assert_called_with(
            "test-secret"
        )

    def test_secret_caching(self, clean_env, mock_azure_sdk):
        """Test that secrets are cached."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        settings = TestSettings()
        settings.clear_keyvault_cache()

        # First call - should hit Key Vault
        result1 = settings.get_keyvault_secret("test-secret")
        # Second call - should use cache
        result2 = settings.get_keyvault_secret("test-secret")

        assert result1 == result2
        # Should only call get_secret once due to caching
        assert mock_azure_sdk["client"].return_value.get_secret.call_count == 1

    def test_clear_cache(self, clean_env, mock_azure_sdk):
        """Test clearing Key Vault cache."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        settings = TestSettings()
        settings.clear_keyvault_cache()

        # Get secret (cached)
        settings.get_keyvault_secret("test-secret")

        # Clear cache
        settings.clear_keyvault_cache()

        # Get secret again (should hit Key Vault again)
        settings.get_keyvault_secret("test-secret")

        assert mock_azure_sdk["client"].return_value.get_secret.call_count == 2


class TestKeyVaultMixinResourceNotFound:
    """Tests for handling missing secrets."""

    @pytest.fixture
    def mock_azure_not_found(self):
        """Mock Azure SDK with ResourceNotFoundError."""
        from azure.core.exceptions import ResourceNotFoundError

        with patch("netrun_config.keyvault.AZURE_AVAILABLE", True), patch(
            "netrun_config.keyvault.SecretClient"
        ) as mock_client, patch(
            "netrun_config.keyvault.DefaultAzureCredential"
        ):
            mock_client.return_value.get_secret.side_effect = ResourceNotFoundError(
                "Secret not found"
            )
            yield mock_client

    def test_fallback_to_env_on_not_found(self, clean_env, mock_azure_not_found):
        """Test fallback to env var when secret not found in Key Vault."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        clean_env.setenv("MISSING_SECRET", "fallback_value")
        settings = TestSettings()
        settings.clear_keyvault_cache()

        result = settings.get_keyvault_secret("missing-secret")
        assert result == "fallback_value"


class TestKeyVaultMixinCredentials:
    """Tests for credential selection."""

    @pytest.fixture
    def mock_credential_selection(self):
        """Mock credential classes."""
        with patch("netrun_config.keyvault.AZURE_AVAILABLE", True), patch(
            "netrun_config.keyvault.ManagedIdentityCredential"
        ) as mock_managed, patch(
            "netrun_config.keyvault.DefaultAzureCredential"
        ) as mock_default, patch(
            "netrun_config.keyvault.SecretClient"
        ):
            yield {"managed": mock_managed, "default": mock_default}

    def test_uses_default_credential_in_dev(
        self, clean_env, mock_credential_selection
    ):
        """Test that DefaultAzureCredential is used in development."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        clean_env.setenv("APP_ENVIRONMENT", "development")
        settings = TestSettings()

        # Trigger lazy initialization by accessing _kv_enabled
        _ = settings._kv_enabled

        mock_credential_selection["default"].assert_called()
        mock_credential_selection["managed"].assert_not_called()

    def test_uses_managed_identity_in_production(
        self, clean_env, mock_credential_selection
    ):
        """Test that ManagedIdentityCredential is used in production."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        clean_env.setenv("APP_ENVIRONMENT", "production")
        settings = TestSettings()

        # Trigger lazy initialization by accessing _kv_enabled
        _ = settings._kv_enabled

        mock_credential_selection["managed"].assert_called()


class TestKeyVaultIntegrationPattern:
    """Tests for practical Key Vault integration patterns."""

    def test_hybrid_config_pattern(self, clean_env, mock_keyvault):
        """Test hybrid configuration with Key Vault for secrets."""

        class HybridSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = None
            database_password: str = ""

            @property
            def database_password_resolved(self) -> str:
                """Get password from Key Vault or environment."""
                if self.is_production and self.KEY_VAULT_URL:
                    return self.get_keyvault_secret("database-password") or ""
                return self.database_password

        clean_env.setenv("APP_ENVIRONMENT", "development")
        clean_env.setenv("DATABASE_PASSWORD", "dev_password")

        settings = HybridSettings()
        # In development without Key Vault, returns the field value (populated from env)
        assert settings.database_password_resolved == "dev_password"


class TestKeyVaultSecretNameConversion:
    """Tests for secret name conversion (hyphens to underscores)."""

    def test_secret_name_conversion(self, clean_env, mock_keyvault):
        """Test that secret names are converted from hyphens to underscores for env vars."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = None

        clean_env.setenv("DATABASE_PASSWORD", "env_value")
        settings = TestSettings()

        # Secret name with hyphens should look for env var with underscores
        result = settings.get_keyvault_secret("database-password")
        assert result == "env_value"

    @pytest.mark.parametrize("secret_name,env_var_name,test_value", [
        ("database-password", "DATABASE_PASSWORD", "test_db_password_32_chars_long!!!"),
        ("api-key", "API_KEY", "test_api_key_value"),
        ("jwt-secret", "JWT_SECRET", "test_jwt_secret_32_characters_long!!"),
    ])
    def test_multiple_secret_conversions(
        self, clean_env, mock_keyvault, secret_name, env_var_name, test_value
    ):
        """Test various secret name conversions."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = None

        clean_env.setenv(env_var_name, test_value)
        settings = TestSettings()

        result = settings.get_keyvault_secret(secret_name)
        assert result == test_value


class TestKeyVaultErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.fixture
    def mock_azure_generic_error(self):
        """Mock Azure SDK with generic exception."""
        with patch("netrun_config.keyvault.AZURE_AVAILABLE", True), patch(
            "netrun_config.keyvault.SecretClient"
        ) as mock_client, patch(
            "netrun_config.keyvault.DefaultAzureCredential"
        ):
            mock_client.return_value.get_secret.side_effect = Exception(
                "Network error"
            )
            yield mock_client

    def test_generic_error_returns_none(self, clean_env, mock_azure_generic_error):
        """Test that generic errors return None instead of crashing."""

        class TestSettings(BaseConfig, KeyVaultMixin):
            KEY_VAULT_URL: Optional[str] = "https://test.vault.azure.net"

        settings = TestSettings()
        settings.clear_keyvault_cache()

        result = settings.get_keyvault_secret("test-secret")
        assert result is None
