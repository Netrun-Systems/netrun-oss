"""
DEPRECATED: Import from netrun.logging.formatters.json_formatter instead.

This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_logging.formatters.json_formatter is deprecated. "
    "Use 'from netrun.logging.formatters.json_formatter import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from netrun.logging.formatters.json_formatter import *  # noqa: F401, F403
