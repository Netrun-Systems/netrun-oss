"""
WebSocket Session Manager with Redis Backend
File: session_manager.py
Netrun Systems - SDLC v2.3 Compliant

WebSocket session management with Redis backend for connection tracking,
reconnection handling, and cross-node session sharing.

Features:
- WebSocket connection lifecycle management
- Redis-backed persistence for cross-node coordination
- Automatic reconnection with state restoration
- Multi-tab support (same user, multiple connections)
- Heartbeat mechanism for stale connection detection
- Connection metadata tracking
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .protocol import ConnectionState

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = Any  # Type hint placeholder

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """WebSocket connection metadata for Redis persistence."""

    connection_id: str
    session_id: str
    user_id: str
    username: str
    connected_at: str
    last_heartbeat: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    tab_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """Persistent connection state for reconnection."""

    conversation_id: Optional[str] = None
    active_workspace_id: Optional[int] = None
    active_persona_id: Optional[int] = None
    voice_session_config: Optional[Dict[str, Any]] = None
    emotion_history: List[Dict[str, Any]] = field(default_factory=list)
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)


class WebSocketSessionManager:
    """
    Manage WebSocket connections with Redis persistence.

    Features:
    - Connection tracking with metadata
    - Graceful reconnection with state restoration
    - Multi-tab support for same user
    - Heartbeat mechanism (30-second interval)
    - Automatic cleanup of stale connections
    - Connection analytics

    Redis Key Structure:
    - ws:{connection_id} - Connection metadata
    - ws_user:{user_id} - Set of active connection IDs per user
    - ws_session:{session_id} - Set of connection IDs per session
    - ws_state:{connection_id} - Persistent connection state
    - ws_heartbeat:{connection_id} - Last heartbeat timestamp
    """

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        redis_url: Optional[str] = None,
        connection_ttl: int = 3600,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 90
    ):
        """
        Initialize WebSocket session manager.

        Args:
            redis_client: Optional existing Redis connection
            redis_url: Redis connection URL (if redis_client not provided)
            connection_ttl: Connection TTL in seconds (default: 3600)
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
            heartbeat_timeout: Heartbeat timeout in seconds (default: 90)
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis support not available. Install with: "
                "pip install netrun-websocket[redis]"
            )

        self.redis_client = redis_client
        self.redis_url = redis_url
        self.connection_ttl = connection_ttl
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._initialized = False

    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return

        try:
            if not self.redis_client:
                if not self.redis_url:
                    raise ValueError(
                        "Either redis_client or redis_url must be provided"
                    )

                self.redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )

            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info("WebSocket session manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket session manager: {e}")
            self._initialized = False
            raise

    async def create_connection(
        self,
        session_id: str,
        user_id: str,
        username: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        tab_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a new WebSocket connection.

        Args:
            session_id: User session ID
            user_id: User identifier
            username: User display name
            client_ip: Client IP address
            user_agent: Client user agent string
            tab_id: Browser tab identifier (for multi-tab support)
            metadata: Additional connection metadata

        Returns:
            connection_id: Unique connection identifier
        """
        if not self._initialized:
            await self.initialize()

        # Generate unique connection ID
        connection_id = f"ws_{user_id}_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        connection = WebSocketConnection(
            connection_id=connection_id,
            session_id=session_id,
            user_id=user_id,
            username=username,
            connected_at=now,
            last_heartbeat=now,
            client_ip=client_ip,
            user_agent=user_agent,
            tab_id=tab_id,
            metadata=metadata or {}
        )

        try:
            # Store connection metadata
            ws_key = f"ws:{connection_id}"
            await self.redis_client.setex(
                ws_key,
                self.connection_ttl,
                json.dumps(asdict(connection))
            )

            # Add to user's active connections
            user_ws_key = f"ws_user:{user_id}"
            await self.redis_client.sadd(user_ws_key, connection_id)
            await self.redis_client.expire(user_ws_key, self.connection_ttl)

            # Add to session's active connections
            session_ws_key = f"ws_session:{session_id}"
            await self.redis_client.sadd(session_ws_key, connection_id)
            await self.redis_client.expire(session_ws_key, self.connection_ttl)

            # Initialize heartbeat
            heartbeat_key = f"ws_heartbeat:{connection_id}"
            await self.redis_client.setex(heartbeat_key, self.heartbeat_timeout, now)

            logger.info(f"Created WebSocket connection {connection_id} for user {user_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}")
            raise

    async def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        Retrieve connection metadata.

        Args:
            connection_id: Connection identifier

        Returns:
            WebSocketConnection or None if not found
        """
        if not self._initialized:
            await self.initialize()

        try:
            ws_key = f"ws:{connection_id}"
            data = await self.redis_client.get(ws_key)

            if not data:
                return None

            conn_dict = json.loads(data)
            return WebSocketConnection(**conn_dict)

        except Exception as e:
            logger.error(f"Failed to get connection {connection_id}: {e}")
            return None

    async def update_heartbeat(self, connection_id: str) -> bool:
        """
        Update connection heartbeat timestamp.

        Args:
            connection_id: Connection identifier

        Returns:
            True if updated, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Check if connection exists
            connection = await self.get_connection(connection_id)
            if not connection:
                return False

            now = datetime.now(timezone.utc).isoformat()

            # Update last heartbeat
            connection.last_heartbeat = now
            ws_key = f"ws:{connection_id}"
            await self.redis_client.setex(
                ws_key,
                self.connection_ttl,
                json.dumps(asdict(connection))
            )

            # Update heartbeat tracker
            heartbeat_key = f"ws_heartbeat:{connection_id}"
            await self.redis_client.setex(heartbeat_key, self.heartbeat_timeout, now)

            return True

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {connection_id}: {e}")
            return False

    async def save_connection_state(
        self,
        connection_id: str,
        state: SessionState
    ) -> bool:
        """
        Save connection state for reconnection.

        Args:
            connection_id: Connection identifier
            state: Connection state to persist

        Returns:
            True if saved, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            state_key = f"ws_state:{connection_id}"
            await self.redis_client.setex(
                state_key,
                self.connection_ttl,
                json.dumps(asdict(state))
            )

            logger.debug(f"Saved connection state for {connection_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save connection state for {connection_id}: {e}")
            return False

    async def restore_connection_state(
        self,
        connection_id: str
    ) -> Optional[SessionState]:
        """
        Restore connection state for reconnection.

        Args:
            connection_id: Connection identifier

        Returns:
            SessionState or None if not found
        """
        if not self._initialized:
            await self.initialize()

        try:
            state_key = f"ws_state:{connection_id}"
            data = await self.redis_client.get(state_key)

            if not data:
                return None

            state_dict = json.loads(data)
            return SessionState(**state_dict)

        except Exception as e:
            logger.error(f"Failed to restore connection state for {connection_id}: {e}")
            return None

    async def get_user_connections(self, user_id: str) -> List[WebSocketConnection]:
        """
        Get all active connections for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active WebSocketConnection objects
        """
        if not self._initialized:
            await self.initialize()

        try:
            user_ws_key = f"ws_user:{user_id}"
            connection_ids = await self.redis_client.smembers(user_ws_key)

            connections = []
            for conn_id in connection_ids:
                connection = await self.get_connection(conn_id)
                if connection:
                    connections.append(connection)

            return connections

        except Exception as e:
            logger.error(f"Failed to get connections for user {user_id}: {e}")
            return []

    async def get_session_connections(self, session_id: str) -> List[WebSocketConnection]:
        """
        Get all active connections for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of active WebSocketConnection objects
        """
        if not self._initialized:
            await self.initialize()

        try:
            session_ws_key = f"ws_session:{session_id}"
            connection_ids = await self.redis_client.smembers(session_ws_key)

            connections = []
            for conn_id in connection_ids:
                connection = await self.get_connection(conn_id)
                if connection:
                    connections.append(connection)

            return connections

        except Exception as e:
            logger.error(f"Failed to get connections for session {session_id}: {e}")
            return []

    async def disconnect(self, connection_id: str, save_state: bool = True) -> bool:
        """
        Handle connection disconnect with optional state saving.

        Args:
            connection_id: Connection identifier
            save_state: Whether to preserve state for reconnection

        Returns:
            True if disconnected, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            connection = await self.get_connection(connection_id)
            if not connection:
                return False

            # Remove from user's active connections
            user_ws_key = f"ws_user:{connection.user_id}"
            await self.redis_client.srem(user_ws_key, connection_id)

            # Remove from session's active connections
            session_ws_key = f"ws_session:{connection.session_id}"
            await self.redis_client.srem(session_ws_key, connection_id)

            # Remove heartbeat tracker
            heartbeat_key = f"ws_heartbeat:{connection_id}"
            await self.redis_client.delete(heartbeat_key)

            if not save_state:
                # Delete connection metadata
                ws_key = f"ws:{connection_id}"
                await self.redis_client.delete(ws_key)

                # Delete connection state
                state_key = f"ws_state:{connection_id}"
                await self.redis_client.delete(state_key)
            else:
                # Mark connection as disconnected but keep for reconnection
                # Set shorter TTL for reconnection window (5 minutes)
                ws_key = f"ws:{connection_id}"
                await self.redis_client.expire(ws_key, 300)

                state_key = f"ws_state:{connection_id}"
                await self.redis_client.expire(state_key, 300)

            logger.info(f"Disconnected WebSocket {connection_id}, save_state={save_state}")
            return True

        except Exception as e:
            logger.error(f"Failed to disconnect {connection_id}: {e}")
            return False

    async def cleanup_stale_connections(self) -> int:
        """
        Clean up connections with expired heartbeats.

        Returns:
            Number of connections cleaned up
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Scan for all WebSocket connections
            cursor = 0
            stale_count = 0
            now = datetime.now(timezone.utc)

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match="ws:*", count=100
                )

                for key in keys:
                    connection_id = key.split(":")[1]
                    heartbeat_key = f"ws_heartbeat:{connection_id}"

                    # Check if heartbeat exists
                    heartbeat = await self.redis_client.get(heartbeat_key)
                    if not heartbeat:
                        # No heartbeat = stale connection
                        await self.disconnect(connection_id, save_state=False)
                        stale_count += 1
                        continue

                    # Check heartbeat age
                    try:
                        last_heartbeat = datetime.fromisoformat(
                            heartbeat.replace('Z', '+00:00')
                        )
                        age_seconds = (now - last_heartbeat).total_seconds()

                        if age_seconds > self.heartbeat_timeout:
                            await self.disconnect(connection_id, save_state=True)
                            stale_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Invalid heartbeat timestamp for {connection_id}: {e}"
                        )

                if cursor == 0:
                    break

            if stale_count > 0:
                logger.info(f"Cleaned up {stale_count} stale WebSocket connections")

            return stale_count

        except Exception as e:
            logger.error(f"Failed to cleanup stale connections: {e}")
            return 0

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket connection statistics.

        Returns:
            Statistics dictionary
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Count all active connections
            cursor = 0
            total_connections = 0
            unique_users = set()
            unique_sessions = set()

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match="ws:*", count=100
                )

                for key in keys:
                    connection_id = key.split(":")[1]
                    connection = await self.get_connection(connection_id)

                    if connection:
                        total_connections += 1
                        unique_users.add(connection.user_id)
                        unique_sessions.add(connection.session_id)

                if cursor == 0:
                    break

            return {
                "total_connections": total_connections,
                "unique_users": len(unique_users),
                "unique_sessions": len(unique_sessions),
                "redis_connected": self._initialized,
                "heartbeat_interval_seconds": self.heartbeat_interval,
                "heartbeat_timeout_seconds": self.heartbeat_timeout
            }

        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {
                "total_connections": 0,
                "unique_users": 0,
                "unique_sessions": 0,
                "redis_connected": False,
                "heartbeat_interval_seconds": self.heartbeat_interval,
                "heartbeat_timeout_seconds": self.heartbeat_timeout
            }

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False
            logger.info("WebSocket session manager closed")


__all__ = [
    "WebSocketConnection",
    "SessionState",
    "WebSocketSessionManager",
]
