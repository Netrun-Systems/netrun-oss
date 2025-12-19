"""
Microsoft OAuth 2.0 Adapter
Supports Azure AD, Office 365, Microsoft Graph API

Part of: netrun-oauth v1.0.0
SDLC v2.2 Compliant
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

from .base import BaseOAuthAdapter, TokenData, PostResult
from ..exceptions import AuthenticationError, RateLimitError, ValidationError

logger = logging.getLogger(__name__)


class MicrosoftAdapter(BaseOAuthAdapter):
    """
    Microsoft OAuth 2.0 adapter for Azure AD and Microsoft Graph

    **Features:**
    - OAuth 2.0 with Microsoft Identity Platform
    - Microsoft Graph API access
    - Office 365 integration
    - Azure Active Directory authentication

    **Scopes:**
    - User.Read (basic profile)
    - Mail.Send (send email)
    - Calendars.ReadWrite (calendar access)
    - Files.ReadWrite (OneDrive)

    **Documentation:**
    https://docs.microsoft.com/en-us/azure/active-directory/develop/
    """

    # OAuth URLs
    AUTH_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    GRAPH_URL = "https://graph.microsoft.com/v1.0"

    # Default scopes
    DEFAULT_SCOPES = ["User.Read", "offline_access"]

    def __init__(
        self,
        client_id: str = "{{MICROSOFT_CLIENT_ID}}",
        client_secret: str = "{{MICROSOFT_CLIENT_SECRET}}",
        tenant: str = "common"
    ):
        """
        Initialize Microsoft OAuth adapter

        Args:
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            tenant: Azure AD tenant ID or "common" for multi-tenant
        """
        super().__init__(client_id, client_secret)
        self.tenant = tenant
        self.platform_name = "microsoft"

    async def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None
    ) -> str:
        """Generate Microsoft OAuth authorization URL"""
        scopes = scopes or self.DEFAULT_SCOPES

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
            "response_mode": "query",
        }

        auth_url = self.AUTH_URL.format(tenant=self.tenant)
        url = f"{auth_url}?{urlencode(params)}"
        logger.info(f"Generated Microsoft auth URL for state={state}")
        return url

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
        state: Optional[str] = None
    ) -> TokenData:
        """Exchange authorization code for Microsoft access token"""
        try:
            token_url = self.TOKEN_URL.format(tenant=self.tenant)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                self._check_rate_limit_response(response.status_code, dict(response.headers))
                self._check_authentication_response(response.status_code)

                if response.status_code != 200:
                    raise AuthenticationError(f"Token exchange failed: {response.text}")

                data = response.json()
                expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))

                logger.info("Successfully exchanged Microsoft authorization code for token")

                return TokenData(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_at=expires_at,
                    token_type="Bearer",
                    scope=data.get("scope"),
                )

        except (AuthenticationError, RateLimitError):
            raise
        except Exception as e:
            logger.error(f"Microsoft token exchange error: {e}")
            raise AuthenticationError(f"Token exchange failed: {str(e)}")

    async def refresh_token(self, refresh_token: str) -> TokenData:
        """Refresh Microsoft access token"""
        try:
            token_url = self.TOKEN_URL.format(tenant=self.tenant)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                self._check_authentication_response(response.status_code)

                if response.status_code != 200:
                    raise AuthenticationError(f"Token refresh failed: {response.text}")

                data = response.json()
                expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))

                logger.info("Successfully refreshed Microsoft access token")

                return TokenData(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_at=expires_at,
                    token_type="Bearer",
                )

        except (AuthenticationError, RateLimitError):
            raise
        except Exception as e:
            logger.error(f"Microsoft token refresh error: {e}")
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke Microsoft token

        Note: Microsoft doesn't provide a public revoke endpoint.
        Tokens expire automatically based on expires_in value.
        """
        logger.warning("Microsoft doesn't support programmatic token revocation")
        return False

    async def post_text(
        self,
        access_token: str,
        content: str,
        **kwargs
    ) -> PostResult:
        """
        Post text (not applicable for Microsoft Graph API)

        Note: Microsoft Graph doesn't have a "post text" concept.
        Use send_email or create_calendar_event instead.
        """
        return PostResult(
            success=False,
            platform="microsoft",
            error_message="Microsoft Graph API doesn't support generic text posting. Use send_email() or create_calendar_event().",
        )

    async def post_image(
        self,
        access_token: str,
        content: str,
        image_url: str,
        **kwargs
    ) -> PostResult:
        """Post image (not applicable for Microsoft Graph)"""
        return PostResult(
            success=False,
            platform="microsoft",
            error_message="Microsoft Graph API doesn't support image posting. Use upload_to_onedrive() instead.",
        )

    async def post_video(
        self,
        access_token: str,
        content: str,
        video_url: str,
        **kwargs
    ) -> PostResult:
        """Post video (not applicable for Microsoft Graph)"""
        return PostResult(
            success=False,
            platform="microsoft",
            error_message="Microsoft Graph API doesn't support video posting. Use upload_to_onedrive() instead.",
        )

    async def schedule_post(
        self,
        access_token: str,
        content: str,
        scheduled_time: datetime,
        media_url: Optional[str] = None,
        **kwargs
    ) -> PostResult:
        """Schedule post (not applicable for Microsoft Graph)"""
        return PostResult(
            success=False,
            platform="microsoft",
            error_message="Microsoft Graph API doesn't support scheduling posts. Use create_calendar_event() instead.",
        )

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch authenticated user's Microsoft profile"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.GRAPH_URL}/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                self._check_authentication_response(response.status_code)

                if response.status_code != 200:
                    raise AuthenticationError(f"Failed to fetch user profile: {response.text}")

                data = response.json()

                return {
                    "platform_user_id": data.get("id"),
                    "username": data.get("userPrincipalName"),
                    "display_name": data.get("displayName"),
                    "email": data.get("mail") or data.get("userPrincipalName"),
                    "given_name": data.get("givenName"),
                    "surname": data.get("surname"),
                    "job_title": data.get("jobTitle"),
                    "office_location": data.get("officeLocation"),
                }

        except Exception as e:
            logger.error(f"Microsoft user profile error: {e}")
            raise AuthenticationError(f"Failed to fetch user profile: {str(e)}")
