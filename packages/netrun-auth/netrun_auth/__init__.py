"""
DEPRECATED: Import from netrun.auth instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_auth import JWTManager

    # New:
    from netrun.auth import JWTManager

Migration Guide:
    1. Replace all imports:
       - from netrun_auth import ... → from netrun.auth import ...
       - from netrun_auth.middleware import ... → from netrun.auth.middleware import ...
       - from netrun_auth.integrations.azure_ad import ... → from netrun.auth.integrations.azure_ad import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=1.0.0
       - Update: netrun-auth>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_auth is deprecated. Use 'from netrun.auth import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/auth/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.auth
from netrun.auth import *
from netrun.auth import __all__
