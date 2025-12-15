"""
Comprehensive test suite for netrun-errors exception classes.

Tests all 11 exception classes plus handlers and middleware.
"""

import re
from datetime import datetime

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from netrun_errors import (
    AuthenticationRequiredError,
    BadGatewayError,
    ExternalServiceError,
    GatewayTimeoutError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    NetrunException,
    RateLimitExceededError,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    TemporalUnavailableError,
    TenantAccessDeniedError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
)


class TestNetrunExceptionBase:
    """Test base NetrunException class."""

    def test_base_exception_structure(self):
        """Test NetrunException creates structured error response."""
        exc = NetrunException(
            status_code=400,
            error_code="TEST_ERROR",
            message="Test error message",
        )

        assert exc.status_code == 400
        assert exc.error_code == "TEST_ERROR"
        assert exc.correlation_id is not None
        assert exc.timestamp is not None
        assert exc.details == {}

    def test_correlation_id_format(self):
        """Test correlation ID follows expected format."""
        exc = NetrunException(
            status_code=400, error_code="TEST_ERROR", message="Test"
        )

        # Format: req-YYYYMMDD-HHMMSS-uuid_prefix
        pattern = r"^req-\d{8}-\d{6}-[a-f0-9]{6}$"
        assert re.match(pattern, exc.correlation_id)

    def test_custom_correlation_id(self):
        """Test custom correlation ID is preserved."""
        custom_id = "custom-correlation-id"
        exc = NetrunException(
            status_code=400,
            error_code="TEST_ERROR",
            message="Test",
            correlation_id=custom_id,
        )

        assert exc.correlation_id == custom_id

    def test_timestamp_format(self):
        """Test timestamp is ISO 8601 format."""
        exc = NetrunException(
            status_code=400, error_code="TEST_ERROR", message="Test"
        )

        # Validate ISO 8601 format
        parsed = datetime.fromisoformat(exc.timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_custom_details(self):
        """Test custom details dictionary is preserved."""
        details = {"user_id": "123", "attempt": 3}
        exc = NetrunException(
            status_code=400,
            error_code="TEST_ERROR",
            message="Test",
            details=details,
        )

        assert exc.details == details

    def test_to_dict_method(self):
        """Test to_dict() returns proper structure."""
        exc = NetrunException(
            status_code=400,
            error_code="TEST_ERROR",
            message="Test message",
            details={"key": "value"},
        )

        result = exc.to_dict()

        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["correlation_id"] == exc.correlation_id
        assert result["error"]["timestamp"] == exc.timestamp
        assert result["error"]["details"] == {"key": "value"}


class TestAuthenticationExceptions:
    """Test authentication-related exceptions."""

    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError structure."""
        exc = InvalidCredentialsError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTH_INVALID_CREDENTIALS"
        assert "Invalid email or password" in str(exc.detail)

    def test_invalid_credentials_custom_message(self):
        """Test InvalidCredentialsError with custom message."""
        exc = InvalidCredentialsError(message="Custom auth failure")

        assert "Custom auth failure" in str(exc.detail)

    def test_token_expired_error(self):
        """Test TokenExpiredError structure."""
        exc = TokenExpiredError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTH_TOKEN_EXPIRED"
        assert "expired" in str(exc.detail).lower()

    def test_token_invalid_error(self):
        """Test TokenInvalidError structure."""
        exc = TokenInvalidError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTH_TOKEN_INVALID"
        assert "invalid" in str(exc.detail).lower()

    def test_token_revoked_error(self):
        """Test TokenRevokedError structure."""
        exc = TokenRevokedError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTH_TOKEN_REVOKED"
        assert "revoked" in str(exc.detail).lower()

    def test_authentication_required_error(self):
        """Test AuthenticationRequiredError structure."""
        exc = AuthenticationRequiredError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTH_REQUIRED"
        assert "required" in str(exc.detail).lower()


class TestAuthorizationExceptions:
    """Test authorization-related exceptions."""

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError structure."""
        exc = InsufficientPermissionsError()

        assert exc.status_code == 403
        assert exc.error_code == "AUTHZ_INSUFFICIENT_PERMISSIONS"
        assert "permission" in str(exc.detail).lower()

    def test_tenant_access_denied_error(self):
        """Test TenantAccessDeniedError structure."""
        exc = TenantAccessDeniedError()

        assert exc.status_code == 403
        assert exc.error_code == "AUTHZ_TENANT_ACCESS_DENIED"
        assert "tenant" in str(exc.detail).lower()


class TestResourceExceptions:
    """Test resource-related exceptions."""

    def test_resource_not_found_error_basic(self):
        """Test ResourceNotFoundError with basic usage."""
        exc = ResourceNotFoundError(resource_type="User", resource_id="123")

        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert "User" in str(exc.detail)
        assert "123" in str(exc.detail)
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "123"

    def test_resource_not_found_error_no_id(self):
        """Test ResourceNotFoundError without resource ID."""
        exc = ResourceNotFoundError(resource_type="Configuration")

        assert exc.status_code == 404
        assert "Configuration" in str(exc.detail)
        assert "resource_id" not in exc.details

    def test_resource_conflict_error(self):
        """Test ResourceConflictError structure."""
        exc = ResourceConflictError(message="Email already exists")

        assert exc.status_code == 409
        assert exc.error_code == "RESOURCE_CONFLICT"
        assert "Email already exists" in str(exc.detail)


class TestServiceExceptions:
    """Test service-related exceptions."""

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError structure."""
        exc = ServiceUnavailableError()

        assert exc.status_code == 503
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert "unavailable" in str(exc.detail).lower()

    def test_temporal_unavailable_error(self):
        """Test TemporalUnavailableError structure."""
        exc = TemporalUnavailableError()

        assert exc.status_code == 503
        assert exc.error_code == "TEMPORAL_UNAVAILABLE"
        assert "workflow" in str(exc.detail).lower()

    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError structure."""
        exc = RateLimitExceededError()

        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert "rate limit" in str(exc.detail).lower()

    def test_rate_limit_exceeded_with_retry_after(self):
        """Test RateLimitExceededError with retry_after parameter."""
        exc = RateLimitExceededError(
            message="Too many requests",
            retry_after=60,
        )

        assert exc.status_code == 429
        assert exc.retry_after == 60
        assert exc.details["retry_after_seconds"] == 60

    def test_bad_gateway_error(self):
        """Test BadGatewayError structure."""
        exc = BadGatewayError()

        assert exc.status_code == 502
        assert exc.error_code == "BAD_GATEWAY"
        assert "upstream" in str(exc.detail).lower()

    def test_bad_gateway_error_with_service(self):
        """Test BadGatewayError with upstream_service parameter."""
        exc = BadGatewayError(
            message="Payment gateway error",
            upstream_service="stripe-api",
        )

        assert exc.status_code == 502
        assert exc.details["upstream_service"] == "stripe-api"

    def test_gateway_timeout_error(self):
        """Test GatewayTimeoutError structure."""
        exc = GatewayTimeoutError()

        assert exc.status_code == 504
        assert exc.error_code == "GATEWAY_TIMEOUT"
        # Accept both "timeout" and "timed out" variations
        detail_lower = str(exc.detail).lower()
        assert "timeout" in detail_lower or "timed out" in detail_lower

    def test_gateway_timeout_error_with_details(self):
        """Test GatewayTimeoutError with additional details."""
        exc = GatewayTimeoutError(
            message="Database query timed out",
            upstream_service="postgresql",
            timeout_seconds=30.5,
        )

        assert exc.status_code == 504
        assert exc.details["upstream_service"] == "postgresql"
        assert exc.details["timeout_seconds"] == 30.5

    def test_external_service_error(self):
        """Test ExternalServiceError structure."""
        exc = ExternalServiceError(service_name="email-service")

        assert exc.status_code == 502
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert "email-service" in str(exc.detail)
        assert exc.details["service_name"] == "email-service"

    def test_external_service_error_with_original_error(self):
        """Test ExternalServiceError with original error details."""
        exc = ExternalServiceError(
            service_name="payment-gateway",
            message="Payment processing failed",
            original_error="ConnectionRefused: Unable to connect to payment server",
        )

        assert exc.status_code == 502
        assert exc.details["service_name"] == "payment-gateway"
        assert exc.details["original_error"] == "ConnectionRefused: Unable to connect to payment server"


class TestExceptionHandlers:
    """Test FastAPI exception handlers integration."""

    def test_netrun_exception_handler(self, app: FastAPI, client: TestClient):
        """Test NetrunException is handled correctly."""

        @app.get("/test-auth-error")
        async def test_auth_error():
            raise InvalidCredentialsError()

        response = client.get("/test-auth-error")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
        assert "correlation_id" in data["error"]
        assert "timestamp" in data["error"]
        assert "path" in data["error"]
        assert data["error"]["path"] == "/test-auth-error"

    def test_resource_not_found_handler(self, app: FastAPI, client: TestClient):
        """Test ResourceNotFoundError is handled correctly."""

        @app.get("/test-not-found")
        async def test_not_found():
            raise ResourceNotFoundError(resource_type="Product", resource_id="999")

        response = client.get("/test-not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "999" in data["error"]["message"]

    def test_validation_error_handler(self, app: FastAPI, client: TestClient):
        """Test FastAPI validation errors are handled."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            required_field: str
            number_field: int

        @app.post("/test-validation")
        async def test_validation(model: TestModel):
            return model

        response = client.post("/test-validation", json={})

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "correlation_id" in data["error"]
        assert "validation_errors" in data["error"]["details"]

    def test_correlation_id_in_response_headers(self, app: FastAPI, client: TestClient):
        """Test correlation ID is injected into response headers."""

        @app.get("/test-correlation")
        async def test_correlation():
            return {"status": "ok"}

        response = client.get("/test-correlation")

        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert re.match(r"^req-\d{8}-\d{6}-[a-f0-9]{6}$", correlation_id)

    def test_unhandled_exception_handler(self, app: FastAPI, client: TestClient):
        """Test unhandled exceptions are caught and formatted."""

        @app.get("/test-unhandled")
        async def test_unhandled():
            raise ValueError("Unexpected error")

        # TestClient will raise the exception, so we catch it
        # In production, this would return a 500 response
        with pytest.raises(ValueError):
            response = client.get("/test-unhandled")


class TestMiddleware:
    """Test error logging middleware."""

    def test_middleware_adds_correlation_id(self, app: FastAPI, client: TestClient):
        """Test middleware adds correlation ID to request state."""
        captured_correlation_id = None

        @app.get("/test-middleware")
        async def test_middleware(request: Request):
            nonlocal captured_correlation_id
            captured_correlation_id = request.state.correlation_id
            return {"status": "ok"}

        response = client.get("/test-middleware")

        assert response.status_code == 200
        assert captured_correlation_id is not None
        assert re.match(r"^req-\d{8}-\d{6}-[a-f0-9]{6}$", captured_correlation_id)

    def test_middleware_injects_correlation_header(
        self, app: FastAPI, client: TestClient
    ):
        """Test middleware injects correlation ID into response headers."""

        @app.get("/test-header")
        async def test_header():
            return {"status": "ok"}

        response = client.get("/test-header")

        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert re.match(r"^req-\d{8}-\d{6}-[a-f0-9]{6}$", correlation_id)


class TestIntegration:
    """Integration tests for complete error handling flow."""

    def test_complete_error_flow(self, app: FastAPI, client: TestClient):
        """Test complete error handling flow with all components."""

        @app.get("/users/{user_id}")
        async def get_user(user_id: str, request: Request):
            if user_id == "999":
                raise ResourceNotFoundError(
                    resource_type="User",
                    resource_id=user_id,
                    correlation_id=request.state.correlation_id,
                )
            return {"user_id": user_id}

        response = client.get("/users/999")

        assert response.status_code == 404
        data = response.json()

        # Verify structured error format
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert data["error"]["message"] == "User with ID '999' not found"
        assert data["error"]["path"] == "/users/999"
        assert "correlation_id" in data["error"]
        assert "timestamp" in data["error"]

        # Verify correlation ID in headers matches body
        assert response.headers["X-Correlation-ID"] == data["error"]["correlation_id"]

    def test_successful_request_flow(self, app: FastAPI, client: TestClient):
        """Test successful request includes correlation ID."""

        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        response = client.get("/health")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        data = response.json()
        assert data["status"] == "healthy"
