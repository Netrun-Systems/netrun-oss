"""
Tests for tier-driven rate limiting (back-port B5).

Covers:
- TierLimits resolution + expensive-operation categorization (unit).
- unverified_jwt_tier_resolver / header_tier_resolver (unit).
- RateLimitMiddleware with tiers: standard vs premium limits, expensive-path
  stricter limit, X-RateLimit-* headers, 429 Retry-After, and the regression
  that a middleware built WITHOUT tier params behaves as before.

Ported/generalized from intirkon:src/api/middleware/rate_limiter.py
(_get_tier_from_token ~L328, _is_expensive_operation ~L320, X-RateLimit headers ~L453).
"""

import base64
import json

import pytest

from netrun.ratelimit import (
    RateLimiter,
    MemoryBackend,
    TierLimit,
    TierLimits,
    unverified_jwt_tier_resolver,
    header_tier_resolver,
)


def _make_jwt(payload: dict) -> str:
    """Build an (unsigned) 3-part JWT-shaped token for resolver tests."""
    def b64(obj):
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{b64({'alg': 'none'})}.{b64(payload)}.sig"


class TestTierLimit:
    def test_effective_burst_defaults_to_rate(self):
        assert TierLimit(rate=5, period=60).effective_burst == 5
        assert TierLimit(rate=5, period=60, burst=9).effective_burst == 9

    def test_validation(self):
        with pytest.raises(ValueError):
            TierLimit(rate=0, period=60)
        with pytest.raises(ValueError):
            TierLimit(rate=5, period=0)
        with pytest.raises(ValueError):
            TierLimit(rate=5, period=60, burst=0)


class TestTierLimits:
    def _tiers(self):
        return TierLimits(
            {
                "standard": TierLimit(100, 60),
                "premium": TierLimit(500, 60),
            },
            default_tier="standard",
            expensive_limit=TierLimit(10, 60),
            expensive_paths=["/api/ml/", "/api/tenants/{tenant_id}/costs"],
        )

    def test_default_tier_must_exist(self):
        with pytest.raises(ValueError):
            TierLimits({"standard": TierLimit(10, 60)}, default_tier="premium")

    def test_empty_tiers_rejected(self):
        with pytest.raises(ValueError):
            TierLimits({})

    def test_resolve_known_tier(self):
        tiers = self._tiers()
        limit, category = tiers.limit_for("premium", "/api/hello")
        assert category == "premium"
        assert limit.rate == 500

    def test_unknown_tier_falls_back_to_default(self):
        tiers = self._tiers()
        limit, category = tiers.limit_for("enterprise", "/api/hello")
        assert category == "standard"
        assert limit.rate == 100

    def test_none_tier_falls_back_to_default(self):
        tiers = self._tiers()
        limit, category = tiers.limit_for(None, "/api/hello")
        assert category == "standard"

    def test_expensive_path_overrides_tier(self):
        tiers = self._tiers()
        # even a premium caller is capped by the expensive limit
        limit, category = tiers.limit_for("premium", "/api/ml/predict")
        assert category == "expensive"
        assert limit.rate == 10

    def test_expensive_path_template_placeholder(self):
        tiers = self._tiers()
        assert tiers.is_expensive("/api/tenants/abc-123/costs") is True
        assert tiers.is_expensive("/api/hello") is False

    def test_no_expensive_limit_means_not_expensive(self):
        tiers = TierLimits(
            {"standard": TierLimit(100, 60)},
            expensive_paths=["/api/ml/"],
        )
        assert tiers.is_expensive("/api/ml/x") is False

    def test_custom_expensive_matcher(self):
        tiers = TierLimits(
            {"standard": TierLimit(100, 60)},
            expensive_limit=TierLimit(5, 60),
            expensive_matcher=lambda path: path.endswith("/export"),
        )
        assert tiers.is_expensive("/report/export") is True
        assert tiers.is_expensive("/report/view") is False


class TestResolvers:
    def test_jwt_resolver_reads_tier_claim(self):
        resolver = unverified_jwt_tier_resolver("tier")
        token = _make_jwt({"tier": "premium", "sub": "u1"})

        class Req:
            headers = {"Authorization": f"Bearer {token}"}

        assert resolver(Req()) == "premium"

    def test_jwt_resolver_missing_claim_returns_none(self):
        resolver = unverified_jwt_tier_resolver("tier")
        token = _make_jwt({"sub": "u1"})

        class Req:
            headers = {"Authorization": f"Bearer {token}"}

        assert resolver(Req()) is None

    def test_jwt_resolver_no_bearer_returns_none(self):
        resolver = unverified_jwt_tier_resolver("tier")

        class Req:
            headers = {"Authorization": "Basic abc"}

        assert resolver(Req()) is None

    def test_jwt_resolver_garbage_returns_none(self):
        resolver = unverified_jwt_tier_resolver("tier")

        class Req:
            headers = {"Authorization": "Bearer not-a-jwt"}

        assert resolver(Req()) is None

    def test_header_resolver(self):
        resolver = header_tier_resolver("X-RateLimit-Tier")

        class Req:
            headers = {"X-RateLimit-Tier": "premium"}

        assert resolver(Req()) == "premium"

        class Req2:
            headers = {}

        assert resolver(Req2()) is None


# ---------------------------------------------------------------------------
# ASGI integration
# ---------------------------------------------------------------------------

starlette = pytest.importorskip("starlette")
from starlette.applications import Starlette  # noqa: E402
from starlette.responses import PlainTextResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from netrun.ratelimit import RateLimitMiddleware  # noqa: E402


def _build_client(**mw_kwargs):
    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/ml/predict", ok), Route("/api/hello", ok)])
    limiter = RateLimiter(backend=MemoryBackend(), rate=1000, period=60, key_prefix="t:")
    app.add_middleware(RateLimitMiddleware, limiter=limiter, **mw_kwargs)
    return TestClient(app)


def _tiers():
    return TierLimits(
        {"standard": TierLimit(3, 60), "premium": TierLimit(6, 60)},
        default_tier="standard",
        expensive_limit=TierLimit(1, 60),
        expensive_paths=["/api/ml/"],
    )


def test_standard_tier_limit_enforced():
    client = _build_client(
        tier_limits=_tiers(),
        tier_resolver=header_tier_resolver("X-RateLimit-Tier"),
    )
    h = {"X-RateLimit-Tier": "standard"}
    for _ in range(3):
        assert client.get("/api/hello", headers=h).status_code == 200
    r = client.get("/api/hello", headers=h)
    assert r.status_code == 429
    assert r.headers["X-RateLimit-Limit"] == "3"
    assert r.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1


def test_premium_tier_gets_higher_limit():
    client = _build_client(
        tier_limits=_tiers(),
        tier_resolver=header_tier_resolver("X-RateLimit-Tier"),
    )
    h = {"X-RateLimit-Tier": "premium"}
    # premium allows 6 where standard allowed only 3
    for i in range(6):
        assert client.get("/api/hello", headers=h).status_code == 200, i
    assert client.get("/api/hello", headers=h).status_code == 429


def test_expensive_path_is_stricter_than_tier():
    client = _build_client(
        tier_limits=_tiers(),
        tier_resolver=header_tier_resolver("X-RateLimit-Tier"),
    )
    h = {"X-RateLimit-Tier": "premium"}
    # expensive limit is 1 even for premium
    first = client.get("/api/ml/predict", headers=h)
    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "1"
    assert client.get("/api/ml/predict", headers=h).status_code == 429


def test_success_response_has_ratelimit_headers():
    client = _build_client(tier_limits=_tiers())
    r = client.get("/api/hello")
    assert r.status_code == 200
    assert r.headers["X-RateLimit-Limit"] == "3"  # default tier = standard
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Reset" in r.headers


def test_no_tier_params_is_backward_compatible():
    """Regression: middleware without tier params uses the limiter's own limit."""
    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/hello", ok)])
    limiter = RateLimiter(backend=MemoryBackend(), rate=2, period=60, key_prefix="bc:")
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    client = TestClient(app)

    assert client.get("/api/hello").status_code == 200
    assert client.get("/api/hello").status_code == 200
    r = client.get("/api/hello")
    assert r.status_code == 429
    assert r.headers["X-RateLimit-Limit"] == "2"
