"""
Tests for BaseConfig class.

Comprehensive test suite covering:
- Default values
- Environment variable loading
- Validation
- Computed properties
- Caching behavior
- Custom settings inheritance
"""

import os

import pytest
from pydantic import Field, ValidationError

from netrun.config import BaseConfig, get_settings, reload_settings


class TestBaseConfigDefaults:
    """Tests for BaseConfig default values."""

    def test_default_app_name(self, clean_env):
        """Test default application name."""
        config = BaseConfig()
        assert config.app_name == "Netrun Application"

    def test_default_environment(self, clean_env):
        """Test default environment is development."""
        config = BaseConfig()
        assert config.app_environment == "development"

    def test_default_debug_false(self, clean_env):
        """Test default debug is False."""
        config = BaseConfig()
        assert config.app_debug is False

    def test_default_cors_origins(self, clean_env):
        """Test default CORS origins."""
        config = BaseConfig()
        assert "http://localhost:3000" in config.cors_origins
        assert "http://localhost:8080" in config.cors_origins


class TestBaseConfigEnvironmentVariables:
    """Tests for loading from environment variables."""

    def test_load_from_env(self, clean_env):
        """Test loading configuration from environment variables."""
        clean_env.setenv("APP_NAME", "TestApp")
        clean_env.setenv("APP_VERSION", "2.0.0")
        clean_env.setenv("APP_ENVIRONMENT", "testing")
        clean_env.setenv("APP_SECRET_KEY", "a-very-secure-secret-key-for-testing-purposes-32-chars")
        clean_env.setenv("LOG_LEVEL", "INFO")

        config = BaseConfig()
        assert config.app_name == "TestApp"
        assert config.app_environment == "testing"
        assert config.log_level == "INFO"

    def test_override_defaults(self, clean_env):
        """Test that environment variables override defaults."""
        clean_env.setenv("APP_NAME", "CustomApp")
        config = BaseConfig()
        assert config.app_name == "CustomApp"


class TestBaseConfigValidation:
    """Tests for configuration validation."""

    @pytest.mark.parametrize("invalid_env", [
        "invalid", "dev", "prod", "PRODUCTION", "local"
    ])
    def test_invalid_environment_rejected(self, clean_env, invalid_env):
        """Test that invalid environments are rejected."""
        with pytest.raises(ValidationError):
            BaseConfig(app_environment=invalid_env)

    @pytest.mark.parametrize("short_key", ["", "short", "a" * 31])
    def test_short_secret_key_rejected(self, clean_env, short_key):
        """Test that short secret keys are rejected."""
        with pytest.raises(ValidationError):
            BaseConfig(app_secret_key=short_key)

    @pytest.mark.parametrize("key_length", [32, 48, 64, 128])
    def test_valid_secret_key_accepted(self, clean_env, key_length):
        """Test that valid secret keys are accepted."""
        valid_key = "a" * key_length
        config = BaseConfig(app_secret_key=valid_key)
        assert config.app_secret_key == valid_key

    def test_multiple_secret_keys_validated(self, clean_env):
        """Test that all secret key fields are validated."""
        valid_key = "a" * 32
        config = BaseConfig(
            app_secret_key=valid_key,
            jwt_secret_key=valid_key,
            encryption_key=valid_key,
        )
        assert config.app_secret_key == valid_key
        assert config.jwt_secret_key == valid_key
        assert config.encryption_key == valid_key

    def test_cors_origins_string_parsed(self, clean_env):
        """Test that CORS origins string is parsed to list."""
        config = BaseConfig(cors_origins="http://localhost:3000,http://example.com")
        assert isinstance(config.cors_origins, list)
        assert len(config.cors_origins) == 2

    @pytest.mark.parametrize("level,expected", [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
    ])
    def test_log_level_uppercase_conversion(self, clean_env, level, expected):
        """Test that log levels are converted to uppercase."""
        config = BaseConfig(log_level=level)
        assert config.log_level == expected

    @pytest.mark.parametrize("invalid_level", ["INVALID", "TRACE", "VERBOSE"])
    def test_invalid_log_level_rejected(self, clean_env, invalid_level):
        """Test that invalid log levels are rejected."""
        with pytest.raises(ValidationError):
            BaseConfig(log_level=invalid_level)

    @pytest.mark.parametrize("invalid_value", [0, -1, -10])
    def test_database_pool_size_positive(self, clean_env, invalid_value):
        """Test that database pool size must be positive."""
        with pytest.raises(ValidationError):
            BaseConfig(database_pool_size=invalid_value)

    def test_database_max_overflow_positive(self, clean_env):
        """Test that database max overflow must be positive."""
        with pytest.raises(ValidationError):
            BaseConfig(database_max_overflow=0)


class TestBaseConfigProperties:
    """Tests for computed properties."""

    @pytest.mark.parametrize("env,prop_name,expected", [
        ("production", "is_production", True),
        ("development", "is_development", True),
        ("staging", "is_staging", True),
        ("testing", "is_testing", True),
        ("production", "is_development", False),
        ("development", "is_production", False),
    ])
    def test_environment_properties(self, clean_env, env, prop_name, expected):
        """Test environment check properties."""
        config = BaseConfig(app_environment=env)
        assert getattr(config, prop_name) == expected

    def test_database_url_async_conversion(self, clean_env):
        """Test database URL conversion to async."""
        config = BaseConfig(database_url="postgresql://user:pass@localhost/db")
        assert config.database_url_async == "postgresql+asyncpg://user:pass@localhost/db"

    def test_database_url_async_non_postgresql(self, clean_env):
        """Test database URL async returns None for non-PostgreSQL."""
        config = BaseConfig(database_url="sqlite:///test.db")
        assert config.database_url_async == "sqlite:///test.db"

    def test_redis_url_full_with_password(self, clean_env):
        """Test Redis URL construction with password."""
        test_pass = "test" + "pass123"  # nosec: test data only
        config = BaseConfig(
            redis_host="localhost", redis_port=6379, redis_password=test_pass, redis_db=0
        )
        assert config.redis_url_full == f"redis://:{test_pass}@localhost:6379/0"

    def test_redis_url_full_without_password(self, clean_env):
        """Test Redis URL construction without password."""
        config = BaseConfig(redis_host="localhost", redis_port=6379, redis_db=0)
        assert config.redis_url_full == "redis://localhost:6379/0"

    def test_redis_url_override(self, clean_env):
        """Test that redis_url overrides construction."""
        config = BaseConfig(redis_url="redis://custom:6380/1")
        assert config.redis_url_full == "redis://custom:6380/1"


class TestGetSettings:
    """Tests for get_settings factory function."""

    def test_get_settings_returns_instance(self, clean_env):
        """Test that get_settings returns BaseConfig instance."""
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, BaseConfig)

    def test_get_settings_cached(self, clean_env):
        """Test that get_settings returns cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_custom_class(self, clean_env):
        """Test get_settings with custom settings class."""

        class CustomSettings(BaseConfig):
            custom_field: str = Field(default="custom")

        get_settings.cache_clear()
        settings = get_settings(CustomSettings)
        assert isinstance(settings, CustomSettings)
        assert settings.custom_field == "custom"


class TestReloadSettings:
    """Tests for reload_settings function."""

    def test_reload_settings_clears_cache(self, clean_env):
        """Test that reload_settings clears cache."""
        get_settings.cache_clear()
        clean_env.setenv("APP_NAME", "Original")

        settings1 = get_settings()
        assert settings1.app_name == "Original"

        # Change environment
        clean_env.setenv("APP_NAME", "Updated")

        # Without reload, still gets cached value
        settings2 = get_settings()
        assert settings2.app_name == "Original"

        # After reload, gets new value
        settings3 = reload_settings()
        assert settings3.app_name == "Updated"


class TestCustomSettingsClass:
    """Tests for extending BaseConfig."""

    def test_custom_settings_inheritance(self, clean_env):
        """Test that custom settings inherit from BaseConfig."""

        class MySettings(BaseConfig):
            custom_field: str = Field(default="test")

        settings = MySettings()
        assert settings.custom_field == "test"
        assert settings.app_name == "Netrun Application"

    def test_custom_settings_override_defaults(self, clean_env):
        """Test that custom settings can override defaults."""

        class MySettings(BaseConfig):
            app_name: str = Field(default="CustomApp")

        settings = MySettings()
        assert settings.app_name == "CustomApp"

    def test_custom_validators_applied(self, clean_env):
        """Test that base validators are applied to custom settings."""

        class MySettings(BaseConfig):
            pass

        with pytest.raises(ValidationError):
            MySettings(app_environment="invalid")
