"""
OAuth 2.0 Platform Adapters for Multi-tenant SaaS Applications
Reusable adapters for popular OAuth platforms

Part of: netrun-oauth v1.0.0
SDLC v2.2 Compliant - Extracted from Intirkast OAuth adapters
"""

from .base import BaseOAuthAdapter, PostResult, TokenData
from .microsoft import MicrosoftAdapter
from .google import GoogleAdapter
from .salesforce import SalesforceAdapter
from .hubspot import HubSpotAdapter
from .quickbooks import QuickBooksAdapter
from .xero import XeroAdapter
from .meta import MetaAdapter
from .mailchimp import MailchimpAdapter
from .slack import SlackAdapter
from .zoom import ZoomAdapter
from .docusign import DocuSignAdapter
from .dropbox import DropboxAdapter

__all__ = [
    "BaseOAuthAdapter",
    "PostResult",
    "TokenData",
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
]
