"""
DEPRECATED: Import from netrun.logging.processors instead.

This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.processors is deprecated. Use 'from netrun.logging.processors import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from netrun.logging.processors import *  # noqa: F401, F403
