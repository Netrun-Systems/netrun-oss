"""
Pytest configuration and shared fixtures for netrun-config tests.

Provides reusable fixtures for:
- Environment variable management
- Mock .env files
- Mock Azure Key Vault clients
- Settings cache management
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Generator
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def clean_env(monkeypatch):
    """
    Fixture to provide a clean environment for each test.

    Clears all relevant environment variables before test execution.
    """
    # Clear all Netrun-related environment variables
    env_vars = [
        "APP_NAME", "APP_VERSION", "APP_ENVIRONMENT", "APP_DEBUG",
        "APP_SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY",
        "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        "DATABASE_URL", "DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW",
        "DATABASE_POOL_TIMEOUT", "DATABASE_POOL_RECYCLE",
        "REDIS_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD",
        "LOG_LEVEL", "LOG_FORMAT", "LOG_FILE",
        "ENABLE_METRICS", "METRICS_PORT", "SENTRY_DSN",
        "KEY_VAULT_URL", "CORS_ORIGINS", "CORS_ALLOW_CREDENTIALS",
        "AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    yield monkeypatch


@pytest.fixture
def sample_env_vars():
    """
    Fixture providing common test environment variables as a dictionary.

    Returns:
        Dictionary of test environment variables
    """
    return {
        "APP_NAME": "TestApp",
        "APP_VERSION": "2.0.0",
        "APP_ENVIRONMENT": "testing",
        "APP_SECRET_KEY": "a-very-secure-secret-key-for-testing-purposes-32-chars",
        "JWT_SECRET_KEY": "another-very-secure-jwt-secret-key-for-testing-32-chars",
        "DATABASE_URL": "postgresql://testuser:testpass@testhost:5432/testdb",
        "REDIS_HOST": "redis.test.com",
        "REDIS_PORT": "6380",
        "LOG_LEVEL": "INFO",
        "CORS_ORIGINS": "http://test1.com,http://test2.com",
    }


@pytest.fixture
def mock_env_file(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary .env file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path to the temporary .env file
    """
    env_file = tmp_path / ".env"
    env_content = """
APP_NAME=EnvFileApp
APP_VERSION=1.5.0
APP_ENVIRONMENT=development
APP_SECRET_KEY=env-file-secret-key-with-32-chars-minimum-length
DATABASE_URL=postgresql://envuser:envpass@localhost:5432/envdb
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=WARNING
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
"""
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def mock_keyvault_client():
    """
    Fixture to create a mock Azure Key Vault SecretClient.

    Returns:
        Mock SecretClient with configurable responses
    """
    mock_client = Mock()

    # Mock secret object
    mock_secret = Mock()
    mock_secret.value = "test-secret-value-from-keyvault-32-chars-long"

    # Configure get_secret to return mock secret
    mock_client.get_secret.return_value = mock_secret

    return mock_client


@pytest.fixture
def mock_azure_credential():
    """
    Fixture to create a mock Azure credential.

    Returns:
        Mock credential object
    """
    return Mock()


@pytest.fixture
def mock_keyvault():
    """
    Mock Azure Key Vault availability.

    Simulates Azure SDK being unavailable for testing fallback behavior.
    """
    with patch("netrun_config.keyvault.AZURE_AVAILABLE", False):
        yield


@pytest.fixture
def settings_cache_reset():
    """
    Fixture to reset settings cache before and after each test.

    This ensures test isolation when using cached settings.
    """
    from netrun.config import get_settings

    # Clear cache before test
    get_settings.__wrapped__.cache_clear()

    yield

    # Clear cache after test
    get_settings.__wrapped__.cache_clear()


@pytest.fixture
def sample_database_urls():
    """
    Fixture providing various database URL formats for testing.

    Returns:
        Dictionary of valid and invalid database URLs
    """
    return {
        "valid": [
            "postgresql://user:pass@localhost:5432/db",
            "postgresql://user:pass@host.com:5432/db?sslmode=require",
            "mysql://user:pass@localhost:3306/db",
            "sqlite:///path/to/database.db",
        ],
        "invalid": [
            "not-a-url",
            "missing-scheme.com",
            "",
        ],
    }


@pytest.fixture
def sample_cors_origins():
    """
    Fixture providing various CORS origin formats for testing.

    Returns:
        Dictionary of CORS origin test cases
    """
    return {
        "string_single": "http://localhost:3000",
        "string_multiple": "http://localhost:3000,http://localhost:8080",
        "string_whitespace": "  http://localhost:3000  ,  http://localhost:8080  ",
        "list": ["http://localhost:3000", "http://localhost:8080"],
        "empty_string": "",
        "none": None,
    }
