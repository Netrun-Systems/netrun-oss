# netrun-oss — Active TODO / Project Charter

**Opened:** 2026-09-21 · **Owner:** @cto-cpo-agent (delivery), @code-reusability-specialist (audit) · **Status:** 🟢 ACTIVE (reactivated after ~4 months cold)

## Why this project exists
`netrun-oss` is the public home of Netrun's reusable Python libraries (19 on PyPI) + `netrun-touch-ui` (TS). The last push was **2026-05-27**. Since then we've shipped real production work across the portfolio (Sigil/netrun-cms, wilbur/Charlotte, Kevin, Poppies, KOG, Survai, Intirkon, etc.). **Improvements made in those apps have not been flowed back into the libraries.** This project audits the portfolio for back-port candidates, integrates the good ones upstream, and cuts fresh, versioned releases.

## Current state (verified 2026-09-21 from origin/main)
- **20 packages.** 19 Python/FastAPI infra libs + `netrun-touch-ui` (TS component lib — newest, **not in README table**).
- **No GitHub Releases have ever been cut** — only in-repo version bumps + PyPI publishes. Tags/release notes are missing.
- **Windows checkout is broken:** `packages/netrun-dogfood/nul` is a reserved device name; git cannot materialize the tree on Windows.

### Package inventory + version state
| Package | Ver | Lang | Domain |
|---|---|---|---|
| netrun-core | 2.0.0 | py | root `netrun.*` namespace |
| netrun-auth | 2.0.0 | py | JWT / OAuth2 / Azure AD / Casbin RBAC |
| netrun-cache | **1.0.0** | py | Redis + in-memory caching |
| netrun-config | 2.0.0 | py | config mgmt + Azure Key Vault + TTL cache |
| netrun-cors | 2.0.0 | py | FastAPI CORS presets |
| netrun-db-pool | 2.0.0 | py | async DB pooling + tenant isolation |
| netrun-dee | **1.0.0** | py | Digital Emotion Equivalents / ECI scoring |
| netrun-dogfood | 2.0.0 | py | internal integration-test MCP server |
| netrun-env | 2.0.0 | py | schema env-var validator |
| netrun-errors | 2.0.0 | py | unified FastAPI error handling |
| netrun-llm | 2.0.0 | py | multi-provider LLM orchestration + telemetry |
| netrun-logging | 2.0.0 | py | structured logging + App Insights |
| netrun-oauth | 2.0.0 | py | OAuth2 adapters (12+ providers) |
| netrun-pytest-fixtures | 2.0.0 | py | shared pytest fixtures |
| netrun-ratelimit | 2.0.0 | py | distributed token-bucket rate limiting |
| netrun-rbac | **3.0.0** | py | multi-tenant RBAC + isolation testing |
| netrun-resilience | **1.0.0** | py | retry / circuit-breaker / timeout / bulkhead |
| netrun-validation | **1.0.0** | py | Pydantic validators |
| netrun-websocket | **1.0.0** | py | WS mgmt + Redis sessions + JWT |
| netrun-touch-ui | (TS) | ts | touch/mobile component library |

## Workstream 0 — Housekeeping (P0, fast)
- [ ] **Remove `packages/netrun-dogfood/nul`** — unblocks Windows checkout + local dev on this workstation. (Can be done via `gh api` without a local checkout.)
- [ ] **Add `netrun-touch-ui` to the README** package table (currently undocumented).
- [ ] **Backfill GitHub Releases + tags** for the versions already on PyPI (v2.0.0, v2.1, rbac v3.0.0) so history is traceable.

## Workstream 1 — Back-port audit (agent-driven) 🔵 IN PROGRESS
Determine what improvements across the portfolio can be integrated/back-ported into the libraries.
- **Method:** for each package, find where consumer/app repos have *diverged* — vendored copies, local reimplementations, bug fixes, hardening, new features — that are ahead of the published lib. Head-start from the existing reuse reports (DungeonMaster `CODE_REUSE_INTEGRATION_REPORT_v2.0.md`, eiscore-data `CODE_REUSE_SCAN_REPORT_2025-11-11.md`, Dec-2025 reuse retrospective).
- **Candidate source repos on disk:** wilbur (Charlotte), netrun-cms (Sigil), DungeonMaster (Kevin), kamera-pillar, meridian, intirkon / intirkon-pillar, poppies, Survai, netrun-crm (KOG), SecureVault, fabric-pillar; `netrun-shared-ts` for the TS/`touch-ui` side.
- **Deliverable:** a ranked **Back-Port Register** — per candidate: target package · source repo+path (evidence) · what improved · type (bugfix/feature/hardening/perf) · reuse score · effort (S/M/L) · suggested version bump · risk. Plus a per-package "needs a release?" call and a top-10 do-first list.
- **Output file:** `boardroom/reports/2026-09-21-netrun-oss-backport-audit.md`

## Workstream 2 — Release prep (after audit picks winners)
For each package with accepted back-ports:
- [ ] Integrate the back-port (PR into netrun-oss).
- [ ] Bump version (semver) + update CHANGELOG.
- [ ] Run the package test suite + isolation tests where applicable.
- [ ] Publish to PyPI + cut a matching GitHub Release with notes.
- [ ] Bump the pinned version in consumer repos that vendored the old copy.

## Open decisions
- **D-?? (to ratify):** reactivate netrun-oss as an active lane and run the back-port + release cycle. (This is founder-directed 2026-09-21.)
- Release cadence: batch all packages in one "v2.2 wave," or ship per-package as each back-port lands?
- Does `netrun-touch-ui` get folded into this repo's release process or tracked with the TS/`netrun-shared-ts` side?

---
*Charter opened 2026-09-21. Back-port audit dispatched to @code-reusability-specialist same day.*
