"""
Netrun Dogfood MCP Server - Unified API access to all Netrun Systems products.

This MCP server provides Claude Code agents with direct access to:
- Intirkon: Azure multi-tenant management platform
- Charlotte: AI orchestration and LLM mesh
- Meridian: Document publishing and flipbook generation
- NetrunSite: Company website and blog API
- SecureVault: Password and credential management

All APIs are secured with MSAL/Azure AD authentication.

Author: Netrun Systems
Version: 2.0.0
Date: 2025-12-18
"""

__version__ = "2.0.0"
__author__ = "Netrun Systems"

from netrun.dogfood.config import DogfoodConfig
from netrun.dogfood.auth import DogfoodAuth

__all__ = [
    "__version__",
    "DogfoodConfig",
    "DogfoodAuth",
]
