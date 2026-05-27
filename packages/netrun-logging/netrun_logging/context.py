"""
DEPRECATED: Import from netrun.logging.context instead.

This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.context is deprecated. Use 'from netrun.logging.context import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from netrun.logging.context import *  # noqa: F401, F403
