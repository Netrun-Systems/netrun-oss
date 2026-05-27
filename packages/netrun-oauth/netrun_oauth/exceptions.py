"""
DEPRECATED: Import from netrun.oauth.exceptions instead.

This compatibility shim will be removed in version 3.0.0.
"""
import warnings

warnings.warn(
    "netrun_oauth.exceptions is deprecated. Use 'from netrun.oauth.exceptions import ...' instead. "
    "This module will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the canonical exception classes so isinstance() checks still work
from netrun.oauth.exceptions import (  # noqa: F401
    OAuthError,
    AdapterError,
    RateLimitError,
    AuthenticationError,
    MediaUploadError,
    ValidationError,
    TokenEncryptionError,
    UnsupportedPlatformError,
    ConfigurationError,
)
