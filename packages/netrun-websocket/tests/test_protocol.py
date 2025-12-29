"""Tests for protocol module."""

import pytest
from datetime import datetime

from netrun.websocket.protocol import (
    MessageType,
    ConnectionState,
    WebSocketMessage,
    PingMessage,
    PongMessage,
    ErrorMessage,
    UserMessage,
    TypingIndicatorMessage,
    NotificationMessage,
    parse_message
)


class TestMessageTypes:
    """Test message type enum."""

    def test_message_types_exist(self):
        """Test all expected message types exist."""
        assert MessageType.PING == "ping"
        assert MessageType.PONG == "pong"
        assert MessageType.USER_MESSAGE == "user_message"
        assert MessageType.ERROR == "error"


class TestWebSocketMessage:
    """Test base WebSocketMessage."""

    def test_create_message(self):
        """Test creating a basic message."""
        msg = WebSocketMessage(
            type=MessageType.PING,
            content="test"
        )
        assert msg.type == MessageType.PING
        assert msg.content == "test"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = WebSocketMessage(
            type=MessageType.PING,
            metadata={"key": "value"}
        )
        assert msg.metadata["key"] == "value"


class TestPingPongMessages:
    """Test ping/pong messages."""

    def test_ping_message(self):
        """Test creating ping message."""
        msg = PingMessage()
        assert msg.type == MessageType.PING
        assert msg.timestamp is not None

    def test_pong_message(self):
        """Test creating pong message."""
        msg = PongMessage(ping_timestamp="2024-01-01T00:00:00")
        assert msg.type == MessageType.PONG
        assert msg.ping_timestamp == "2024-01-01T00:00:00"


class TestUserMessage:
    """Test user message."""

    def test_create_user_message(self):
        """Test creating user message."""
        msg = UserMessage(
            user_id="user123",
            username="Test User",
            content="Hello, world!"
        )
        assert msg.type == MessageType.USER_MESSAGE
        assert msg.user_id == "user123"
        assert msg.username == "Test User"
        assert msg.content == "Hello, world!"

    def test_user_message_validation(self):
        """Test user message validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            UserMessage(
                user_id="user123",
                username="Test User",
                content=""  # Empty content should fail
            )


class TestErrorMessage:
    """Test error message."""

    def test_create_error_message(self):
        """Test creating error message."""
        msg = ErrorMessage(
            error="Test error",
            code="ERR001",
            details={"context": "test"}
        )
        assert msg.type == MessageType.ERROR
        assert msg.error == "Test error"
        assert msg.code == "ERR001"
        assert msg.details["context"] == "test"


class TestTypingIndicatorMessage:
    """Test typing indicator message."""

    def test_create_typing_message(self):
        """Test creating typing indicator."""
        msg = TypingIndicatorMessage(
            type=MessageType.USER_TYPING,
            user_id="user123",
            username="Test User",
            is_typing=True
        )
        assert msg.type == MessageType.USER_TYPING
        assert msg.is_typing is True

    def test_typing_type_validation(self):
        """Test that type must be typing-related."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TypingIndicatorMessage(
                type=MessageType.PING,  # Wrong type
                user_id="user123",
                username="Test User",
                is_typing=True
            )


class TestNotificationMessage:
    """Test notification message."""

    def test_create_notification(self):
        """Test creating notification message."""
        msg = NotificationMessage(
            notification_id="notif123",
            title="Test Notification",
            body="This is a test",
            priority="high"
        )
        assert msg.type == MessageType.NOTIFICATION
        assert msg.notification_id == "notif123"
        assert msg.title == "Test Notification"
        assert msg.priority == "high"

    def test_notification_priority_validation(self):
        """Test priority validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            NotificationMessage(
                notification_id="notif123",
                title="Test",
                body="Test",
                priority="invalid"  # Invalid priority
            )


class TestParseMessage:
    """Test message parsing."""

    def test_parse_ping(self):
        """Test parsing ping message."""
        data = {"type": "ping"}
        msg = parse_message(data)
        assert isinstance(msg, PingMessage)
        assert msg.type == MessageType.PING

    def test_parse_user_message(self):
        """Test parsing user message."""
        data = {
            "type": "user_message",
            "user_id": "user123",
            "username": "Test User",
            "content": "Hello"
        }
        msg = parse_message(data)
        assert isinstance(msg, UserMessage)
        assert msg.user_id == "user123"

    def test_parse_invalid_type(self):
        """Test parsing invalid message type."""
        data = {"type": "invalid_type"}
        with pytest.raises(ValueError):
            parse_message(data)

    def test_parse_generic_message(self):
        """Test parsing generic message."""
        data = {
            "type": "connect",
            "content": "test"
        }
        msg = parse_message(data)
        assert isinstance(msg, WebSocketMessage)
        assert msg.type == MessageType.CONNECT

    def test_parse_pong_message(self):
        """Test parsing pong message."""
        data = {
            "type": "pong",
            "ping_timestamp": "2024-01-01T00:00:00"
        }
        msg = parse_message(data)
        assert isinstance(msg, PongMessage)
        assert msg.type == MessageType.PONG

    def test_parse_error_message(self):
        """Test parsing error message."""
        data = {
            "type": "error",
            "error": "Test error",
            "code": "ERR001"
        }
        msg = parse_message(data)
        assert isinstance(msg, ErrorMessage)
        assert msg.error == "Test error"

    def test_parse_typing_indicator(self):
        """Test parsing typing indicator message."""
        data = {
            "type": "user_typing",
            "user_id": "user123",
            "username": "Test User",
            "is_typing": True
        }
        msg = parse_message(data)
        assert isinstance(msg, TypingIndicatorMessage)
        assert msg.is_typing is True

    def test_parse_presence_update(self):
        """Test parsing presence update message."""
        data = {
            "type": "presence_update",
            "user_id": "user123",
            "status": "online"
        }
        msg = parse_message(data)
        assert msg.type == MessageType.PRESENCE_UPDATE

    def test_parse_notification_message(self):
        """Test parsing notification message."""
        data = {
            "type": "notification",
            "notification_id": "notif123",
            "title": "Test",
            "body": "Test notification",
            "priority": "high"
        }
        msg = parse_message(data)
        assert isinstance(msg, NotificationMessage)
        assert msg.title == "Test"
