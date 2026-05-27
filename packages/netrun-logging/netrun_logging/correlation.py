"""
DEPRECATED: Import from netrun.logging.correlation instead.

This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.correlation is deprecated. Use 'from netrun.logging.correlation import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from netrun.logging.correlation import *  # noqa: F401, F403
