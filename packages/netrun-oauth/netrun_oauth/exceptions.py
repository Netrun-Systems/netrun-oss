"""
OAuth Adapter Exceptions
Custom exceptions for OAuth 2.0 adapter operations

Part of: netrun-oauth v1.0.0
SDLC v2.2 Compliant - Extracted from Intirkast OAuth adapters
"""


class OAuthError(Exception):
    """Base exception for OAuth adapter errors"""
    pass


class AdapterError(OAuthError):
    """Base exception for adapter-level errors"""
    pass


class RateLimitError(AdapterError):
    """Raised when platform rate limit is exceeded"""

    def __init__(self, message: str, retry_after_seconds: int = 900):
        """
        Initialize rate limit error

        Args:
            message: Error message describing the rate limit
            retry_after_seconds: Seconds to wait before retry (default: 15 minutes)
        """
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AuthenticationError(AdapterError):
    """Raised when OAuth authentication fails"""
    pass


class MediaUploadError(AdapterError):
    """Raised when media upload fails"""
    pass


class ValidationError(AdapterError):
    """Raised when content validation fails"""
    pass


class TokenEncryptionError(OAuthError):
    """Raised when token encryption/decryption fails"""
    pass


class UnsupportedPlatformError(AdapterError):
    """Raised when attempting to use unsupported OAuth platform"""
    pass


class ConfigurationError(OAuthError):
    """Raised when OAuth configuration is invalid or missing"""
    pass
