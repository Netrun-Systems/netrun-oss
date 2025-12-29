"""
Type definitions for netrun-cache package.

Provides type-safe configuration and statistics models.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CacheBackend(str, Enum):
    """Cache backend types."""

    REDIS = "redis"
    MEMORY = "memory"
    MULTI_LAYER = "multi_layer"


class CacheConfig(BaseModel):
    """Cache configuration model."""

    backend: CacheBackend = Field(
        default=CacheBackend.MEMORY, description="Cache backend to use"
    )
    namespace: str = Field(default="cache", description="Cache namespace for key isolation")
    default_ttl: int = Field(default=3600, description="Default TTL in seconds", gt=0)
    max_size: Optional[int] = Field(
        default=1000, description="Maximum cache size (memory backend only)", gt=0
    )

    # Redis-specific configuration
    redis_url: Optional[str] = Field(
        default=None, description="Redis connection URL (redis://host:port/db)"
    )
    redis_host: Optional[str] = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port", gt=0, lt=65536)
    redis_db: int = Field(default=0, description="Redis database number", ge=0)
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    socket_timeout: int = Field(default=5, description="Redis socket timeout in seconds", gt=0)
    socket_connect_timeout: int = Field(
        default=5, description="Redis socket connect timeout in seconds", gt=0
    )

    # Multi-layer configuration
    l1_max_size: int = Field(
        default=100, description="L1 (memory) cache max size for multi-layer", gt=0
    )
    l1_ttl: int = Field(default=300, description="L1 (memory) cache TTL in seconds", gt=0)


class CacheStats(BaseModel):
    """Cache statistics model."""

    namespace: str = Field(description="Cache namespace")
    hits: int = Field(default=0, description="Cache hits", ge=0)
    misses: int = Field(default=0, description="Cache misses", ge=0)
    total_requests: int = Field(default=0, description="Total cache requests", ge=0)
    hit_rate_percent: float = Field(
        default=0.0, description="Cache hit rate percentage", ge=0.0, le=100.0
    )
    cached_keys: int = Field(default=0, description="Number of cached keys", ge=0)
    backend: str = Field(default="unknown", description="Cache backend type")
    connected: bool = Field(default=False, description="Backend connection status")

    @property
    def hit_rate(self) -> float:
        """Get hit rate as decimal (0.0 to 1.0)."""
        return self.hit_rate_percent / 100.0
