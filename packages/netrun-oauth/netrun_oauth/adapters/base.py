"""
Abstract Base Class for OAuth 2.0 Platform Adapters
Defines interface that all platform adapters must implement

Part of: netrun-oauth v1.0.0
SDLC v2.2 Compliant - Extracted from Intirkast OAuth adapters
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from ..exceptions import (
    AdapterError,
    RateLimitError,
    AuthenticationError,
    MediaUploadError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class PostResult:
    """Result of a post operation"""
    success: bool
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_after_seconds: Optional[int] = None


@dataclass
class TokenData:
    """OAuth token data"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None


class BaseOAuthAdapter(ABC):
    """
    Abstract base class for social media platform OAuth adapters

    All platform-specific adapters must implement these methods to ensure
    consistent OAuth flows and posting capabilities across platforms.

    Attributes:
        client_id: OAuth client ID (use placeholder {{OAUTH_CLIENT_ID}} in production)
        client_secret: OAuth client secret (use placeholder {{OAUTH_CLIENT_SECRET}} in production)
        platform_name: Lowercase platform identifier
    """

    def __init__(
        self,
        client_id: str = "{{OAUTH_CLIENT_ID}}",
        client_secret: str = "{{OAUTH_CLIENT_SECRET}}"
    ):
        """
        Initialize adapter with OAuth credentials

        Args:
            client_id: OAuth client ID (default placeholder)
            client_secret: OAuth client secret (default placeholder)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.platform_name = self.__class__.__name__.replace("Adapter", "").lower()

    # OAuth 2.0 Flow Methods
    @abstractmethod
    async def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None
    ) -> str:
        """
        Generate OAuth authorization URL for user consent

        Args:
            state: CSRF protection token
            redirect_uri: Callback URL after authorization
            scopes: Optional custom scopes (uses default if not provided)

        Returns:
            Authorization URL to redirect user to

        Example:
            url = await adapter.get_authorization_url(
                state="random_state_token",
                redirect_uri="https://app.example.com/oauth/callback"
            )
        """
        pass

    @abstractmethod
    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
        state: Optional[str] = None
    ) -> TokenData:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization
            code_verifier: PKCE code verifier (required for Twitter)
            state: State token (for PKCE cache lookup)

        Returns:
            TokenData with access_token, refresh_token, expiry

        Raises:
            AuthenticationError: If token exchange fails

        Example:
            token_data = await adapter.exchange_code_for_token(
                code="4/0AY0e-g7X...",
                redirect_uri="https://app.example.com/oauth/callback"
            )
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenData:
        """
        Refresh an expired access token

        Args:
            refresh_token: Valid refresh token

        Returns:
            New TokenData with refreshed access token

        Raises:
            AuthenticationError: If refresh fails

        Example:
            new_token = await adapter.refresh_token(
                refresh_token="1//0gHZwG..."
            )
        """
        pass

    @abstractmethod
    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke OAuth access token (disconnect account)

        Args:
            access_token: Token to revoke

        Returns:
            True if revocation successful, False otherwise

        Example:
            revoked = await adapter.revoke_token(access_token="ya29.a0...")
        """
        pass

    # Posting Methods
    @abstractmethod
    async def post_text(
        self,
        access_token: str,
        content: str,
        **kwargs
    ) -> PostResult:
        """
        Post text content to the platform

        Args:
            access_token: Valid OAuth access token
            content: Text content to post
            **kwargs: Platform-specific parameters

        Returns:
            PostResult with success status and post details

        Raises:
            RateLimitError: If rate limit exceeded
            AuthenticationError: If token invalid
            ValidationError: If content validation fails

        Example:
            result = await adapter.post_text(
                access_token="token",
                content="Hello, world! #FirstPost"
            )
        """
        pass

    @abstractmethod
    async def post_image(
        self,
        access_token: str,
        content: str,
        image_url: str,
        **kwargs
    ) -> PostResult:
        """
        Post image content to the platform

        Args:
            access_token: Valid OAuth access token
            content: Caption/text for the image
            image_url: URL of image to post
            **kwargs: Platform-specific parameters (alt_text, etc.)

        Returns:
            PostResult with success status and post details

        Raises:
            RateLimitError: If rate limit exceeded
            AuthenticationError: If token invalid
            MediaUploadError: If image upload fails
            ValidationError: If content validation fails

        Example:
            result = await adapter.post_image(
                access_token="token",
                content="Check out this image!",
                image_url="https://storage.example.com/image.jpg"
            )
        """
        pass

    @abstractmethod
    async def post_video(
        self,
        access_token: str,
        content: str,
        video_url: str,
        **kwargs
    ) -> PostResult:
        """
        Post video content to the platform

        Args:
            access_token: Valid OAuth access token
            content: Caption/text for the video
            video_url: URL of video to post
            **kwargs: Platform-specific parameters (thumbnail, privacy, etc.)

        Returns:
            PostResult with success status and post details

        Raises:
            RateLimitError: If rate limit exceeded
            AuthenticationError: If token invalid
            MediaUploadError: If video upload fails
            ValidationError: If content validation fails

        Example:
            result = await adapter.post_video(
                access_token="token",
                content="New video alert!",
                video_url="https://storage.example.com/video.mp4"
            )
        """
        pass

    @abstractmethod
    async def schedule_post(
        self,
        access_token: str,
        content: str,
        scheduled_time: datetime,
        media_url: Optional[str] = None,
        **kwargs
    ) -> PostResult:
        """
        Schedule a post for future publication (if platform supports native scheduling)

        Args:
            access_token: Valid OAuth access token
            content: Text content to post
            scheduled_time: When to publish the post
            media_url: Optional media URL (image/video)
            **kwargs: Platform-specific parameters

        Returns:
            PostResult with success status and scheduled post ID

        Raises:
            RateLimitError: If rate limit exceeded
            AuthenticationError: If token invalid
            ValidationError: If scheduling not supported or time invalid

        Note:
            If platform doesn't support native scheduling, raise ValidationError
            with message indicating feature not available

        Example:
            result = await adapter.schedule_post(
                access_token="token",
                content="Scheduled post",
                scheduled_time=datetime(2025, 11, 5, 10, 0, 0),
                media_url="https://storage.example.com/image.jpg"
            )
        """
        pass

    # Helper Methods (optional to override)
    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if access token is still valid

        Args:
            access_token: Token to validate

        Returns:
            True if valid, False if expired/invalid

        Note:
            Default implementation returns True.
            Override for platforms with token validation endpoints.
        """
        return True

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user profile information

        Args:
            access_token: Valid OAuth access token

        Returns:
            Dictionary with user profile data

        Raises:
            AuthenticationError: If token invalid

        Note:
            Default implementation raises NotImplementedError.
            Override if platform supports user profile fetching.
        """
        raise NotImplementedError(
            f"{self.platform_name} adapter does not support user profile fetching"
        )

    def _validate_content_length(
        self,
        content: str,
        max_length: int,
        truncate: bool = False
    ) -> str:
        """
        Validate and optionally truncate content to platform limits

        Args:
            content: Content to validate
            max_length: Maximum allowed length
            truncate: If True, truncate to max_length with ellipsis

        Returns:
            Validated (and possibly truncated) content

        Raises:
            ValidationError: If content too long and truncate=False
        """
        if len(content) <= max_length:
            return content

        if truncate:
            return content[:max_length - 3] + "..."

        raise ValidationError(
            f"Content exceeds {max_length} character limit ({len(content)} characters)"
        )

    def _check_rate_limit_response(self, status_code: int, headers: Dict[str, str]) -> None:
        """
        Check HTTP response for rate limiting

        Args:
            status_code: HTTP status code
            headers: Response headers

        Raises:
            RateLimitError: If rate limit detected
        """
        if status_code == 429:
            retry_after = int(headers.get("Retry-After", 900))
            raise RateLimitError(
                f"{self.platform_name} rate limit exceeded",
                retry_after_seconds=retry_after
            )

    def _check_authentication_response(self, status_code: int) -> None:
        """
        Check HTTP response for authentication errors

        Args:
            status_code: HTTP status code

        Raises:
            AuthenticationError: If authentication error detected
        """
        if status_code in (401, 403):
            raise AuthenticationError(
                f"{self.platform_name} authentication failed. Token may be expired or invalid."
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} platform={self.platform_name}>"
