"""
DEPRECATED: Import from netrun.errors instead.

This compatibility shim will be removed in version 3.0.0.

Migration Guide:
    # Old (deprecated):
    from netrun_errors import NetrunException
    from netrun_errors import InvalidCredentialsError
    from netrun_errors import install_exception_handlers

    # New:
    from netrun.errors import NetrunException
    from netrun.errors import InvalidCredentialsError
    from netrun.errors import install_exception_handlers

Version 2.0.0 introduced namespace packaging to align with Python standards
and enable better package organization across the Netrun ecosystem.

All functionality remains identical - only the import path has changed.
"""
import warnings

warnings.warn(
    "netrun_errors is deprecated. Use 'from netrun.errors import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location
from netrun.errors import *  # noqa: F401, F403
from netrun.errors import __all__  # noqa: F401

__version__ = "2.0.0"
