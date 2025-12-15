"""
FastAPI route decorators for rate limiting.

Provides fine-grained control over rate limits on individual routes.
"""

from functools import wraps
from typing import Callable, Optional, Any, Union
import inspect

from netrun_ratelimit.bucket import RateLimiter
from netrun_ratelimit.exceptions import RateLimitExceeded


def rate_limit(
    rate: int = 100,
    period: int = 60,
    burst: Optional[int] = None,
    key: Optional[Union[str, Callable[..., str]]] = None,
    limiter: Optional[RateLimiter] = None,
) -> Callable:
    """
    Decorator for rate limiting individual routes.

    Args:
        rate: Requests allowed per period.
        period: Time period in seconds.
        burst: Maximum burst capacity.
        key: Static key string or function to extract key from request.
        limiter: Existing RateLimiter instance (creates one if not provided).

    Example:
        from fastapi import FastAPI, Request
        from netrun_ratelimit import rate_limit

        app = FastAPI()

        @app.get("/api/data")
        @rate_limit(rate=10, period=60)
        async def get_data(request: Request):
            return {"data": "value"}

        # With custom key
        def get_api_key(request: Request) -> str:
            return request.headers.get("X-API-Key", "anonymous")

        @app.post("/api/submit")
        @rate_limit(rate=5, period=60, key=get_api_key)
        async def submit(request: Request):
            return {"status": "ok"}
    """
    def decorator(func: Callable) -> Callable:
        # Create limiter if not provided
        nonlocal limiter
        if limiter is None:
            from netrun_ratelimit.backends import MemoryBackend
            limiter = RateLimiter(
                backend=MemoryBackend(),
                rate=rate,
                period=period,
                burst=burst,
            )

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find request in args/kwargs
            request = _find_request(args, kwargs, func)

            # Extract key
            if key is None:
                rate_key = _default_key(request)
            elif callable(key):
                rate_key = key(request)
                if inspect.isawaitable(rate_key):
                    rate_key = await rate_key
            else:
                rate_key = key

            # Check rate limit
            result = await limiter.acheck(
                rate_key,
                rate=rate,
                period=period,
                burst=burst,
            )

            if not result.allowed:
                raise RateLimitExceeded(
                    message="Rate limit exceeded",
                    limit=result.limit,
                    remaining=result.remaining,
                    reset_at=result.reset_at,
                    retry_after=result.retry_after,
                    key=rate_key,
                )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs, func)

            if key is None:
                rate_key = _default_key(request)
            elif callable(key):
                rate_key = key(request)
            else:
                rate_key = key

            result = limiter.check(
                rate_key,
                rate=rate,
                period=period,
                burst=burst,
            )

            if not result.allowed:
                raise RateLimitExceeded(
                    message="Rate limit exceeded",
                    limit=result.limit,
                    remaining=result.remaining,
                    reset_at=result.reset_at,
                    retry_after=result.retry_after,
                    key=rate_key,
                )

            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _find_request(args: tuple, kwargs: dict, func: Callable) -> Any:
    """Find Request object in function arguments."""
    # Check kwargs first
    if "request" in kwargs:
        return kwargs["request"]

    # Check positional args by inspecting signature
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    for i, param_name in enumerate(params):
        if param_name == "request" and i < len(args):
            return args[i]

    # Check by type annotation
    for i, (param_name, param) in enumerate(sig.parameters.items()):
        if param.annotation != inspect.Parameter.empty:
            ann = param.annotation
            if hasattr(ann, "__name__") and ann.__name__ == "Request":
                if param_name in kwargs:
                    return kwargs[param_name]
                if i < len(args):
                    return args[i]

    # Last resort: look for anything that looks like a request
    for arg in args:
        if hasattr(arg, "client") and hasattr(arg, "headers"):
            return arg

    return None


def _default_key(request: Any) -> str:
    """Extract default key from request."""
    if request is None:
        return "unknown"

    # Try X-Forwarded-For
    if hasattr(request, "headers"):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

    # Try client IP
    if hasattr(request, "client") and request.client:
        return request.client.host

    return "unknown"


class RateLimitRoute:
    """
    Custom APIRoute class for rate-limited routes.

    Use with FastAPI's route_class parameter for automatic rate limiting
    on all routes in a router.

    Example:
        from fastapi import APIRouter
        from netrun_ratelimit import RateLimitRoute, RateLimiter, MemoryBackend

        limiter = RateLimiter(backend=MemoryBackend(), rate=50, period=60)

        router = APIRouter(route_class=RateLimitRoute.with_limiter(limiter))

        @router.get("/resource")
        async def get_resource():
            return {"data": "value"}
    """

    _limiter: Optional[RateLimiter] = None
    _rate: int = 100
    _period: int = 60

    @classmethod
    def with_limiter(
        cls,
        limiter: RateLimiter,
        rate: Optional[int] = None,
        period: Optional[int] = None,
    ) -> type:
        """
        Create a RateLimitRoute class with the given limiter.

        Args:
            limiter: RateLimiter instance to use.
            rate: Override default rate.
            period: Override default period.

        Returns:
            Configured RateLimitRoute class.
        """
        try:
            from fastapi.routing import APIRoute
        except ImportError:
            raise ImportError(
                "fastapi is required for RateLimitRoute. "
                "Install with: pip install netrun-ratelimit[fastapi]"
            )

        class ConfiguredRoute(APIRoute):
            def get_route_handler(self) -> Callable:
                original_handler = super().get_route_handler()

                async def rate_limited_handler(request: Any) -> Any:
                    # Extract key
                    key = _default_key(request)

                    # Check limit
                    result = await limiter.acheck(
                        key,
                        rate=rate or limiter.rate,
                        period=period or limiter.period,
                    )

                    if not result.allowed:
                        from starlette.responses import JSONResponse
                        return JSONResponse(
                            status_code=429,
                            content={
                                "error": "rate_limit_exceeded",
                                "retry_after": int(result.retry_after) + 1,
                            },
                            headers=result.headers,
                        )

                    response = await original_handler(request)

                    # Add rate limit headers
                    if hasattr(response, "headers"):
                        for name, value in result.headers.items():
                            response.headers[name] = value

                    return response

                return rate_limited_handler

        return ConfiguredRoute


def limit_by_user(
    rate: int = 100,
    period: int = 60,
    user_attr: str = "id",
    limiter: Optional[RateLimiter] = None,
) -> Callable:
    """
    Rate limit decorator keyed by authenticated user.

    Args:
        rate: Requests allowed per period.
        period: Time period in seconds.
        user_attr: Attribute name for user ID.
        limiter: Existing RateLimiter instance.

    Example:
        @app.get("/user/profile")
        @limit_by_user(rate=30, period=60)
        async def get_profile(request: Request):
            return {"user": request.state.user.id}
    """
    def get_user_key(request: Any) -> str:
        if hasattr(request, "state") and hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, user_attr):
                return f"user:{getattr(user, user_attr)}"
            return f"user:{user}"
        return _default_key(request)

    return rate_limit(rate=rate, period=period, key=get_user_key, limiter=limiter)


def limit_by_api_key(
    rate: int = 1000,
    period: int = 60,
    header_name: str = "X-API-Key",
    limiter: Optional[RateLimiter] = None,
) -> Callable:
    """
    Rate limit decorator keyed by API key header.

    Args:
        rate: Requests allowed per period.
        period: Time period in seconds.
        header_name: Name of the API key header.
        limiter: Existing RateLimiter instance.

    Example:
        @app.get("/api/data")
        @limit_by_api_key(rate=1000, period=3600)
        async def get_data(request: Request):
            return {"data": "value"}
    """
    def get_api_key(request: Any) -> str:
        if hasattr(request, "headers"):
            api_key = request.headers.get(header_name)
            if api_key:
                return f"apikey:{api_key}"
        return _default_key(request)

    return rate_limit(rate=rate, period=period, key=get_api_key, limiter=limiter)
