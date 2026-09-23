"""
Configuration for netrun-ratelimit.

Provides Pydantic-based configuration with sensible defaults.
"""

import base64
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple
from pydantic import Field
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Tier-driven rate limiting (back-port B5, generalized from intirkon:
# src/api/middleware/rate_limiter.py _get_tier_from_token / _is_expensive_operation).
#
# Everything here is opt-in: the classic RateLimitMiddleware constructed without
# a TierLimits/TierResolver behaves exactly as before.
# ---------------------------------------------------------------------------

# A TierResolver maps a request to a tier name (or None if it can't tell, in
# which case the default tier is used). The signature is intentionally loose
# (``Any`` request) so the JWT payload shape is NOT hardwired here — a consumer
# such as netrun-auth supplies the resolver.
TierResolver = Callable[[Any], Optional[str]]


@dataclass(frozen=True)
class TierLimit:
    """A single tier's limit definition.

    Attributes:
        rate: Requests allowed per ``period``.
        period: Window length in seconds.
        burst: Bucket capacity. Defaults to ``rate`` (no extra burst) so that
            exactly ``rate`` requests are permitted per window.
    """

    rate: int
    period: int = 60
    burst: Optional[int] = None

    def __post_init__(self) -> None:
        if self.rate < 1:
            raise ValueError("rate must be at least 1")
        if self.period < 1:
            raise ValueError("period must be at least 1")
        if self.burst is not None and self.burst < 1:
            raise ValueError("burst must be at least 1")

    @property
    def effective_burst(self) -> int:
        """Bucket capacity, defaulting to ``rate`` when unset."""
        return self.burst if self.burst is not None else self.rate


def _pattern_fragments(pattern: str) -> Tuple[str, ...]:
    """Split a path pattern into the literal fragments around ``{param}`` slots.

    Generalizes intirkon's ``pattern.replace("{tenant_id}", "")`` trick: instead
    of removing a placeholder and hoping the leftover is a contiguous substring
    (which breaks for real values, e.g. ``/api/tenants//costs``), we keep the
    literal fragments and require them to appear in order.

    ``"/api/tenants/{tenant_id}/costs"`` -> ``("/api/tenants/", "/costs")``.
    ``"/api/ml/"`` -> ``("/api/ml/",)``.
    """
    fragments = []
    buf = []
    depth = 0
    for ch in pattern:
        if ch == "{":
            depth += 1
            if buf:
                fragments.append("".join(buf))
                buf = []
        elif ch == "}":
            if depth:
                depth -= 1
        elif depth == 0:
            buf.append(ch)
    if buf:
        fragments.append("".join(buf))
    return tuple(f for f in fragments if f)


def _pattern_matches(fragments: Tuple[str, ...], path: str) -> bool:
    """True if every literal fragment appears in ``path`` in order."""
    if not fragments:
        return False
    idx = 0
    for fragment in fragments:
        found = path.find(fragment, idx)
        if found == -1:
            return False
        idx = found + len(fragment)
    return True


class TierLimits:
    """Resolve ``(rate, period, burst)`` for a request from its tier and path.

    Expensive-path matching (when configured) overrides the tier limit, matching
    the intirkon precedence where ``_is_expensive_operation`` wins over tier.

    Args:
        tiers: Mapping of tier name -> :class:`TierLimit` (e.g.
            ``{"standard": TierLimit(100, 60), "premium": TierLimit(500, 60)}``).
        default_tier: Tier used when the resolver returns None/an unknown name.
            Must be a key in ``tiers``.
        expensive_limit: Optional stricter :class:`TierLimit` applied to paths
            classified as expensive.
        expensive_paths: Path patterns (substring / ``{param}`` templates) that
            mark an endpoint as expensive.
        expensive_matcher: Optional callable ``(path) -> bool`` that fully
            replaces the built-in path matching when supplied.
    """

    def __init__(
        self,
        tiers: Mapping[str, TierLimit],
        *,
        default_tier: str = "standard",
        expensive_limit: Optional[TierLimit] = None,
        expensive_paths: Optional[Sequence[str]] = None,
        expensive_matcher: Optional[Callable[[str], bool]] = None,
    ) -> None:
        if not tiers:
            raise ValueError("tiers must not be empty")
        self._tiers = dict(tiers)
        if default_tier not in self._tiers:
            raise ValueError(
                f"default_tier {default_tier!r} is not defined in tiers "
                f"{sorted(self._tiers)}"
            )
        self.default_tier = default_tier
        self._expensive_limit = expensive_limit
        self._expensive_patterns = tuple(
            _pattern_fragments(p) for p in (expensive_paths or ())
        )
        self._expensive_matcher = expensive_matcher

    def is_expensive(self, path: str) -> bool:
        """Return True if ``path`` is classified as an expensive operation."""
        if self._expensive_limit is None:
            return False
        if self._expensive_matcher is not None:
            return bool(self._expensive_matcher(path))
        return any(
            _pattern_matches(fragments, path)
            for fragments in self._expensive_patterns
        )

    def resolve_tier_name(self, tier_name: Optional[str]) -> str:
        """Normalize a (possibly None/unknown) tier name to a defined tier."""
        if tier_name and tier_name in self._tiers:
            return tier_name
        return self.default_tier

    def limit_for(self, tier_name: Optional[str], path: str) -> Tuple[TierLimit, str]:
        """Resolve the effective limit and a category label for a request.

        Returns a tuple of ``(TierLimit, category)`` where ``category`` is
        ``"expensive"`` or the resolved tier name. The category is suitable for
        namespacing the rate-limit bucket key so different categories don't
        share a bucket.
        """
        if self._expensive_limit is not None and self.is_expensive(path):
            return self._expensive_limit, "expensive"
        name = self.resolve_tier_name(tier_name)
        return self._tiers[name], name


def _decode_unverified_jwt_payload(token: str) -> Optional[dict]:
    """Best-effort decode of a JWT payload WITHOUT signature verification.

    For rate-limiting classification only — never for authorization. Full
    verification is the job of the auth layer. Returns None on any problem.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_part = parts[1]
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_part))
    except Exception:
        return None


def unverified_jwt_tier_resolver(
    claim: str = "tier",
    *,
    header: str = "Authorization",
    scheme: str = "Bearer",
) -> TierResolver:
    """Build a :data:`TierResolver` that reads a tier claim from a bearer JWT.

    Generalizes intirkon's ``_get_tier_from_token`` (which hardcoded the
    ``tier`` claim and the Authorization/Bearer header). The token is decoded
    WITHOUT verification purely to classify the request for rate limiting;
    returns None on any failure so the middleware falls back to the default tier.
    """

    prefix = f"{scheme} "

    def _resolver(request: Any) -> Optional[str]:
        try:
            auth_header = request.headers.get(header, "")
            if not auth_header.startswith(prefix):
                return None
            payload = _decode_unverified_jwt_payload(auth_header[len(prefix):])
            if not payload:
                return None
            value = payload.get(claim)
            return str(value) if value is not None else None
        except Exception:
            return None

    return _resolver


def header_tier_resolver(header: str = "X-RateLimit-Tier") -> TierResolver:
    """Build a :data:`TierResolver` that reads the tier from a request header."""

    def _resolver(request: Any) -> Optional[str]:
        try:
            return request.headers.get(header) or None
        except Exception:
            return None

    return _resolver


class RateLimitConfig(BaseSettings):
    """
    Rate limiting configuration.

    Attributes:
        rate: Number of requests allowed per period.
        period: Time period in seconds.
        burst: Maximum burst size (defaults to rate).
        key_prefix: Prefix for Redis keys.
        redis_url: Redis connection URL.
        block_duration: How long to block after limit exceeded (seconds).
        include_headers: Whether to include rate limit headers in responses.
    """

    rate: int = Field(
        default=100,
        ge=1,
        description="Number of requests allowed per period"
    )
    period: int = Field(
        default=60,
        ge=1,
        description="Time period in seconds"
    )
    burst: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum burst size (defaults to rate if not set)"
    )
    key_prefix: str = Field(
        default="ratelimit:",
        description="Prefix for rate limit keys"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL (e.g., redis://localhost:6379)"
    )
    block_duration: int = Field(
        default=0,
        ge=0,
        description="Additional block duration after limit exceeded (seconds)"
    )
    include_headers: bool = Field(
        default=True,
        description="Include X-RateLimit-* headers in responses"
    )

    # Header names (customizable)
    header_limit: str = Field(
        default="X-RateLimit-Limit",
        description="Header name for rate limit"
    )
    header_remaining: str = Field(
        default="X-RateLimit-Remaining",
        description="Header name for remaining requests"
    )
    header_reset: str = Field(
        default="X-RateLimit-Reset",
        description="Header name for reset timestamp"
    )
    header_retry_after: str = Field(
        default="Retry-After",
        description="Header name for retry after (seconds)"
    )

    model_config = {
        "env_prefix": "RATELIMIT_",
        "case_sensitive": False,
    }

    @property
    def effective_burst(self) -> int:
        """Get effective burst size (defaults to rate if not set)."""
        return self.burst if self.burst is not None else self.rate

    @property
    def refill_rate(self) -> float:
        """Calculate token refill rate (tokens per second)."""
        return self.rate / self.period
