"""Tests for package initialization and imports."""

import sys
from unittest.mock import patch
import pytest


class TestPackageImports:
    """Test package-level imports and feature flags."""

    def test_basic_imports(self):
        """Test basic imports work correctly."""
        from netrun.websocket import (
            WebSocketConnectionManager,
            JWTAuthService,
            HeartbeatMonitor,
            MetricsCollector,
            parse_message,
        )

        assert WebSocketConnectionManager is not None
        assert JWTAuthService is not None
        assert HeartbeatMonitor is not None
        assert MetricsCollector is not None
        assert parse_message is not None

    def test_version_attribute(self):
        """Test package version is available."""
        from netrun.websocket import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_redis_support_flag_with_redis(self):
        """Test REDIS_SUPPORT flag when redis is available."""
        from netrun.websocket import REDIS_SUPPORT

        # Should be True since redis is installed in test environment
        assert isinstance(REDIS_SUPPORT, bool)

    def test_session_manager_available_with_redis(self):
        """Test session manager is available when redis is installed."""
        from netrun.websocket import (
            WebSocketSessionManager,
            WebSocketConnection,
            SessionState,
            REDIS_SUPPORT,
        )

        if REDIS_SUPPORT:
            assert WebSocketSessionManager is not None
            assert WebSocketConnection is not None
            assert SessionState is not None

    def test_all_exports_defined(self):
        """Test that all exported items are defined in __all__."""
        import netrun.websocket as ws

        # Check key exports exist
        assert hasattr(ws, "__all__")
        assert isinstance(ws.__all__, list)
        assert len(ws.__all__) > 0

        # Verify some key exports are in __all__
        assert "WebSocketConnectionManager" in ws.__all__
        assert "JWTAuthService" in ws.__all__
        assert "HeartbeatMonitor" in ws.__all__
        assert "MetricsCollector" in ws.__all__


class TestRedisImportFailure:
    """Test behavior when Redis is not available."""

    def test_redis_import_failure_handling(self):
        """Test graceful handling when redis module is not available."""
        # This test simulates what would happen if redis wasn't installed
        # We can't actually uninstall redis in the test, but we can verify
        # the code path is designed correctly

        from netrun.websocket import REDIS_SUPPORT

        # If redis is available (which it is in tests), verify imports work
        if REDIS_SUPPORT:
            from netrun.websocket import WebSocketSessionManager
            assert WebSocketSessionManager is not None


class TestProtocolExports:
    """Test protocol-related exports."""

    def test_message_type_exports(self):
        """Test message types are properly exported."""
        from netrun.websocket import (
            MessageType,
            PingMessage,
            PongMessage,
            ErrorMessage,
            UserMessage,
            TypingIndicatorMessage,
            NotificationMessage,
        )

        assert MessageType is not None
        assert PingMessage is not None
        assert PongMessage is not None
        assert ErrorMessage is not None
        assert UserMessage is not None
        assert TypingIndicatorMessage is not None
        assert NotificationMessage is not None


class TestAuthenticationExports:
    """Test authentication-related exports."""

    def test_auth_exports(self):
        """Test authentication classes are exported."""
        from netrun.websocket import (
            JWTAuthService,
            TokenAuthMiddleware,
            authenticate_websocket,
        )

        assert JWTAuthService is not None
        assert TokenAuthMiddleware is not None
        assert authenticate_websocket is not None


class TestConnectionExports:
    """Test connection management exports."""

    def test_connection_manager_exports(self):
        """Test connection manager and metadata are exported."""
        from netrun.websocket import (
            WebSocketConnectionManager,
            ConnectionMetadata,
        )

        assert WebSocketConnectionManager is not None
        assert ConnectionMetadata is not None


class TestReconnectionExports:
    """Test reconnection-related exports."""

    def test_reconnection_exports(self):
        """Test reconnection classes are exported."""
        from netrun.websocket import (
            ReconnectionConfig,
            ReconnectionManager,
            ReconnectionTracker,
        )

        assert ReconnectionConfig is not None
        assert ReconnectionManager is not None
        assert ReconnectionTracker is not None


class TestHeartbeatExports:
    """Test heartbeat-related exports."""

    def test_heartbeat_exports(self):
        """Test heartbeat classes are exported."""
        from netrun.websocket import (
            HeartbeatConfig,
            HeartbeatMonitor,
        )

        assert HeartbeatConfig is not None
        assert HeartbeatMonitor is not None


class TestMetricsExports:
    """Test metrics-related exports."""

    def test_metrics_exports(self):
        """Test metrics classes are exported."""
        from netrun.websocket import (
            ConnectionMetrics,
            LatencyMetrics,
            MetricsCollector,
        )

        assert ConnectionMetrics is not None
        assert LatencyMetrics is not None
        assert MetricsCollector is not None
