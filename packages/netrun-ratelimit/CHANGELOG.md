# Changelog — netrun-ratelimit

All notable changes to this package are documented here.

## [2.1.0] - 2026-09-22

### Added (back-port B5)

Tier-driven rate limiting, generalized from the production middleware in
`intirkon:src/api/middleware/rate_limiter.py` (`_get_tier_from_token` ~L328,
`_is_expensive_operation` ~L320, X-RateLimit header set ~L453). All additions
are **opt-in and backward-compatible** — a `RateLimitMiddleware` constructed
without the new parameters behaves exactly as in 2.0.0.

- `TierLimit` — a per-tier `(rate, period, burst)` definition (`burst` defaults
  to `rate`).
- `TierLimits` — resolves the effective limit for a request from its tier and
  path. Expensive-path matches override the tier limit (matching intirkon's
  precedence). Ships literal-fragment path matching that correctly handles
  `{param}` templates (e.g. `/api/tenants/{tenant_id}/costs`), plus a
  `expensive_matcher` hook for full control.
- `TierResolver` — a pluggable `Callable[[request], Optional[str]]` so the JWT
  payload shape is **not** hardwired into the middleware; a consumer such as
  netrun-auth supplies the resolver.
- `unverified_jwt_tier_resolver(claim="tier", ...)` — reads a tier claim from a
  bearer JWT **without** signature verification (classification only; never for
  authorization), returning `None` on any failure. Generalizes intirkon's
  hardcoded `tier`-claim/Authorization-Bearer reader.
- `header_tier_resolver(header="X-RateLimit-Tier")` — reads the tier from a
  request header.
- `RateLimitMiddleware` gains optional `tier_limits` and `tier_resolver`
  parameters. When set, the bucket key is namespaced by category
  (`expensive` or the tier name) so categories don't share a bucket, and the
  full `X-RateLimit-*` header set (Limit / Remaining / Reset, plus `Retry-After`
  on 429) is emitted per the resolved tier.

### Tests

- Added `tests/test_tiers.py` (21 tests): tier resolution + fallback, expensive
  path override, `{param}` template matching, custom matcher, JWT/header
  resolvers, and ASGI integration (standard vs premium limits, expensive-path
  stricter limit, X-RateLimit headers, 429 Retry-After, and the
  no-tier-params backward-compatibility regression).

## [2.0.0]

- Namespace packaging migration (`netrun_ratelimit` -> `netrun.ratelimit`).
