"""
Netrun LLM - Exception Classes

Structured exceptions for LLM orchestration with comprehensive error context.
"""

from typing import Optional, Dict, Any, List


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.adapter_name = adapter_name
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.adapter_name:
            return f"[{self.adapter_name}] {self.message}"
        return self.message


class AdapterUnavailableError(LLMError):
    """Raised when an adapter is unavailable (health check failed, not configured)."""

    def __init__(
        self,
        message: str,
        adapter_name: str,
        reason: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            details={"reason": reason} if reason else {},
        )
        self.reason = reason


class RateLimitError(LLMError):
    """Raised when rate limit is hit on an adapter."""

    def __init__(
        self,
        message: str,
        adapter_name: str,
        retry_after_seconds: Optional[int] = None,
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            details={"retry_after_seconds": retry_after_seconds},
        )
        self.retry_after_seconds = retry_after_seconds


class CircuitBreakerOpenError(LLMError):
    """Raised when circuit breaker is open (too many consecutive failures)."""

    def __init__(
        self,
        message: str,
        adapter_name: str,
        cooldown_remaining_seconds: Optional[float] = None,
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            details={"cooldown_remaining_seconds": cooldown_remaining_seconds},
        )
        self.cooldown_remaining_seconds = cooldown_remaining_seconds


class AllAdaptersFailedError(LLMError):
    """Raised when all adapters in a fallback chain have failed."""

    def __init__(
        self,
        message: str,
        failed_adapters: List[str],
        errors: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            message=message,
            details={
                "failed_adapters": failed_adapters,
                "errors": errors or {},
            },
        )
        self.failed_adapters = failed_adapters
        self.errors = errors or {}

    def __str__(self) -> str:
        adapter_list = ", ".join(self.failed_adapters)
        return f"{self.message} (tried: {adapter_list})"


class AuthenticationError(LLMError):
    """Raised when authentication fails (invalid API key)."""

    def __init__(self, message: str, adapter_name: str):
        super().__init__(message=message, adapter_name=adapter_name)


class TimeoutError(LLMError):
    """Raised when request times out."""

    def __init__(
        self,
        message: str,
        adapter_name: str,
        timeout_seconds: Optional[float] = None,
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            details={"timeout_seconds": timeout_seconds},
        )
        self.timeout_seconds = timeout_seconds


class CognitionTimeoutError(LLMError):
    """Raised when a cognition tier times out."""

    def __init__(
        self,
        message: str,
        tier_name: str,
        target_latency_ms: int,
        actual_latency_ms: int,
    ):
        super().__init__(
            message=message,
            details={
                "tier_name": tier_name,
                "target_latency_ms": target_latency_ms,
                "actual_latency_ms": actual_latency_ms,
            },
        )
        self.tier_name = tier_name
        self.target_latency_ms = target_latency_ms
        self.actual_latency_ms = actual_latency_ms
