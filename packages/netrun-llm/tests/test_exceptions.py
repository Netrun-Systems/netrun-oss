"""
Tests for LLM Exception Classes.

Tests cover:
    - All exception types
    - Exception initialization with various parameters
    - Exception string representations
    - Exception details and attributes
    - Error context preservation
"""

import pytest
from netrun.llm.exceptions import (
    LLMError,
    AdapterUnavailableError,
    RateLimitError,
    CircuitBreakerOpenError,
    AllAdaptersFailedError,
    AuthenticationError,
    TimeoutError,
    CognitionTimeoutError,
)


class TestLLMError:
    """Test base LLMError exception."""

    def test_basic_initialization(self):
        """Test LLMError with just message."""
        error = LLMError("Test error message")

        assert error.message == "Test error message"
        assert error.adapter_name is None
        assert error.details == {}
        assert str(error) == "Test error message"

    def test_initialization_with_adapter_name(self):
        """Test LLMError with adapter name."""
        error = LLMError("Test error", adapter_name="TestAdapter")

        assert error.adapter_name == "TestAdapter"
        assert str(error) == "[TestAdapter] Test error"

    def test_initialization_with_details(self):
        """Test LLMError with custom details."""
        details = {"key1": "value1", "key2": 42}
        error = LLMError("Test error", details=details)

        assert error.details == details
        assert error.details["key1"] == "value1"
        assert error.details["key2"] == 42

    def test_initialization_with_all_params(self):
        """Test LLMError with all parameters."""
        error = LLMError(
            message="Complete error",
            adapter_name="CompleteAdapter",
            details={"extra": "info"}
        )

        assert error.message == "Complete error"
        assert error.adapter_name == "CompleteAdapter"
        assert error.details == {"extra": "info"}
        assert str(error) == "[CompleteAdapter] Complete error"

    def test_is_exception_instance(self):
        """Test LLMError is proper Exception."""
        error = LLMError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, LLMError)


class TestAdapterUnavailableError:
    """Test AdapterUnavailableError exception."""

    def test_initialization_basic(self):
        """Test basic initialization."""
        error = AdapterUnavailableError(
            message="Adapter is down",
            adapter_name="TestAdapter"
        )

        assert error.message == "Adapter is down"
        assert error.adapter_name == "TestAdapter"
        assert error.reason is None
        assert error.details == {}

    def test_initialization_with_reason(self):
        """Test initialization with reason."""
        error = AdapterUnavailableError(
            message="Adapter unavailable",
            adapter_name="TestAdapter",
            reason="Health check failed"
        )

        assert error.reason == "Health check failed"
        assert error.details == {"reason": "Health check failed"}

    def test_inherits_from_llm_error(self):
        """Test AdapterUnavailableError inherits from LLMError."""
        error = AdapterUnavailableError("Test", "TestAdapter")

        assert isinstance(error, LLMError)
        assert isinstance(error, AdapterUnavailableError)

    def test_string_representation(self):
        """Test string representation includes adapter name."""
        error = AdapterUnavailableError(
            message="Cannot connect",
            adapter_name="BrokenAdapter"
        )

        assert str(error) == "[BrokenAdapter] Cannot connect"


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_initialization_without_retry_after(self):
        """Test initialization without retry_after."""
        error = RateLimitError(
            message="Rate limit exceeded",
            adapter_name="APIAdapter"
        )

        assert error.message == "Rate limit exceeded"
        assert error.adapter_name == "APIAdapter"
        assert error.retry_after_seconds is None

    def test_initialization_with_retry_after(self):
        """Test initialization with retry_after_seconds."""
        error = RateLimitError(
            message="Rate limit hit",
            adapter_name="APIAdapter",
            retry_after_seconds=60
        )

        assert error.retry_after_seconds == 60
        assert error.details == {"retry_after_seconds": 60}

    def test_inherits_from_llm_error(self):
        """Test RateLimitError inherits from LLMError."""
        error = RateLimitError("Test", "TestAdapter")

        assert isinstance(error, LLMError)
        assert isinstance(error, RateLimitError)

    def test_zero_retry_after(self):
        """Test with zero retry_after_seconds."""
        error = RateLimitError(
            message="Immediate retry",
            adapter_name="APIAdapter",
            retry_after_seconds=0
        )

        assert error.retry_after_seconds == 0


class TestCircuitBreakerOpenError:
    """Test CircuitBreakerOpenError exception."""

    def test_initialization_without_cooldown(self):
        """Test initialization without cooldown time."""
        error = CircuitBreakerOpenError(
            message="Circuit breaker open",
            adapter_name="FailingAdapter"
        )

        assert error.message == "Circuit breaker open"
        assert error.adapter_name == "FailingAdapter"
        assert error.cooldown_remaining_seconds is None

    def test_initialization_with_cooldown(self):
        """Test initialization with cooldown time."""
        error = CircuitBreakerOpenError(
            message="Circuit open",
            adapter_name="FailingAdapter",
            cooldown_remaining_seconds=30.5
        )

        assert error.cooldown_remaining_seconds == 30.5
        assert error.details == {"cooldown_remaining_seconds": 30.5}

    def test_inherits_from_llm_error(self):
        """Test CircuitBreakerOpenError inherits from LLMError."""
        error = CircuitBreakerOpenError("Test", "TestAdapter")

        assert isinstance(error, LLMError)
        assert isinstance(error, CircuitBreakerOpenError)

    def test_string_representation(self):
        """Test string representation."""
        error = CircuitBreakerOpenError(
            message="Adapter circuit open",
            adapter_name="BrokenAdapter",
            cooldown_remaining_seconds=15.0
        )

        assert str(error) == "[BrokenAdapter] Adapter circuit open"


class TestAllAdaptersFailedError:
    """Test AllAdaptersFailedError exception."""

    def test_initialization_basic(self):
        """Test basic initialization with failed adapters."""
        error = AllAdaptersFailedError(
            message="All failed",
            failed_adapters=["Adapter1", "Adapter2"]
        )

        assert error.message == "All failed"
        assert error.failed_adapters == ["Adapter1", "Adapter2"]
        assert error.errors == {}

    def test_initialization_with_errors(self):
        """Test initialization with error details."""
        errors = {
            "Adapter1": "Connection timeout",
            "Adapter2": "Rate limit exceeded"
        }
        error = AllAdaptersFailedError(
            message="Chain failed",
            failed_adapters=["Adapter1", "Adapter2"],
            errors=errors
        )

        assert error.errors == errors
        assert error.details["errors"] == errors
        assert error.details["failed_adapters"] == ["Adapter1", "Adapter2"]

    def test_string_representation(self):
        """Test custom string representation."""
        error = AllAdaptersFailedError(
            message="Complete failure",
            failed_adapters=["Claude", "GPT-4", "Ollama"]
        )

        error_str = str(error)
        assert "Complete failure" in error_str
        assert "tried: Claude, GPT-4, Ollama" in error_str

    def test_empty_failed_adapters(self):
        """Test with empty failed adapters list."""
        error = AllAdaptersFailedError(
            message="No adapters",
            failed_adapters=[]
        )

        assert error.failed_adapters == []
        assert str(error) == "No adapters (tried: )"

    def test_inherits_from_llm_error(self):
        """Test AllAdaptersFailedError inherits from LLMError."""
        error = AllAdaptersFailedError("Test", [])

        assert isinstance(error, LLMError)
        assert isinstance(error, AllAdaptersFailedError)


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_initialization(self):
        """Test initialization."""
        error = AuthenticationError(
            message="Invalid API key",
            adapter_name="SecureAdapter"
        )

        assert error.message == "Invalid API key"
        assert error.adapter_name == "SecureAdapter"

    def test_inherits_from_llm_error(self):
        """Test AuthenticationError inherits from LLMError."""
        error = AuthenticationError("Test", "TestAdapter")

        assert isinstance(error, LLMError)
        assert isinstance(error, AuthenticationError)

    def test_string_representation(self):
        """Test string representation."""
        error = AuthenticationError(
            message="Auth failed",
            adapter_name="ClaudeAdapter"
        )

        assert str(error) == "[ClaudeAdapter] Auth failed"


class TestTimeoutError:
    """Test TimeoutError exception."""

    def test_initialization_without_timeout_value(self):
        """Test initialization without timeout value."""
        error = TimeoutError(
            message="Request timed out",
            adapter_name="SlowAdapter"
        )

        assert error.message == "Request timed out"
        assert error.adapter_name == "SlowAdapter"
        assert error.timeout_seconds is None

    def test_initialization_with_timeout_value(self):
        """Test initialization with timeout value."""
        error = TimeoutError(
            message="Timeout occurred",
            adapter_name="SlowAdapter",
            timeout_seconds=30.0
        )

        assert error.timeout_seconds == 30.0
        assert error.details == {"timeout_seconds": 30.0}

    def test_inherits_from_llm_error(self):
        """Test TimeoutError inherits from LLMError."""
        error = TimeoutError("Test", "TestAdapter")

        assert isinstance(error, LLMError)
        assert isinstance(error, TimeoutError)

    def test_fractional_timeout(self):
        """Test with fractional timeout seconds."""
        error = TimeoutError(
            message="Quick timeout",
            adapter_name="FastAdapter",
            timeout_seconds=0.5
        )

        assert error.timeout_seconds == 0.5


class TestCognitionTimeoutError:
    """Test CognitionTimeoutError exception."""

    def test_initialization(self):
        """Test initialization with all parameters."""
        error = CognitionTimeoutError(
            message="Cognition tier timeout",
            tier_name="DEEP",
            target_latency_ms=5000,
            actual_latency_ms=7500
        )

        assert error.message == "Cognition tier timeout"
        assert error.tier_name == "DEEP"
        assert error.target_latency_ms == 5000
        assert error.actual_latency_ms == 7500

    def test_details_populated(self):
        """Test details dictionary is properly populated."""
        error = CognitionTimeoutError(
            message="RAG timeout",
            tier_name="RAG",
            target_latency_ms=2000,
            actual_latency_ms=3000
        )

        assert error.details["tier_name"] == "RAG"
        assert error.details["target_latency_ms"] == 2000
        assert error.details["actual_latency_ms"] == 3000

    def test_inherits_from_llm_error(self):
        """Test CognitionTimeoutError inherits from LLMError."""
        error = CognitionTimeoutError(
            message="Test",
            tier_name="TEST",
            target_latency_ms=100,
            actual_latency_ms=200
        )

        assert isinstance(error, LLMError)
        assert isinstance(error, CognitionTimeoutError)

    def test_fast_ack_timeout(self):
        """Test with FAST_ACK tier timeout."""
        error = CognitionTimeoutError(
            message="Fast ack too slow",
            tier_name="FAST_ACK",
            target_latency_ms=100,
            actual_latency_ms=150
        )

        assert error.tier_name == "FAST_ACK"
        assert error.actual_latency_ms > error.target_latency_ms


class TestExceptionRaising:
    """Test exceptions can be raised and caught properly."""

    def test_raise_and_catch_llm_error(self):
        """Test raising and catching LLMError."""
        with pytest.raises(LLMError) as exc_info:
            raise LLMError("Test error")

        assert exc_info.value.message == "Test error"

    def test_catch_specific_exception(self):
        """Test catching specific exception type."""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("Rate limited", "TestAdapter", retry_after_seconds=60)

        assert exc_info.value.retry_after_seconds == 60

    def test_catch_base_exception_for_derived(self):
        """Test catching base LLMError for derived exceptions."""
        with pytest.raises(LLMError):
            raise AuthenticationError("Auth failed", "TestAdapter")

    def test_exception_chain(self):
        """Test exception chaining with from."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise LLMError("Wrapped error") from e
        except LLMError as error:
            assert error.message == "Wrapped error"
            assert isinstance(error.__cause__, ValueError)
