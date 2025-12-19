"""
DEPRECATED: Import from netrun.logging.formatters instead.
This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.formatters is deprecated. Use 'from netrun.logging.formatters import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from netrun.logging.formatters import *  # noqa: F401, F403
from netrun.logging.formatters import __all__  # noqa: F401
