"""
netrun-oauth: Reusable OAuth 2.0 adapters for multi-tenant SaaS applications

Provides:
- Platform-specific OAuth adapters (Microsoft, Google, Salesforce, etc.)
- Adapter factory for dynamic adapter creation
- Token encryption service (AES-256-GCM via Fernet)
- Comprehensive exception hierarchy

Part of: Netrun Service Library v2
Version: 1.0.0
SDLC v2.2 Compliant
"""

__version__ = "2.0.0"

from .factory import OAuthAdapterFactory
from .token_manager import (
    TokenEncryptionService,
    get_token_encryption,
    initialize_token_encryption,
    encrypt_access_token,
    decrypt_access_token,
)
from .adapters import (
    BaseOAuthAdapter,
    PostResult,
    TokenData,
    MicrosoftAdapter,
    GoogleAdapter,
    SalesforceAdapter,
    HubSpotAdapter,
    QuickBooksAdapter,
    XeroAdapter,
    MetaAdapter,
    MailchimpAdapter,
    SlackAdapter,
    ZoomAdapter,
    DocuSignAdapter,
    DropboxAdapter,
)
from .exceptions import (
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

__all__ = [
    # Version
    "__version__",
    # Factory
    "OAuthAdapterFactory",
    # Token Management
    "TokenEncryptionService",
    "get_token_encryption",
    "initialize_token_encryption",
    "encrypt_access_token",
    "decrypt_access_token",
    # Base Classes
    "BaseOAuthAdapter",
    "PostResult",
    "TokenData",
    # Adapters
    "MicrosoftAdapter",
    "GoogleAdapter",
    "SalesforceAdapter",
    "HubSpotAdapter",
    "QuickBooksAdapter",
    "XeroAdapter",
    "MetaAdapter",
    "MailchimpAdapter",
    "SlackAdapter",
    "ZoomAdapter",
    "DocuSignAdapter",
    "DropboxAdapter",
    # Exceptions
    "OAuthError",
    "AdapterError",
    "RateLimitError",
    "AuthenticationError",
    "MediaUploadError",
    "ValidationError",
    "TokenEncryptionError",
    "UnsupportedPlatformError",
    "ConfigurationError",
]
