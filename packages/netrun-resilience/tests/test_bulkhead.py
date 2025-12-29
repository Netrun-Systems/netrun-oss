"""Tests for bulkhead decorator."""

import asyncio
import pytest
import time
from netrun.resilience import bulkhead, BulkheadFullError


class TestBulkhead:
    """Test bulkhead decorator with sync and async functions."""

    async def test_bulkhead_async_within_limit(self):
        """Test async execution within concurrency limit."""
        @bulkhead(max_concurrent=5)
        async def func():
            await asyncio.sleep(0.1)
            return "success"

        # Run 3 concurrent (within limit of 5)
        results = await asyncio.gather(*[func() for _ in range(3)])
        assert all(r == "success" for r in results)

    async def test_bulkhead_async_at_limit(self):
        """Test async execution at concurrency limit."""
        active_count = [0]
        max_active = [0]

        @bulkhead(max_concurrent=3, max_queue=10)
        async def func():
            active_count[0] += 1
            max_active[0] = max(max_active[0], active_count[0])
            await asyncio.sleep(0.1)
            active_count[0] -= 1
            return "success"

        # Run 10 concurrent (3 active, 7 queued)
        results = await asyncio.gather(*[func() for _ in range(10)])
        assert all(r == "success" for r in results)
        assert max_active[0] <= 3  # Never exceeded limit

    async def test_bulkhead_async_exceeds_limit(self):
        """Test async rejection when bulkhead is full."""
        @bulkhead(max_concurrent=2, max_queue=3)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "success"

        # Start 5 tasks (2 active, 3 queued)
        tasks = [asyncio.create_task(slow_func()) for _ in range(5)]
        await asyncio.sleep(0.01)  # Let tasks start

        # 6th task should be rejected
        with pytest.raises(BulkheadFullError) as exc_info:
            await slow_func()

        assert "Bulkhead full" in str(exc_info.value)

        # Clean up
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def test_bulkhead_sync_within_limit(self):
        """Test sync execution within concurrency limit."""
        @bulkhead(max_concurrent=5)
        def func():
            time.sleep(0.05)
            return "success"

        result = func()
        assert result == "success"

    def test_bulkhead_sync_exceeds_limit(self):
        """Test sync rejection when bulkhead is full."""
        import threading

        @bulkhead(max_concurrent=2, max_queue=2)
        def slow_func():
            time.sleep(0.5)
            return "success"

        # Start 4 threads (2 active, 2 queued)
        threads = [threading.Thread(target=slow_func) for _ in range(4)]
        for t in threads:
            t.start()

        time.sleep(0.1)  # Let threads start

        # 5th call should be rejected
        with pytest.raises(BulkheadFullError):
            slow_func()

        # Wait for threads
        for t in threads:
            t.join()

    async def test_bulkhead_async_metrics(self):
        """Test bulkhead metrics tracking."""
        @bulkhead(max_concurrent=3, max_queue=10)
        async def func():
            await asyncio.sleep(0.1)
            return "success"

        # Get initial metrics
        metrics = func.bulkhead.get_metrics()
        assert metrics["max_concurrent"] == 3
        assert metrics["max_queue"] == 10
        assert metrics["total_accepted"] == 0

        # Run some tasks
        await asyncio.gather(*[func() for _ in range(5)])

        # Check metrics
        metrics = func.bulkhead.get_metrics()
        assert metrics["total_accepted"] == 5
        assert metrics["total_rejected"] == 0

    async def test_bulkhead_async_rejection_metrics(self):
        """Test bulkhead rejection metrics."""
        @bulkhead(max_concurrent=1, max_queue=1)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "success"

        # Start 2 tasks (1 active, 1 queued)
        tasks = [asyncio.create_task(slow_func()) for _ in range(2)]
        await asyncio.sleep(0.01)

        # 3rd should be rejected
        try:
            await slow_func()
        except BulkheadFullError:
            pass

        metrics = slow_func.bulkhead.get_metrics()
        assert metrics["total_rejected"] == 1

        # Clean up
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def test_bulkhead_async_queue_processing(self):
        """Test queued tasks are processed when slots free."""
        execution_order = []

        @bulkhead(max_concurrent=2, max_queue=5)
        async def func(task_id):
            execution_order.append(f"start-{task_id}")
            await asyncio.sleep(0.1)
            execution_order.append(f"end-{task_id}")
            return task_id

        # Run 5 tasks (2 active initially, 3 queued)
        results = await asyncio.gather(*[func(i) for i in range(5)])
        assert results == [0, 1, 2, 3, 4]

        # Verify tasks ran (some queued, then processed)
        assert len(execution_order) == 10  # 5 starts + 5 ends

    async def test_bulkhead_async_exception_handling(self):
        """Test bulkhead handles exceptions properly."""
        @bulkhead(max_concurrent=2)
        async def failing_func():
            await asyncio.sleep(0.05)
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_func()

        # Metrics should still be tracked
        metrics = failing_func.bulkhead.get_metrics()
        assert metrics["total_accepted"] == 1

    def test_bulkhead_sync_exception_handling(self):
        """Test bulkhead handles sync exceptions properly."""
        @bulkhead(max_concurrent=2)
        def failing_func():
            time.sleep(0.05)
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_func()

        # Metrics should still be tracked
        metrics = failing_func.bulkhead.get_metrics()
        assert metrics["total_accepted"] == 1

    async def test_bulkhead_zero_queue(self):
        """Test bulkhead with zero queue size."""
        @bulkhead(max_concurrent=1, max_queue=0)
        async def func():
            await asyncio.sleep(0.2)
            return "success"

        # Start 1 task (fills concurrency)
        task = asyncio.create_task(func())
        await asyncio.sleep(0.01)

        # 2nd task should be rejected (no queue)
        with pytest.raises(BulkheadFullError):
            await func()

        # Clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
