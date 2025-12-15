"""
Netrun Authentication - Casbin FastAPI Middleware
===================================================

FastAPI middleware for Casbin-based authorization.

Integrates with existing AuthenticationMiddleware to enforce
Casbin RBAC policies on HTTP requests.

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-03
"""

import logging
from typing import List, Optional, Callable, Awaitable

try:
    from fastapi import Request, HTTPException
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    Request = None  # type: ignore
    HTTPException = None  # type: ignore
    BaseHTTPMiddleware = object  # type: ignore
    Response = None  # type: ignore

from .rbac_casbin import CasbinRBACManager
from .types import User

logger = logging.getLogger(__name__)


class CasbinAuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for Casbin-based authorization.

    Enforces RBAC policies on incoming HTTP requests using Casbin enforcer.

    Features:
    - Automatic HTTP method to action mapping (GET -> read, POST -> create, etc.)
    - URL path to resource mapping
    - Multi-tenant support with organization-based isolation
    - Configurable excluded paths (e.g., /health, /docs)
    - Integration with existing authentication middleware

    Examples:
        from netrun_auth import CasbinRBACManager
        from netrun_auth.middleware_casbin import CasbinAuthMiddleware

        # Initialize Casbin manager
        rbac_manager = CasbinRBACManager(multi_tenant=True)
        await rbac_manager.initialize()

        # Add middleware to FastAPI app
        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=rbac_manager,
            excluded_paths=["/health", "/docs", "/openapi.json"],
            resource_mapper=custom_resource_mapper,  # Optional
        )

    Note:
        This middleware requires AuthenticationMiddleware to run first
        to populate request.state.user with authenticated user information.
    """

    def __init__(
        self,
        app,
        rbac_manager: CasbinRBACManager,
        excluded_paths: List[str] | None = None,
        resource_mapper: Optional[Callable[[Request], str]] = None,
        action_mapper: Optional[Callable[[Request], str]] = None,
    ):
        """
        Initialize Casbin authorization middleware.

        Args:
            app: FastAPI application instance
            rbac_manager: Initialized CasbinRBACManager instance
            excluded_paths: List of paths to exclude from authorization checks
            resource_mapper: Custom function to map request to resource name
            action_mapper: Custom function to map request to action name
        """
        if not _HAS_FASTAPI:
            raise ImportError(
                "FastAPI is required for CasbinAuthMiddleware. "
                "Install with: pip install 'netrun-auth[fastapi]'"
            )

        super().__init__(app)
        self.rbac_manager = rbac_manager
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self.resource_mapper = resource_mapper or self._default_resource_mapper
        self.action_mapper = action_mapper or self._default_action_mapper

        logger.info(
            f"Initialized CasbinAuthMiddleware with {len(self.excluded_paths)} excluded paths"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Process request and enforce Casbin authorization.

        Args:
            request: HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response

        Raises:
            HTTPException: 401 if not authenticated, 403 if permission denied
        """
        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Get authenticated user from request state
        user = getattr(request.state, "user", None)
        if not user:
            logger.warning(
                f"Unauthenticated request to {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Add AuthenticationMiddleware before CasbinAuthMiddleware.",
            )

        # Ensure user is User object
        if not isinstance(user, User):
            logger.warning(
                f"Invalid user type in request.state.user: {type(user)}. Expected User object."
            )
            raise HTTPException(
                status_code=500,
                detail="Internal authentication error. Invalid user context.",
            )

        # Map request to resource and action
        resource = self.resource_mapper(request)
        action = self.action_mapper(request)
        tenant_id = user.organization_id if self.rbac_manager.multi_tenant else None

        # Check permission using Casbin
        try:
            has_permission = await self.rbac_manager.check_permission(
                user_id=user.user_id,
                resource=resource,
                action=action,
                tenant_id=tenant_id,
            )
        except Exception as e:
            logger.error(
                f"Error checking permission for user {user.user_id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Internal authorization error",
            )

        if not has_permission:
            logger.warning(
                f"Permission denied for user {user.user_id} on {action} {resource} "
                f"(tenant={tenant_id})"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {action} on {resource}",
                headers={
                    "X-Permission-Required": f"{resource}:{action}",
                },
            )

        # Permission granted, continue to next middleware
        logger.debug(
            f"Permission granted for user {user.user_id} on {action} {resource}"
        )
        return await call_next(request)

    @staticmethod
    def _default_resource_mapper(request: Request) -> str:
        """
        Default resource mapper: uses URL path.

        Examples:
            /api/users -> /api/users
            /api/users/123 -> /api/users
            /projects/456/tasks -> /projects

        Args:
            request: HTTP request

        Returns:
            Resource name
        """
        # Use full path as resource
        path = request.url.path

        # Optional: Strip /api prefix
        if path.startswith("/api/"):
            path = path[4:]

        # Optional: Strip ID segments (numeric or UUID)
        # Example: /users/123 -> /users
        # Uncomment if needed:
        # import re
        # path = re.sub(r'/[0-9a-f-]+(?=/|$)', '', path)

        return path

    @staticmethod
    def _default_action_mapper(request: Request) -> str:
        """
        Default action mapper: maps HTTP methods to CRUD actions.

        Mapping:
            GET -> read
            POST -> create
            PUT -> update
            PATCH -> update
            DELETE -> delete
            HEAD -> read
            OPTIONS -> read

        Args:
            request: HTTP request

        Returns:
            Action name
        """
        method_to_action = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
            "HEAD": "read",
            "OPTIONS": "read",
        }

        return method_to_action.get(request.method, request.method.lower())


# Convenience function for custom resource mappers


def path_prefix_mapper(prefix_to_resource: dict[str, str]) -> Callable[[Request], str]:
    """
    Create custom resource mapper based on path prefix matching.

    Examples:
        mapper = path_prefix_mapper({
            "/api/users": "users",
            "/api/projects": "projects",
            "/api/admin": "admin",
        })

        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=rbac_manager,
            resource_mapper=mapper,
        )

    Args:
        prefix_to_resource: Dictionary mapping path prefixes to resource names

    Returns:
        Resource mapper function
    """

    def mapper(request: Request) -> str:
        path = request.url.path
        for prefix, resource in prefix_to_resource.items():
            if path.startswith(prefix):
                return resource
        # Default to path if no prefix matches
        return path

    return mapper


def regex_resource_mapper(patterns: List[tuple[str, str]]) -> Callable[[Request], str]:
    """
    Create custom resource mapper based on regex pattern matching.

    Examples:
        import re
        mapper = regex_resource_mapper([
            (r"^/api/users(/.*)?$", "users"),
            (r"^/api/projects/[^/]+/tasks(/.*)?$", "tasks"),
            (r"^/api/admin(/.*)?$", "admin"),
        ])

        app.add_middleware(
            CasbinAuthMiddleware,
            rbac_manager=rbac_manager,
            resource_mapper=mapper,
        )

    Args:
        patterns: List of (regex_pattern, resource_name) tuples

    Returns:
        Resource mapper function
    """
    import re

    compiled_patterns = [(re.compile(pattern), resource) for pattern, resource in patterns]

    def mapper(request: Request) -> str:
        path = request.url.path
        for pattern, resource in compiled_patterns:
            if pattern.match(path):
                return resource
        # Default to path if no pattern matches
        return path

    return mapper
