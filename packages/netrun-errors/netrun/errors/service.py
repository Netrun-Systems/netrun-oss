"""
Service-related exceptions for Netrun Systems.

Exceptions for service availability, external dependencies,
and system-level errors.
"""

from typing import Any, Dict, Optional

from fastapi import status

from .base import NetrunException


class ServiceUnavailableError(NetrunException):
    """
    Raised when service or dependency is temporarily unavailable.

    Common scenarios:
    - Database connection failures
    - External API timeouts
    - Maintenance mode
    - Circuit breaker open

    Status Code: 503 Service Unavailable
    Error Code: SERVICE_UNAVAILABLE
    """

    def __init__(
        self,
        message: str = "Service is temporarily unavailable. Please try again later.",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class TemporalUnavailableError(NetrunException):
    """
    Raised when Temporal workflow engine is unavailable.

    Specific to Netrun Systems' Temporal.io integration for
    long-running workflows and distributed transactions.

    Status Code: 503 Service Unavailable
    Error Code: TEMPORAL_UNAVAILABLE
    """

    def __init__(
        self,
        message: str = "Workflow engine is temporarily unavailable. Please try again later.",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="TEMPORAL_UNAVAILABLE",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class RateLimitExceededError(NetrunException):
    """
    Raised when rate limit is exceeded.

    Common scenarios:
    - API request quota exceeded
    - Too many login attempts
    - Bulk operation throttling

    Status Code: 429 Too Many Requests
    Error Code: RATE_LIMIT_EXCEEDED
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        details = details or {}
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )
        self.retry_after = retry_after


class BadGatewayError(NetrunException):
    """
    Raised when upstream service returns invalid response.

    Common scenarios:
    - Invalid response from upstream API
    - Proxy/load balancer errors
    - Malformed upstream responses

    Status Code: 502 Bad Gateway
    Error Code: BAD_GATEWAY
    """

    def __init__(
        self,
        message: str = "Upstream service returned an invalid response.",
        upstream_service: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        details = details or {}
        if upstream_service:
            details["upstream_service"] = upstream_service

        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="BAD_GATEWAY",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class GatewayTimeoutError(NetrunException):
    """
    Raised when upstream service times out.

    Common scenarios:
    - Upstream API request timeout
    - Database query timeout
    - External service not responding

    Status Code: 504 Gateway Timeout
    Error Code: GATEWAY_TIMEOUT
    """

    def __init__(
        self,
        message: str = "Upstream service timed out. Please try again.",
        upstream_service: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        details = details or {}
        if upstream_service:
            details["upstream_service"] = upstream_service
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds

        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="GATEWAY_TIMEOUT",
            message=message,
            details=details,
            correlation_id=correlation_id,
        )


class ExternalServiceError(NetrunException):
    """
    Raised when external service integration fails.

    Generic error for external API failures that don't fit
    specific categories (BadGateway, GatewayTimeout, etc.)

    Status Code: 502 Bad Gateway
    Error Code: EXTERNAL_SERVICE_ERROR
    """

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        original_error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        details = details or {}
        details["service_name"] = service_name
        if original_error:
            details["original_error"] = original_error

        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            message=message or f"External service '{service_name}' is unavailable.",
            details=details,
            correlation_id=correlation_id,
        )
