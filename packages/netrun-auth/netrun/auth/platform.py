"""
Netrun Authentication - Platform-JWT Alternate Credential Path
==============================================================

Verifies short-lived HS256 JWTs minted by a Netrun *platform* issuer (e.g.
the Sigil operator portal's cross-tenant proxy). When a valid platform JWT
is presented, the bearer is resolved to a synthetic cross-tenant
*platform-admin* principal — distinct from a normal per-tenant user session.

This is an ADDITIVE, OPT-IN, alternate-credential path. It is deliberately
orthogonal to the JWT/RBAC, Azure AD, Azure AD B2C, and OAuth flows already
in netrun-auth. The intended use is:

    principal = verify_platform_jwt(bearer, audience="my-service")
    if principal is not None:
        # cross-tenant platform admin — short-circuit normal user auth
        ...
    else:
        # not a platform JWT — fall through to the normal user-auth path
        ...

Opt-in contract (STRICT):
    * If the platform secret is not configured (env
      ``NETRUN_PLATFORM_JWT_SECRET`` unset AND no ``secret=`` passed),
      ``verify_platform_jwt`` is a NO-OP: it always returns ``None`` and
      never changes behavior for existing consumers.
    * Every negative outcome returns ``None`` (never raises), so a caller can
      always fall through to its normal auth path.

Contract of an accepted token (all must hold):
    iss   == expected_iss   (default "sigil-platform")
    aud   == audience       (verified by PyJWT when ``audience`` is not None)
    ctx   == expected_ctx   (default "platform-admin")
    actor == { email, tenantId?, userId? }  (email required)
    exp   not in the past   (verified by PyJWT)

Back-ported (audit row B2) from netrun-crm:app/platform_auth.py. Generalized
for the OSS library: the env var is ``NETRUN_PLATFORM_JWT_SECRET`` (not the
CRM's ``KOG_PLATFORM_PROXY_SECRET``), the ``audience`` is a required
parameter (not hardcoded to ``kog-api``), and the uuid5 namespace is
overridable. Uses PyJWT (the JWT library netrun-auth already depends on) so
no new dependency is introduced.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import jwt  # PyJWT (netrun-auth already depends on pyjwt[crypto])
from pydantic import BaseModel, ConfigDict, Field

from .types import User

logger = logging.getLogger(__name__)

# Environment variable holding the HS256 HMAC secret shared with the platform
# issuer. Unset == platform-JWT path disabled (strict no-op).
PLATFORM_JWT_SECRET_ENV = "NETRUN_PLATFORM_JWT_SECRET"

# Stable default namespace for deriving deterministic platform-admin ids from
# actor.email. Preserved from the CRM source for audit-id continuity. Callers
# may override via the ``namespace=`` parameter.
DEFAULT_PLATFORM_NAMESPACE = uuid.UUID("3b1b8c4e-2a4e-4d6a-9f1a-7f1234567890")

# Default immutable claim values. Overridable per call.
DEFAULT_EXPECTED_ISS = "sigil-platform"
DEFAULT_EXPECTED_CTX = "platform-admin"


class PlatformPrincipal(BaseModel):
    """Identity returned by a successful platform-JWT verification.

    Represents a synthetic, cross-tenant platform-admin. Downstream code can
    read ``.id`` / ``.email`` / ``.tenant_id`` / ``.is_superuser`` / ``.roles``
    directly, or call :meth:`to_user` to obtain a netrun-auth
    :class:`~netrun.auth.types.User`.
    """

    model_config = ConfigDict(extra="allow")

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = True  # cross-tenant admin context
    tenant_id: Optional[uuid.UUID] = None
    roles: List[str] = Field(
        default_factory=lambda: ["platform-admin", "admin", "user"]
    )
    permissions: List[str] = Field(default_factory=lambda: ["*"])
    created_at: datetime
    last_login: Optional[datetime] = None
    # Marker so audit / logging code can tell this principal apart from a
    # normal user session. Code that doesn't know about it simply ignores it.
    auth_provider: str = "netrun-platform"

    def to_user(self) -> User:
        """Convert to a netrun-auth :class:`User` for integration convenience."""
        return User(
            user_id=str(self.id),
            organization_id=str(self.tenant_id) if self.tenant_id else None,
            roles=list(self.roles),
            permissions=list(self.permissions),
            email=self.email,
            display_name=self.full_name,
        )


def _resolve_secret(secret: Optional[str]) -> Optional[str]:
    """Return the platform HMAC secret, or None if not configured.

    An explicit ``secret`` wins; otherwise the ``NETRUN_PLATFORM_JWT_SECRET``
    env var is read. A missing/empty secret disables the platform-JWT path.
    """
    if secret and secret.strip():
        return secret.strip()
    env = os.environ.get(PLATFORM_JWT_SECRET_ENV, "").strip()
    return env or None


def platform_jwt_enabled(secret: Optional[str] = None) -> bool:
    """True if a platform secret is configured (env or explicit)."""
    return _resolve_secret(secret) is not None


def verify_platform_jwt(
    token: Optional[str],
    *,
    audience: Optional[str],
    secret: Optional[str] = None,
    namespace: Optional[uuid.UUID] = None,
    expected_iss: Optional[str] = DEFAULT_EXPECTED_ISS,
    expected_ctx: Optional[str] = DEFAULT_EXPECTED_CTX,
) -> Optional[PlatformPrincipal]:
    """Try to validate ``token`` as a Netrun platform JWT.

    Returns a :class:`PlatformPrincipal` when the secret is configured and the
    token satisfies the full contract (see module docstring). Returns ``None``
    for ANY failure — including a missing secret — so callers treat ``None`` as
    "not a platform JWT, fall through to normal user auth". Never raises on a
    bad token.

    Args:
        token: The raw bearer token (may be ``None``/empty).
        audience: Expected ``aud`` claim. When not ``None`` it is verified by
            PyJWT; pass ``None`` to skip audience verification.
        secret: Optional explicit HMAC secret. Falls back to
            ``NETRUN_PLATFORM_JWT_SECRET``.
        namespace: uuid5 namespace for deterministic principal ids. Defaults to
            :data:`DEFAULT_PLATFORM_NAMESPACE`.
        expected_iss: Required ``iss`` claim (``None`` to skip).
        expected_ctx: Required ``ctx`` claim (``None`` to skip).
    """
    if not token:
        return None

    resolved_secret = _resolve_secret(secret)
    if not resolved_secret:
        # Platform-JWT path disabled on this instance — strict no-op.
        return None

    ns = namespace or DEFAULT_PLATFORM_NAMESPACE

    options = {"verify_exp": True, "verify_aud": audience is not None}
    decode_kwargs = {"algorithms": ["HS256"], "options": options}
    if audience is not None:
        decode_kwargs["audience"] = audience

    try:
        payload = jwt.decode(token, resolved_secret, **decode_kwargs)
    except jwt.PyJWTError as exc:
        # Wrong signature, wrong audience, expired, or a non-platform JWT.
        # Quiet by design — fall through to normal user auth.
        logger.debug("Platform-JWT decode rejected: %s", exc)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Platform-JWT decode unexpected error: %s", exc)
        return None

    if expected_iss is not None and payload.get("iss") != expected_iss:
        return None
    if expected_ctx is not None and payload.get("ctx") != expected_ctx:
        return None

    actor = payload.get("actor") or {}
    if not isinstance(actor, dict):
        return None

    email = (actor.get("email") or "").strip().lower()
    if not email:
        # actor.email is required — audit needs a stable identity.
        return None

    principal_id = uuid.uuid5(ns, email)

    tenant_id: Optional[uuid.UUID] = None
    raw_tenant = actor.get("tenantId")
    if raw_tenant:
        try:
            tenant_id = uuid.UUID(str(raw_tenant))
        except (ValueError, TypeError):
            # Bad tenantId — accept the JWT but leave tenant context empty so
            # downstream routes fall back to their defaults.
            tenant_id = None

    now = datetime.now(timezone.utc)
    principal = PlatformPrincipal(
        id=principal_id,
        username=email,
        email=email,
        full_name=f"Netrun Platform Admin ({email})",
        is_active=True,
        is_superuser=True,
        tenant_id=tenant_id,
        roles=["platform-admin", "admin", "user"],
        permissions=["*"],
        created_at=now,
        last_login=now,
    )

    logger.info(
        "Platform-JWT auth OK: actor_email=%s tenant_id=%s actor_user=%s",
        email,
        tenant_id,
        actor.get("userId"),
    )
    return principal


__all__ = [
    "PlatformPrincipal",
    "verify_platform_jwt",
    "platform_jwt_enabled",
    "PLATFORM_JWT_SECRET_ENV",
    "DEFAULT_PLATFORM_NAMESPACE",
]
