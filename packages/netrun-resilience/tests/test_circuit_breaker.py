"""Tests for circuit breaker decorator."""

import asyncio
import pytest
import time
from netrun.resilience import circuit_breaker, CircuitOpenError, CircuitState


class TestCircuitBreaker:
    """Test circuit breaker decorator with sync and async functions."""

    def test_circuit_breaker_closed_state(self):
        """Test normal operation in CLOSED state."""
        @circuit_breaker(failure_threshold=3)
        def normal_func():
            return "success"

        result = normal_func()
        assert result == "success"
        assert normal_func.circuit_breaker.get_state() == CircuitState.CLOSED

    async def test_circuit_breaker_async_closed_state(self):
        """Test async normal operation in CLOSED state."""
        @circuit_breaker(failure_threshold=3)
        async def normal_func():
            return "success"

        result = await normal_func()
        assert result == "success"
        assert normal_func.circuit_breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit opens after failure threshold."""
        call_count = [0]

        @circuit_breaker(failure_threshold=3)
        def failing_func():
            call_count[0] += 1
            raise ConnectionError("Service unavailable")

        # First 3 calls should raise ConnectionError
        for i in range(3):
            with pytest.raises(ConnectionError):
                failing_func()

        # Circuit should now be OPEN
        assert failing_func.circuit_breaker.get_state() == CircuitState.OPEN

        # Next call should raise CircuitOpenError
        with pytest.raises(CircuitOpenError):
            failing_func()

        assert call_count[0] == 3  # Circuit breaker prevented 4th call

    async def test_circuit_breaker_async_opens_on_failures(self):
        """Test async circuit opens after failure threshold."""
        call_count = [0]

        @circuit_breaker(failure_threshold=3)
        async def failing_func():
            call_count[0] += 1
            raise ConnectionError("Service unavailable")

        # First 3 calls should raise ConnectionError
        for i in range(3):
            with pytest.raises(ConnectionError):
                await failing_func()

        # Circuit should now be OPEN
        assert failing_func.circuit_breaker.get_state() == CircuitState.OPEN

        # Next call should raise CircuitOpenError
        with pytest.raises(CircuitOpenError):
            await failing_func()

        assert call_count[0] == 3

    def test_circuit_breaker_half_open_transition(self):
        """Test transition from OPEN to HALF_OPEN after timeout."""
        call_count = [0]

        @circuit_breaker(failure_threshold=2, timeout_seconds=0.1)
        def recoverable_func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Temporary failure")
            return "success"

        # Trigger circuit opening
        for i in range(2):
            with pytest.raises(ConnectionError):
                recoverable_func()

        assert recoverable_func.circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next call should transition to HALF_OPEN and succeed
        result = recoverable_func()
        assert result == "success"
        assert recoverable_func.circuit_breaker.get_state() == CircuitState.HALF_OPEN

    async def test_circuit_breaker_async_half_open_transition(self):
        """Test async transition from OPEN to HALF_OPEN after timeout."""
        call_count = [0]

        @circuit_breaker(failure_threshold=2, timeout_seconds=0.1)
        async def recoverable_func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Temporary failure")
            return "success"

        # Trigger circuit opening
        for i in range(2):
            with pytest.raises(ConnectionError):
                await recoverable_func()

        assert recoverable_func.circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should transition to HALF_OPEN and succeed
        result = await recoverable_func()
        assert result == "success"
        assert recoverable_func.circuit_breaker.get_state() == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_successes(self):
        """Test circuit closes after success threshold in HALF_OPEN."""
        call_count = [0]

        @circuit_breaker(failure_threshold=2, success_threshold=3, timeout_seconds=0.1)
        def func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Failure")
            return "success"

        # Open circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                func()

        # Wait for timeout
        time.sleep(0.15)

        # 3 successful calls in HALF_OPEN should close circuit
        for i in range(3):
            result = func()
            assert result == "success"

        assert func.circuit_breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_reopens_on_half_open_failure(self):
        """Test circuit reopens if failure occurs in HALF_OPEN."""
        call_count = [0]

        @circuit_breaker(failure_threshold=2, timeout_seconds=0.1)
        def unstable_func():
            call_count[0] += 1
            if call_count[0] <= 2 or call_count[0] == 4:
                raise ConnectionError("Failure")
            return "success"

        # Open circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                unstable_func()

        # Wait for timeout
        time.sleep(0.15)

        # First HALF_OPEN call succeeds
        result = unstable_func()
        assert result == "success"
        assert unstable_func.circuit_breaker.get_state() == CircuitState.HALF_OPEN

        # Second HALF_OPEN call fails - circuit should reopen
        with pytest.raises(ConnectionError):
            unstable_func()

        assert unstable_func.circuit_breaker.get_state() == CircuitState.OPEN

    def test_circuit_breaker_manual_reset(self):
        """Test manual circuit reset."""
        @circuit_breaker(failure_threshold=2)
        def failing_func():
            raise ConnectionError("Failure")

        # Open circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                failing_func()

        assert failing_func.circuit_breaker.get_state() == CircuitState.OPEN

        # Manual reset
        failing_func.circuit_breaker.reset()
        assert failing_func.circuit_breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics."""
        call_count = [0]

        @circuit_breaker(failure_threshold=3)
        def func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Failure")
            return "success"

        # 2 failures
        for i in range(2):
            with pytest.raises(ConnectionError):
                func()

        metrics = func.circuit_breaker.get_metrics()
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 2

        # 1 success
        func()
        metrics = func.circuit_breaker.get_metrics()
        assert metrics["failure_count"] == 1  # Decremented on success

    def test_circuit_breaker_state_callback(self):
        """Test state change callback."""
        state_changes = []

        def on_state_change(old_state, new_state):
            state_changes.append((old_state, new_state))

        @circuit_breaker(failure_threshold=2, on_state_change=on_state_change)
        def func():
            raise ConnectionError("Failure")

        # Trigger state change to OPEN
        for i in range(2):
            with pytest.raises(ConnectionError):
                func()

        assert len(state_changes) == 1
        assert state_changes[0] == (CircuitState.CLOSED, CircuitState.OPEN)

    async def test_circuit_breaker_half_open_metrics(self):
        """Test circuit breaker metrics in HALF_OPEN state."""
        call_count = [0]

        @circuit_breaker(failure_threshold=2, timeout_seconds=0.1, success_threshold=2)
        async def func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Failure")
            return "success"

        # Open circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                await func()

        metrics = func.circuit_breaker.get_metrics()
        assert metrics["state"] == "open"

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Success in HALF_OPEN
        result = await func()
        assert result == "success"

        metrics = func.circuit_breaker.get_metrics()
        assert metrics["state"] == "half_open"
        assert metrics["success_count"] == 1
