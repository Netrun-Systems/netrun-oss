---
name: DEE Layer A — hatchling namespace migration (April 2026)
description: Completed migration from setuptools + netrun_dee to hatchling + netrun.dee namespace; PyPI v1.0.0 published; npm blocked by 2FA
type: project
---

Migration completed 2026-04-30.

**What was done:**
- Moved `src/netrun_dee/` to `src/netrun/dee/` with pkgutil namespace `src/netrun/__init__.py` (matching netrun-cache/netrun-validation pattern)
- Rewrote `pyproject.toml` to use hatchling 1.29.0 with `packages = ["src/netrun"]` and `force-include` for `prompt-templates.json`
- Updated 14 consumer files: 5 test files, 3 scripts, 5 integration docs, 1 README, 1 wilbur/charlotte/api/dee_router.py (11 import lines)
- PyPI publish succeeded: https://pypi.org/project/netrun-dee/1.0.0/
- npm publish BLOCKED: `@netrun/dee` requires 2FA bypass token; Daniel must run `npm publish --access public` manually from netrun-shared-ts/packages/dee/
- Git tags created: `netrun-dee-v1.0.0` (netrun-oss), `v1.0.0-dee` (netrun-shared-ts)
- Commits: ee4bf9f (netrun-oss), 3e80ff7 (wilbur) — NOT pushed

**Why:** Consistency with the other 18 netrun-oss packages. PyPI versions are immutable; shipping `netrun_dee` would be a permanent oddity.

**How to apply:** Future netrun-oss packages should mirror netrun-cache: `src/netrun/<pkg>/` + pkgutil namespace `__init__.py` + hatchling `packages = ["src/netrun"]`.
