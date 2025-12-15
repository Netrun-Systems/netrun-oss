"""Tests for FastAPI middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from netrun_logging import configure_logging
from netrun_logging.middleware import add_logging_middleware


class TestLoggingMiddleware:
    """Tests for FastAPI logging middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with middleware."""
        configure_logging(app_name="test-app")

        test_app = FastAPI()
        add_logging_middleware(test_app)

        @test_app.get("/")
        async def root():
            return {"message": "Hello"}

        @test_app.get("/error")
        async def error():
            raise ValueError("Test error")

        return test_app

    def test_middleware_adds_correlation_id(self, app):
        """Test that middleware adds correlation ID to response headers."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

    def test_middleware_correlation_id_is_uuid(self, app):
        """Test that correlation ID is valid UUID format."""
        client = TestClient(app)
        response = client.get("/")

        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None

        # UUID format: 8-4-4-4-12
        parts = correlation_id.split("-")
        assert len(parts) == 5

    def test_middleware_accepts_existing_correlation_id(self, app):
        """Test that middleware uses provided correlation ID."""
        client = TestClient(app)
        custom_id = "custom-correlation-id-123"

        response = client.get("/", headers={"X-Correlation-ID": custom_id})

        assert response.headers.get("X-Correlation-ID") == custom_id

    def test_middleware_logs_request_info(self, app, caplog):
        """Test that middleware logs request information."""
        client = TestClient(app)

        with caplog.at_level("INFO"):
            response = client.get("/")

        # Check that request was logged (actual message format from middleware)
        assert any("Request:" in record.message for record in caplog.records)
        assert any("Response:" in record.message for record in caplog.records)
