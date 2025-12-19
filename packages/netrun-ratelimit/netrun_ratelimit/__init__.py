"""
DEPRECATED: Import from netrun.ratelimit instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_ratelimit import RateLimiter

    # New:
    from netrun.ratelimit import RateLimiter

Migration Guide:
    1. Replace all imports:
       - from netrun_ratelimit import ... → from netrun.ratelimit import ...
       - from netrun_ratelimit.backends import ... → from netrun.ratelimit.backends import ...
       - from netrun_ratelimit.middleware import ... → from netrun.ratelimit.middleware import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: netrun-ratelimit>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_ratelimit is deprecated. Use 'from netrun.ratelimit import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/ratelimit/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.ratelimit
from netrun.ratelimit import *
from netrun.ratelimit import __all__
