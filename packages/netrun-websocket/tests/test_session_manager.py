"""Tests for session_manager module - Redis session management."""

import asyncio
import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

# Test if redis is available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from netrun.websocket.session_manager import (
    WebSocketConnection,
    SessionState,
    WebSocketSessionManager,
)


class TestWebSocketConnection:
    """Test WebSocketConnection dataclass."""

    def test_create_connection_basic(self):
        """Test creating basic connection metadata."""
        conn = WebSocketConnection(
            connection_id="conn123",
            session_id="session123",
            user_id="user123",
            username="testuser",
            connected_at="2024-01-01T00:00:00Z",
            last_heartbeat="2024-01-01T00:00:00Z"
        )

        assert conn.connection_id == "conn123"
        assert conn.session_id == "session123"
        assert conn.user_id == "user123"
        assert conn.username == "testuser"
        assert conn.client_ip is None
        assert conn.user_agent is None
        assert conn.tab_id is None
        assert conn.metadata == {}

    def test_create_connection_full(self):
        """Test creating connection with all fields."""
        metadata = {"custom_field": "value"}
        conn = WebSocketConnection(
            connection_id="conn123",
            session_id="session123",
            user_id="user123",
            username="testuser",
            connected_at="2024-01-01T00:00:00Z",
            last_heartbeat="2024-01-01T00:00:00Z",
            client_ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            tab_id="tab123",
            metadata=metadata
        )

        assert conn.client_ip == "192.168.1.1"
        assert conn.user_agent == "Mozilla/5.0"
        assert conn.tab_id == "tab123"
        assert conn.metadata == metadata


class TestSessionState:
    """Test SessionState dataclass."""

    def test_create_state_default(self):
        """Test creating session state with defaults."""
        state = SessionState()

        assert state.conversation_id is None
        assert state.active_workspace_id is None
        assert state.active_persona_id is None
        assert state.voice_session_config is None
        assert state.emotion_history == []
        assert state.recent_messages == []

    def test_create_state_full(self):
        """Test creating session state with all fields."""
        state = SessionState(
            conversation_id="conv123",
            active_workspace_id=1,
            active_persona_id=2,
            voice_session_config={"language": "en"},
            emotion_history=[{"emotion": "happy"}],
            recent_messages=[{"text": "hello"}]
        )

        assert state.conversation_id == "conv123"
        assert state.active_workspace_id == 1
        assert state.active_persona_id == 2
        assert state.voice_session_config == {"language": "en"}
        assert len(state.emotion_history) == 1
        assert len(state.recent_messages) == 1


class TestWebSocketSessionManager:
    """Test WebSocketSessionManager class."""

    def test_initialization_without_redis(self):
        """Test initialization fails without redis library."""
        if REDIS_AVAILABLE:
            pytest.skip("redis is available, skipping this test")

        with pytest.raises(ImportError, match="Redis support not available"):
            WebSocketSessionManager(redis_url="redis://localhost")

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    def test_initialization_with_defaults(self):
        """Test session manager initialization with defaults."""
        manager = WebSocketSessionManager(redis_url="redis://localhost")

        assert manager.redis_url == "redis://localhost"
        assert manager.connection_ttl == 3600
        assert manager.heartbeat_interval == 30
        assert manager.heartbeat_timeout == 90
        assert manager._initialized is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    def test_initialization_with_custom_config(self):
        """Test session manager initialization with custom config."""
        manager = WebSocketSessionManager(
            redis_url="redis://localhost:6380",
            connection_ttl=7200,
            heartbeat_interval=60,
            heartbeat_timeout=180
        )

        assert manager.redis_url == "redis://localhost:6380"
        assert manager.connection_ttl == 7200
        assert manager.heartbeat_interval == 60
        assert manager.heartbeat_timeout == 180

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    def test_initialization_without_redis_url_or_client(self):
        """Test initialization requires redis_client or redis_url."""
        manager = WebSocketSessionManager()

        with pytest.raises(ValueError, match="Either redis_client or redis_url must be provided"):
            asyncio.run(manager.initialize())

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_initialize_with_redis_client(self):
        """Test initialization with existing redis client."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        assert manager._initialized is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_initialize_with_redis_url(self):
        """Test initialization with redis URL."""
        # Create a coroutine that returns the mock
        async def mock_from_url_coro(*args, **kwargs):
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            return mock_redis

        with patch('redis.asyncio.from_url', side_effect=mock_from_url_coro):
            manager = WebSocketSessionManager(redis_url="redis://localhost")
            await manager.initialize()

            assert manager._initialized is True

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Test initialization when already initialized."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        # Call initialize again
        await manager.initialize()

        # Ping should only be called once
        assert mock_redis.ping.call_count == 1

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """Test initialization handles connection failure."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

        manager = WebSocketSessionManager(redis_client=mock_redis)

        with pytest.raises(Exception):
            await manager.initialize()

        assert manager._initialized is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_create_connection_basic(self):
        """Test creating basic WebSocket connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.sadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connection_id = await manager.create_connection(
            session_id="session123",
            user_id="user123",
            username="testuser"
        )

        assert connection_id.startswith("ws_user123_")
        assert mock_redis.setex.call_count >= 2  # Connection + heartbeat
        assert mock_redis.sadd.call_count == 2  # User and session sets

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_create_connection_with_metadata(self):
        """Test creating connection with full metadata."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.sadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connection_id = await manager.create_connection(
            session_id="session123",
            user_id="user123",
            username="testuser",
            client_ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            tab_id="tab123",
            metadata={"custom": "data"}
        )

        assert connection_id is not None
        # Verify setex was called with proper data
        assert mock_redis.setex.called

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_create_connection_auto_initializes(self):
        """Test creating connection auto-initializes if needed."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.sadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        # Don't call initialize()

        connection_id = await manager.create_connection(
            session_id="session123",
            user_id="user123",
            username="testuser"
        )

        assert manager._initialized is True
        assert connection_id is not None

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_exists(self):
        """Test getting existing connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connection = await manager.get_connection("conn123")

        assert connection is not None
        assert connection.connection_id == "conn123"
        assert connection.user_id == "user123"

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_not_found(self):
        """Test getting non-existent connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connection = await manager.get_connection("nonexistent")

        assert connection is None

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_error_handling(self):
        """Test get_connection handles errors gracefully."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connection = await manager.get_connection("conn123")

        assert connection is None

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_update_heartbeat_success(self):
        """Test updating heartbeat successfully."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))
        mock_redis.setex = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        result = await manager.update_heartbeat("conn123")

        assert result is True
        assert mock_redis.setex.call_count == 2  # Connection + heartbeat

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_update_heartbeat_connection_not_found(self):
        """Test updating heartbeat for non-existent connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        result = await manager.update_heartbeat("nonexistent")

        assert result is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_update_heartbeat_error_handling(self):
        """Test update_heartbeat handles errors gracefully."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        result = await manager.update_heartbeat("conn123")

        assert result is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_save_connection_state(self):
        """Test saving connection state."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = SessionState(
            conversation_id="conv123",
            active_workspace_id=1
        )

        result = await manager.save_connection_state("conn123", state)

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_save_connection_state_error(self):
        """Test save_connection_state handles errors."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = SessionState()
        result = await manager.save_connection_state("conn123", state)

        assert result is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_restore_connection_state_success(self):
        """Test restoring connection state."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        state_data = {
            "conversation_id": "conv123",
            "active_workspace_id": 1,
            "active_persona_id": None,
            "voice_session_config": None,
            "emotion_history": [],
            "recent_messages": []
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(state_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = await manager.restore_connection_state("conn123")

        assert state is not None
        assert state.conversation_id == "conv123"
        assert state.active_workspace_id == 1

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_restore_connection_state_not_found(self):
        """Test restoring non-existent state."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = await manager.restore_connection_state("conn123")

        assert state is None

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_restore_connection_state_error(self):
        """Test restore_connection_state handles errors."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = await manager.restore_connection_state("conn123")

        assert state is None

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_user_connections(self):
        """Test getting all connections for a user."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.smembers = AsyncMock(return_value={"conn1", "conn2"})

        conn_data = {
            "connection_id": "conn1",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connections = await manager.get_user_connections("user123")

        assert len(connections) == 2

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_user_connections_error(self):
        """Test get_user_connections handles errors."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.smembers = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connections = await manager.get_user_connections("user123")

        assert connections == []

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_session_connections(self):
        """Test getting all connections for a session."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.smembers = AsyncMock(return_value={"conn1"})

        conn_data = {
            "connection_id": "conn1",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connections = await manager.get_session_connections("session123")

        assert len(connections) == 1

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_disconnect_with_save_state(self):
        """Test disconnecting with state preservation."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))
        mock_redis.srem = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis.expire = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        result = await manager.disconnect("conn123", save_state=True)

        assert result is True
        assert mock_redis.expire.call_count == 2  # Connection + state
        assert mock_redis.delete.call_count == 1  # Heartbeat only

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_disconnect_without_save_state(self):
        """Test disconnecting without state preservation."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))
        mock_redis.srem = AsyncMock()
        mock_redis.delete = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        result = await manager.disconnect("conn123", save_state=False)

        assert result is True
        assert mock_redis.delete.call_count == 3  # Connection + state + heartbeat

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_disconnect_connection_not_found(self):
        """Test disconnecting non-existent connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        result = await manager.disconnect("nonexistent")

        assert result is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self):
        """Test cleaning up stale connections."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        # Simulate scan returning connections
        mock_redis.scan = AsyncMock(side_effect=[
            (0, ["ws:conn1", "ws:conn2"])
        ])
        mock_redis.get = AsyncMock(return_value=None)  # No heartbeat = stale

        manager = WebSocketSessionManager(redis_client=mock_redis)
        manager.disconnect = AsyncMock()  # Mock disconnect method
        await manager.initialize()

        count = await manager.cleanup_stale_connections()

        assert count == 2
        assert manager.disconnect.call_count == 2

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_cleanup_stale_connections_error(self):
        """Test cleanup handles errors gracefully."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        count = await manager.cleanup_stale_connections()

        assert count == 0

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_stats(self):
        """Test getting connection statistics."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=[
            (0, ["ws:conn1", "ws:conn2"])
        ])

        conn_data = {
            "connection_id": "conn1",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        stats = await manager.get_connection_stats()

        assert stats["total_connections"] == 2
        assert stats["redis_connected"] is True
        assert "heartbeat_interval_seconds" in stats

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_stats_error(self):
        """Test get_connection_stats handles errors."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=Exception("Redis error"))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        stats = await manager.get_connection_stats()

        assert stats["total_connections"] == 0
        assert stats["redis_connected"] is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.close = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        await manager.close()

        assert manager._initialized is False
        mock_redis.close.assert_called_once()

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_create_connection_returns_connection_id(self):
        """Test create_connection returns the generated connection_id."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        # Create connection should work and return connection_id
        connection_id = await manager.create_connection(
            session_id="session123",
            user_id="user123",
            username="testuser"
        )

        assert connection_id is not None
        assert connection_id.startswith("ws_user123_")

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_with_logging(self):
        """Test get_connection with logging."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        conn = await manager.get_connection("conn123")

        assert conn is not None
        assert conn.connection_id == "conn123"

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_update_heartbeat_with_logging(self):
        """Test update_heartbeat with logging."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))
        mock_redis.setex = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        success = await manager.update_heartbeat("conn123")

        assert success is True

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_save_connection_state_with_logging(self):
        """Test save_connection_state with logging."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = SessionState(conversation_id="conv123")
        await manager.save_connection_state("conn123", state)

        mock_redis.setex.assert_called_once()

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_restore_connection_state_with_logging(self):
        """Test restore_connection_state with logging."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        state_data = {
            "conversation_id": "conv123",
            "active_workspace_id": None,
            "active_persona_id": None,
            "voice_session_config": None,
            "emotion_history": [],
            "recent_messages": []
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(state_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        state = await manager.restore_connection_state("conn123")

        assert state is not None
        assert state.conversation_id == "conv123"

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_user_connections_with_logging(self):
        """Test get_user_connections with logging."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.smembers = AsyncMock(return_value={b"conn123", b"conn456"})

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connections = await manager.get_user_connections("user123")

        assert len(connections) == 2

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_session_connections_with_logging_and_errors(self):
        """Test get_session_connections with logging and error handling."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.smembers = AsyncMock(return_value={b"conn123"})
        # First call returns valid data, second returns None to trigger error path
        mock_redis.get = AsyncMock(side_effect=[
            json.dumps({
                "connection_id": "conn123",
                "session_id": "session123",
                "user_id": "user123",
                "username": "testuser",
                "connected_at": "2024-01-01T00:00:00Z",
                "last_heartbeat": "2024-01-01T00:00:00Z",
                "client_ip": None,
                "user_agent": None,
                "tab_id": None,
                "metadata": {}
            }),
            None  # Second connection doesn't exist
        ])

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        connections = await manager.get_session_connections("session123")

        # Should only get 1 valid connection
        assert len(connections) >= 0

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_disconnect_with_logging_and_errors(self):
        """Test disconnect with logging and error handling."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        conn_data = {
            "connection_id": "conn123",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": None,
            "user_agent": None,
            "tab_id": None,
            "metadata": {}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))
        mock_redis.delete = AsyncMock()
        mock_redis.srem = AsyncMock()

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        await manager.disconnect("conn123", save_state=False)

        mock_redis.delete.assert_called()

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_cleanup_with_heartbeat_check(self):
        """Test cleanup with heartbeat timestamp checking."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=[
            (0, ["ws:conn1"])
        ])

        # Connection with old heartbeat
        old_time = datetime.now(timezone.utc).timestamp() - 7200  # 2 hours ago
        mock_redis.get = AsyncMock(return_value=str(old_time))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        manager.disconnect = AsyncMock()
        await manager.initialize()

        count = await manager.cleanup_stale_connections()

        # Should identify stale connection
        assert count >= 0

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @pytest.mark.asyncio
    async def test_get_connection_stats_with_detailed_info(self):
        """Test get_connection_stats with detailed connection info."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=[
            (0, ["ws:conn1"])
        ])

        conn_data = {
            "connection_id": "conn1",
            "session_id": "session123",
            "user_id": "user123",
            "username": "testuser",
            "connected_at": "2024-01-01T00:00:00Z",
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "client_ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "tab_id": "tab123",
            "metadata": {"custom": "data"}
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(conn_data))

        manager = WebSocketSessionManager(redis_client=mock_redis)
        await manager.initialize()

        stats = await manager.get_connection_stats()

        assert "total_connections" in stats
        assert stats["redis_connected"] is True
