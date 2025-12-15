"""
Netrun Authentication - FastAPI Middleware
===========================================

Authentication middleware for FastAPI with JWT/API key validation,
rate limiting, and security headers.

Changelog:
- v1.2.0: Integrated netrun-logging with structured request/auth logging
- v1.0.0: Initial release with JWT validation and rate limiting

Author: Netrun Systems
Version: 1.2.0
Date: 2025-12-05
"""

from typing import Optional, Callable, List
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis

from .jwt import JWTManager
from .types import TokenType, AuthContext, User
from .config import AuthConfig
from .exceptions import (
    AuthenticationError,
    TokenInvalidError,
    RateLimitExceededError
)

# Graceful netrun-logging integration
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger, bind_request_context, bind_context
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)

logger = _logger


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI authentication middleware.

    Validates JWT Bearer tokens and API keys, injects claims into request context,
    and handles rate limiting and audit logging.
    """

    def __init__(
        self,
        app: ASGIApp,
        jwt_manager: JWTManager,
        redis_client: Optional[redis.Redis] = None,
        config: Optional[AuthConfig] = None
    ):
        """
        Initialize authentication middleware.

        Args:
            app: ASGI application
            jwt_manager: JWT token manager
            redis_client: Redis client for rate limiting
            config: Authentication configuration
        """
        super().__init__(app)
        self.jwt_manager = jwt_manager
        self.redis_client = redis_client
        self.config = config or AuthConfig()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process authentication for each request."""
        # Check if path is exempt from authentication
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Try to authenticate request
        try:
            auth_context = await self._authenticate_request(request)

            # Inject auth context into request state
            request.state.auth = auth_context
            request.state.authenticated = True
            request.state.user_id = auth_context.user_id

            # Bind request context for structured logging
            if _use_netrun_logging:
                bind_request_context(
                    method=request.method,
                    path=request.url.path,
                    user_id=auth_context.user_id,
                    tenant_id=auth_context.organization_id
                )

            # Rate limiting check
            if self.config.rate_limit_enabled and self.redis_client:
                await self._check_rate_limit(request, auth_context)

            # Audit log
            self._log_request(request, auth_context)

            # Process request
            response = await call_next(request)

            # Add security headers
            self._add_security_headers(response)

            return response

        except AuthenticationError as e:
            # Log authentication failure
            if _use_netrun_logging:
                logger.warning(
                    "authentication_failed",
                    error_message=e.message,
                    error_code=e.error_code,
                    path=request.url.path,
                    method=request.method,
                    ip_address=self._get_client_ip(request),
                    operation="authentication"
                )
            else:
                logger.warning(
                    f"Authentication failed: {e.message}",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "ip": self._get_client_ip(request),
                        "error_code": e.error_code
                    }
                )
            raise

    async def _authenticate_request(self, request: Request) -> AuthContext:
        """
        Authenticate request using JWT Bearer token or API key.

        Args:
            request: FastAPI request object

        Returns:
            AuthContext with user information

        Raises:
            AuthenticationError: If authentication fails
        """
        # Try JWT Bearer token first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            claims = await self.jwt_manager.verify_token(token, TokenType.ACCESS)

            return AuthContext(
                user_id=claims.user_id,
                organization_id=claims.organization_id,
                roles=claims.roles,
                permissions=claims.permissions,
                session_id=claims.session_id,
                authenticated_at=datetime.utcnow(),
                auth_method="jwt",
                token_jti=claims.jti,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent")
            )

        # Try API key (X-API-Key header)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Placeholder for API key validation
            # In production, validate against database
            # For now, reject as not implemented
            raise TokenInvalidError(
                message="API key authentication not implemented",
                error_code="API_KEY_NOT_IMPLEMENTED"
            )

        # No authentication provided
        raise AuthenticationError(
            message="No authentication credentials provided",
            error_code="AUTH_REQUIRED"
        )

    async def _check_rate_limit(self, request: Request, auth_context: AuthContext) -> None:
        """
        Check rate limits for authenticated user.

        Args:
            request: FastAPI request
            auth_context: Authentication context

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        if not self.redis_client:
            return

        # Generate rate limit key
        window_seconds = self.config.rate_limit_default_window_seconds
        current_window = int(datetime.utcnow().timestamp() // window_seconds)
        rate_limit_key = f"{self.config.redis_key_prefix}rate_limit:{auth_context.user_id}:{current_window}"

        # Increment counter
        try:
            current_count = await self.redis_client.incr(rate_limit_key)
            if current_count == 1:
                # Set expiry on first request in window
                await self.redis_client.expire(rate_limit_key, window_seconds)

            # Check if limit exceeded
            limit = self.config.rate_limit_default_requests
            if current_count > limit:
                retry_after = window_seconds - (int(datetime.utcnow().timestamp()) % window_seconds)
                raise RateLimitExceededError(
                    message="Rate limit exceeded",
                    retry_after=retry_after,
                    details={
                        "limit": limit,
                        "window_seconds": window_seconds,
                        "current_count": current_count
                    }
                )

        except redis.RedisError as e:
            logger.error(f"Rate limit check failed: {e}")
            # Continue without rate limiting if Redis fails

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication."""
        return any(path.startswith(exempt) for exempt in self.config.exempt_paths)

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header first (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to direct connection IP
        if request.client:
            return request.client.host

        return None

    def _log_request(self, request: Request, auth_context: AuthContext) -> None:
        """Log authenticated request for audit trail."""
        if self.config.audit_log_enabled:
            if _use_netrun_logging:
                logger.info(
                    "authenticated_request",
                    user_id=auth_context.user_id,
                    organization_id=auth_context.organization_id,
                    session_id=auth_context.session_id,
                    auth_method=auth_context.auth_method,
                    ip_address=auth_context.ip_address,
                    user_agent=auth_context.user_agent,
                    path=request.url.path,
                    method=request.method,
                    operation="request_audit"
                )
            else:
                logger.info(
                    f"{request.method} {request.url.path}",
                    extra={
                        "user_id": auth_context.user_id,
                        "organization_id": auth_context.organization_id,
                        "session_id": auth_context.session_id,
                        "auth_method": auth_context.auth_method,
                        "ip_address": auth_context.ip_address,
                        "user_agent": auth_context.user_agent,
                        "path": request.url.path,
                        "method": request.method
                    }
                )

    def _add_security_headers(self, response: Response) -> None:
        """Add OWASP recommended security headers."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
