"""
Base exception class for Netrun Systems unified error handling.

Provides structured error responses with correlation IDs, timestamps,
and machine-readable error codes for FastAPI applications.

v1.1.0: Added netrun-logging integration for structured exception logging.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING
from uuid import uuid4

from fastapi import HTTPException, status

# Optional netrun-logging integration (soft dependency)
_netrun_logging_available = False
_get_correlation_id = None

try:
    from netrun_logging import get_correlation_id as _logging_get_correlation_id
    _netrun_logging_available = True
    _get_correlation_id = _logging_get_correlation_id
except ImportError:
    pass


class NetrunException(HTTPException):
    """
    Base exception class for all Netrun Systems exceptions.

    Extends FastAPI's HTTPException with additional metadata:
    - error_code: Machine-readable error identifier
    - correlation_id: Request tracking identifier
    - timestamp: ISO 8601 formatted timestamp
    - details: Additional context dictionary

    All Netrun exceptions inherit from this class and return structured
    JSON responses compatible with frontend error handling.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        Initialize NetrunException with structured error data.

        Args:
            status_code: HTTP status code (401, 403, 404, etc.)
            error_code: Machine-readable error code (e.g., "AUTH_INVALID_CREDENTIALS")
            message: Human-readable error message
            details: Additional context dictionary (optional)
            correlation_id: Request tracking ID (auto-generated if not provided)
        """
        self.error_code = error_code
        self.message = message
        self.correlation_id = correlation_id or self._get_or_generate_correlation_id()
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.details = details or {}

        # Store message as detail for HTTPException (plain string)
        super().__init__(status_code=status_code, detail=message)

    @staticmethod
    def _get_or_generate_correlation_id() -> str:
        """
        Get correlation ID from netrun-logging context or generate a new one.

        If netrun-logging is available and has an active correlation ID,
        uses that for consistent request tracking. Otherwise generates a new ID.

        Returns:
            Correlation ID string
        """
        # Try to get correlation ID from netrun-logging context
        if _netrun_logging_available and _get_correlation_id is not None:
            try:
                existing_id = _get_correlation_id()
                if existing_id:
                    return existing_id
            except Exception:
                pass  # Fall through to generate new ID

        return NetrunException._generate_correlation_id()

    @staticmethod
    def _generate_correlation_id() -> str:
        """
        Generate a unique correlation ID for request tracking.

        Format: req-YYYYMMDD-HHMMSS-uuid4_prefix
        Example: req-20251125-143210-a8f3c9

        Returns:
            Correlation ID string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        uuid_prefix = str(uuid4())[:6]
        return f"req-{timestamp}-{uuid_prefix}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.

        Returns:
            Dictionary with error structure
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp,
            }
        }
