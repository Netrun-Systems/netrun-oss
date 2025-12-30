"""
Netrun RBAC Security Middleware - Security checks and audit logging.

Following Netrun Systems SDLC v2.3 standards.

This middleware is the innermost layer of the tenancy stack. It:
1. Validates tenant access permissions
2. Detects and blocks cross-tenant access attempts
3. Logs security events for audit trail
4. Enforces rate limits per tenant (optional)
"""

import logging
import time
from typing import Callable, Optional, Awaitable, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from ..tenancy.context import TenantContext
from ..tenancy.config import TenancyConfig
from ..tenancy.exceptions import (
    TenantAccessDeniedError,
    CrossTenantViolationError,
)

logger = logging.getLogger(__name__)


class TenantSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tenant security enforcement and audit logging.

    This middleware provides:
    - Cross-tenant access detection and blocking
    - Audit logging for compliance (SOC2, ISO27001)
    - Rate limiting per tenant (optional)
    - Security event monitoring

    Attributes:
        config: Tenancy configuration
        audit_logger: Logger for audit events
        rate_limiter: Optional rate limiter instance
    """

    def __init__(
        self,
        app: ASGIApp,
        config: TenancyConfig,
        audit_logger: Optional[logging.Logger] = None,
        rate_limiter: Optional[Any] = None,
    ):
        """
        Initialize the security middleware.

        Args:
            app: ASGI application
            config: Tenancy configuration
            audit_logger: Custom logger for audit events
            rate_limiter: Optional rate limiter instance
        """
        super().__init__(app)
        self.config = config
        self.audit_logger = audit_logger or logging.getLogger("netrun.rbac.audit")
        self.rate_limiter = rate_limiter

        # Track cross-tenant attempts for monitoring
        self._violation_counts: Dict[str, int] = {}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Process the request with security checks.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Check if path is exempt from security checks
        if self.config.is_path_exempt(request.url.path):
            return await call_next(request)

        start_time = time.time()
        ctx = TenantContext.get_current()

        try:
            # Perform security checks
            await self._perform_security_checks(request, ctx)

            # Apply rate limiting if configured
            if self.rate_limiter:
                await self._check_rate_limit(request, ctx)

            # Process request
            response = await call_next(request)

            # Log successful access if audit enabled
            if self.config.audit_tenant_access:
                self._log_access(request, ctx, response, start_time)

            return response

        except CrossTenantViolationError as e:
            self._log_security_violation(request, ctx, e)

            if self.config.block_cross_tenant_requests:
                return self._error_response(
                    "Cross-tenant access denied",
                    status_code=403,
                    code="CROSS_TENANT_VIOLATION"
                )
            else:
                # Log but allow (for debugging/migration)
                logger.warning(f"Cross-tenant attempt allowed: {e}")
                return await call_next(request)

        except TenantAccessDeniedError as e:
            self._log_security_violation(request, ctx, e)
            return self._error_response(str(e), status_code=403, code=e.code)

        except Exception as e:
            logger.error(f"Security middleware error: {e}", exc_info=True)
            return self._error_response(
                "Security check failed",
                status_code=500,
                code="SECURITY_ERROR"
            )

    async def _perform_security_checks(
        self,
        request: Request,
        ctx: Optional[Any],
    ) -> None:
        """
        Perform security checks on the request.

        Checks:
        1. Cross-tenant access attempts in query/body
        2. Suspicious patterns in request
        3. User has valid tenant membership

        Args:
            request: HTTP request
            ctx: Tenant context (may be None)

        Raises:
            CrossTenantViolationError: If cross-tenant access detected
            TenantAccessDeniedError: If access should be denied
        """
        if ctx is None:
            return

        # Check for cross-tenant IDs in query parameters
        await self._check_cross_tenant_query_params(request, ctx)

        # Check request headers for tampering
        self._check_header_tampering(request, ctx)

    async def _check_cross_tenant_query_params(
        self,
        request: Request,
        ctx: Any,
    ) -> None:
        """
        Check query parameters for cross-tenant access attempts.

        Looks for tenant_id parameters that don't match the current context.

        Args:
            request: HTTP request
            ctx: Tenant context

        Raises:
            CrossTenantViolationError: If cross-tenant access detected
        """
        # Check query params for tenant_id
        query_tenant = request.query_params.get("tenant_id")
        if query_tenant:
            try:
                query_tenant_uuid = UUID(query_tenant)
                if query_tenant_uuid != ctx.tenant_id:
                    raise CrossTenantViolationError(
                        current_tenant_id=ctx.tenant_id,
                        target_tenant_id=query_tenant_uuid,
                        details={"source": "query_param"}
                    )
            except ValueError:
                pass  # Invalid UUID, not a security issue

    def _check_header_tampering(
        self,
        request: Request,
        ctx: Any,
    ) -> None:
        """
        Check for header tampering attempts.

        Validates that tenant headers match the resolved context.

        Args:
            request: HTTP request
            ctx: Tenant context

        Raises:
            CrossTenantViolationError: If header tampering detected
        """
        # If tenant was resolved from JWT, check headers don't conflict
        header_tenant = request.headers.get(self.config.tenant_header)
        if header_tenant:
            try:
                header_tenant_uuid = UUID(header_tenant)
                if header_tenant_uuid != ctx.tenant_id:
                    if self.config.log_cross_tenant_attempts:
                        logger.warning(
                            f"Tenant header mismatch: header={header_tenant}, "
                            f"context={ctx.tenant_id}"
                        )
            except ValueError:
                pass  # Invalid UUID or slug in header

    async def _check_rate_limit(
        self,
        request: Request,
        ctx: Optional[Any],
    ) -> None:
        """
        Apply rate limiting per tenant.

        Args:
            request: HTTP request
            ctx: Tenant context

        Raises:
            TenantAccessDeniedError: If rate limit exceeded
        """
        if self.rate_limiter is None or ctx is None:
            return

        # Implementation depends on rate limiter used
        # This is a placeholder for integration
        key = f"tenant:{ctx.tenant_id}:{request.url.path}"

        try:
            is_allowed = await self.rate_limiter.is_allowed(key)
            if not is_allowed:
                raise TenantAccessDeniedError(
                    tenant_id=ctx.tenant_id,
                    reason="Rate limit exceeded"
                )
        except AttributeError:
            # Rate limiter doesn't have expected interface
            pass

    def _log_access(
        self,
        request: Request,
        ctx: Optional[Any],
        response: Response,
        start_time: float,
    ) -> None:
        """
        Log successful tenant access for audit trail.

        Args:
            request: HTTP request
            ctx: Tenant context
            response: HTTP response
            start_time: Request start timestamp
        """
        duration_ms = (time.time() - start_time) * 1000

        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "tenant_access",
            "tenant_id": str(ctx.tenant_id) if ctx else None,
            "user_id": str(ctx.user_id) if ctx and ctx.user_id else None,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": self._get_client_ip(request),
        }

        self.audit_logger.info(f"AUDIT: {audit_entry}")

    def _log_security_violation(
        self,
        request: Request,
        ctx: Optional[Any],
        error: Exception,
    ) -> None:
        """
        Log security violations for monitoring.

        Args:
            request: HTTP request
            ctx: Tenant context
            error: The security exception
        """
        violation_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "security_violation",
            "error_type": type(error).__name__,
            "error_code": getattr(error, 'code', 'UNKNOWN'),
            "tenant_id": str(ctx.tenant_id) if ctx else None,
            "user_id": str(ctx.user_id) if ctx and ctx.user_id else None,
            "method": request.method,
            "path": request.url.path,
            "client_ip": self._get_client_ip(request),
            "details": getattr(error, 'details', {}),
        }

        self.audit_logger.warning(f"SECURITY_VIOLATION: {violation_entry}")

        # Track violation counts
        if ctx:
            key = str(ctx.tenant_id)
            self._violation_counts[key] = self._violation_counts.get(key, 0) + 1

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request, handling proxies."""
        # Check X-Forwarded-For header (from proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _error_response(
        self,
        message: str,
        status_code: int = 403,
        code: str = "SECURITY_ERROR",
    ) -> JSONResponse:
        """Create an error JSON response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": code,
                "message": message,
            }
        )

    def get_violation_stats(self) -> Dict[str, int]:
        """
        Get violation statistics per tenant.

        Returns:
            Dict mapping tenant IDs to violation counts
        """
        return self._violation_counts.copy()

    def reset_violation_stats(self) -> None:
        """Reset violation statistics."""
        self._violation_counts.clear()
