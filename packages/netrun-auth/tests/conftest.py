"""
Pytest Configuration and Shared Fixtures
Service #59 Unified Authentication

Provides shared test fixtures for:
- Async event loops
- Mock Redis clients
- RSA key pairs for JWT testing
- Sample user claims and user objects
- Mock FastAPI request objects
"""

import pytest
import asyncio
from typing import Generator, Dict, Any
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import tempfile


@pytest.fixture(scope="function")
def event_loop():
    """
    Create event loop for async tests.

    Uses function scope for compatibility with pytest-asyncio.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """
    Mock Redis client for testing without Redis server.

    Provides AsyncMock implementations of common Redis operations:
    - get, set, delete, exists
    - setex for expiring keys
    - All methods return success values by default
    """
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.setex = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=0)
    redis.ttl = AsyncMock(return_value=-1)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def rsa_key_pair():
    """
    Generate RSA key pair for JWT testing.

    Returns:
        Tuple[bytes, bytes]: (private_key_pem, public_key_pem)

    Uses 2048-bit RSA keys with RS256 algorithm.
    Keys are generated fresh for each test to ensure isolation.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem


@pytest.fixture
def temp_key_files(rsa_key_pair):
    """
    Create temporary PEM files for key loading tests.

    Args:
        rsa_key_pair: RSA key pair fixture

    Returns:
        Tuple[Path, Path]: (private_key_path, public_key_path)
    """
    private_pem, public_pem = rsa_key_pair

    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem') as private_file:
        private_file.write(private_pem)
        private_path = Path(private_file.name)

    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem') as public_file:
        public_file.write(public_pem)
        public_path = Path(public_file.name)

    yield private_path, public_path

    # Cleanup
    private_path.unlink(missing_ok=True)
    public_path.unlink(missing_ok=True)


@pytest.fixture
def sample_claims() -> Dict[str, Any]:
    """
    Sample JWT claims for testing.

    Returns standard JWT claims structure with:
    - jti: JWT ID for blacklisting
    - sub: Subject (user ID)
    - user_id: Netrun user identifier
    - organization_id: Multi-tenant organization ID
    - roles: List of user roles
    - permissions: List of granular permissions
    - session_id: Session tracking
    - ip_address: Client IP for security logging
    - user_agent: Client user agent
    """
    return {
        "jti": "test-jti-12345",
        "sub": "user-123",
        "user_id": "user-123",
        "organization_id": "org-456",
        "roles": ["user", "admin"],
        "permissions": ["users:read", "users:write", "admin:read"],
        "session_id": "session-789",
        "ip_address": "192.168.1.1",
        "user_agent": "TestAgent/1.0",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
    }


@pytest.fixture
def minimal_claims() -> Dict[str, Any]:
    """
    Minimal valid JWT claims (only required fields).

    Used for testing required vs optional claim validation.
    """
    return {
        "jti": "test-jti-minimal",
        "sub": "user-minimal",
        "user_id": "user-minimal",
        "organization_id": "org-minimal",
        "roles": [],
        "permissions": [],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
    }


@pytest.fixture
def expired_claims() -> Dict[str, Any]:
    """
    Expired JWT claims for testing token expiry validation.
    """
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    return {
        "jti": "test-jti-expired",
        "sub": "user-expired",
        "user_id": "user-expired",
        "organization_id": "org-expired",
        "roles": ["user"],
        "permissions": ["users:read"],
        "iat": int((past_time - timedelta(minutes=15)).timestamp()),
        "exp": int(past_time.timestamp())
    }


@pytest.fixture
def test_user() -> Dict[str, Any]:
    """
    Sample regular user for testing.

    Standard user with basic read permissions.
    """
    return {
        "id": "user-123",
        "email": "test@netrunsystems.com",
        "name": "Test User",
        "organization_id": "org-456",
        "roles": ["user"],
        "permissions": ["users:read", "dashboard:read"]
    }


@pytest.fixture
def admin_user() -> Dict[str, Any]:
    """
    Sample admin user for testing.

    Admin user with elevated read/write permissions.
    """
    return {
        "id": "admin-001",
        "email": "admin@netrunsystems.com",
        "name": "Admin User",
        "organization_id": "org-456",
        "roles": ["admin", "user"],
        "permissions": [
            "users:read",
            "users:write",
            "admin:read",
            "admin:write",
            "organizations:read",
            "organizations:write"
        ]
    }


@pytest.fixture
def superadmin_user() -> Dict[str, Any]:
    """
    Sample superadmin user for testing.

    Superadmin with full system permissions.
    """
    return {
        "id": "superadmin-001",
        "email": "superadmin@netrunsystems.com",
        "name": "Super Admin",
        "organization_id": "org-netrun",
        "roles": ["superadmin", "admin", "user"],
        "permissions": [
            "users:read", "users:write", "users:delete",
            "admin:read", "admin:write", "admin:delete",
            "organizations:read", "organizations:write", "organizations:delete",
            "system:read", "system:write", "system:configure"
        ]
    }


@pytest.fixture
def mock_request():
    """
    Mock FastAPI Request object for middleware testing.

    Provides a MagicMock with common request attributes:
    - headers: Dict of HTTP headers
    - url: Request URL object
    - client: Client connection info
    - state: Request state for storing auth context
    """
    request = MagicMock()
    request.headers = {}
    request.url.path = "/api/test"
    request.client.host = "192.168.1.1"
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_request_with_jwt(mock_request, rsa_key_pair, sample_claims):
    """
    Mock FastAPI Request with valid JWT in Authorization header.

    Pre-configured for testing authenticated request flows.
    """
    # This will be populated by tests that need a real token
    mock_request.headers["Authorization"] = "Bearer test-token-placeholder"
    return mock_request


@pytest.fixture
def mock_api_key_request(mock_request):
    """
    Mock FastAPI Request with API key authentication.
    """
    mock_request.headers["X-API-Key"] = "test-api-key-12345"
    return mock_request


@pytest.fixture
def mock_key_vault():
    """
    Mock Azure Key Vault client for testing key retrieval.
    """
    vault = AsyncMock()
    vault.get_secret = AsyncMock(return_value=MagicMock(value="mock-secret-value"))
    return vault


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """
    Test configuration dictionary for AuthConfig testing.
    """
    return {
        "jwt_algorithm": "RS256",
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30,
        "redis_url": "redis://localhost:6379",
        "key_vault_url": "https://test-vault.vault.azure.net",
        "private_key_secret_name": "jwt-private-key",
        "public_key_secret_name": "jwt-public-key",
        "environment": "test"
    }


@pytest.fixture
def sample_role_hierarchy() -> Dict[str, list]:
    """
    Sample role hierarchy for RBAC testing.

    Defines role inheritance:
    - superadmin inherits from admin
    - admin inherits from user
    """
    return {
        "superadmin": ["admin", "user"],
        "admin": ["user"],
        "user": []
    }


@pytest.fixture
def sample_permission_map() -> Dict[str, list]:
    """
    Sample permission mapping for roles.

    Defines which permissions each role grants.
    """
    return {
        "user": [
            "users:read",
            "dashboard:read",
            "profile:read",
            "profile:write"
        ],
        "admin": [
            "users:read",
            "users:write",
            "organizations:read",
            "admin:read",
            "admin:write"
        ],
        "superadmin": [
            "users:read", "users:write", "users:delete",
            "organizations:read", "organizations:write", "organizations:delete",
            "system:read", "system:write", "system:configure",
            "admin:read", "admin:write", "admin:delete"
        ]
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Reset environment variables before each test.

    Ensures test isolation by clearing auth-related env vars.
    """
    import os
    auth_env_vars = [
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "REDIS_URL",
        "KEY_VAULT_URL"
    ]
    original_values = {var: os.environ.get(var) for var in auth_env_vars}

    # Clear for test
    for var in auth_env_vars:
        os.environ.pop(var, None)

    yield

    # Restore
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


@pytest.fixture
def mock_datetime_now(monkeypatch):
    """
    Mock datetime.now() for testing time-sensitive operations.

    Returns a function that can be called to set the mocked time.
    """
    class MockDateTime:
        @classmethod
        def now(cls, tz=None):
            return cls._now

        @classmethod
        def set_now(cls, dt):
            cls._now = dt

    MockDateTime.set_now(datetime.now(timezone.utc))

    monkeypatch.setattr("datetime.datetime", MockDateTime)
    return MockDateTime.set_now
