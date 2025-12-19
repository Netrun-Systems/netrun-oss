"""
DEPRECATED: Import from netrun.env instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_env import ...

    # New:
    from netrun.env import ...

Migration Guide:
    1. Replace all imports:
       - from netrun_env import ... → from netrun.env import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: netrun-env>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_env is deprecated. Use 'from netrun.env import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/env/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.env
from netrun.env import *
from netrun.env import __all__
