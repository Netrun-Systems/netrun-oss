"""
Authentication Fixtures for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides comprehensive authentication test fixtures including:
- RSA key pair generation for JWT testing
- Sample JWT claims with various permission levels
- Test users (regular, admin, superadmin)
- Test tenant IDs for multi-tenancy testing
- Mock FastAPI request objects with authentication headers

Usage:
    def test_jwt_encoding(rsa_key_pair, sample_jwt_claims):
        token = encode_jwt(sample_jwt_claims, rsa_key_pair[0])
        assert token is not None

Fixtures:
    - rsa_key_pair: Generate RSA keys for JWT signing/verification
    - temp_key_files: Temporary PEM files for key loading tests
    - sample_jwt_claims: Standard JWT claims with full permissions
    - minimal_claims: Minimal valid JWT claims (required fields only)
    - expired_claims: Expired JWT claims for expiry testing
    - test_user: Regular user with basic permissions
    - admin_user: Admin user with elevated permissions
    - superadmin_user: Superadmin with full system access
    - test_tenant_id: Standard test tenant UUID
    - mock_request: Mock FastAPI Request object
    - mock_request_with_jwt: Request with JWT Authorization header
    - mock_api_key_request: Request with X-API-Key header
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, Generator
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Graceful netrun-logging integration (optional)
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


@pytest.fixture
def rsa_key_pair() -> Tuple[bytes, bytes]:
    """
    Generate RSA key pair for JWT testing.

    Creates a 2048-bit RSA key pair for RS256 JWT signing and verification.
    Keys are generated fresh for each test to ensure isolation and prevent
    cross-test contamination.

    Returns:
        Tuple[bytes, bytes]: (private_key_pem, public_key_pem)

    Example:
        def test_jwt_signing(rsa_key_pair):
            private_pem, public_pem = rsa_key_pair
            token = jwt.encode(payload, private_pem, algorithm='RS256')
            decoded = jwt.decode(token, public_pem, algorithms=['RS256'])
    """
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
def temp_key_files(rsa_key_pair) -> Generator[Tuple[Path, Path], None, None]:
    """
    Create temporary PEM files for key loading tests.

    Writes RSA key pair to temporary PEM files for testing file-based
    key loading scenarios (Azure Key Vault fallback, local development).

    Args:
        rsa_key_pair: RSA key pair fixture

    Yields:
        Tuple[Path, Path]: (private_key_path, public_key_path)

    Cleanup:
        Automatically deletes temporary files after test completion

    Example:
        def test_load_keys_from_file(temp_key_files):
            private_path, public_path = temp_key_files
            private_key = load_private_key(private_path)
            assert private_key is not None
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
def sample_jwt_claims() -> Dict[str, Any]:
    """
    Sample JWT claims for testing with full permissions.

    Provides a complete JWT claims structure with:
    - jti: JWT ID for token blacklisting
    - sub: Subject (user ID)
    - user_id: Netrun user identifier
    - tenant_id: Multi-tenant organization ID
    - roles: List of user roles
    - permissions: Granular permission list
    - session_id: Session tracking
    - ip_address: Client IP for security logging
    - user_agent: Client user agent
    - iat: Issued at timestamp
    - exp: Expiration timestamp (15 minutes from now)

    Returns:
        Dict[str, Any]: Complete JWT claims dictionary

    Example:
        def test_permission_check(sample_jwt_claims):
            assert "users:write" in sample_jwt_claims["permissions"]
            assert "admin" in sample_jwt_claims["roles"]
    """
    return {
        "jti": "test-jti-12345",
        "sub": "user-123",
        "user_id": "user-123",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
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
    Minimal valid JWT claims (required fields only).

    Use for testing required vs optional claim validation.
    Contains only mandatory fields without optional metadata.

    Returns:
        Dict[str, Any]: Minimal JWT claims dictionary

    Example:
        def test_minimal_token_validation(minimal_claims):
            # Should validate with only required fields
            is_valid = validate_claims(minimal_claims)
            assert is_valid is True
    """
    return {
        "jti": "test-jti-minimal",
        "sub": "user-minimal",
        "user_id": "user-minimal",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "roles": [],
        "permissions": [],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
    }


@pytest.fixture
def expired_claims() -> Dict[str, Any]:
    """
    Expired JWT claims for testing token expiry validation.

    Claims with expiration timestamp set 1 hour in the past.
    Use for testing expired token rejection and refresh flows.

    Returns:
        Dict[str, Any]: Expired JWT claims dictionary

    Example:
        def test_expired_token_rejection(expired_claims):
            with pytest.raises(ExpiredTokenError):
                validate_token_expiry(expired_claims)
    """
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    return {
        "jti": "test-jti-expired",
        "sub": "user-expired",
        "user_id": "user-expired",
        "tenant_id": "00000000-0000-0000-0000-000000000003",
        "roles": ["user"],
        "permissions": ["users:read"],
        "iat": int((past_time - timedelta(minutes=15)).timestamp()),
        "exp": int(past_time.timestamp())
    }


@pytest.fixture
def test_user() -> Dict[str, Any]:
    """
    Sample regular user for testing.

    Standard user with basic read permissions for dashboard and profile.
    Use for testing standard user access patterns.

    Returns:
        Dict[str, Any]: Regular user dictionary

    Example:
        def test_user_dashboard_access(test_user):
            assert can_access_dashboard(test_user)
            assert not can_access_admin_panel(test_user)
    """
    return {
        "id": "user-123",
        "email": "test@netrunsystems.com",
        "name": "Test User",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "roles": ["user"],
        "permissions": ["users:read", "dashboard:read"]
    }


@pytest.fixture
def admin_user() -> Dict[str, Any]:
    """
    Sample admin user for testing.

    Admin user with elevated read/write permissions for users and organizations.
    Use for testing admin access patterns and elevated permission checks.

    Returns:
        Dict[str, Any]: Admin user dictionary

    Example:
        def test_admin_user_management(admin_user):
            assert can_create_users(admin_user)
            assert can_manage_organizations(admin_user)
    """
    return {
        "id": "admin-001",
        "email": "admin@netrunsystems.com",
        "name": "Admin User",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "roles": ["admin", "user"],
        "permissions": [
            "users:read", "users:write",
            "admin:read", "admin:write",
            "organizations:read", "organizations:write"
        ]
    }


@pytest.fixture
def superadmin_user() -> Dict[str, Any]:
    """
    Sample superadmin user for testing.

    Superadmin with full system permissions including delete operations.
    Use for testing maximum privilege scenarios and system-level operations.

    Returns:
        Dict[str, Any]: Superadmin user dictionary

    Example:
        def test_superadmin_system_access(superadmin_user):
            assert can_configure_system(superadmin_user)
            assert can_delete_organizations(superadmin_user)
    """
    return {
        "id": "superadmin-001",
        "email": "superadmin@netrunsystems.com",
        "name": "Super Admin",
        "tenant_id": "org-netrun",
        "roles": ["superadmin", "admin", "user"],
        "permissions": [
            "users:read", "users:write", "users:delete",
            "admin:read", "admin:write", "admin:delete",
            "organizations:read", "organizations:write", "organizations:delete",
            "system:read", "system:write", "system:configure"
        ]
    }


@pytest.fixture
def test_tenant_id() -> str:
    """
    Standard test tenant UUID for multi-tenancy testing.

    Consistent tenant ID used across test fixtures for data isolation testing.

    Returns:
        str: Test tenant UUID

    Example:
        def test_tenant_isolation(test_tenant_id):
            data = fetch_tenant_data(test_tenant_id)
            assert all(record.tenant_id == test_tenant_id for record in data)
    """
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def mock_request():
    """
    Mock FastAPI Request object for middleware testing.

    Provides a MagicMock with common request attributes:
    - headers: Dict of HTTP headers
    - url: Request URL object with path
    - client: Client connection info (host)
    - state: Request state for storing auth context

    Returns:
        MagicMock: Mock FastAPI Request object

    Example:
        def test_auth_middleware(mock_request):
            mock_request.headers["Authorization"] = "Bearer token"
            await auth_middleware(mock_request)
            assert hasattr(mock_request.state, "user")
    """
    request = MagicMock()
    request.headers = {}
    request.url.path = "/api/test"
    request.client.host = "192.168.1.1"
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_request_with_jwt(mock_request, rsa_key_pair, sample_jwt_claims):
    """
    Mock FastAPI Request with valid JWT in Authorization header.

    Pre-configured request for testing authenticated request flows.
    Note: Contains placeholder token - tests should generate real token if needed.

    Args:
        mock_request: Base mock request fixture
        rsa_key_pair: RSA key pair for token generation
        sample_jwt_claims: Sample JWT claims

    Returns:
        MagicMock: Mock request with Authorization header

    Example:
        def test_authenticated_endpoint(mock_request_with_jwt):
            user = extract_user_from_request(mock_request_with_jwt)
            assert user is not None
    """
    mock_request.headers["Authorization"] = "Bearer test-token-placeholder"
    return mock_request


@pytest.fixture
def mock_api_key_request(mock_request):
    """
    Mock FastAPI Request with API key authentication.

    Pre-configured request with X-API-Key header for testing
    API key authentication flows (service-to-service communication).

    Args:
        mock_request: Base mock request fixture

    Returns:
        MagicMock: Mock request with X-API-Key header

    Example:
        def test_api_key_auth(mock_api_key_request):
            is_valid = validate_api_key(mock_api_key_request)
            assert is_valid is True
    """
    mock_request.headers["X-API-Key"] = "test-api-key-12345"
    return mock_request


@pytest.fixture
def sample_role_hierarchy() -> Dict[str, list]:
    """
    Sample role hierarchy for RBAC testing.

    Defines role inheritance:
    - superadmin inherits admin and user
    - admin inherits user
    - user has no inheritance

    Returns:
        Dict[str, list]: Role hierarchy mapping

    Example:
        def test_role_inheritance(sample_role_hierarchy):
            assert "admin" in sample_role_hierarchy["superadmin"]
            assert "user" in sample_role_hierarchy["admin"]
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
    Use for testing permission resolution and RBAC logic.

    Returns:
        Dict[str, list]: Role to permissions mapping

    Example:
        def test_permission_resolution(sample_permission_map):
            user_perms = sample_permission_map["user"]
            assert "users:read" in user_perms
    """
    return {
        "user": [
            "users:read",
            "dashboard:read",
            "profile:read",
            "profile:write"
        ],
        "admin": [
            "users:read", "users:write",
            "organizations:read",
            "admin:read", "admin:write"
        ],
        "superadmin": [
            "users:read", "users:write", "users:delete",
            "organizations:read", "organizations:write", "organizations:delete",
            "system:read", "system:write", "system:configure",
            "admin:read", "admin:write", "admin:delete"
        ]
    }
