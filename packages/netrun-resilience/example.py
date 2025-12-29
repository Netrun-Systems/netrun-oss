"""
Example usage of netrun-resilience package.

Demonstrates retry, circuit breaker, timeout, and bulkhead patterns.
"""

import asyncio
import random
from netrun.resilience import retry, circuit_breaker, timeout, bulkhead


# Example 1: Retry with exponential backoff
@retry(max_attempts=3, base_delay_ms=500, exceptions=(ConnectionError,))
async def fetch_data_with_retry():
    """Simulates an API call that might fail."""
    if random.random() < 0.5:
        raise ConnectionError("Temporary network issue")
    return {"status": "success", "data": [1, 2, 3]}


# Example 2: Circuit breaker for unreliable service
@circuit_breaker(failure_threshold=3, timeout_seconds=5)
async def call_unreliable_service():
    """Simulates calling an unreliable external service."""
    if random.random() < 0.3:
        raise Exception("Service unavailable")
    return {"result": "processed"}


# Example 3: Timeout enforcement
@timeout(seconds=2.0)
async def slow_operation():
    """Simulates an operation that might take too long."""
    await asyncio.sleep(1.0)  # Completes within timeout
    return "completed"


# Example 4: Bulkhead isolation
@bulkhead(max_concurrent=5, max_queue=10)
async def resource_intensive_task(task_id: int):
    """Simulates a resource-intensive operation."""
    await asyncio.sleep(0.5)
    return f"Task {task_id} completed"


# Example 5: Combined patterns
@timeout(seconds=10.0)
@retry(max_attempts=3, base_delay_ms=1000)
@circuit_breaker(failure_threshold=5)
async def resilient_api_call():
    """Demonstrates combining multiple resilience patterns."""
    if random.random() < 0.2:
        raise ConnectionError("Network error")
    return {"data": "success"}


async def main():
    print("netrun-resilience Examples\n")
    print("=" * 50)

    # Example 1: Retry
    print("\n1. Retry with exponential backoff:")
    try:
        result = await fetch_data_with_retry()
        print(f"   ✓ Success: {result}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Example 2: Circuit breaker
    print("\n2. Circuit breaker pattern:")
    for i in range(3):
        try:
            result = await call_unreliable_service()
            print(f"   ✓ Call {i+1} succeeded: {result}")
        except Exception as e:
            print(f"   ✗ Call {i+1} failed: {type(e).__name__}")

    # Check circuit breaker state
    breaker = call_unreliable_service.circuit_breaker
    print(f"   Circuit state: {breaker.get_state().value}")

    # Example 3: Timeout
    print("\n3. Timeout enforcement:")
    try:
        result = await slow_operation()
        print(f"   ✓ Completed: {result}")
    except Exception as e:
        print(f"   ✗ Timed out: {e}")

    # Example 4: Bulkhead
    print("\n4. Bulkhead isolation (max 5 concurrent):")
    tasks = [resource_intensive_task(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    print(f"   ✓ Completed {len(results)} tasks")

    # Check bulkhead metrics
    bulkhead_instance = resource_intensive_task.bulkhead
    metrics = bulkhead_instance.get_metrics()
    print(f"   Metrics: {metrics['total_accepted']} accepted, {metrics['total_rejected']} rejected")

    # Example 5: Combined patterns
    print("\n5. Combined resilience patterns:")
    try:
        result = await resilient_api_call()
        print(f"   ✓ Success: {result}")
    except Exception as e:
        print(f"   ✗ Failed: {type(e).__name__}")

    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
