"""
Tests for the platform-JWT alternate-credential path (netrun.auth.platform).

Adapted from the source suite netrun-crm:tests/unit/test_platform_auth.py
(12 tests) and extended for the OSS generalizations: the
``NETRUN_PLATFORM_JWT_SECRET`` env var, the required ``audience`` parameter,
an overridable uuid5 namespace, and the strict secret-unset no-op contract.

Uses PyJWT (the library netrun-auth depends on) to mint crafted tokens.
"""

import time
import uuid

import jwt as pyjwt  # PyJWT
import pytest

from netrun.auth.platform import (
    DEFAULT_PLATFORM_NAMESPACE,
    PLATFORM_JWT_SECRET_ENV,
    PlatformPrincipal,
    platform_jwt_enabled,
    verify_platform_jwt,
)
from netrun.auth.types import User

_TEST_SECRET = "test-platform-proxy-secret-for-unit-tests-only-32+chars"
_AUD = "netrun-service"


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    """Default every test to a configured secret; individual tests may unset it."""
    monkeypatch.setenv(PLATFORM_JWT_SECRET_ENV, _TEST_SECRET)


def _make_token(
    *,
    secret: str = _TEST_SECRET,
    iss: str = "sigil-platform",
    aud: str = _AUD,
    ctx: str = "platform-admin",
    actor: dict | None = None,
    exp_offset_s: int = 60,
    extra: dict | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "iss": iss,
        "aud": aud,
        "ctx": ctx,
        "actor": actor
        if actor is not None
        else {
            "email": "daniel@netrunsystems.com",
            "tenantId": "19a0c807-948c-4c20-a66d-155caa5558ff",
            "userId": "daniel-user-id",
        },
        "iat": now,
        "exp": now + exp_offset_s,
    }
    if extra:
        payload.update(extra)
    return pyjwt.encode(payload, secret, algorithm="HS256")


# --- Happy path -----------------------------------------------------------

def test_valid_platform_jwt_returns_principal():
    principal = verify_platform_jwt(_make_token(), audience=_AUD)
    assert principal is not None
    assert isinstance(principal, PlatformPrincipal)
    assert principal.email == "daniel@netrunsystems.com"
    assert principal.is_superuser is True
    assert "platform-admin" in principal.roles
    assert principal.permissions == ["*"]
    assert str(principal.tenant_id) == "19a0c807-948c-4c20-a66d-155caa5558ff"
    assert principal.auth_provider == "netrun-platform"


def test_stable_principal_id_for_same_email():
    p1 = verify_platform_jwt(_make_token(), audience=_AUD)
    p2 = verify_platform_jwt(_make_token(), audience=_AUD)
    assert p1.id == p2.id
    # Deterministic against the documented namespace + email.
    assert p1.id == uuid.uuid5(DEFAULT_PLATFORM_NAMESPACE, "daniel@netrunsystems.com")


def test_email_is_normalized_lowercase():
    token = _make_token(actor={"email": "Ops@Netrunsystems.COM"})
    principal = verify_platform_jwt(token, audience=_AUD)
    assert principal is not None
    assert principal.email == "ops@netrunsystems.com"


# --- Rejections (all fall through to None) --------------------------------

def test_rejects_wrong_audience():
    token = _make_token(aud="some-other-service")
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_rejects_wrong_issuer():
    token = _make_token(iss="some-other-issuer")
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_rejects_wrong_context():
    token = _make_token(ctx="user")
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_rejects_expired_token():
    token = _make_token(exp_offset_s=-30)
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_rejects_bad_signature():
    token = _make_token(secret="wrong-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_rejects_missing_actor_email():
    token = _make_token(actor={"tenantId": "19a0c807-948c-4c20-a66d-155caa5558ff"})
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_rejects_empty_token():
    assert verify_platform_jwt("", audience=_AUD) is None
    assert verify_platform_jwt(None, audience=_AUD) is None


def test_rejects_completely_random_string():
    assert verify_platform_jwt("not.a.jwt", audience=_AUD) is None
    assert verify_platform_jwt("abcdef", audience=_AUD) is None


# --- Optional / lenient behavior ------------------------------------------

def test_accepts_missing_tenant_id():
    token = _make_token(actor={"email": "ops@netrunsystems.com"})
    principal = verify_platform_jwt(token, audience=_AUD)
    assert principal is not None
    assert principal.tenant_id is None


def test_bad_tenant_id_is_accepted_with_empty_tenant():
    token = _make_token(actor={"email": "ops@netrunsystems.com", "tenantId": "not-a-uuid"})
    principal = verify_platform_jwt(token, audience=_AUD)
    assert principal is not None
    assert principal.tenant_id is None


# --- Opt-in contract (regression-critical) --------------------------------

def test_strict_no_op_when_secret_env_unset(monkeypatch):
    """Unset env + no explicit secret => strict no-op (never touch behavior)."""
    monkeypatch.delenv(PLATFORM_JWT_SECRET_ENV, raising=False)
    assert platform_jwt_enabled() is False
    # Even a token that is otherwise perfectly valid must be ignored.
    token = _make_token()
    assert verify_platform_jwt(token, audience=_AUD) is None


def test_enabled_reports_true_when_configured():
    assert platform_jwt_enabled() is True
    assert platform_jwt_enabled(secret="explicit") is True


def test_explicit_secret_overrides_env(monkeypatch):
    monkeypatch.delenv(PLATFORM_JWT_SECRET_ENV, raising=False)
    token = _make_token(secret="explicit-secret-xxxxxxxxxxxxxxxxxxxxxxxxx")
    # Env unset, but explicit secret provided => path is enabled.
    principal = verify_platform_jwt(
        token, audience=_AUD, secret="explicit-secret-xxxxxxxxxxxxxxxxxxxxxxxxx"
    )
    assert principal is not None


# --- Generalizations over the CRM source ----------------------------------

def test_audience_none_skips_aud_verification():
    token = _make_token(aud="whatever-service")
    principal = verify_platform_jwt(token, audience=None)
    assert principal is not None


def test_custom_namespace_changes_id_deterministically():
    ns = uuid.UUID("11111111-2222-3333-4444-555555555555")
    p_default = verify_platform_jwt(_make_token(), audience=_AUD)
    p_custom = verify_platform_jwt(_make_token(), audience=_AUD, namespace=ns)
    assert p_custom.id != p_default.id
    assert p_custom.id == uuid.uuid5(ns, "daniel@netrunsystems.com")


def test_custom_expected_iss_and_ctx():
    token = _make_token(iss="my-portal", ctx="operator")
    # Default expectations reject it...
    assert verify_platform_jwt(token, audience=_AUD) is None
    # ...but explicit expectations accept it.
    principal = verify_platform_jwt(
        token, audience=_AUD, expected_iss="my-portal", expected_ctx="operator"
    )
    assert principal is not None


def test_to_user_conversion():
    principal = verify_platform_jwt(_make_token(), audience=_AUD)
    user = principal.to_user()
    assert isinstance(user, User)
    assert user.user_id == str(principal.id)
    assert user.email == principal.email
    assert user.organization_id == str(principal.tenant_id)
    assert "*" in user.permissions
