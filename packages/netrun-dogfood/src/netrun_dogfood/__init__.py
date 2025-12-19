"""
DEPRECATED: Import from netrun.dogfood instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_dogfood import DogfoodConfig

    # New:
    from netrun.dogfood import DogfoodConfig

Migration Guide:
    1. Replace all imports:
       - from netrun_dogfood import ... → from netrun.dogfood import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: netrun-dogfood>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_dogfood is deprecated. Use 'from netrun.dogfood import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/dogfood/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.dogfood
from netrun.dogfood import *
from netrun.dogfood import __all__
