"""
Google Cloud Secret Manager integration for netrun-config.

Provides a GCP Secret Manager secret provider (parity with the Azure
``KeyVaultMixin``) plus a database DSN resolver that works unchanged on a
Cloud Run cron-image (WIF + cloud-sql-proxy), on local dev, and in CI.

Back-ported (audit row B3, 2026-09-21) from the pattern established in
DungeonMaster after it retired hardcoded superuser DSNs:

* ``DungeonMaster/ml/nba/ingestion/rest_days.py`` — ``_pg_password()`` +
  ``_conn()``: preference chain DATABASE_URL -> PGPASSWORD -> Secret Manager.
* ``DungeonMaster/ops/rag_ic_tracker.py`` — ``_paper_db_url()``: same chain
  resolving a full DSN.

The DungeonMaster originals shell out to ``subprocess(["gcloud", ...])``.
This back-port deliberately uses the ``google-cloud-secret-manager`` Python
SDK instead, avoiding the "No such file or directory: gcloud" failure mode
that made those scripts a no-op inside the cron image. The SDK is a SOFT
dependency: install with ``pip install 'netrun-config[gcp]'``.
"""

import logging
import os
from typing import Mapping, Optional

from .exceptions import GCPSecretError

logger = logging.getLogger(__name__)

# Optional GCP dependency. Imported lazily inside the provider so that merely
# importing netrun.config never requires the SDK.
try:
    from google.cloud import secretmanager  # type: ignore

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    logger.debug(
        "google-cloud-secret-manager not available. "
        "GCP Secret Manager integration disabled."
    )


class GCPSecretManagerProvider:
    """
    Google Cloud Secret Manager secret provider.

    A thin, testable wrapper over ``SecretManagerServiceClient`` that fetches
    the value of a secret version. Mirrors the role of the Azure
    ``KeyVaultMixin`` but is a standalone provider (composition over mixin) so
    it can back a DSN resolver in plain scripts as well as config classes.

    The ``google-cloud-secret-manager`` SDK is a soft dependency: it is
    imported lazily and a clear :class:`GCPSecretError` is raised if it is
    missing.

    Example:
        >>> from netrun.config import GCPSecretManagerProvider
        >>> provider = GCPSecretManagerProvider(project_id="my-project")
        >>> dsn = provider.get_secret("database-url")  # doctest: +SKIP

    Args:
        project_id: GCP project id. Defaults to the ``GOOGLE_CLOUD_PROJECT``
            or ``GCP_PROJECT`` environment variable.
        client: Optional pre-built client (dependency injection for tests).
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        client=None,
    ) -> None:
        self.project_id = (
            project_id
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GCP_PROJECT")
        )
        self._client = client

    def _get_client(self):
        """Lazily build (or return the injected) Secret Manager client."""
        if self._client is not None:
            return self._client
        if not GCP_AVAILABLE:
            raise GCPSecretError(
                "google-cloud-secret-manager is not installed. "
                "Install the GCP extra with: pip install 'netrun-config[gcp]'"
            )
        self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def get_secret(
        self,
        secret_id: str,
        version: str = "latest",
        project_id: Optional[str] = None,
    ) -> str:
        """
        Fetch a secret value from GCP Secret Manager.

        Args:
            secret_id: Short secret name (e.g. "database-url").
            version: Secret version to access (default "latest").
            project_id: Override the provider's project id for this call.

        Returns:
            The decoded (utf-8) secret payload.

        Raises:
            GCPSecretError: if the SDK is missing, no project id is
                configured, or the resolved secret is empty.
        """
        project = project_id or self.project_id
        if not project:
            raise GCPSecretError(
                "No GCP project id configured. Pass project_id or set "
                "GOOGLE_CLOUD_PROJECT / GCP_PROJECT."
            )
        client = self._get_client()
        name = f"projects/{project}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("utf-8").strip()
        if not value:
            raise GCPSecretError(f"Secret {secret_id!r} resolved empty")
        logger.debug("GCP Secret Manager: loaded %r (%s)", secret_id, version)
        return value


def resolve_database_dsn(
    *,
    secret_id: str = "database-url",
    project_id: Optional[str] = None,
    provider: Optional[GCPSecretManagerProvider] = None,
    env: Optional[Mapping[str, str]] = None,
) -> str:
    """
    Resolve a PostgreSQL DSN without hardcoding credentials.

    Preference order (mirrors DungeonMaster ``rest_days._conn`` /
    ``rag_ic_tracker._paper_db_url``, so the same code path works on a Cloud
    Run cron-image, local dev, and CI without changes):

    1. ``DATABASE_URL`` from the environment — the gcloud-less path exported by
       the Cloud Run cron entrypoint via WIF + cloud-sql-proxy.
    2. A local env password: assemble a DSN from ``PGPASSWORD`` (or
       ``DB_PASSWORD``) plus host/port/user/dbname envs.
    3. GCP Secret Manager fetch of ``secret_id`` (devbox / production without an
       exported DATABASE_URL).

    Args:
        secret_id: Secret name holding a full DSN, used only for step 3.
        project_id: GCP project id for step 3 (else provider/env default).
        provider: Injected provider (tests); else one is built on demand.
        env: Environment mapping to read (defaults to ``os.environ``).

    Returns:
        A DSN string suitable for ``psycopg2.connect`` / SQLAlchemy.

    Raises:
        GCPSecretError: if step 3 is reached and the SDK is missing, no project
            is configured, or the secret is empty.
    """
    env = env if env is not None else os.environ

    # 1. DATABASE_URL wins.
    url = env.get("DATABASE_URL")
    if url:
        return url

    # 2. Local env password -> assembled DSN.
    password = env.get("PGPASSWORD") or env.get("DB_PASSWORD")
    if password:
        host = env.get("PGHOST") or env.get("DB_HOST") or "localhost"
        port = env.get("PGPORT") or env.get("DB_PORT") or "5432"
        user = env.get("PGUSER") or env.get("DB_USER") or "postgres"
        dbname = env.get("PGDATABASE") or env.get("DB_NAME") or "postgres"
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    # 3. GCP Secret Manager.
    provider = provider or GCPSecretManagerProvider(project_id=project_id)
    return provider.get_secret(secret_id, project_id=project_id)
