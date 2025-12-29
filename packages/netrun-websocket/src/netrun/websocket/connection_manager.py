"""
WebSocket Connection Manager
File: connection_manager.py
Netrun Systems - SDLC v2.3 Compliant

Production-grade WebSocket connection pool management with lifecycle handling,
connection limits, and broadcasting capabilities.

Features:
- Connection pool management (per-user and global)
- Connection lifecycle (connect, disconnect)
- Broadcast and targeted messaging
- Max connections per user (configurable, default: 5)
- Connection metadata tracking
- Automatic cleanup of stale connections
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .protocol import ConnectionState, MessageType, WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionMetadata:
    """
    WebSocket connection metadata.

    Tracks connection state, activity, and metrics for monitoring
    and management purposes.
    """

    def __init__(
        self,
        connection_id: str,
        user_id: str,
        websocket: WebSocket,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: str = "/ws",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize connection metadata."""
        self.connection_id = connection_id
        self.user_id = user_id
        self.session_id = session_id
        self.websocket = websocket
        self.state = ConnectionState.CONNECTED
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.last_ping = datetime.now(timezone.utc)
        self.message_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.endpoint = endpoint
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "endpoint": self.endpoint,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "message_count": self.message_count,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata
        }


class WebSocketConnectionManager:
    """
    Production-grade WebSocket connection manager.

    Manages connection pool, lifecycle, and message broadcasting.
    Thread-safe with asyncio locks for concurrent access.

    Usage:
        manager = WebSocketConnectionManager(max_connections_per_user=5)
        connection_id = await manager.connect(websocket, user_id, session_id)
        await manager.send_message(connection_id, {"type": "notification", "data": {...}})
        await manager.disconnect(connection_id)
    """

    def __init__(
        self,
        max_connections_per_user: int = 5,
        heartbeat_interval: int = 30,
        connection_timeout: int = 300
    ):
        """
        Initialize WebSocket connection manager.

        Args:
            max_connections_per_user: Maximum connections per user (default: 5)
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
            connection_timeout: Idle timeout in seconds (default: 300)
        """
        # Connection pools
        self.connections: Dict[str, ConnectionMetadata] = {}  # connection_id → metadata
        self.user_connections: Dict[str, Set[str]] = {}  # user_id → set(connection_ids)
        self.session_connections: Dict[str, str] = {}  # session_id → connection_id

        # Configuration
        self.max_connections_per_user = max_connections_per_user
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout

        # Metrics
        self.total_connections = 0
        self.total_disconnections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.peak_connections = 0

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        logger.info("WebSocket Connection Manager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        session_id: Optional[str] = None,
        endpoint: str = "/ws",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Connect a new WebSocket.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: User identifier
            session_id: Optional session identifier
            endpoint: WebSocket endpoint path
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional connection metadata

        Returns:
            str: Connection ID

        Raises:
            ValueError: If max connections per user exceeded
        """
        async with self._lock:
            # Check connection limit
            if self._get_user_connection_count(user_id) >= self.max_connections_per_user:
                raise ValueError(
                    f"Maximum {self.max_connections_per_user} connections per user exceeded"
                )

            # Accept WebSocket connection
            await websocket.accept()

            # Generate connection ID
            connection_id = str(uuid.uuid4())

            # Create connection metadata
            conn_metadata = ConnectionMetadata(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                metadata=metadata
            )

            # Register connection
            self.connections[connection_id] = conn_metadata

            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

            if session_id:
                self.session_connections[session_id] = connection_id

            # Update metrics
            self.total_connections += 1
            current_count = len(self.connections)
            if current_count > self.peak_connections:
                self.peak_connections = current_count

            logger.info(
                f"WebSocket connected: {connection_id[:8]} | "
                f"User: {user_id} | Session: {session_id or 'none'} | "
                f"Total: {current_count}"
            )

            return connection_id

    async def disconnect(
        self,
        connection_id: str,
        code: int = 1000,
        reason: str = "Normal closure"
    ):
        """
        Disconnect a WebSocket connection gracefully.

        Args:
            connection_id: Connection identifier
            code: WebSocket close code (default: 1000 = normal closure)
            reason: Disconnect reason
        """
        async with self._lock:
            metadata = self.connections.get(connection_id)
            if not metadata:
                logger.warning(f"Connection {connection_id[:8]} not found for disconnect")
                return

            try:
                # Update state
                metadata.state = ConnectionState.DISCONNECTING

                # Close WebSocket
                if metadata.websocket.client_state == WebSocketState.CONNECTED:
                    await metadata.websocket.close(code=code, reason=reason)

                # Remove from pools
                self._remove_connection(connection_id)

                # Update metrics
                self.total_disconnections += 1

                duration = (datetime.now(timezone.utc) - metadata.connected_at).total_seconds()
                logger.info(
                    f"WebSocket disconnected: {connection_id[:8]} | "
                    f"User: {metadata.user_id} | Reason: {reason} | "
                    f"Messages: {metadata.message_count} | Duration: {duration:.1f}s"
                )

            except Exception as e:
                logger.error(f"Error disconnecting {connection_id[:8]}: {e}")
                # Force cleanup
                self._remove_connection(connection_id)

    async def send_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
        binary: bool = False
    ) -> bool:
        """
        Send message to specific connection.

        Args:
            connection_id: Connection identifier
            message: Message data (JSON or binary)
            binary: Whether to send as binary data

        Returns:
            bool: True if sent successfully
        """
        metadata = self.connections.get(connection_id)
        if not metadata:
            logger.warning(f"Connection {connection_id[:8]} not found for send")
            return False

        if metadata.websocket.client_state != WebSocketState.CONNECTED:
            logger.warning(f"Connection {connection_id[:8]} not in connected state")
            return False

        try:
            if binary:
                data = message if isinstance(message, bytes) else str(message).encode()
                await metadata.websocket.send_bytes(data)
            else:
                await metadata.websocket.send_json(message)

            # Update metadata
            metadata.last_activity = datetime.now(timezone.utc)
            metadata.message_count += 1

            # Update metrics
            self.total_messages_sent += 1

            return True

        except Exception as e:
            logger.error(f"Error sending message to {connection_id[:8]}: {e}")
            await self.disconnect(connection_id, code=1011, reason="Send error")
            return False

    async def send_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
        binary: bool = False
    ) -> int:
        """
        Send message to all connections for a user.

        Args:
            user_id: User identifier
            message: Message data
            binary: Whether to send as binary

        Returns:
            int: Number of successful sends
        """
        connection_ids = self.user_connections.get(user_id, set())
        if not connection_ids:
            logger.warning(f"No connections found for user {user_id}")
            return 0

        success_count = 0
        for conn_id in list(connection_ids):  # Copy to avoid modification during iteration
            if await self.send_message(conn_id, message, binary):
                success_count += 1

        return success_count

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude_users: Optional[Set[str]] = None,
        binary: bool = False
    ) -> int:
        """
        Broadcast message to all connected users.

        Args:
            message: Message data
            exclude_users: Optional set of user IDs to exclude
            binary: Whether to send as binary

        Returns:
            int: Number of successful sends
        """
        exclude = exclude_users or set()
        success_count = 0

        for conn_id, metadata in list(self.connections.items()):
            if metadata.user_id not in exclude:
                if await self.send_message(conn_id, message, binary):
                    success_count += 1

        return success_count

    async def receive_message(self, connection_id: str) -> Optional[Any]:
        """
        Receive message from connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Message data (JSON or bytes) or None
        """
        metadata = self.connections.get(connection_id)
        if not metadata:
            return None

        try:
            # Try JSON first, fallback to text
            try:
                data = await metadata.websocket.receive_json()
            except Exception:
                data = await metadata.websocket.receive_text()

            # Update metadata
            metadata.last_activity = datetime.now(timezone.utc)
            metadata.message_count += 1
            self.total_messages_received += 1

            return data

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id[:8]}")
            await self.disconnect(connection_id, code=1000, reason="Client disconnected")
            return None
        except Exception as e:
            logger.error(f"Error receiving message from {connection_id[:8]}: {e}")
            await self.disconnect(connection_id, code=1011, reason="Receive error")
            return None

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information."""
        metadata = self.connections.get(connection_id)
        if not metadata:
            return None
        return metadata.to_dict()

    def get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all connections for a user."""
        connection_ids = self.user_connections.get(user_id, set())
        return [
            self.get_connection_info(conn_id)
            for conn_id in connection_ids
            if conn_id in self.connections
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        return {
            "active_connections": len(self.connections),
            "unique_users": len(self.user_connections),
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "peak_connections": self.peak_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "heartbeat_interval": self.heartbeat_interval,
            "max_connections_per_user": self.max_connections_per_user,
            "connection_timeout": self.connection_timeout
        }

    def _remove_connection(self, connection_id: str):
        """Remove connection from all pools."""
        metadata = self.connections.pop(connection_id, None)
        if not metadata:
            return

        # Remove from user connections
        if metadata.user_id in self.user_connections:
            self.user_connections[metadata.user_id].discard(connection_id)
            if not self.user_connections[metadata.user_id]:
                del self.user_connections[metadata.user_id]

        # Remove from session connections
        if metadata.session_id and metadata.session_id in self.session_connections:
            del self.session_connections[metadata.session_id]

    def _get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for user."""
        return len(self.user_connections.get(user_id, set()))


__all__ = ["ConnectionMetadata", "WebSocketConnectionManager"]
