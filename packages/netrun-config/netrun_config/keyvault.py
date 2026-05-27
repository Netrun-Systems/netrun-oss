"""
DEPRECATED: Import from netrun.config.keyvault instead.

This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_config.keyvault is deprecated. Use 'from netrun.config.keyvault import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from netrun.config.keyvault import *  # noqa: F401, F403

# Explicitly re-export AZURE_AVAILABLE so patches work correctly
try:
    from netrun.config.keyvault import AZURE_AVAILABLE  # noqa: F401
except ImportError:
    pass
