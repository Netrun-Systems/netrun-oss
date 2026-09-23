"""
Tests for GCP Secret Manager integration (netrun.config.gcp_secrets).

All tests are hermetic: the google-cloud-secret-manager SDK is never actually
called. The client is either injected (a Mock) or the SDK is simulated as
absent via monkeypatching GCP_AVAILABLE.
"""

from unittest.mock import Mock

import pytest

from netrun.config import (
    GCPSecretError,
    GCPSecretManagerProvider,
    resolve_database_dsn,
)
from netrun.config import gcp_secrets


def _mock_gcp_client(secret_value: str = "postgresql://u:p@localhost:5432/db"):
    """Build a Mock mimicking SecretManagerServiceClient.access_secret_version."""
    client = Mock()
    response = Mock()
    response.payload.data = secret_value.encode("utf-8")
    client.access_secret_version.return_value = response
    return client


# ---------------------------------------------------------------------------
# GCPSecretManagerProvider
# ---------------------------------------------------------------------------

class TestGCPSecretManagerProvider:
    def test_get_secret_with_injected_client(self):
        client = _mock_gcp_client("the-secret-dsn")
        provider = GCPSecretManagerProvider(project_id="proj-123", client=client)

        value = provider.get_secret("database-url")

        assert value == "the-secret-dsn"
        client.access_secret_version.assert_called_once_with(
            request={
                "name": "projects/proj-123/secrets/database-url/versions/latest"
            }
        )

    def test_get_secret_custom_version(self):
        client = _mock_gcp_client("v5-value")
        provider = GCPSecretManagerProvider(project_id="proj-123", client=client)

        provider.get_secret("api-key", version="5")

        client.access_secret_version.assert_called_once_with(
            request={"name": "projects/proj-123/secrets/api-key/versions/5"}
        )

    def test_project_id_from_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-proj")
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        client = _mock_gcp_client()
        provider = GCPSecretManagerProvider(client=client)

        provider.get_secret("s")

        assert provider.project_id == "env-proj"
        client.access_secret_version.assert_called_once_with(
            request={"name": "projects/env-proj/secrets/s/versions/latest"}
        )

    def test_missing_project_id_raises(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        provider = GCPSecretManagerProvider(client=_mock_gcp_client())

        with pytest.raises(GCPSecretError, match="No GCP project id"):
            provider.get_secret("database-url")

    def test_empty_secret_raises(self):
        provider = GCPSecretManagerProvider(
            project_id="p", client=_mock_gcp_client("   ")
        )

        with pytest.raises(GCPSecretError, match="resolved empty"):
            provider.get_secret("database-url")

    def test_missing_sdk_raises_clear_error(self, monkeypatch):
        # Simulate google-cloud-secret-manager not installed AND no injected
        # client, so the lazy client build path is exercised.
        monkeypatch.setattr(gcp_secrets, "GCP_AVAILABLE", False)
        provider = GCPSecretManagerProvider(project_id="p")

        with pytest.raises(GCPSecretError, match="netrun-config\\[gcp\\]"):
            provider.get_secret("database-url")


# ---------------------------------------------------------------------------
# resolve_database_dsn
# ---------------------------------------------------------------------------

class TestResolveDatabaseDSN:
    def test_database_url_wins(self):
        env = {
            "DATABASE_URL": "postgresql://envwins@host/db",
            "PGPASSWORD": "should-not-be-used",
        }
        # Provider that would explode if ever reached.
        provider = GCPSecretManagerProvider(project_id="p", client=Mock())

        dsn = resolve_database_dsn(env=env, provider=provider)

        assert dsn == "postgresql://envwins@host/db"

    def test_env_password_assembles_dsn(self):
        env = {
            "PGPASSWORD": "s3cret",
            "PGHOST": "db.internal",
            "PGPORT": "6543",
            "PGUSER": "appuser",
            "PGDATABASE": "appdb",
        }

        dsn = resolve_database_dsn(env=env)

        assert dsn == "postgresql://appuser:s3cret@db.internal:6543/appdb"

    def test_env_password_defaults(self):
        env = {"DB_PASSWORD": "pw"}

        dsn = resolve_database_dsn(env=env)

        assert dsn == "postgresql://postgres:pw@localhost:5432/postgres"

    def test_falls_back_to_gcp_provider(self):
        env = {}  # no DATABASE_URL, no password
        client = _mock_gcp_client("postgresql://fromsecret@host/db")
        provider = GCPSecretManagerProvider(project_id="p", client=client)

        dsn = resolve_database_dsn(
            env=env, provider=provider, secret_id="database-url"
        )

        assert dsn == "postgresql://fromsecret@host/db"
        client.access_secret_version.assert_called_once_with(
            request={"name": "projects/p/secrets/database-url/versions/latest"}
        )

    def test_gcp_fallback_missing_sdk_raises(self, monkeypatch):
        monkeypatch.setattr(gcp_secrets, "GCP_AVAILABLE", False)
        with pytest.raises(GCPSecretError, match="netrun-config\\[gcp\\]"):
            resolve_database_dsn(env={}, project_id="p")
