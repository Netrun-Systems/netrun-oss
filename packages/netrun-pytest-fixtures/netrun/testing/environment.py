"""
Environment Fixtures for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides environment variable isolation and management for testing.
Ensures tests don't pollute system environment and maintain isolation.

Usage:
    def test_with_env(clean_env):
        clean_env.setenv("API_KEY", "test-key")
        assert os.getenv("API_KEY") == "test-key"
        # Environment automatically restored after test

Fixtures:
    - clean_env: Clean environment with Netrun variables cleared
    - sample_env_vars: Common test environment variables
    - mock_env_file: Temporary .env file for testing
    - temp_env_file: Factory for creating custom .env files
    - reset_environment: Auto-cleanup of environment variables
"""

import pytest
import os
import tempfile
from pathlib import Path
from typing import Dict, Generator

# Graceful netrun-logging integration (optional)
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


@pytest.fixture
def clean_env(monkeypatch):
    """
    Fixture to provide a clean environment for each test.

    Clears all Netrun-related environment variables before test execution.
    Provides monkeypatch instance for setting custom env vars.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        monkeypatch: Configured monkeypatch instance

    Example:
        def test_config_from_env(clean_env):
            clean_env.setenv("DATABASE_URL", "postgresql://test")
            clean_env.setenv("REDIS_URL", "redis://test")

            config = load_config()
            assert config.database_url == "postgresql://test"
    """
    # Clear all Netrun-related environment variables
    env_vars = [
        # Application
        "APP_NAME", "APP_VERSION", "APP_ENVIRONMENT", "APP_DEBUG",

        # Security
        "APP_SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY",
        "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS",

        # Database
        "DATABASE_URL", "DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW",
        "DATABASE_POOL_TIMEOUT", "DATABASE_POOL_RECYCLE",
        "TEST_DATABASE_URL",

        # Redis
        "REDIS_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_DB",
        "REDIS_PASSWORD", "REDIS_SSL",

        # Logging
        "LOG_LEVEL", "LOG_FORMAT", "LOG_FILE", "LOG_JSON",

        # Monitoring
        "ENABLE_METRICS", "METRICS_PORT", "SENTRY_DSN",

        # Azure
        "KEY_VAULT_URL", "AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",

        # CORS
        "CORS_ORIGINS", "CORS_ALLOW_CREDENTIALS",

        # API
        "API_PREFIX", "API_VERSION",
    ]

    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    return monkeypatch


@pytest.fixture
def sample_env_vars() -> Dict[str, str]:
    """
    Fixture providing common test environment variables as a dictionary.

    Returns standard configuration for Netrun applications with
    safe test values (no production credentials).

    Returns:
        Dict[str, str]: Test environment variables

    Example:
        def test_config_loading(clean_env, sample_env_vars):
            for key, value in sample_env_vars.items():
                clean_env.setenv(key, value)

            config = load_config()
            assert config.app_name == "TestApp"
            assert config.environment == "testing"
    """
    return {
        "APP_NAME": "TestApp",
        "APP_VERSION": "2.0.0",
        "APP_ENVIRONMENT": "testing",
        "APP_SECRET_KEY": "test-secret-key-32-characters-min",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-chars-min",
        "JWT_ALGORITHM": "RS256",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "30",
        "DATABASE_URL": "postgresql://testuser:testpass@localhost:5432/testdb",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0",
        "LOG_LEVEL": "INFO",
        "CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
        "ENABLE_METRICS": "false",
    }


@pytest.fixture
def mock_env_file(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary .env file for testing.

    Creates .env file with standard Netrun configuration for
    testing environment file loading.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path: Path to temporary .env file

    Example:
        def test_load_env_file(mock_env_file):
            from dotenv import load_dotenv

            load_dotenv(mock_env_file)
            assert os.getenv("APP_NAME") == "EnvFileApp"
            assert os.getenv("APP_ENVIRONMENT") == "development"
    """
    env_file = tmp_path / ".env"
    env_content = """
APP_NAME=EnvFileApp
APP_VERSION=1.5.0
APP_ENVIRONMENT=development
APP_SECRET_KEY=env-file-secret-key-32-chars-minimum
DATABASE_URL=postgresql://envuser:envpass@localhost:5432/envdb
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=WARNING
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
"""
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def temp_env_file(tmp_path: Path):
    """
    Factory fixture for creating custom temporary .env files.

    Returns function that creates .env file with custom content.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Callable: Function that creates .env file from dict

    Example:
        def test_custom_env_file(temp_env_file):
            env_vars = {
                "CUSTOM_VAR": "custom_value",
                "API_KEY": "test-api-key"
            }
            env_path = temp_env_file(env_vars)

            from dotenv import load_dotenv
            load_dotenv(env_path)
            assert os.getenv("CUSTOM_VAR") == "custom_value"
    """
    def _create_env_file(env_vars: Dict[str, str], filename: str = ".env") -> Path:
        env_file = tmp_path / filename
        content = "\n".join(f"{key}={value}" for key, value in env_vars.items())
        env_file.write_text(content)
        return env_file

    return _create_env_file


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Reset environment variables before and after each test.

    Autouse fixture that ensures test isolation by capturing
    and restoring environment state automatically.

    Yields:
        None

    Example:
        # No explicit use needed - runs automatically
        def test_env_modification():
            os.environ["TEMP_VAR"] = "value"
            # TEMP_VAR automatically cleaned up after test
    """
    # Capture original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def isolated_env(monkeypatch):
    """
    Create completely isolated environment (no system env vars).

    Use for tests requiring absolute environment isolation.
    All system environment variables are cleared.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        monkeypatch: Configured monkeypatch instance

    Example:
        def test_no_env_fallback(isolated_env):
            # No environment variables set
            config = load_config()
            # Should use defaults
            assert config.app_environment == "development"
    """
    # Clear ALL environment variables
    for key in list(os.environ.keys()):
        monkeypatch.delenv(key, raising=False)

    return monkeypatch


@pytest.fixture
def mock_azure_env(clean_env):
    """
    Set up Azure-specific environment variables for testing.

    Configures Azure credential and Key Vault environment for
    testing Azure integration without actual Azure resources.

    Args:
        clean_env: Clean environment fixture

    Returns:
        monkeypatch: Configured monkeypatch with Azure env

    Example:
        def test_azure_keyvault(mock_azure_env):
            config = load_azure_config()
            assert config.key_vault_url == "https://test-vault.vault.azure.net"
    """
    clean_env.setenv("KEY_VAULT_URL", "https://test-vault.vault.azure.net")
    clean_env.setenv("AZURE_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    clean_env.setenv("AZURE_CLIENT_ID", "00000000-0000-0000-0000-000000000002")
    clean_env.setenv("AZURE_CLIENT_SECRET", "test-client-secret-value")
    clean_env.setenv("AZURE_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000003")

    return clean_env


@pytest.fixture
def production_like_env(clean_env):
    """
    Set up production-like environment for integration testing.

    Configures environment similar to production but with test values.
    Use for testing production configuration validation.

    Args:
        clean_env: Clean environment fixture

    Returns:
        monkeypatch: Configured monkeypatch with production-like env

    Example:
        def test_production_config(production_like_env):
            config = load_config()
            assert config.environment == "production"
            assert config.debug is False
    """
    clean_env.setenv("APP_ENVIRONMENT", "production")
    clean_env.setenv("APP_DEBUG", "false")
    clean_env.setenv("LOG_LEVEL", "WARNING")
    clean_env.setenv("ENABLE_METRICS", "true")
    clean_env.setenv("DATABASE_URL", "postgresql://prod_user:prod_pass@db.example.com:5432/prod_db")
    clean_env.setenv("REDIS_URL", "redis://cache.example.com:6379/0")
    clean_env.setenv("CORS_ORIGINS", "https://app.netrunsystems.com")

    return clean_env
