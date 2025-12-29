"""
Netrun WebSocket Package
File: __init__.py
Netrun Systems - SDLC v2.3 Compliant

Production-grade WebSocket connection management with authentication,
session persistence, reconnection, heartbeat monitoring, and metrics.

Usage:
    from netrun.websocket import WebSocketConnectionManager, JWTAuthService

    # Initialize manager
    manager = WebSocketConnectionManager(max_connections_per_user=5)

    # Initialize auth service
    auth_service = JWTAuthService(secret_key="your-secret-key")

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(...)
    ):
        # Authenticate
        payload = await auth_service.validate_token(token)
        if not payload:
            await websocket.close(code=1008, reason="Authentication failed")
            return

        user_id = payload["user_id"]

        # Connect
        connection_id = await manager.connect(websocket, user_id)

        try:
            while True:
                data = await manager.receive_message(connection_id)
                if data is None:
                    break
                # Handle message
                await manager.send_to_user(user_id, {"echo": data})
        finally:
            await manager.disconnect(connection_id)
"""

from .auth import JWTAuthService, TokenAuthMiddleware, authenticate_websocket
from .connection_manager import ConnectionMetadata, WebSocketConnectionManager
from .heartbeat import HeartbeatConfig, HeartbeatMonitor
from .metrics import ConnectionMetrics, LatencyMetrics, MetricsCollector
from .protocol import (
    ConnectionInfo,
    ConnectionState,
    ErrorMessage,
    MessageType,
    NotificationMessage,
    PingMessage,
    PongMessage,
    PresenceUpdateMessage,
    TypingIndicatorMessage,
    UserMessage,
    WebSocketMessage,
    parse_message,
)
from .reconnection import ReconnectionConfig, ReconnectionManager, ReconnectionTracker

# Conditional imports
try:
    from .session_manager import (
        SessionState,
        WebSocketConnection,
        WebSocketSessionManager,
    )
    REDIS_SUPPORT = True
except ImportError:
    REDIS_SUPPORT = False
    WebSocketSessionManager = None
    WebSocketConnection = None
    SessionState = None

__version__ = "1.0.0"

__all__ = [
    # Connection Management
    "WebSocketConnectionManager",
    "ConnectionMetadata",
    # Protocol
    "MessageType",
    "ConnectionState",
    "WebSocketMessage",
    "PingMessage",
    "PongMessage",
    "ErrorMessage",
    "UserMessage",
    "TypingIndicatorMessage",
    "PresenceUpdateMessage",
    "NotificationMessage",
    "ConnectionInfo",
    "parse_message",
    # Authentication
    "JWTAuthService",
    "TokenAuthMiddleware",
    "authenticate_websocket",
    # Session Management (optional Redis)
    "WebSocketSessionManager",
    "WebSocketConnection",
    "SessionState",
    # Reconnection
    "ReconnectionConfig",
    "ReconnectionManager",
    "ReconnectionTracker",
    # Heartbeat
    "HeartbeatConfig",
    "HeartbeatMonitor",
    # Metrics
    "ConnectionMetrics",
    "LatencyMetrics",
    "MetricsCollector",
    # Metadata
    "__version__",
    "REDIS_SUPPORT",
]
