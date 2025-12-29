"""Tests for connection_manager module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.websockets import WebSocketState

from netrun.websocket.connection_manager import (
    ConnectionMetadata,
    WebSocketConnectionManager
)
from netrun.websocket.protocol import ConnectionState as ProtocolConnectionState


class TestConnectionMetadata:
    """Test ConnectionMetadata class."""

    def test_create_metadata(self):
        """Test creating connection metadata."""
        websocket = MagicMock()
        metadata = ConnectionMetadata(
            connection_id="conn123",
            user_id="user123",
            websocket=websocket,
            session_id="session123"
        )
        assert metadata.connection_id == "conn123"
        assert metadata.user_id == "user123"
        assert metadata.session_id == "session123"
        assert metadata.state == ProtocolConnectionState.CONNECTED

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        websocket = MagicMock()
        metadata = ConnectionMetadata(
            connection_id="conn123",
            user_id="user123",
            websocket=websocket
        )
        data = metadata.to_dict()
        assert data["connection_id"] == "conn123"
        assert data["user_id"] == "user123"
        assert "connected_at" in data
        assert "last_activity" in data


class TestWebSocketConnectionManager:
    """Test WebSocketConnectionManager class."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = WebSocketConnectionManager(
            max_connections_per_user=10,
            heartbeat_interval=60
        )
        assert manager.max_connections_per_user == 10
        assert manager.heartbeat_interval == 60
        assert len(manager.connections) == 0

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting a WebSocket."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()

        connection_id = await manager.connect(
            websocket=websocket,
            user_id="user123",
            session_id="session123"
        )

        assert connection_id is not None
        assert connection_id in manager.connections
        assert "user123" in manager.user_connections
        websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_connections_per_user(self):
        """Test max connections per user enforcement."""
        manager = WebSocketConnectionManager(max_connections_per_user=2)

        # Connect first two connections
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        await manager.connect(websocket1, "user123")
        await manager.connect(websocket2, "user123")

        # Third connection should fail
        websocket3 = AsyncMock()
        with pytest.raises(ValueError, match="Maximum 2 connections per user"):
            await manager.connect(websocket3, "user123")

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting a WebSocket."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()

        connection_id = await manager.connect(websocket, "user123")
        assert connection_id in manager.connections

        await manager.disconnect(connection_id)
        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending message to connection."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED  # Set state

        connection_id = await manager.connect(websocket, "user123")

        message = {"type": "test", "data": "hello"}
        success = await manager.send_message(connection_id, message)

        assert success is True
        websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user(self):
        """Test sending message to all user connections."""
        manager = WebSocketConnectionManager()
        websocket1 = AsyncMock()
        websocket1.client_state = WebSocketState.CONNECTED
        websocket2 = AsyncMock()
        websocket2.client_state = WebSocketState.CONNECTED

        # Connect two WebSockets for same user
        await manager.connect(websocket1, "user123")
        await manager.connect(websocket2, "user123")

        message = {"type": "test", "data": "hello"}
        count = await manager.send_to_user("user123", message)

        assert count == 2
        websocket1.send_json.assert_called_once()
        websocket2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting to all connections."""
        manager = WebSocketConnectionManager()
        websocket1 = AsyncMock()
        websocket1.client_state = WebSocketState.CONNECTED
        websocket2 = AsyncMock()
        websocket2.client_state = WebSocketState.CONNECTED
        websocket3 = AsyncMock()
        websocket3.client_state = WebSocketState.CONNECTED

        await manager.connect(websocket1, "user1")
        await manager.connect(websocket2, "user2")
        await manager.connect(websocket3, "user3")

        message = {"type": "broadcast", "data": "hello all"}
        count = await manager.broadcast(message, exclude_users={"user2"})

        assert count == 2
        websocket1.send_json.assert_called_once()
        websocket2.send_json.assert_not_called()
        websocket3.send_json.assert_called_once()

    def test_get_stats(self):
        """Test getting connection statistics."""
        manager = WebSocketConnectionManager()
        stats = manager.get_stats()

        assert "active_connections" in stats
        assert "total_connections" in stats
        assert "peak_connections" in stats
        assert stats["active_connections"] == 0

    @pytest.mark.asyncio
    async def test_get_user_connections(self):
        """Test getting user's connections."""
        manager = WebSocketConnectionManager()
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()

        await manager.connect(websocket1, "user123")
        await manager.connect(websocket2, "user123")

        connections = manager.get_user_connections("user123")
        assert len(connections) == 2
        assert all(conn["user_id"] == "user123" for conn in connections)

    @pytest.mark.asyncio
    async def test_connect_with_full_metadata(self):
        """Test connecting with full metadata."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()

        connection_id = await manager.connect(
            websocket=websocket,
            user_id="user123",
            session_id="session123",
            endpoint="/ws/custom",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"custom": "data"}
        )

        assert connection_id in manager.connections
        metadata = manager.connections[connection_id]
        assert metadata.endpoint == "/ws/custom"
        assert metadata.ip_address == "192.168.1.1"
        assert metadata.user_agent == "Mozilla/5.0"
        assert metadata.metadata == {"custom": "data"}

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self):
        """Test disconnecting non-existent connection."""
        manager = WebSocketConnectionManager()

        # Should not raise error
        await manager.disconnect("nonexistent")

        assert len(manager.connections) == 0

    @pytest.mark.asyncio
    async def test_disconnect_with_error(self):
        """Test disconnect handles WebSocket close errors."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.close = AsyncMock(side_effect=Exception("Close error"))

        connection_id = await manager.connect(websocket, "user123")

        # Should handle error and still cleanup
        await manager.disconnect(connection_id)

        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_send_message_connection_not_found(self):
        """Test sending message to non-existent connection."""
        manager = WebSocketConnectionManager()

        success = await manager.send_message("nonexistent", {"test": "data"})

        assert success is False

    @pytest.mark.asyncio
    async def test_send_message_websocket_not_connected(self):
        """Test sending message when WebSocket not connected."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.DISCONNECTED

        connection_id = await manager.connect(websocket, "user123")

        success = await manager.send_message(connection_id, {"test": "data"})

        assert success is False

    @pytest.mark.asyncio
    async def test_send_message_error_triggers_disconnect(self):
        """Test send error triggers disconnect."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_json = AsyncMock(side_effect=Exception("Send error"))
        websocket.close = AsyncMock()

        connection_id = await manager.connect(websocket, "user123")

        success = await manager.send_message(connection_id, {"test": "data"})

        assert success is False
        # Connection should be disconnected
        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_send_message_binary(self):
        """Test sending binary message."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED

        connection_id = await manager.connect(websocket, "user123")

        binary_data = b"binary data"
        success = await manager.send_message(connection_id, binary_data, binary=True)

        assert success is True
        websocket.send_bytes.assert_called_once_with(binary_data)

    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(self):
        """Test sending to user with no connections."""
        manager = WebSocketConnectionManager()

        count = await manager.send_to_user("nonexistent", {"test": "data"})

        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_no_exclusions(self):
        """Test broadcasting without exclusions."""
        manager = WebSocketConnectionManager()
        websocket1 = AsyncMock()
        websocket1.client_state = WebSocketState.CONNECTED
        websocket2 = AsyncMock()
        websocket2.client_state = WebSocketState.CONNECTED

        await manager.connect(websocket1, "user1")
        await manager.connect(websocket2, "user2")

        message = {"type": "broadcast"}
        count = await manager.broadcast(message)

        assert count == 2

    @pytest.mark.asyncio
    async def test_receive_message_json(self):
        """Test receiving JSON message."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.receive_json = AsyncMock(return_value={"type": "test"})

        connection_id = await manager.connect(websocket, "user123")

        data = await manager.receive_message(connection_id)

        assert data == {"type": "test"}

    @pytest.mark.asyncio
    async def test_receive_message_text_fallback(self):
        """Test receiving text message when JSON fails."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.receive_json = AsyncMock(side_effect=Exception("Not JSON"))
        websocket.receive_text = AsyncMock(return_value="text message")

        connection_id = await manager.connect(websocket, "user123")

        data = await manager.receive_message(connection_id)

        assert data == "text message"

    @pytest.mark.asyncio
    async def test_receive_message_websocket_disconnect(self):
        """Test receive handles WebSocket disconnect."""
        from fastapi import WebSocketDisconnect

        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        # Both receive methods should raise WebSocketDisconnect
        websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect)
        websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect)
        websocket.client_state = WebSocketState.CONNECTED
        websocket.close = AsyncMock()

        connection_id = await manager.connect(websocket, "user123")

        data = await manager.receive_message(connection_id)

        assert data is None
        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_receive_message_error_triggers_disconnect(self):
        """Test receive error triggers disconnect."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()
        websocket.receive_json = AsyncMock(side_effect=Exception("Receive error"))
        websocket.receive_text = AsyncMock(side_effect=Exception("Receive error"))
        websocket.client_state = WebSocketState.CONNECTED
        websocket.close = AsyncMock()

        connection_id = await manager.connect(websocket, "user123")

        data = await manager.receive_message(connection_id)

        assert data is None
        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_receive_message_connection_not_found(self):
        """Test receiving from non-existent connection."""
        manager = WebSocketConnectionManager()

        data = await manager.receive_message("nonexistent")

        assert data is None

    def test_get_connection_info_exists(self):
        """Test getting connection info for existing connection."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()

        import asyncio
        connection_id = asyncio.run(manager.connect(websocket, "user123"))

        info = manager.get_connection_info(connection_id)

        assert info is not None
        assert info["connection_id"] == connection_id
        assert info["user_id"] == "user123"

    def test_get_connection_info_not_found(self):
        """Test getting connection info for non-existent connection."""
        manager = WebSocketConnectionManager()

        info = manager.get_connection_info("nonexistent")

        assert info is None

    def test_get_user_connections_empty(self):
        """Test getting connections for user with none."""
        manager = WebSocketConnectionManager()

        connections = manager.get_user_connections("nonexistent")

        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test connection metrics are tracked."""
        manager = WebSocketConnectionManager()
        websocket1 = AsyncMock()
        websocket1.client_state = WebSocketState.CONNECTED
        websocket2 = AsyncMock()
        websocket2.client_state = WebSocketState.CONNECTED

        # Connect
        conn1 = await manager.connect(websocket1, "user1")
        conn2 = await manager.connect(websocket2, "user2")

        # Send messages
        await manager.send_message(conn1, {"test": "data"})
        await manager.send_message(conn2, {"test": "data"})

        # Disconnect
        await manager.disconnect(conn1)
        await manager.disconnect(conn2)

        stats = manager.get_stats()

        assert stats["total_connections"] == 2
        assert stats["total_disconnections"] == 2
        assert stats["total_messages_sent"] == 2
        assert stats["peak_connections"] == 2

    @pytest.mark.asyncio
    async def test_session_connection_tracking(self):
        """Test session connections are tracked."""
        manager = WebSocketConnectionManager()
        websocket = AsyncMock()

        connection_id = await manager.connect(
            websocket=websocket,
            user_id="user123",
            session_id="session123"
        )

        assert "session123" in manager.session_connections
        assert manager.session_connections["session123"] == connection_id

    def test_metadata_to_dict_complete(self):
        """Test metadata to_dict includes all fields."""
        websocket = MagicMock()
        metadata = ConnectionMetadata(
            connection_id="conn123",
            user_id="user123",
            websocket=websocket,
            session_id="session123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            endpoint="/ws/test",
            metadata={"custom": "data"}
        )

        data = metadata.to_dict()

        assert data["connection_id"] == "conn123"
        assert data["user_id"] == "user123"
        assert data["session_id"] == "session123"
        assert data["ip_address"] == "192.168.1.1"
        assert data["user_agent"] == "Mozilla/5.0"
        assert data["endpoint"] == "/ws/test"
        assert data["metadata"] == {"custom": "data"}
        assert data["state"] == ProtocolConnectionState.CONNECTED.value
