"""FastAPI middleware for tenant context extraction."""

import logging
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware to extract tenant/user context from requests.

    Extracts tenant_id and user_id from JWT tokens or headers and stores
    them in request.state for use by tenant-aware database sessions.

    Example:
        >>> from fastapi import FastAPI
        >>> from netrun_db_pool.middleware import TenantContextMiddleware
        >>>
        >>> app = FastAPI()
        >>>
        >>> def extract_tenant_id(request: Request) -> Optional[str]:
        ...     # Extract from JWT claims
        ...     token = request.headers.get("Authorization", "").replace("Bearer ", "")
        ...     claims = decode_jwt(token)
        ...     return claims.get("tenant_id")
        >>>
        >>> app.add_middleware(
        ...     TenantContextMiddleware,
        ...     tenant_id_extractor=extract_tenant_id,
        ... )
    """

    def __init__(
        self,
        app,
        tenant_id_extractor: Callable[[Request], Optional[str]],
        user_id_extractor: Optional[Callable[[Request], Optional[str]]] = None,
    ):
        """
        Initialize tenant context middleware.

        Args:
            app: FastAPI application
            tenant_id_extractor: Function to extract tenant_id from request
            user_id_extractor: Function to extract user_id from request (optional)
        """
        super().__init__(app)
        self.tenant_id_extractor = tenant_id_extractor
        self.user_id_extractor = user_id_extractor

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Extract tenant context and attach to request.state.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            Response: HTTP response
        """
        # Extract tenant_id
        try:
            tenant_id = self.tenant_id_extractor(request)
            request.state.tenant_id = tenant_id
            if tenant_id:
                logger.debug(f"Set tenant context: {tenant_id}")
        except Exception as e:
            logger.warning(f"Failed to extract tenant_id: {e}")
            request.state.tenant_id = None

        # Extract user_id (optional)
        if self.user_id_extractor:
            try:
                user_id = self.user_id_extractor(request)
                request.state.user_id = user_id
                if user_id:
                    logger.debug(f"Set user context: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to extract user_id: {e}")
                request.state.user_id = None
        else:
            request.state.user_id = None

        # Process request
        response = await call_next(request)
        return response
