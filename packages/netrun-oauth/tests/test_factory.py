"""
Tests for OAuthAdapterFactory

Part of: netrun-oauth v1.0.0
"""

import pytest
import os
from netrun_oauth import (
    OAuthAdapterFactory,
    MicrosoftAdapter,
    GoogleAdapter,
    UnsupportedPlatformError,
)


def test_factory_create_microsoft():
    """Test creating Microsoft adapter via factory"""
    adapter = OAuthAdapterFactory.create("microsoft")
    assert isinstance(adapter, MicrosoftAdapter)
    assert adapter.platform_name == "microsoft"


def test_factory_create_google():
    """Test creating Google adapter via factory"""
    adapter = OAuthAdapterFactory.create("google")
    assert isinstance(adapter, GoogleAdapter)
    assert adapter.platform_name == "google"


def test_factory_create_with_explicit_credentials():
    """Test creating adapter with explicit credentials"""
    adapter = OAuthAdapterFactory.create(
        "microsoft",
        client_id="test_client_id",
        client_secret="test_client_secret"
    )
    assert adapter.client_id == "test_client_id"
    assert adapter.client_secret == "test_client_secret"


def test_factory_unsupported_platform():
    """Test creating adapter for unsupported platform raises exception"""
    with pytest.raises(UnsupportedPlatformError):
        OAuthAdapterFactory.create("unsupported_platform")


def test_factory_list_platforms():
    """Test listing all supported platforms"""
    platforms = OAuthAdapterFactory.list_platforms()
    assert "microsoft" in platforms
    assert "google" in platforms
    assert "salesforce" in platforms
    assert len(platforms) > 0


def test_factory_credential_resolution_from_env(monkeypatch):
    """Test credential resolution from environment variables"""
    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "env_client_id")
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "env_client_secret")

    adapter = OAuthAdapterFactory.create("microsoft")
    assert adapter.client_id == "env_client_id"
    assert adapter.client_secret == "env_client_secret"


def test_factory_credential_resolution_placeholder_fallback():
    """Test credential resolution falls back to placeholders"""
    # Ensure no env vars are set
    os.environ.pop("TEST_PLATFORM_CLIENT_ID", None)
    os.environ.pop("TEST_PLATFORM_CLIENT_SECRET", None)

    adapter = OAuthAdapterFactory.create("microsoft")
    # Should have placeholder format
    assert "{{" in adapter.client_id or adapter.client_id.startswith("env_")
