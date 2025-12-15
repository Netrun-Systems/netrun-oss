"""
Custom configuration types for netrun-config.

Provides reusable types for common configuration patterns.
"""

from typing import Literal

# Common type aliases
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
Environment = Literal["development", "staging", "production", "testing"]
