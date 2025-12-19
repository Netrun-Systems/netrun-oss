"""
DEPRECATED: Import from netrun.testing instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from netrun_pytest_fixtures import ...

    # New:
    from netrun.testing import ...

Migration Guide:
    1. Replace all imports:
       - from netrun_pytest_fixtures import ... → from netrun.testing import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: netrun-pytest-fixtures>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "netrun_pytest_fixtures is deprecated. Use 'from netrun.testing import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/testing/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.testing
from netrun.testing import *
from netrun.testing import __all__
