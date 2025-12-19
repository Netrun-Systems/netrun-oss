"""
DEPRECATED: Import from netrun.cors instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_cors import ...

    # New:
    from netrun.cors import ...

Migration Guide:
    1. Replace all imports:
       - from netrun_cors import ... → from netrun.cors import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: netrun-cors>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_cors is deprecated. Use 'from netrun.cors import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/cors/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.cors
from netrun.cors import *
from netrun.cors import __all__
