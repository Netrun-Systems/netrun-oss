"""
WebSocket Protocol Message Types and Validation
File: protocol.py
Netrun Systems - SDLC v2.3 Compliant

Defines WebSocket message types, structures, and validation using Pydantic.
Provides type-safe message handling with comprehensive validation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """WebSocket message types."""

    # System messages
    PING = "ping"
    PONG = "pong"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    ACK = "ack"
    ERROR = "error"

    # User messages
    USER_MESSAGE = "user_message"
    USER_TYPING = "user_typing"
    USER_STOPPED_TYPING = "user_stopped_typing"

    # Presence
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    PRESENCE_UPDATE = "presence_update"

    # Session
    SESSION_UPDATED = "session_updated"

    # Notifications
    NOTIFICATION = "notification"

    # Heartbeat
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"


class ConnectionState(str, Enum):
    """WebSocket connection states."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """
    Base WebSocket message structure.

    All WebSocket messages follow this structure for consistency
    and type safety across the application.
    """

    type: MessageType = Field(..., description="Message type")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp"
    )
    content: Optional[str] = Field(None, description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PingMessage(BaseModel):
    """Ping message for connection health check."""

    type: Literal[MessageType.PING] = MessageType.PING
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PongMessage(BaseModel):
    """Pong response message."""

    type: Literal[MessageType.PONG] = MessageType.PONG
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ping_timestamp: Optional[str] = Field(None, description="Original ping timestamp")


class ErrorMessage(BaseModel):
    """Error message."""

    type: Literal[MessageType.ERROR] = MessageType.ERROR
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Dict[str, Any] = Field(default_factory=dict, description="Error details")


class UserMessage(BaseModel):
    """User-sent message."""

    type: Literal[MessageType.USER_MESSAGE] = MessageType.USER_MESSAGE
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="User display name")
    content: str = Field(..., description="Message content", min_length=1)
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TypingIndicatorMessage(BaseModel):
    """Typing indicator message."""

    type: MessageType = Field(..., description="USER_TYPING or USER_STOPPED_TYPING")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="User display name")
    session_id: Optional[str] = Field(None, description="Session identifier")
    is_typing: bool = Field(..., description="Whether user is typing")

    @field_validator('type')
    @classmethod
    def validate_typing_type(cls, v: MessageType) -> MessageType:
        """Validate that type is a typing indicator type."""
        if v not in (MessageType.USER_TYPING, MessageType.USER_STOPPED_TYPING):
            raise ValueError(
                f"Type must be USER_TYPING or USER_STOPPED_TYPING, got {v}"
            )
        return v


class PresenceUpdateMessage(BaseModel):
    """Presence update message."""

    type: Literal[MessageType.PRESENCE_UPDATE] = MessageType.PRESENCE_UPDATE
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    active_users: list = Field(default_factory=list, description="List of active users")
    typing_users: list = Field(default_factory=list, description="List of typing users")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationMessage(BaseModel):
    """Notification message."""

    type: Literal[MessageType.NOTIFICATION] = MessageType.NOTIFICATION
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notification_id: str = Field(..., description="Notification identifier")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    priority: str = Field("normal", description="Priority: low, normal, high")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority value."""
        if v not in ("low", "normal", "high"):
            raise ValueError(f"Priority must be low, normal, or high, got {v}")
        return v


class ConnectionInfo(BaseModel):
    """Connection information metadata."""

    connection_id: str = Field(..., description="Connection identifier")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    state: ConnectionState = Field(..., description="Connection state")
    connected_at: str = Field(..., description="ISO 8601 connection timestamp")
    last_activity: str = Field(..., description="ISO 8601 last activity timestamp")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    metadata: Dict[str, Any] = Field(default_factory=dict)


def parse_message(data: Dict[str, Any]) -> WebSocketMessage:
    """
    Parse incoming WebSocket message data into appropriate message type.

    Args:
        data: Raw message data dictionary

    Returns:
        Parsed WebSocketMessage or specific message type

    Raises:
        ValueError: If message type is invalid or data is malformed
    """
    try:
        msg_type = MessageType(data.get("type"))
    except ValueError as e:
        raise ValueError(f"Invalid message type: {data.get('type')}") from e

    # Route to specific message type
    if msg_type == MessageType.PING:
        return PingMessage(**data)
    elif msg_type == MessageType.PONG:
        return PongMessage(**data)
    elif msg_type == MessageType.ERROR:
        return ErrorMessage(**data)
    elif msg_type == MessageType.USER_MESSAGE:
        return UserMessage(**data)
    elif msg_type in (MessageType.USER_TYPING, MessageType.USER_STOPPED_TYPING):
        return TypingIndicatorMessage(**data)
    elif msg_type == MessageType.PRESENCE_UPDATE:
        return PresenceUpdateMessage(**data)
    elif msg_type == MessageType.NOTIFICATION:
        return NotificationMessage(**data)
    else:
        # Generic message for other types
        return WebSocketMessage(**data)


__all__ = [
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
]
