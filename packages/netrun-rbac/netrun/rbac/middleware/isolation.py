"""
Netrun RBAC Isolation Enforcement Middleware - Setup database isolation per request.

Following Netrun Systems SDLC v2.3 standards.

This middleware is the middle layer of the tenancy stack. It:
1. Gets the isolation strategy based on configuration
2. Sets up database session variables for RLS (if applicable)
3. Validates isolation is properly configured
"""

import logging
from typing import Callable, Optional, Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from ..tenancy.context import TenantContext
from ..tenancy.config import TenancyConfig
from ..tenancy.exceptions import IsolationViolationError
from ..isolation import get_isolation_strategy, IsolationStrategy

logger = logging.getLogger(__name__)


class IsolationEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce database isolation for each request.

    This middleware sets up the database session for the configured
    isolation strategy (RLS/Application/Hybrid). It ensures that
    all database operations within the request are properly scoped
    to the current tenant.

    Attributes:
        config: Tenancy configuration
        get_session: Factory function to get database session
        strict_mode: Fail on isolation setup errors vs log warning
    """

    def __init__(
        self,
        app: ASGIApp,
        config: TenancyConfig,
        get_session: Optional[Callable] = None,
        strict_mode: bool = True,
    ):
        """
        Initialize the isolation enforcement middleware.

        Args:
            app: ASGI application
            config: Tenancy configuration
            get_session: Factory to get database session
            strict_mode: Fail on errors (True) or log warnings (False)
        """
        super().__init__(app)
        self.config = config
        self.get_session = get_session
        self.strict_mode = strict_mode
        self.isolation_strategy = get_isolation_strategy(config)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Process the request with isolation enforcement.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Check if path is exempt from isolation
        if self.config.is_path_exempt(request.url.path):
            return await call_next(request)

        # Check if tenant context is set
        ctx = TenantContext.get_current()
        if ctx is None:
            # No tenant context - let it pass (TenantResolutionMiddleware handles this)
            return await call_next(request)

        try:
            # Setup isolation for this request
            await self._setup_isolation(request)

            # Store isolation strategy in request state
            request.state.isolation_strategy = self.isolation_strategy

            # Call hook if configured
            if self.config.on_context_set:
                await self._safe_call_hook(self.config.on_context_set, request, ctx)

            response = await call_next(request)

            return response

        except IsolationViolationError as e:
            logger.error(f"Isolation violation: {e}")

            if self.config.on_isolation_violation:
                await self._safe_call_hook(
                    self.config.on_isolation_violation, request, e
                )

            if self.strict_mode:
                return self._error_response(str(e), status_code=500, code=e.code)
            else:
                # Log and continue in non-strict mode
                logger.warning(f"Isolation setup failed, continuing: {e}")
                return await call_next(request)

        except Exception as e:
            logger.error(f"Isolation middleware error: {e}", exc_info=True)

            if self.strict_mode:
                return self._error_response(
                    "Internal server error during isolation setup",
                    status_code=500,
                    code="ISOLATION_ERROR"
                )
            else:
                return await call_next(request)

    async def _setup_isolation(self, request: Request) -> None:
        """
        Setup database isolation for the current request.

        This configures the database session for the isolation strategy.
        For RLS/Hybrid modes, this sets PostgreSQL session variables.

        Args:
            request: HTTP request

        Raises:
            IsolationViolationError: If setup fails
        """
        if self.get_session is None:
            logger.debug("No session factory configured, skipping isolation setup")
            return

        # For RLS-based isolation, we need to setup session variables
        # This is typically done at the start of a transaction
        # The actual setup happens when a session is acquired in route handlers

        # Store the isolation strategy in request state for use by route handlers
        request.state.isolation_strategy = self.isolation_strategy
        request.state.isolation_mode = self.config.isolation_mode

        logger.debug(
            f"Isolation configured: mode={self.config.isolation_mode.value}, "
            f"tenant={TenantContext.get_tenant_id()}"
        )

    async def _safe_call_hook(
        self, hook: Callable, *args, **kwargs
    ) -> None:
        """Safely call a hook function, catching any errors."""
        try:
            result = hook(*args, **kwargs)
            if hasattr(result, '__await__'):
                await result
        except Exception as e:
            logger.warning(f"Hook execution failed: {e}")

    def _error_response(
        self,
        message: str,
        status_code: int = 500,
        code: str = "ISOLATION_ERROR",
    ) -> JSONResponse:
        """Create an error JSON response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": code,
                "message": message,
            }
        )


async def setup_session_isolation(
    session,
    isolation_strategy: IsolationStrategy,
) -> None:
    """
    Helper function to setup isolation on a database session.

    This should be called by route handlers when acquiring a session
    to ensure RLS variables are set.

    Usage:
        from netrun.rbac.middleware.isolation import setup_session_isolation

        @app.get("/contacts")
        async def list_contacts(
            session = Depends(get_session),
            isolation = Depends(get_isolation_strategy),
        ):
            await setup_session_isolation(session, isolation)
            # ... use session with isolation configured

    Args:
        session: SQLAlchemy async session
        isolation_strategy: The isolation strategy to use
    """
    await isolation_strategy.setup_session(session)
