"""
Tenant Isolation Contract Testing Utilities for Multi-Tenant Applications.

Provides pgTAP-style assertions for verifying multi-tenant data isolation.
Use in integration tests to prove cross-tenant data access is impossible.

This module is CRITICAL for security compliance (SOC2, ISO27001, NIST).

Features:
- Query analysis to detect missing tenant filters
- Test context management for multi-tenant scenarios
- Background task tenant context preservation
- Escape path detection and prevention
- CI/CD integration utilities

Usage:
    from netrun.rbac.testing import (
        TenantIsolationError,
        assert_tenant_isolation,
        TenantTestContext,
        BackgroundTaskTenantContext,
        TenantEscapePathScanner,
    )

    # Assert query includes tenant filter
    query = select(Item).where(Item.tenant_id == tenant_id)
    await assert_tenant_isolation(query)

    # Test cross-tenant isolation
    async with TenantTestContext(session) as ctx:
        # Create data in tenant A
        item = Item(name="Secret", tenant_id=ctx.tenant_a_id)
        session.add(item)

        # Switch to tenant B and verify isolation
        await ctx.switch_to_tenant_b()
        items = await session.execute(select(Item))
        assert len(items.scalars().all()) == 0

Security Level: CRITICAL
Compliance: SOC2 CC6.1, ISO27001 A.9.4, NIST AC-4
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import logging
import re
import warnings
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Pattern,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)
from uuid import uuid4

from sqlalchemy import Select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement

from .exceptions import TenantIsolationError

logger = logging.getLogger(__name__)

# Type variables
T = TypeVar("T")
AsyncFunc = TypeVar("AsyncFunc", bound=Callable[..., Coroutine[Any, Any, Any]])

# Context variable for current tenant in async context
_current_tenant_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


class EscapePathSeverity(str, Enum):
    """Severity levels for tenant escape path findings."""

    CRITICAL = "critical"  # Immediate data leak risk
    HIGH = "high"  # Likely data leak with specific conditions
    MEDIUM = "medium"  # Potential leak in edge cases
    LOW = "low"  # Best practice violation, no immediate risk
    INFO = "info"  # Informational finding


@dataclass
class EscapePathFinding:
    """
    A finding from tenant escape path analysis.

    Attributes:
        severity: Severity level of the finding
        category: Category of the escape path (query, context, background, raw_sql)
        description: Human-readable description of the issue
        location: Code location or query fragment where issue was found
        remediation: Suggested fix for the issue
        compliance_impact: Affected compliance controls
    """

    severity: EscapePathSeverity
    category: str
    description: str
    location: str
    remediation: str
    compliance_impact: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"[{self.severity.value.upper()}] {self.category}: {self.description}\n"
            f"  Location: {self.location}\n"
            f"  Remediation: {self.remediation}"
        )


class SessionFactoryProtocol(Protocol):
    """Protocol for async session factory functions."""

    async def __call__(self, tenant_id: str) -> AsyncSession:
        """Create a session scoped to the given tenant."""
        ...


# =============================================================================
# Core Assertion Functions
# =============================================================================


async def assert_tenant_isolation(
    query: Union[Select, ClauseElement, str],
    tenant_column: str = "tenant_id",
    session: Optional[AsyncSession] = None,
    strict: bool = True,
    allowed_patterns: Optional[List[Pattern[str]]] = None,
) -> None:
    """
    Assert that a SQLAlchemy query includes tenant filtering.

    Raises TenantIsolationError if query could leak cross-tenant data.

    Args:
        query: SQLAlchemy Select statement, ClauseElement, or raw SQL string
        tenant_column: Name of the tenant column (default: "tenant_id")
        session: Optional session for query compilation (if needed)
        strict: If True, require exact tenant_id match; if False, allow patterns
        allowed_patterns: List of regex patterns for allowed queries without tenant filter
                         (e.g., system tables, public lookup tables)

    Raises:
        TenantIsolationError: If query is missing tenant filter

    Example:
        # This FAILS - no tenant filter
        query = select(Item).where(Item.status == "active")
        await assert_tenant_isolation(query)  # Raises TenantIsolationError!

        # This PASSES
        query = select(Item).where(Item.tenant_id == tenant_id, Item.status == "active")
        await assert_tenant_isolation(query)  # OK

        # Allow certain system queries
        allowed = [re.compile(r"system_config"), re.compile(r"lookup_")]
        query = select(SystemConfig)  # No tenant_id column
        await assert_tenant_isolation(query, allowed_patterns=allowed)  # OK

    Security Note:
        This function performs STATIC analysis of the query string.
        It cannot detect all possible bypass scenarios (e.g., dynamic SQL injection).
        Use in combination with RLS policies for defense-in-depth.
    """
    # Convert query to string for analysis
    if isinstance(query, str):
        compiled = query
    else:
        try:
            compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        except Exception:
            # Fall back to simple string conversion
            compiled = str(query)

    compiled_lower = compiled.lower()

    # Check allowed patterns first
    if allowed_patterns:
        for pattern in allowed_patterns:
            if pattern.search(compiled):
                logger.debug(f"Query allowed by pattern {pattern.pattern}: {compiled[:100]}...")
                return

    # Check for tenant filter presence
    tenant_col_lower = tenant_column.lower()

    # Patterns that indicate proper tenant filtering
    tenant_filter_patterns = [
        # Direct column reference in WHERE
        rf"{tenant_col_lower}\s*=",
        # Parameterized version
        rf"{tenant_col_lower}\s*=\s*:",
        # IN clause with tenant
        rf"{tenant_col_lower}\s+in\s*\(",
        # JOIN condition with tenant
        rf"on\s+.*{tenant_col_lower}\s*=",
        # Subquery correlation
        rf"where\s+.*{tenant_col_lower}",
    ]

    has_tenant_filter = any(
        re.search(pattern, compiled_lower) for pattern in tenant_filter_patterns
    )

    if not has_tenant_filter:
        # Truncate long queries for error message
        query_preview = compiled[:500] + "..." if len(compiled) > 500 else compiled

        raise TenantIsolationError(
            f"Query missing tenant isolation! Expected '{tenant_column}' filter.\n"
            f"Query: {query_preview}\n\n"
            f"REMEDIATION: Add .where({tenant_column} == tenant_id) to your query.\n"
            f"COMPLIANCE IMPACT: SOC2 CC6.1, ISO27001 A.9.4.1, NIST AC-4"
        )

    logger.debug(f"Tenant isolation verified for query: {compiled[:100]}...")


def assert_tenant_isolation_sync(
    query: Union[Select, ClauseElement, str],
    tenant_column: str = "tenant_id",
    strict: bool = True,
    allowed_patterns: Optional[List[Pattern[str]]] = None,
) -> None:
    """
    Synchronous version of assert_tenant_isolation.

    For use in non-async contexts or pytest fixtures.
    """
    # Run the async version in a new event loop
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            assert_tenant_isolation(
                query=query,
                tenant_column=tenant_column,
                strict=strict,
                allowed_patterns=allowed_patterns,
            )
        )
    finally:
        loop.close()


# =============================================================================
# Test Context Management
# =============================================================================


class TenantTestContext:
    """
    Context manager for testing tenant isolation.

    Creates two test tenants and verifies data cannot leak between them.
    Automatically sets PostgreSQL RLS session variables.

    Example:
        async with TenantTestContext(session) as ctx:
            # Create data in tenant A (context starts here)
            item_a = Item(name="Secret", tenant_id=ctx.tenant_a_id)
            session.add(item_a)
            await session.commit()

            # Switch to tenant B and try to read
            await ctx.switch_to_tenant_b()

            # This query should return empty due to RLS
            result = await session.execute(select(Item))
            items = result.scalars().all()
            assert item_a not in items, "CRITICAL: Tenant B can see Tenant A's data!"

    Attributes:
        tenant_a_id: UUID for test tenant A
        tenant_b_id: UUID for test tenant B
        current_tenant: Currently active tenant ID
        session: Database session with RLS context
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_a_id: Optional[str] = None,
        tenant_b_id: Optional[str] = None,
        session_variable: str = "app.current_tenant_id",
        user_session_variable: str = "app.current_user_id",
        auto_cleanup: bool = True,
    ):
        """
        Initialize tenant test context.

        Args:
            session: SQLAlchemy AsyncSession to use for testing
            tenant_a_id: Override tenant A ID (default: auto-generated)
            tenant_b_id: Override tenant B ID (default: auto-generated)
            session_variable: PostgreSQL session variable for tenant ID
            user_session_variable: PostgreSQL session variable for user ID
            auto_cleanup: Whether to reset context on exit
        """
        self.session = session
        self.tenant_a_id = tenant_a_id or f"test-tenant-a-{uuid4().hex[:8]}"
        self.tenant_b_id = tenant_b_id or f"test-tenant-b-{uuid4().hex[:8]}"
        self.current_tenant = self.tenant_a_id
        self.session_variable = session_variable
        self.user_session_variable = user_session_variable
        self.auto_cleanup = auto_cleanup
        self._original_tenant: Optional[str] = None
        self._context_history: List[Tuple[str, str]] = []  # (action, tenant_id)

    async def __aenter__(self) -> "TenantTestContext":
        """Enter context and set RLS for tenant A."""
        # Store original tenant context if any
        try:
            result = await self.session.execute(
                text(f"SELECT current_setting('{self.session_variable}', true)")
            )
            self._original_tenant = result.scalar()
        except Exception:
            self._original_tenant = None

        # Set RLS context for tenant A
        await self._set_tenant(self.tenant_a_id)
        self._context_history.append(("enter", self.tenant_a_id))

        logger.info(f"TenantTestContext initialized. Tenant A: {self.tenant_a_id}")
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit context and optionally reset RLS."""
        if self.auto_cleanup:
            if self._original_tenant:
                await self._set_tenant(self._original_tenant)
            else:
                await self.session.execute(text(f"RESET {self.session_variable}"))
                await self.session.execute(text(f"RESET {self.user_session_variable}"))

        self._context_history.append(("exit", self.current_tenant))
        logger.info(f"TenantTestContext exited. History: {len(self._context_history)} actions")

    async def _set_tenant(self, tenant_id: str) -> None:
        """Set tenant context via PostgreSQL session variable."""
        # Use parameterized query to prevent SQL injection
        await self.session.execute(
            text(f"SET LOCAL {self.session_variable} = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        self.current_tenant = tenant_id
        _current_tenant_id.set(tenant_id)

    async def switch_to_tenant_a(self) -> None:
        """Switch to tenant A context."""
        await self._set_tenant(self.tenant_a_id)
        self._context_history.append(("switch_a", self.tenant_a_id))
        logger.debug(f"Switched to tenant A: {self.tenant_a_id}")

    async def switch_to_tenant_b(self) -> None:
        """Switch to tenant B context."""
        await self._set_tenant(self.tenant_b_id)
        self._context_history.append(("switch_b", self.tenant_b_id))
        logger.debug(f"Switched to tenant B: {self.tenant_b_id}")

    async def switch_to_tenant(self, tenant_id: str) -> None:
        """Switch to arbitrary tenant context (for advanced testing)."""
        await self._set_tenant(tenant_id)
        self._context_history.append(("switch_custom", tenant_id))
        logger.debug(f"Switched to custom tenant: {tenant_id}")

    async def clear_tenant_context(self) -> None:
        """
        Clear tenant context (simulate superuser/admin access).

        WARNING: Use only for testing admin bypass scenarios.
        """
        await self.session.execute(text(f"RESET {self.session_variable}"))
        self.current_tenant = ""
        _current_tenant_id.set(None)
        self._context_history.append(("clear", ""))
        logger.warning("Tenant context cleared - operating without RLS filtering")

    async def get_current_tenant(self) -> Optional[str]:
        """Get the currently set tenant ID from PostgreSQL session."""
        result = await self.session.execute(
            text(f"SELECT current_setting('{self.session_variable}', true)")
        )
        value = result.scalar()
        return value if value and value != "" else None

    def get_context_history(self) -> List[Tuple[str, str]]:
        """Get history of context switches for debugging."""
        return self._context_history.copy()


@asynccontextmanager
async def tenant_test_context(
    session: AsyncSession,
    **kwargs: Any,
) -> AsyncGenerator[TenantTestContext, None]:
    """
    Functional context manager for tenant isolation testing.

    Alternative to using TenantTestContext directly.

    Example:
        async with tenant_test_context(session) as ctx:
            # Create data in tenant A
            ...
            # Switch and verify isolation
            await ctx.switch_to_tenant_b()
            ...
    """
    ctx = TenantTestContext(session, **kwargs)
    async with ctx:
        yield ctx


# =============================================================================
# Background Task Context Preservation
# =============================================================================


class BackgroundTaskTenantContext:
    """
    Wrapper for background tasks that preserves tenant context.

    CRITICAL: Background tasks lose request context by default!
    FastAPI's BackgroundTasks runs after the response is sent,
    meaning the original request's tenant context is lost.

    Example:
        # WRONG - loses tenant context
        background_tasks.add_task(process_items)

        # RIGHT - preserves tenant context
        background_tasks.add_task(
            BackgroundTaskTenantContext(tenant_id, session_factory).run(process_items)
        )

    For Celery/Redis Queue integration:
        # In task definition
        @celery_app.task
        def process_items_task(tenant_id: str, item_ids: list):
            async def inner():
                async with BackgroundTaskTenantContext(tenant_id).get_session() as session:
                    await process_items(session, item_ids)
            asyncio.run(inner())

    Security Note:
        Always pass tenant_id explicitly - never rely on context inheritance.
        This ensures audit trails are maintained for background operations.
    """

    def __init__(
        self,
        tenant_id: str,
        session_factory: Optional[SessionFactoryProtocol] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        Initialize background task tenant context.

        Args:
            tenant_id: Tenant ID to scope the background task
            session_factory: Async function that creates a session with tenant context
            user_id: User ID for audit logging (optional)
            correlation_id: Request correlation ID for tracing (optional)
        """
        self.tenant_id = tenant_id
        self.session_factory = session_factory
        self.user_id = user_id
        self.correlation_id = correlation_id or uuid4().hex

    def run(
        self,
        func: AsyncFunc,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[], Coroutine[Any, Any, Any]]:
        """
        Wrap an async function to run with tenant context.

        Args:
            func: Async function to wrap
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Wrapped async function that can be added to BackgroundTasks
        """

        @functools.wraps(func)
        async def wrapped() -> Any:
            # Set context variable for tenant
            _current_tenant_id.set(self.tenant_id)

            logger.info(
                f"Background task starting: {func.__name__} "
                f"[tenant={self.tenant_id}, correlation={self.correlation_id}]"
            )

            try:
                if self.session_factory:
                    # Use provided session factory
                    session = await self.session_factory(self.tenant_id)
                    return await func(*args, session=session, **kwargs)
                else:
                    # Session should be provided in kwargs
                    return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Background task failed: {func.__name__} "
                    f"[tenant={self.tenant_id}, correlation={self.correlation_id}]: {e}"
                )
                raise
            finally:
                logger.info(
                    f"Background task completed: {func.__name__} "
                    f"[tenant={self.tenant_id}, correlation={self.correlation_id}]"
                )

        return wrapped

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a session with tenant context set.

        Requires session_factory to be configured.

        Example:
            async with BackgroundTaskTenantContext(tenant_id, factory).get_session() as session:
                result = await session.execute(select(Item))
        """
        if not self.session_factory:
            raise ValueError(
                "session_factory must be provided to use get_session(). "
                "Either pass session_factory in constructor or provide session manually."
            )

        session = await self.session_factory(self.tenant_id)
        try:
            yield session
        finally:
            await session.close()


def preserve_tenant_context(
    tenant_id: str,
    session_factory: Optional[SessionFactoryProtocol] = None,
) -> Callable[[AsyncFunc], Callable[..., Coroutine[Any, Any, Any]]]:
    """
    Decorator to preserve tenant context in background tasks.

    Example:
        @preserve_tenant_context(tenant_id, session_factory)
        async def process_items(session, item_ids):
            ...

        # Add to background tasks
        background_tasks.add_task(process_items, item_ids)
    """

    def decorator(func: AsyncFunc) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = BackgroundTaskTenantContext(tenant_id, session_factory)
            return await ctx.run(func, *args, **kwargs)()

        return wrapper

    return decorator


# =============================================================================
# Escape Path Detection and Scanning
# =============================================================================


class TenantEscapePathScanner:
    """
    Scans code and queries for potential tenant isolation escape paths.

    Use in CI/CD pipelines to detect security issues before deployment.

    Detects:
    - Queries without tenant filters
    - Raw SQL that bypasses ORM
    - Background tasks without context preservation
    - Pagination without tenant scope
    - Aggregations that leak tenant boundaries
    - JOIN queries with missing tenant conditions
    - Subqueries without tenant correlation

    Example:
        scanner = TenantEscapePathScanner()

        # Scan a query
        findings = scanner.scan_query(query_string)

        # Scan a Python file
        findings = scanner.scan_file("/path/to/repo.py")

        # Scan entire directory
        findings = scanner.scan_directory("/path/to/repo")

        # Fail CI if critical findings
        critical = [f for f in findings if f.severity == EscapePathSeverity.CRITICAL]
        if critical:
            sys.exit(1)
    """

    # Patterns that indicate potential escape paths
    DANGEROUS_PATTERNS: List[Tuple[Pattern[str], EscapePathSeverity, str, str]] = [
        # Raw SQL execution
        (
            re.compile(r"execute\s*\(\s*['\"]SELECT", re.IGNORECASE),
            EscapePathSeverity.HIGH,
            "raw_sql",
            "Raw SELECT query detected. Ensure tenant filter is included.",
        ),
        (
            re.compile(r"execute\s*\(\s*['\"]UPDATE", re.IGNORECASE),
            EscapePathSeverity.CRITICAL,
            "raw_sql",
            "Raw UPDATE query detected. Could modify other tenants' data.",
        ),
        (
            re.compile(r"execute\s*\(\s*['\"]DELETE", re.IGNORECASE),
            EscapePathSeverity.CRITICAL,
            "raw_sql",
            "Raw DELETE query detected. Could delete other tenants' data.",
        ),
        # Pagination without tenant filter
        (
            re.compile(r"\.offset\s*\([^)]+\)\.limit\s*\([^)]+\)(?!.*tenant)", re.IGNORECASE),
            EscapePathSeverity.HIGH,
            "pagination",
            "Pagination detected without visible tenant filter.",
        ),
        # Aggregation across tenants
        (
            re.compile(r"func\.(count|sum|avg|max|min)\s*\((?!.*tenant)", re.IGNORECASE),
            EscapePathSeverity.MEDIUM,
            "aggregation",
            "Aggregation function without tenant filter could leak cross-tenant metrics.",
        ),
        # Background task without context
        (
            re.compile(r"add_task\s*\([^B]*\)(?!.*TenantContext)", re.IGNORECASE),
            EscapePathSeverity.HIGH,
            "background",
            "BackgroundTask may lose tenant context. Use BackgroundTaskTenantContext.",
        ),
        # Session without RLS
        (
            re.compile(r"AsyncSession\s*\(\s*\)(?!.*set_tenant)", re.IGNORECASE),
            EscapePathSeverity.MEDIUM,
            "session",
            "Session created without explicit RLS context setup.",
        ),
        # UNION queries (potential cross-tenant join)
        (
            re.compile(r"\bUNION\b(?!.*tenant)", re.IGNORECASE),
            EscapePathSeverity.HIGH,
            "union",
            "UNION query detected. Ensure all subqueries have tenant filters.",
        ),
        # Subquery without correlation
        (
            re.compile(r"\(\s*SELECT[^)]+FROM[^)]+\)(?!.*tenant)", re.IGNORECASE),
            EscapePathSeverity.MEDIUM,
            "subquery",
            "Subquery without visible tenant correlation.",
        ),
    ]

    # Patterns that indicate SAFE tenant handling
    SAFE_PATTERNS: List[Pattern[str]] = [
        re.compile(r"tenant_id\s*=", re.IGNORECASE),
        re.compile(r"\.filter\s*\([^)]*tenant", re.IGNORECASE),
        re.compile(r"\.where\s*\([^)]*tenant", re.IGNORECASE),
        re.compile(r"current_setting\s*\(['\"]app\.current_tenant", re.IGNORECASE),
        re.compile(r"set_tenant_context", re.IGNORECASE),
        re.compile(r"BackgroundTaskTenantContext", re.IGNORECASE),
        re.compile(r"TenantTestContext", re.IGNORECASE),
    ]

    def __init__(
        self,
        tenant_column: str = "tenant_id",
        custom_dangerous_patterns: Optional[List[Tuple[Pattern[str], EscapePathSeverity, str, str]]] = None,
        custom_safe_patterns: Optional[List[Pattern[str]]] = None,
        ignore_patterns: Optional[List[Pattern[str]]] = None,
    ):
        """
        Initialize escape path scanner.

        Args:
            tenant_column: Name of tenant column to check for
            custom_dangerous_patterns: Additional patterns to detect
            custom_safe_patterns: Additional patterns that indicate safe handling
            ignore_patterns: Patterns to ignore (e.g., test files, comments)
        """
        self.tenant_column = tenant_column
        self.dangerous_patterns = list(self.DANGEROUS_PATTERNS)
        self.safe_patterns = list(self.SAFE_PATTERNS)
        self.ignore_patterns = ignore_patterns or []

        if custom_dangerous_patterns:
            self.dangerous_patterns.extend(custom_dangerous_patterns)
        if custom_safe_patterns:
            self.safe_patterns.extend(custom_safe_patterns)

    def scan_query(self, query: str, context: str = "unknown") -> List[EscapePathFinding]:
        """
        Scan a query string for potential escape paths.

        Args:
            query: SQL query or SQLAlchemy query string
            context: Context information (e.g., file:line)

        Returns:
            List of findings
        """
        findings: List[EscapePathFinding] = []

        # Check if query is explicitly safe
        for safe_pattern in self.safe_patterns:
            if safe_pattern.search(query):
                return []  # Query appears to have proper tenant handling

        # Check for dangerous patterns
        for pattern, severity, category, description in self.dangerous_patterns:
            if pattern.search(query):
                finding = EscapePathFinding(
                    severity=severity,
                    category=category,
                    description=description,
                    location=context,
                    remediation=f"Add {self.tenant_column} filter to query",
                    compliance_impact=["SOC2 CC6.1", "ISO27001 A.9.4", "NIST AC-4"],
                )
                findings.append(finding)

        return findings

    def scan_file(self, file_path: str) -> List[EscapePathFinding]:
        """
        Scan a Python file for potential escape paths.

        Args:
            file_path: Path to Python file

        Returns:
            List of findings with line numbers
        """
        findings: List[EscapePathFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return findings

        # Skip ignored files
        for ignore_pattern in self.ignore_patterns:
            if ignore_pattern.search(file_path):
                return findings

        # Scan line by line for context
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            line_findings = self.scan_query(line, f"{file_path}:{line_num}")
            findings.extend(line_findings)

        return findings

    def scan_directory(
        self,
        directory: str,
        file_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[EscapePathFinding]:
        """
        Scan a directory recursively for potential escape paths.

        Args:
            directory: Root directory to scan
            file_patterns: Glob patterns for files to include (default: ["*.py"])
            exclude_patterns: Glob patterns for files to exclude

        Returns:
            List of all findings across all files
        """
        import glob
        import os

        findings: List[EscapePathFinding] = []
        file_patterns = file_patterns or ["**/*.py"]
        exclude_patterns = exclude_patterns or ["**/test_*.py", "**/tests/**", "**/__pycache__/**"]

        for pattern in file_patterns:
            full_pattern = os.path.join(directory, pattern)
            for file_path in glob.glob(full_pattern, recursive=True):
                # Check exclusions
                excluded = False
                for exclude in exclude_patterns:
                    if glob.fnmatch.fnmatch(file_path, exclude):
                        excluded = True
                        break

                if not excluded:
                    findings.extend(self.scan_file(file_path))

        return findings

    def generate_report(
        self,
        findings: List[EscapePathFinding],
        format: str = "text",
    ) -> str:
        """
        Generate a report from scan findings.

        Args:
            findings: List of findings to report
            format: Output format ("text", "json", "markdown")

        Returns:
            Formatted report string
        """
        if format == "json":
            import json

            return json.dumps(
                [
                    {
                        "severity": f.severity.value,
                        "category": f.category,
                        "description": f.description,
                        "location": f.location,
                        "remediation": f.remediation,
                        "compliance_impact": f.compliance_impact,
                    }
                    for f in findings
                ],
                indent=2,
            )

        elif format == "markdown":
            lines = ["# Tenant Isolation Escape Path Report\n"]

            # Group by severity
            by_severity: Dict[EscapePathSeverity, List[EscapePathFinding]] = {}
            for f in findings:
                by_severity.setdefault(f.severity, []).append(f)

            for severity in [
                EscapePathSeverity.CRITICAL,
                EscapePathSeverity.HIGH,
                EscapePathSeverity.MEDIUM,
                EscapePathSeverity.LOW,
            ]:
                if severity in by_severity:
                    lines.append(f"\n## {severity.value.upper()} ({len(by_severity[severity])})\n")
                    for f in by_severity[severity]:
                        lines.append(f"### {f.category}\n")
                        lines.append(f"- **Location**: `{f.location}`\n")
                        lines.append(f"- **Description**: {f.description}\n")
                        lines.append(f"- **Remediation**: {f.remediation}\n")
                        lines.append(f"- **Compliance**: {', '.join(f.compliance_impact)}\n")

            return "\n".join(lines)

        else:  # text format
            lines = ["=" * 60, "TENANT ISOLATION ESCAPE PATH REPORT", "=" * 60, ""]

            critical = [f for f in findings if f.severity == EscapePathSeverity.CRITICAL]
            high = [f for f in findings if f.severity == EscapePathSeverity.HIGH]
            medium = [f for f in findings if f.severity == EscapePathSeverity.MEDIUM]
            low = [f for f in findings if f.severity == EscapePathSeverity.LOW]

            lines.append(f"CRITICAL: {len(critical)}  HIGH: {len(high)}  MEDIUM: {len(medium)}  LOW: {len(low)}")
            lines.append("")

            for f in findings:
                lines.append(str(f))
                lines.append("-" * 40)

            return "\n".join(lines)


# =============================================================================
# CI/CD Integration Utilities
# =============================================================================


def ci_fail_on_findings(
    findings: List[EscapePathFinding],
    fail_on: Set[EscapePathSeverity] = None,
) -> int:
    """
    Return exit code for CI/CD based on findings.

    Args:
        findings: List of scan findings
        fail_on: Set of severities that should cause failure
                 (default: CRITICAL and HIGH)

    Returns:
        0 if no critical findings, 1 otherwise (for sys.exit())

    Example:
        scanner = TenantEscapePathScanner()
        findings = scanner.scan_directory("./src")
        sys.exit(ci_fail_on_findings(findings))
    """
    if fail_on is None:
        fail_on = {EscapePathSeverity.CRITICAL, EscapePathSeverity.HIGH}

    failing_findings = [f for f in findings if f.severity in fail_on]

    if failing_findings:
        print(f"CI FAILED: Found {len(failing_findings)} critical/high severity findings")
        for f in failing_findings:
            print(f"  - {f.severity.value.upper()}: {f.description} at {f.location}")
        return 1

    print(f"CI PASSED: No critical/high findings ({len(findings)} total findings)")
    return 0


# =============================================================================
# Pytest Fixtures and Markers
# =============================================================================


def pytest_configure(config: Any) -> None:
    """
    Register pytest markers for tenant isolation tests.

    Add to conftest.py:
        from netrun.rbac.testing import pytest_configure
    """
    config.addinivalue_line(
        "markers",
        "tenant_isolation: Mark test as a tenant isolation contract test",
    )
    config.addinivalue_line(
        "markers",
        "escape_path: Mark test as testing a specific escape path scenario",
    )


def tenant_isolation_test(func: AsyncFunc) -> AsyncFunc:
    """
    Decorator to mark a test as a tenant isolation contract test.

    Adds additional validation and logging around the test.

    Example:
        @tenant_isolation_test
        async def test_cross_tenant_read_impossible(self, db_session):
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info(f"Starting tenant isolation test: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"PASSED: {func.__name__}")
            return result
        except TenantIsolationError as e:
            logger.error(f"FAILED (Isolation Error): {func.__name__}: {e}")
            raise
        except AssertionError as e:
            logger.error(f"FAILED (Assertion): {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"FAILED (Exception): {func.__name__}: {e}")
            raise

    return wrapper  # type: ignore


# =============================================================================
# Compliance Documentation
# =============================================================================


COMPLIANCE_MAPPING = {
    "SOC2": {
        "CC6.1": "Logical and Physical Access Controls",
        "CC6.2": "Role-Based Access Control",
        "CC6.3": "Segregation of Duties",
    },
    "ISO27001": {
        "A.9.1": "Business Requirements of Access Control",
        "A.9.4": "System and Application Access Control",
        "A.9.4.1": "Information Access Restriction",
    },
    "NIST": {
        "AC-4": "Information Flow Enforcement",
        "AC-5": "Separation of Duties",
        "AC-6": "Least Privilege",
    },
}


def get_compliance_documentation() -> str:
    """
    Get documentation of compliance controls addressed by tenant isolation testing.

    Returns:
        Formatted compliance documentation
    """
    lines = [
        "# Tenant Isolation Testing - Compliance Mapping",
        "",
        "The tenant isolation testing utilities in this module address the following",
        "compliance requirements:",
        "",
    ]

    for framework, controls in COMPLIANCE_MAPPING.items():
        lines.append(f"## {framework}")
        for control_id, description in controls.items():
            lines.append(f"- **{control_id}**: {description}")
        lines.append("")

    lines.extend(
        [
            "## Testing Requirements",
            "",
            "To maintain compliance, the following tests MUST pass before any release:",
            "",
            "1. **test_cross_tenant_read_impossible** - Proves Tenant B cannot read Tenant A's data",
            "2. **test_cross_tenant_write_impossible** - Proves Tenant B cannot modify Tenant A's data",
            "3. **test_query_without_tenant_filter_fails** - Ensures queries are validated",
            "4. **test_pagination_includes_tenant_filter** - Prevents paginated data leaks",
            "5. **test_background_task_preserves_tenant** - Ensures async context is maintained",
            "",
            "## CI/CD Integration",
            "",
            "Run escape path scanning as part of your CI pipeline:",
            "",
            "```python",
            "from netrun.rbac.testing import TenantEscapePathScanner, ci_fail_on_findings",
            "",
            "scanner = TenantEscapePathScanner()",
            "findings = scanner.scan_directory('./src')",
            "sys.exit(ci_fail_on_findings(findings))",
            "```",
        ]
    )

    return "\n".join(lines)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Exceptions (re-exported for convenience)
    "TenantIsolationError",
    # Core assertions
    "assert_tenant_isolation",
    "assert_tenant_isolation_sync",
    # Test context
    "TenantTestContext",
    "tenant_test_context",
    # Background task handling
    "BackgroundTaskTenantContext",
    "preserve_tenant_context",
    # Escape path detection
    "TenantEscapePathScanner",
    "EscapePathSeverity",
    "EscapePathFinding",
    # CI/CD utilities
    "ci_fail_on_findings",
    # Pytest integration
    "pytest_configure",
    "tenant_isolation_test",
    # Compliance
    "get_compliance_documentation",
    "COMPLIANCE_MAPPING",
]
