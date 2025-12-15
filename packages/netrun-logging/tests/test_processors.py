"""Tests for structlog processors."""

import pytest
from netrun_logging.processors import (
    add_netrun_context,
    add_opentelemetry_trace,
    sanitize_sensitive_fields,
    add_log_context,
)


class TestAddNetrunContext:
    """Tests for add_netrun_context processor."""

    def test_adds_app_and_env_fields(self):
        """Test that processor adds app and env fields."""
        processor = add_netrun_context("test-app", "production")
        event_dict = {"event": "test_event"}

        result = processor(None, None, event_dict)

        assert result["app"] == "test-app"
        assert result["env"] == "production"

    def test_preserves_existing_fields(self):
        """Test that processor preserves existing fields."""
        processor = add_netrun_context("my-app", "dev")
        event_dict = {"event": "test", "user_id": "12345"}

        result = processor(None, None, event_dict)

        assert result["event"] == "test"
        assert result["user_id"] == "12345"
        assert result["app"] == "my-app"
        assert result["env"] == "dev"


class TestSanitizeSensitiveFields:
    """Tests for sanitize_sensitive_fields processor."""

    def test_redacts_password_field(self):
        """Test that password fields are redacted."""
        event_dict = {"event": "login", "password": "secret123"}

        result = sanitize_sensitive_fields(None, None, event_dict)

        assert result["password"] == "[REDACTED]"
        assert result["event"] == "login"

    def test_redacts_api_key_field(self):
        """Test that API key fields are redacted."""
        event_dict = {"event": "api_call", "api_key": "abc123", "apikey": "def456"}

        result = sanitize_sensitive_fields(None, None, event_dict)

        assert result["api_key"] == "[REDACTED]"
        assert result["apikey"] == "[REDACTED]"

    def test_redacts_token_fields(self):
        """Test that token fields are redacted."""
        event_dict = {
            "event": "auth",
            "access_token": "token123",
            "refresh_token": "token456",
        }

        result = sanitize_sensitive_fields(None, None, event_dict)

        assert result["access_token"] == "[REDACTED]"
        assert result["refresh_token"] == "[REDACTED]"

    def test_redacts_authorization_header(self):
        """Test that authorization headers are redacted."""
        event_dict = {"event": "request", "authorization": "Bearer token123"}

        result = sanitize_sensitive_fields(None, None, event_dict)

        assert result["authorization"] == "[REDACTED]"

    def test_case_insensitive_matching(self):
        """Test that field matching is case-insensitive."""
        event_dict = {
            "event": "test",
            "PASSWORD": "secret",
            "Api_Key": "key123",
            "SECRET_VALUE": "secret",
        }

        result = sanitize_sensitive_fields(None, None, event_dict)

        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Api_Key"] == "[REDACTED]"
        assert result["SECRET_VALUE"] == "[REDACTED]"

    def test_preserves_non_sensitive_fields(self):
        """Test that non-sensitive fields are preserved."""
        event_dict = {
            "event": "test",
            "user_id": "12345",
            "email": "user@example.com",
            "status": "success",
        }

        result = sanitize_sensitive_fields(None, None, event_dict)

        assert result["user_id"] == "12345"
        assert result["email"] == "user@example.com"
        assert result["status"] == "success"


class TestAddLogContext:
    """Tests for add_log_context processor."""

    def test_adds_user_id_from_context(self):
        """Test that user_id is added from LogContext."""
        from netrun_logging.context import set_context, clear_context

        clear_context()
        set_context(user_id="user123")

        event_dict = {"event": "test"}
        result = add_log_context(None, None, event_dict)

        assert result["user_id"] == "user123"
        clear_context()

    def test_adds_tenant_id_from_context(self):
        """Test that tenant_id is added from LogContext."""
        from netrun_logging.context import set_context, clear_context

        clear_context()
        set_context(tenant_id="tenant456")

        event_dict = {"event": "test"}
        result = add_log_context(None, None, event_dict)

        assert result["tenant_id"] == "tenant456"
        clear_context()

    def test_adds_version_from_context(self):
        """Test that version is added from LogContext."""
        from netrun_logging.context import set_context, clear_context

        clear_context()
        set_context(version="1.2.3")

        event_dict = {"event": "test"}
        result = add_log_context(None, None, event_dict)

        assert result["version"] == "1.2.3"
        clear_context()

    def test_adds_extra_fields_from_context(self):
        """Test that extra fields are added from LogContext."""
        from netrun_logging.context import set_context, clear_context

        clear_context()
        set_context(custom_field="value123", another_field="value456")

        event_dict = {"event": "test"}
        result = add_log_context(None, None, event_dict)

        assert result["custom_field"] == "value123"
        assert result["another_field"] == "value456"
        clear_context()

    def test_handles_empty_context_gracefully(self):
        """Test that processor handles empty context."""
        from netrun_logging.context import clear_context

        clear_context()

        event_dict = {"event": "test"}
        result = add_log_context(None, None, event_dict)

        assert result["event"] == "test"
        # Should not add any context fields if context is empty


class TestAddOpenTelemetryTrace:
    """Tests for add_opentelemetry_trace processor."""

    def test_handles_missing_opentelemetry_gracefully(self):
        """Test that processor handles missing OpenTelemetry gracefully."""
        event_dict = {"event": "test"}

        # Should not raise an exception even if OpenTelemetry is not installed
        result = add_opentelemetry_trace(None, None, event_dict)

        assert result["event"] == "test"
        # May or may not have trace fields depending on whether OTel is installed

    def test_preserves_existing_fields(self):
        """Test that processor preserves existing fields."""
        event_dict = {"event": "test", "user_id": "12345"}

        result = add_opentelemetry_trace(None, None, event_dict)

        assert result["event"] == "test"
        assert result["user_id"] == "12345"
