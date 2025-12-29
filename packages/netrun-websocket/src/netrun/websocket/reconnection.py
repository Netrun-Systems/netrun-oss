"""
WebSocket Reconnection with Exponential Backoff
File: reconnection.py
Netrun Systems - SDLC v2.3 Compliant

Implements exponential backoff reconnection strategy for WebSocket clients
with configurable max attempts and backoff parameters.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReconnectionConfig:
    """
    Reconnection configuration.

    Attributes:
        initial_delay: Initial delay in seconds (default: 1)
        max_delay: Maximum delay in seconds (default: 60)
        max_attempts: Maximum reconnection attempts (default: 10, 0 = infinite)
        backoff_multiplier: Backoff multiplier (default: 2.0)
        jitter: Add random jitter to delays (default: True)
        jitter_factor: Jitter factor 0.0-1.0 (default: 0.1)
    """

    initial_delay: float = 1.0
    max_delay: float = 60.0
    max_attempts: int = 10  # 0 = infinite
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1


class ReconnectionManager:
    """
    Manages WebSocket reconnection with exponential backoff.

    Provides automatic reconnection with configurable backoff strategy,
    max attempts, and callbacks for connection events.

    Usage:
        config = ReconnectionConfig(max_attempts=5)
        manager = ReconnectionManager(config)

        async def connect_callback():
            # Reconnection logic here
            return await establish_connection()

        await manager.reconnect(connect_callback)
    """

    def __init__(self, config: Optional[ReconnectionConfig] = None):
        """
        Initialize reconnection manager.

        Args:
            config: ReconnectionConfig instance (uses defaults if None)
        """
        self.config = config or ReconnectionConfig()
        self.attempt = 0
        self.connected = False
        self.last_attempt_time: Optional[datetime] = None

    def reset(self):
        """Reset reconnection state."""
        self.attempt = 0
        self.connected = False
        self.last_attempt_time = None
        logger.debug("Reconnection state reset")

    def calculate_delay(self) -> float:
        """
        Calculate next reconnection delay using exponential backoff.

        Returns:
            Delay in seconds
        """
        # Calculate base delay
        delay = min(
            self.config.initial_delay * (self.config.backoff_multiplier ** self.attempt),
            self.config.max_delay
        )

        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        return delay

    async def reconnect(
        self,
        connect_callback: Callable,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
        on_max_attempts: Optional[Callable] = None
    ) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Args:
            connect_callback: Async function to establish connection
            on_success: Optional callback on successful reconnection
            on_failure: Optional callback on failed reconnection attempt
            on_max_attempts: Optional callback when max attempts reached

        Returns:
            True if reconnected successfully, False otherwise
        """
        self.reset()

        while True:
            # Check max attempts
            if self.config.max_attempts > 0 and self.attempt >= self.config.max_attempts:
                logger.warning(
                    f"Max reconnection attempts ({self.config.max_attempts}) reached"
                )
                if on_max_attempts:
                    await on_max_attempts()
                return False

            # Calculate delay
            if self.attempt > 0:
                delay = self.calculate_delay()
                logger.info(
                    f"Reconnection attempt {self.attempt + 1} "
                    f"in {delay:.2f} seconds..."
                )
                await asyncio.sleep(delay)

            # Attempt connection
            self.attempt += 1
            self.last_attempt_time = datetime.now(timezone.utc)

            try:
                result = await connect_callback()

                if result:
                    self.connected = True
                    logger.info(
                        f"Reconnection successful after {self.attempt} attempt(s)"
                    )
                    if on_success:
                        await on_success()
                    return True
                else:
                    logger.warning(f"Reconnection attempt {self.attempt} failed")
                    if on_failure:
                        await on_failure(self.attempt)

            except Exception as e:
                logger.error(
                    f"Reconnection attempt {self.attempt} error: {e}",
                    exc_info=True
                )
                if on_failure:
                    await on_failure(self.attempt)

    def get_stats(self) -> dict:
        """
        Get reconnection statistics.

        Returns:
            Dict with reconnection stats
        """
        return {
            "attempt": self.attempt,
            "connected": self.connected,
            "last_attempt_time": (
                self.last_attempt_time.isoformat() if self.last_attempt_time else None
            ),
            "config": {
                "initial_delay": self.config.initial_delay,
                "max_delay": self.config.max_delay,
                "max_attempts": self.config.max_attempts,
                "backoff_multiplier": self.config.backoff_multiplier,
                "jitter": self.config.jitter
            }
        }


class ReconnectionTracker:
    """
    Track reconnection attempts across multiple connections.

    Useful for monitoring reconnection patterns and identifying
    problematic connections or network issues.
    """

    def __init__(self):
        """Initialize reconnection tracker."""
        self.connections: dict = {}  # connection_id -> stats

    def record_attempt(self, connection_id: str, success: bool):
        """
        Record reconnection attempt.

        Args:
            connection_id: Connection identifier
            success: Whether attempt was successful
        """
        if connection_id not in self.connections:
            self.connections[connection_id] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "last_attempt": None,
                "last_success": None
            }

        stats = self.connections[connection_id]
        stats["total_attempts"] += 1
        stats["last_attempt"] = datetime.now(timezone.utc).isoformat()

        if success:
            stats["successful_attempts"] += 1
            stats["last_success"] = stats["last_attempt"]
        else:
            stats["failed_attempts"] += 1

        logger.debug(
            f"Reconnection attempt recorded for {connection_id}: "
            f"success={success}, total={stats['total_attempts']}"
        )

    def get_connection_stats(self, connection_id: str) -> Optional[dict]:
        """
        Get reconnection stats for specific connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Dict of stats or None
        """
        return self.connections.get(connection_id)

    def get_global_stats(self) -> dict:
        """
        Get global reconnection statistics.

        Returns:
            Dict with aggregated stats
        """
        total_attempts = sum(
            stats["total_attempts"] for stats in self.connections.values()
        )
        successful_attempts = sum(
            stats["successful_attempts"] for stats in self.connections.values()
        )
        failed_attempts = sum(
            stats["failed_attempts"] for stats in self.connections.values()
        )

        success_rate = (
            (successful_attempts / total_attempts * 100)
            if total_attempts > 0 else 0
        )

        return {
            "total_connections": len(self.connections),
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "failed_attempts": failed_attempts,
            "success_rate": f"{success_rate:.2f}%"
        }

    def clear_connection(self, connection_id: str):
        """
        Clear stats for specific connection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connections:
            del self.connections[connection_id]
            logger.debug(f"Cleared reconnection stats for {connection_id}")


__all__ = [
    "ReconnectionConfig",
    "ReconnectionManager",
    "ReconnectionTracker",
]
