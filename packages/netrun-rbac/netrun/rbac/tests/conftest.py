"""
Pytest configuration for tenant isolation tests.

Registers custom markers and provides shared fixtures.
"""

import pytest


def pytest_configure(config):
    """Register custom markers for tenant isolation tests."""
    config.addinivalue_line(
        "markers",
        "tenant_isolation: Mark test as a tenant isolation contract test (CRITICAL)",
    )
    config.addinivalue_line(
        "markers",
        "escape_path: Mark test as testing a specific escape path scenario",
    )
    config.addinivalue_line(
        "markers",
        "integration: Mark test as requiring PostgreSQL database with RLS",
    )
    config.addinivalue_line(
        "markers",
        "critical: Mark test as critical security test that must never fail",
    )
    config.addinivalue_line(
        "markers",
        "security: Mark test as a security-focused test",
    )
