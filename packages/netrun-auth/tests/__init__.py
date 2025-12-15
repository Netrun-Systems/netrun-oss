"""
Netrun Auth Test Suite
Service #59 Unified Authentication

Comprehensive test coverage for JWT authentication, RBAC, middleware,
password hashing, and FastAPI integration.

Test Suite Structure:
- test_jwt.py: JWT manager tests (40+ tests)
- test_middleware.py: Middleware tests (25+ tests)
- test_dependencies.py: FastAPI dependency tests (20+ tests)
- test_rbac.py: RBAC tests (25+ tests)
- test_password.py: Password hashing tests (15+ tests)
- test_types.py: Pydantic model tests (10+ tests)
- test_config.py: Configuration tests (10+ tests)
- test_integration.py: Integration tests (15+ tests)

Target: 160+ tests, 80% coverage minimum
"""

__version__ = "1.0.0"
