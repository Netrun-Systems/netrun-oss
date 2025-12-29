"""
WebSocket JWT Authentication
File: auth.py
Netrun Systems - SDLC v2.3 Compliant

JWT-based authentication for WebSocket connections with token validation,
expiration handling, and claims extraction.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketException, status

try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTError = Exception  # Placeholder

logger = logging.getLogger(__name__)


class JWTAuthService:
    """
    JWT authentication service for WebSocket connections.

    Provides token generation, validation, and claims extraction
    for secure WebSocket authentication.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiry_seconds: int = 7200  # 2 hours default
    ):
        """
        Initialize JWT auth service.

        Args:
            secret_key: Secret key for JWT signing/verification
            algorithm: JWT algorithm (default: HS256)
            token_expiry_seconds: Token expiry duration in seconds
        """
        if not JWT_AVAILABLE:
            raise ImportError(
                "JWT support not available. Install with: "
                "pip install netrun-websocket[auth]"
            )

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry_seconds = token_expiry_seconds

    def generate_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None,
        expiry_seconds: Optional[int] = None
    ) -> str:
        """
        Generate JWT token for user.

        Args:
            user_id: User identifier
            additional_claims: Optional additional JWT claims
            expiry_seconds: Optional custom expiry duration

        Returns:
            str: Encoded JWT token
        """
        expiry = expiry_seconds or self.token_expiry_seconds
        now = datetime.now(timezone.utc)

        claims = {
            "sub": user_id,
            "user_id": user_id,
            "iat": now,
            "exp": now + timedelta(seconds=expiry)
        }

        if additional_claims:
            claims.update(additional_claims)

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Generated JWT token for user {user_id}")
        return token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            Dict of claims if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating JWT: {e}")
            return None

    def get_user_id(self, token: str) -> Optional[str]:
        """
        Extract user ID from JWT token.

        Args:
            token: JWT token string

        Returns:
            User ID if valid, None otherwise
        """
        payload = self.validate_token(token)
        if payload:
            return payload.get("user_id") or payload.get("sub")
        return None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired.

        Args:
            token: JWT token string

        Returns:
            True if expired, False otherwise
        """
        payload = self.validate_token(token)
        if not payload:
            return True

        exp = payload.get("exp")
        if not exp:
            return True

        now = datetime.now(timezone.utc).timestamp()
        return now > exp


async def authenticate_websocket(
    websocket: WebSocket,
    token: str,
    auth_service: JWTAuthService
) -> Dict[str, Any]:
    """
    Authenticate WebSocket connection using JWT token.

    Args:
        websocket: FastAPI WebSocket instance
        token: JWT token from query parameter or header
        auth_service: JWTAuthService instance

    Returns:
        Dict of JWT claims

    Raises:
        WebSocketException: If authentication fails
    """
    if not token:
        logger.warning("WebSocket authentication failed: No token provided")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required"
        )

    payload = auth_service.validate_token(token)
    if not payload:
        logger.warning("WebSocket authentication failed: Invalid token")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid authentication token"
        )

    # Check expiration
    if auth_service.is_token_expired(token):
        logger.warning("WebSocket authentication failed: Token expired")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token expired"
        )

    user_id = payload.get("user_id") or payload.get("sub")
    logger.info(f"WebSocket authenticated for user: {user_id}")

    return payload


class TokenAuthMiddleware:
    """
    Middleware for WebSocket JWT authentication.

    Usage:
        auth_middleware = TokenAuthMiddleware(auth_service)

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
            payload = await auth_middleware.authenticate(websocket, token)
            # ... rest of websocket logic
    """

    def __init__(self, auth_service: JWTAuthService):
        """
        Initialize auth middleware.

        Args:
            auth_service: JWTAuthService instance
        """
        self.auth_service = auth_service

    async def authenticate(
        self,
        websocket: WebSocket,
        token: str
    ) -> Dict[str, Any]:
        """
        Authenticate WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            token: JWT token

        Returns:
            Dict of JWT claims

        Raises:
            WebSocketException: If authentication fails
        """
        return await authenticate_websocket(websocket, token, self.auth_service)


__all__ = [
    "JWTAuthService",
    "TokenAuthMiddleware",
    "authenticate_websocket",
]
