"""
DEPRECATED: Import from netrun.logging.middleware.fastapi instead.
This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.middleware.fastapi is deprecated. Use 'from netrun.logging.middleware.fastapi import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from netrun.logging.middleware.fastapi import *  # noqa: F401, F403
from netrun.logging.middleware.fastapi import __all__  # noqa: F401
