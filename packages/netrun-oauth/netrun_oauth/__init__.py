"""
DEPRECATED: Import from netrun.oauth instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_oauth import ...

    # New:
    from netrun.oauth import ...

Migration Guide:
    1. Replace all imports:
       - from netrun_oauth import ... → from netrun.oauth import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: netrun-oauth>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_oauth is deprecated. Use 'from netrun.oauth import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/oauth/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.oauth
from netrun.oauth import *
from netrun.oauth import __all__
