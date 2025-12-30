"""
Netrun RBAC Isolation Tests - Utilities for testing tenant isolation.

Following Netrun Systems SDLC v2.3 standards.
"""

from dataclasses import dataclass
from typing import List, Callable, Any, Optional, Type
from uuid import UUID, uuid4
import functools

from ..tenancy.context import TenantContext
from ..tenancy.exceptions import CrossTenantViolationError


@dataclass
class IsolationTestResult:
    """Result of an isolation test."""
    passed: bool
    test_name: str
    details: str
    tenant1_id: UUID
    tenant2_id: UUID
    violation_detected: Optional[str] = None


@dataclass
class IsolationTestCase:
    """
    Definition of an isolation test case.

    Usage:
        test = IsolationTestCase(
            name="contacts_isolated",
            description="Contacts from tenant1 not visible to tenant2",
            setup=async_setup_fn,
            test=async_test_fn,
            cleanup=async_cleanup_fn,
        )
    """
    name: str
    description: str
    setup: Optional[Callable] = None
    test: Callable = None
    cleanup: Optional[Callable] = None
    expected_isolation: bool = True


async def assert_tenant_isolation(
    service: Any,
    tenant1_id: UUID,
    tenant2_id: UUID,
    *,
    create_fn: Callable,
    query_fn: Callable,
    identifier_fn: Optional[Callable] = None,
) -> IsolationTestResult:
    """
    Assert that data created in tenant1 is not visible in tenant2.

    This is the core isolation test that verifies tenant boundaries.

    Args:
        service: Service instance to test
        tenant1_id: UUID of first tenant
        tenant2_id: UUID of second tenant
        create_fn: Async function to create test data in tenant1
        query_fn: Async function to query data
        identifier_fn: Function to extract identifier from created item

    Returns:
        IsolationTestResult with pass/fail and details

    Example:
        result = await assert_tenant_isolation(
            contact_service,
            tenant1.id,
            tenant2.id,
            create_fn=lambda: service.create({"name": "Test"}),
            query_fn=lambda: service.get_all(),
            identifier_fn=lambda item: item.id,
        )
        assert result.passed
    """
    result = IsolationTestResult(
        passed=False,
        test_name="tenant_isolation",
        details="",
        tenant1_id=tenant1_id,
        tenant2_id=tenant2_id,
    )

    try:
        # Create data in tenant1
        with TenantContext(tenant_id=tenant1_id, tenant_slug="tenant1"):
            created_item = await create_fn()
            item_id = identifier_fn(created_item) if identifier_fn else getattr(created_item, 'id', None)

        # Try to query from tenant2
        with TenantContext(tenant_id=tenant2_id, tenant_slug="tenant2"):
            items = await query_fn()

            # Check if tenant1's item is visible in tenant2
            if identifier_fn:
                visible_ids = [identifier_fn(item) for item in items]
            else:
                visible_ids = [getattr(item, 'id', None) for item in items]

            if item_id in visible_ids:
                result.passed = False
                result.details = f"VIOLATION: Item {item_id} from tenant1 visible in tenant2"
                result.violation_detected = f"item_id={item_id}"
            else:
                result.passed = True
                result.details = f"Isolation verified: Item {item_id} not visible in tenant2"

    except CrossTenantViolationError as e:
        # This is actually good - the system detected and blocked the violation
        result.passed = True
        result.details = f"Isolation enforced: CrossTenantViolationError raised"

    except Exception as e:
        result.passed = False
        result.details = f"Test error: {str(e)}"

    return result


async def assert_no_cross_tenant_access(
    get_fn: Callable,
    item_id: UUID,
    owner_tenant_id: UUID,
    accessor_tenant_id: UUID,
) -> IsolationTestResult:
    """
    Assert that a specific item cannot be accessed from another tenant.

    Args:
        get_fn: Async function(id) -> item to get the item
        item_id: UUID of the item to access
        owner_tenant_id: UUID of the tenant that owns the item
        accessor_tenant_id: UUID of the tenant trying to access

    Returns:
        IsolationTestResult
    """
    result = IsolationTestResult(
        passed=False,
        test_name="no_cross_tenant_access",
        details="",
        tenant1_id=owner_tenant_id,
        tenant2_id=accessor_tenant_id,
    )

    try:
        # Try to access from wrong tenant
        with TenantContext(tenant_id=accessor_tenant_id, tenant_slug="accessor"):
            item = await get_fn(item_id)

            if item is None:
                result.passed = True
                result.details = f"Isolation verified: Item {item_id} not accessible"
            else:
                result.passed = False
                result.details = f"VIOLATION: Item {item_id} accessible from wrong tenant"
                result.violation_detected = f"item_id={item_id}"

    except CrossTenantViolationError:
        result.passed = True
        result.details = "Isolation enforced: CrossTenantViolationError raised"

    except Exception as e:
        result.passed = False
        result.details = f"Test error: {str(e)}"

    return result


async def run_isolation_tests(
    test_cases: List[IsolationTestCase],
    tenant1_id: Optional[UUID] = None,
    tenant2_id: Optional[UUID] = None,
) -> List[IsolationTestResult]:
    """
    Run a suite of isolation test cases.

    Args:
        test_cases: List of IsolationTestCase definitions
        tenant1_id: UUID for first tenant (auto-generated if not provided)
        tenant2_id: UUID for second tenant (auto-generated if not provided)

    Returns:
        List of IsolationTestResult
    """
    tenant1_id = tenant1_id or uuid4()
    tenant2_id = tenant2_id or uuid4()
    results = []

    for case in test_cases:
        result = IsolationTestResult(
            passed=False,
            test_name=case.name,
            details="",
            tenant1_id=tenant1_id,
            tenant2_id=tenant2_id,
        )

        try:
            # Setup
            if case.setup:
                await case.setup(tenant1_id, tenant2_id)

            # Run test
            if case.test:
                test_passed = await case.test(tenant1_id, tenant2_id)
                result.passed = test_passed == case.expected_isolation
                if result.passed:
                    result.details = f"{case.description} - PASSED"
                else:
                    result.details = f"{case.description} - FAILED (expected isolation={case.expected_isolation})"

        except Exception as e:
            result.passed = False
            result.details = f"{case.description} - ERROR: {str(e)}"

        finally:
            # Cleanup
            if case.cleanup:
                try:
                    await case.cleanup(tenant1_id, tenant2_id)
                except Exception:
                    pass

        results.append(result)

    return results


def multi_tenant_test(
    tenant_count: int = 2,
    user_per_tenant: int = 1,
):
    """
    Decorator for tests that need multiple tenant contexts.

    Creates test tenants and provides them to the test function.

    Usage:
        @multi_tenant_test(tenant_count=2)
        async def test_isolation(tenants, users):
            tenant1, tenant2 = tenants
            # Test isolation between tenant1 and tenant2

    Args:
        tenant_count: Number of test tenants to create
        user_per_tenant: Number of users per tenant

    Returns:
        Decorator function
    """
    def decorator(test_fn):
        @functools.wraps(test_fn)
        async def wrapper(*args, **kwargs):
            # Generate test data
            tenants = [
                {"id": uuid4(), "slug": f"test-tenant-{i}"}
                for i in range(tenant_count)
            ]

            users = []
            for tenant in tenants:
                tenant_users = [
                    {"id": uuid4(), "tenant_id": tenant["id"]}
                    for _ in range(user_per_tenant)
                ]
                users.append(tenant_users)

            # Run test with generated data
            return await test_fn(tenants, users, *args, **kwargs)

        return wrapper
    return decorator


class IsolationTestSuite:
    """
    Suite of standard isolation tests that can be run against any service.

    Usage:
        suite = IsolationTestSuite(
            service_factory=lambda tenant_id: ContactService(session),
            create_fn=lambda svc: svc.create({"name": "Test"}),
            query_fn=lambda svc: svc.get_all(),
        )
        results = await suite.run_all()
        suite.print_report(results)
    """

    def __init__(
        self,
        service_factory: Callable[[UUID], Any],
        create_fn: Callable[[Any], Any],
        query_fn: Callable[[Any], Any],
        get_fn: Optional[Callable[[Any, UUID], Any]] = None,
        update_fn: Optional[Callable[[Any, UUID, dict], Any]] = None,
        delete_fn: Optional[Callable[[Any, UUID], bool]] = None,
    ):
        """
        Initialize the test suite.

        Args:
            service_factory: Function(tenant_id) -> service instance
            create_fn: Function(service) -> created item
            query_fn: Function(service) -> list of items
            get_fn: Function(service, id) -> item
            update_fn: Function(service, id, data) -> updated item
            delete_fn: Function(service, id) -> success bool
        """
        self.service_factory = service_factory
        self.create_fn = create_fn
        self.query_fn = query_fn
        self.get_fn = get_fn
        self.update_fn = update_fn
        self.delete_fn = delete_fn

    async def run_all(
        self,
        tenant1_id: Optional[UUID] = None,
        tenant2_id: Optional[UUID] = None,
    ) -> List[IsolationTestResult]:
        """
        Run all isolation tests in the suite.

        Args:
            tenant1_id: UUID for first tenant
            tenant2_id: UUID for second tenant

        Returns:
            List of test results
        """
        tenant1_id = tenant1_id or uuid4()
        tenant2_id = tenant2_id or uuid4()
        results = []

        # Test 1: Query isolation
        with TenantContext(tenant_id=tenant1_id, tenant_slug="t1"):
            svc1 = self.service_factory(tenant1_id)

        with TenantContext(tenant_id=tenant2_id, tenant_slug="t2"):
            svc2 = self.service_factory(tenant2_id)

        result = await assert_tenant_isolation(
            svc1,
            tenant1_id,
            tenant2_id,
            create_fn=lambda: self.create_fn(svc1),
            query_fn=lambda: self.query_fn(svc2),
            identifier_fn=lambda x: getattr(x, 'id', None),
        )
        result.test_name = "query_isolation"
        results.append(result)

        return results

    def print_report(self, results: List[IsolationTestResult]) -> None:
        """
        Print a formatted report of test results.

        Args:
            results: List of test results
        """
        print("\n" + "=" * 60)
        print("ISOLATION TEST REPORT")
        print("=" * 60)

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"\n{status}: {result.test_name}")
            print(f"  {result.details}")
            if result.violation_detected:
                print(f"  VIOLATION: {result.violation_detected}")

        print("\n" + "-" * 60)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("✓ All isolation tests passed!")
        else:
            print("✗ Some isolation tests failed!")

        print("=" * 60 + "\n")
