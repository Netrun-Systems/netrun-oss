"""
DEPRECATED: Import from netrun.logging.integrations instead.
This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.integrations is deprecated. Use 'from netrun.logging.integrations import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from netrun.logging.integrations import *  # noqa: F401, F403
from netrun.logging.integrations import __all__  # noqa: F401
