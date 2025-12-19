"""
DEPRECATED: Import from netrun.logging instead.

This compatibility shim will be removed in version 3.0.0.

Migration Guide:
    # Old (deprecated):
    from netrun_logging import configure_logging, get_logger
    from netrun_logging import generate_correlation_id
    from netrun_logging import bind_error_context
    from netrun_logging.middleware import add_logging_middleware

    # New:
    from netrun.logging import configure_logging, get_logger
    from netrun.logging import generate_correlation_id
    from netrun.logging import bind_error_context
    from netrun.logging.middleware import add_logging_middleware

Version 2.0.0 introduced namespace packaging to align with Python standards
and enable better package organization across the Netrun ecosystem.

All functionality remains identical - only the import path has changed.
"""
import warnings

warnings.warn(
    "netrun_logging is deprecated. Use 'from netrun.logging import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location
from netrun.logging import *  # noqa: F401, F403
from netrun.logging import __all__  # noqa: F401

__version__ = "2.0.0"
