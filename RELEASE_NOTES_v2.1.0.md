# netrun-oss v2.1.0 — Release Notes (2026-09-23)

Five packages move to **2.1.0**. All changes are **additive / opt-in — no breaking changes from 2.0.0**, plus a test-hardening pass.

## netrun-errors 2.1.0
- `safe_http_error()` — logs the full exception server-side with a correlation id and returns a sanitized `HTTPException` that never echoes `str(exc)`. Closes an API-key-leak class.

## netrun-config 2.1.0
- `GCPSecretManagerProvider` + `resolve_database_dsn()` (DATABASE_URL → env → GCP Secret Manager). GCP parity with the existing Azure Key Vault support. Optional `[gcp]` extra.

## netrun-auth 2.1.0
- Opt-in platform-JWT alternate credential path: `verify_platform_jwt()`, `PlatformPrincipal`, `platform_jwt_enabled()`. **No-op unless `NETRUN_PLATFORM_JWT_SECRET` is set** — fully backward-compatible.

## netrun-ratelimit 2.1.0
- Tier-driven limits: `TierLimit`/`TierLimits`, pluggable `TierResolver` (JWT-claim and header resolvers included), `X-RateLimit-*` headers, expensive-operation categorization.

## netrun-llm 2.1.0
- **[security]** adapter-exception secret redaction (`redact_secrets` / `redact_exception`).
- Long-context escalation (Flash→Pro past 500K tokens) in `LLMFallbackChain`.
- Windows-safe gcloud resolver; operator model-registry drift poller (`[operator]` extra).

## Maintenance
- Test-suite hardening: casbin 1.43 API compat, azure-optional test skips, rate-limit burst-default fix. Test fixtures genericized (no production identifiers ship).
