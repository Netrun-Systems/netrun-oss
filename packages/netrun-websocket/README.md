# netrun-websocket

Production-grade WebSocket connection management for Netrun Systems services.

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

- **Connection Management**: Pool-based connection management with per-user limits
- **Session Persistence**: Redis-backed session storage for cross-node coordination
- **JWT Authentication**: Token-based authentication with expiration handling
- **Protocol Validation**: Pydantic-based message type validation
- **Reconnection**: Exponential backoff reconnection with configurable max attempts
- **Heartbeat Monitoring**: Ping/pong health checks with stale connection cleanup
- **Metrics Tracking**: Comprehensive connection and latency metrics
- **Type Safety**: Full type hints for IDE support and type checking
- **Async/Await**: Built on async/await throughout for high performance

## Installation

### Basic Installation

```bash
pip install netrun-websocket
```

### With Redis Support

```bash
pip install netrun-websocket[redis]
```

### With JWT Authentication

```bash
pip install netrun-websocket[auth]
```

### With All Optional Dependencies

```bash
pip install netrun-websocket[all]
```

### Development Installation

```bash
pip install netrun-websocket[dev]
```

## Quick Start

### Basic WebSocket Connection Manager

```python
from fastapi import FastAPI, WebSocket
from netrun.websocket import WebSocketConnectionManager

app = FastAPI()
manager = WebSocketConnectionManager(max_connections_per_user=5)

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Connect
    connection_id = await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive message
            data = await manager.receive_message(connection_id)
            if data is None:
                break

            # Broadcast to all users except sender
            await manager.broadcast(
                {"type": "message", "data": data},
                exclude_users={user_id}
            )
    finally:
        # Disconnect
        await manager.disconnect(connection_id)
```

### With JWT Authentication

```python
from fastapi import FastAPI, WebSocket, Query, WebSocketException
from netrun.websocket import WebSocketConnectionManager, JWTAuthService

app = FastAPI()
manager = WebSocketConnectionManager()
auth_service = JWTAuthService(secret_key="your-secret-key")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Validate JWT token
    payload = auth_service.validate_token(token)
    if not payload:
        raise WebSocketException(code=1008, reason="Invalid token")

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
```

### With Redis Session Management

```python
from fastapi import FastAPI, WebSocket
from netrun.websocket import WebSocketConnectionManager, WebSocketSessionManager

app = FastAPI()
manager = WebSocketConnectionManager()
session_manager = WebSocketSessionManager(
    redis_url="redis://localhost:6379/0"
)

@app.on_event("startup")
async def startup():
    await session_manager.initialize()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Create session connection
    connection_id = await session_manager.create_connection(
        session_id=f"session_{user_id}",
        user_id=user_id,
        username=f"User {user_id}"
    )

    # Connect WebSocket
    await manager.connect(websocket, user_id, session_id=connection_id)

    try:
        while True:
            data = await manager.receive_message(connection_id)
            if data is None:
                break

            # Update heartbeat
            await session_manager.update_heartbeat(connection_id)

            # Handle message
            await manager.send_message(connection_id, {"echo": data})
    finally:
        await manager.disconnect(connection_id)
        await session_manager.disconnect(connection_id)
```

### With Heartbeat Monitoring

```python
from fastapi import FastAPI, WebSocket
from netrun.websocket import (
    WebSocketConnectionManager,
    HeartbeatMonitor,
    HeartbeatConfig
)

app = FastAPI()
manager = WebSocketConnectionManager()

# Configure heartbeat
heartbeat_config = HeartbeatConfig(
    interval=30,      # Send ping every 30 seconds
    timeout=90,       # Consider stale after 90 seconds
    max_missed=3      # Disconnect after 3 missed heartbeats
)
heartbeat = HeartbeatMonitor(heartbeat_config)

async def send_ping(connection_id: str) -> bool:
    """Send ping to connection."""
    return await manager.send_message(
        connection_id,
        {"type": "ping", "timestamp": time.time()}
    )

async def cleanup_connection(connection_id: str):
    """Cleanup stale connection."""
    await manager.disconnect(connection_id, code=1001, reason="Heartbeat timeout")

@app.on_event("startup")
async def startup():
    # Start heartbeat monitoring
    await heartbeat.start(
        ping_callback=send_ping,
        cleanup_callback=cleanup_connection
    )

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    connection_id = await manager.connect(websocket, user_id)

    # Register for heartbeat monitoring
    heartbeat.register_connection(connection_id)

    try:
        while True:
            data = await manager.receive_message(connection_id)
            if data is None:
                break

            # Update heartbeat on activity
            if data.get("type") == "pong":
                heartbeat.update_heartbeat(connection_id)

            await manager.send_message(connection_id, {"echo": data})
    finally:
        heartbeat.unregister_connection(connection_id)
        await manager.disconnect(connection_id)
```

### With Metrics Collection

```python
from fastapi import FastAPI, WebSocket
from netrun.websocket import WebSocketConnectionManager, MetricsCollector

app = FastAPI()
manager = WebSocketConnectionManager()
metrics = MetricsCollector()

@app.get("/metrics")
async def get_metrics():
    """Get WebSocket metrics."""
    return metrics.get_stats()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    connection_id = await manager.connect(websocket, user_id)

    # Register for metrics
    metrics.register_connection(connection_id, user_id)

    try:
        while True:
            start_time = time.time()
            data = await manager.receive_message(connection_id)
            if data is None:
                break

            # Record metrics
            metrics.record_message_received(connection_id, len(str(data)))

            # Send response
            await manager.send_message(connection_id, {"echo": data})
            metrics.record_message_sent(connection_id, len(str(data)))

            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            metrics.record_latency(latency_ms)
    finally:
        metrics.unregister_connection(connection_id)
        await manager.disconnect(connection_id)
```

## Protocol Message Types

The package includes Pydantic models for type-safe message handling:

```python
from netrun.websocket import (
    MessageType,
    WebSocketMessage,
    PingMessage,
    PongMessage,
    UserMessage,
    ErrorMessage,
    parse_message
)

# Create a user message
message = UserMessage(
    user_id="user123",
    username="John Doe",
    content="Hello, world!"
)

# Parse incoming message
data = {"type": "user_message", "user_id": "user123", "username": "John", "content": "Hi"}
parsed = parse_message(data)  # Returns UserMessage instance
```

## Reconnection with Exponential Backoff

```python
from netrun.websocket import ReconnectionManager, ReconnectionConfig

# Configure reconnection
config = ReconnectionConfig(
    initial_delay=1.0,        # Start with 1 second
    max_delay=60.0,           # Max 60 seconds between attempts
    max_attempts=10,          # Try 10 times (0 = infinite)
    backoff_multiplier=2.0,   # Double delay each time
    jitter=True               # Add random jitter
)

reconnection = ReconnectionManager(config)

async def connect():
    """Your connection logic here."""
    try:
        # Establish connection
        return True
    except Exception:
        return False

# Attempt reconnection
success = await reconnection.reconnect(
    connect_callback=connect,
    on_success=lambda: print("Connected!"),
    on_failure=lambda attempt: print(f"Attempt {attempt} failed"),
    on_max_attempts=lambda: print("Max attempts reached")
)
```

## API Reference

### WebSocketConnectionManager

Main connection manager class.

**Constructor:**
```python
WebSocketConnectionManager(
    max_connections_per_user: int = 5,
    heartbeat_interval: int = 30,
    connection_timeout: int = 300
)
```

**Methods:**
- `connect(websocket, user_id, session_id, ...)` - Connect WebSocket
- `disconnect(connection_id, code, reason)` - Disconnect WebSocket
- `send_message(connection_id, message, binary)` - Send to connection
- `send_to_user(user_id, message, binary)` - Send to all user connections
- `broadcast(message, exclude_users, binary)` - Broadcast to all
- `receive_message(connection_id)` - Receive message
- `get_connection_info(connection_id)` - Get connection metadata
- `get_user_connections(user_id)` - Get user's connections
- `get_stats()` - Get connection statistics

### JWTAuthService

JWT authentication service.

**Constructor:**
```python
JWTAuthService(
    secret_key: str,
    algorithm: str = "HS256",
    token_expiry_seconds: int = 7200
)
```

**Methods:**
- `generate_token(user_id, additional_claims, expiry_seconds)` - Generate JWT
- `validate_token(token)` - Validate and decode JWT
- `get_user_id(token)` - Extract user ID from token
- `is_token_expired(token)` - Check if token expired

### WebSocketSessionManager

Redis-backed session manager (requires `redis` extra).

**Constructor:**
```python
WebSocketSessionManager(
    redis_client: Optional[Redis] = None,
    redis_url: Optional[str] = None,
    connection_ttl: int = 3600,
    heartbeat_interval: int = 30,
    heartbeat_timeout: int = 90
)
```

**Methods:**
- `initialize()` - Initialize Redis connection
- `create_connection(session_id, user_id, username, ...)` - Create connection
- `get_connection(connection_id)` - Get connection metadata
- `update_heartbeat(connection_id)` - Update heartbeat
- `save_connection_state(connection_id, state)` - Save state
- `restore_connection_state(connection_id)` - Restore state
- `disconnect(connection_id, save_state)` - Disconnect
- `cleanup_stale_connections()` - Cleanup stale connections
- `get_connection_stats()` - Get statistics

### HeartbeatMonitor

Heartbeat monitoring for connection health.

**Constructor:**
```python
HeartbeatMonitor(config: Optional[HeartbeatConfig] = None)
```

**Methods:**
- `register_connection(connection_id)` - Register for monitoring
- `unregister_connection(connection_id)` - Unregister
- `update_heartbeat(connection_id)` - Update heartbeat timestamp
- `is_stale(connection_id)` - Check if stale
- `start(ping_callback, cleanup_callback, miss_callback)` - Start monitoring
- `stop()` - Stop monitoring
- `get_stats()` - Get statistics

### MetricsCollector

Connection metrics collection.

**Constructor:**
```python
MetricsCollector()
```

**Methods:**
- `register_connection(connection_id, user_id)` - Register connection
- `unregister_connection(connection_id)` - Unregister connection
- `record_message_sent(connection_id, size_bytes)` - Record sent message
- `record_message_received(connection_id, size_bytes)` - Record received message
- `record_latency(latency_ms)` - Record message latency
- `record_error(connection_id)` - Record error
- `get_connection_metrics(connection_id)` - Get connection metrics
- `get_user_metrics(user_id)` - Get user metrics
- `get_stats()` - Get aggregated statistics

## Testing

Run the test suite:

```bash
pytest
```

With coverage:

```bash
pytest --cov=netrun.websocket --cov-report=html
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Support

For issues, questions, or contributions, please visit:
- GitHub: https://github.com/netrunsystems/netrun-websocket
- Email: engineering@netrunsystems.com

## Related Packages

- `netrun-auth` - Authentication and authorization utilities
- `netrun-db-pool` - Database connection pooling
- `netrun-config` - Configuration management
- `netrun-logging` - Structured logging

---

**Netrun Systems** - Production-Grade Infrastructure for Modern Applications
