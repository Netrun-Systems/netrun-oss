"""
FastAPI middleware for rate limiting.

Provides automatic rate limiting for all requests with configurable
key extraction and response handling.
"""

from typing import Callable, Optional, Awaitable, Union
import time

from netrun_ratelimit.bucket import RateLimiter, RateLimitResult
from netrun_ratelimit.exceptions import RateLimitExceeded


# Type alias for key functions
KeyFunc = Callable[..., Union[str, Awaitable[str]]]


def default_key_func(request: "Request") -> str:  # noqa: F821
    """
    Default key function using client IP address.

    Args:
        request: Starlette/FastAPI Request object.

    Returns:
        Client IP address or "unknown" if not available.
    """
    # Try X-Forwarded-For first (for proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


def get_user_key(request: "Request") -> str:  # noqa: F821
    """
    Key function using authenticated user ID.

    Falls back to IP if user not authenticated.

    Args:
        request: Starlette/FastAPI Request object.

    Returns:
        User ID from request state or IP address.
    """
    # Check for user in request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        user = request.state.user
        if hasattr(user, "id"):
            return f"user:{user.id}"
        return f"user:{user}"

    return default_key_func(request)


def get_endpoint_key(request: "Request") -> str:  # noqa: F821
    """
    Key function combining endpoint and IP.

    Useful for per-endpoint rate limits.

    Args:
        request: Starlette/FastAPI Request object.

    Returns:
        Combined endpoint and IP key.
    """
    ip = default_key_func(request)
    path = request.url.path
    method = request.method
    return f"{method}:{path}:{ip}"


class RateLimitMiddleware:
    """
    ASGI middleware for automatic rate limiting.

    Applies rate limits to all requests and returns 429 Too Many Requests
    when limits are exceeded.

    Args:
        app: ASGI application.
        limiter: RateLimiter instance.
        key_func: Function to extract rate limit key from request.
        exclude_paths: Paths to exclude from rate limiting.
        include_headers: Include rate limit headers in responses.
        on_limited: Custom handler for rate limited requests.

    Example:
        from fastapi import FastAPI
        from netrun_ratelimit import RateLimiter, MemoryBackend, RateLimitMiddleware

        app = FastAPI()
        limiter = RateLimiter(backend=MemoryBackend(), rate=100, period=60)

        app.add_middleware(
            RateLimitMiddleware,
            limiter=limiter,
            key_func=get_user_key,
            exclude_paths=["/health", "/metrics"],
        )
    """

    def __init__(
        self,
        app: "ASGIApp",  # noqa: F821
        limiter: RateLimiter,
        key_func: Optional[KeyFunc] = None,
        exclude_paths: Optional[list[str]] = None,
        include_headers: bool = True,
        on_limited: Optional[Callable[["Request", RateLimitResult], "Response"]] = None,  # noqa: F821
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.key_func = key_func or default_key_func
        self.exclude_paths = set(exclude_paths or [])
        self.include_headers = include_headers
        self.on_limited = on_limited

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
    ) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Lazy import to avoid requiring starlette at import time
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        request = Request(scope, receive)

        # Check exclusions
        if request.url.path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Extract key
        key = self.key_func(request)
        if hasattr(key, "__await__"):
            key = await key

        # Check rate limit
        result = await self.limiter.acheck(key)

        if not result.allowed:
            # Rate limited
            if self.on_limited:
                response = self.on_limited(request, result)
            else:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests",
                        "retry_after": int(result.retry_after) + 1,
                    },
                    headers=result.headers if self.include_headers else {},
                )
            await response(scope, receive, send)
            return

        # Add headers to response
        if self.include_headers:
            # Wrap send to inject headers
            async def send_with_headers(message: dict) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    for name, value in result.headers.items():
                        headers.append((name.lower().encode(), value.encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_headers)
        else:
            await self.app(scope, receive, send)


class SlidingWindowMiddleware:
    """
    Sliding window rate limit middleware.

    Alternative to token bucket that uses a sliding time window
    for more predictable rate limiting behavior.

    Args:
        app: ASGI application.
        rate: Requests allowed per window.
        window: Window size in seconds.
        key_func: Function to extract rate limit key.
        backend: Storage backend.
    """

    def __init__(
        self,
        app: "ASGIApp",  # noqa: F821
        rate: int = 100,
        window: int = 60,
        key_func: Optional[KeyFunc] = None,
        backend: Optional["RateLimitBackend"] = None,  # noqa: F821
    ) -> None:
        from netrun_ratelimit.backends import MemoryBackend

        self.app = app
        self.rate = rate
        self.window = window
        self.key_func = key_func or default_key_func
        self.backend = backend or MemoryBackend()

        # Use token bucket with burst = rate for sliding window behavior
        self.limiter = RateLimiter(
            backend=self.backend,
            rate=rate,
            period=window,
            burst=rate,
        )

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
    ) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        from starlette.responses import JSONResponse

        request = Request(scope, receive)
        key = self.key_func(request)
        if hasattr(key, "__await__"):
            key = await key

        result = await self.limiter.acheck(key)

        if not result.allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "retry_after": int(result.retry_after) + 1,
                },
                headers=result.headers,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
