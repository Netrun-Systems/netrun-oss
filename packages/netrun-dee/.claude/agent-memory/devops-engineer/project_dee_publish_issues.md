---
name: DEE publish prep fixes (April 2026)
description: Three bugs found and fixed during open-source publish validation of netrun-dee and @netrun/dee
type: project
---

Three issues were found and fixed during dry-run validation of DEE Layer A publish (2026-04-30):

1. **pyproject.toml had wrong build-backend**: `setuptools.backends._legacy:_Backend` is an internal path that does not exist as a public API. Fixed to `setuptools.build_meta`. This caused `python3 -m build` to fail entirely.

2. **prompt-templates.json not included in wheel**: `prompt_builder.py` loads the file at runtime via `os.path.dirname(__file__)`. Without `[tool.setuptools.package-data]`, the JSON is excluded and the package would crash on import of prompt_builder. Fixed by adding `netrun_dee = ["prompt-templates.json"]` under `[tool.setuptools.package-data]`.

3. **LICENSE file missing from both packages**: Neither `@netrun/dee` nor `netrun-dee` had a LICENSE file. Added MIT License (Daniel Garza / Netrun Systems 2026) to both package roots. npm auto-includes LICENSE in tarballs; setuptools auto-includes it in sdist and wheel dist-info.

**Why:** These are pre-publish blockers — any one of them would have either prevented publishing or published a broken package.
**How to apply:** Before any open-source publish from a Python package under `wilbur/`, verify build-backend, package-data for non-Python assets, and LICENSE existence.
