"""
API Client Fixtures for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides HTTP client fixtures for API testing:
- httpx AsyncClient for async HTTP testing
- FastAPI TestClient for synchronous API testing
- Mock HTTP response objects

Usage:
    @pytest.mark.asyncio
    async def test_api_endpoint(async_client):
        response = await async_client.get("/api/users")
        assert response.status_code == 200

Fixtures:
    - async_client: httpx AsyncClient for async HTTP requests
    - test_client: FastAPI TestClient for sync API testing
    - mock_response: Mock HTTP response object
    - base_url: Base URL for API testing
"""

import pytest
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import MagicMock

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
def base_url() -> str:
    """
    Base URL for API testing.

    Returns:
        str: Test API base URL

    Example:
        def test_api_url(base_url):
            assert base_url == "http://testserver"
    """
    return "http://testserver"


@pytest.fixture
async def async_client(base_url: str) -> AsyncGenerator:
    """
    Create httpx AsyncClient for async HTTP testing.

    Provides async HTTP client for testing API endpoints without running server.
    Automatically handles client lifecycle and cleanup.

    Args:
        base_url: Base URL fixture

    Yields:
        httpx.AsyncClient: Async HTTP client

    Example:
        @pytest.mark.asyncio
        async def test_get_users(async_client):
            response = await async_client.get("/api/users")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    """
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx not installed - install with: pip install httpx")

    async with httpx.AsyncClient(base_url=base_url) as client:
        yield client


@pytest.fixture
def test_client():
    """
    Create FastAPI TestClient for synchronous API testing.

    Provides sync test client for FastAPI applications.
    Requires app fixture to be defined in test suite.

    Note:
        Requires app fixture in your test suite:

        @pytest.fixture
        def app():
            from myapp import create_app
            return create_app()

        def test_endpoint(test_client, app):
            client = test_client(app)
            response = client.get("/api/health")
            assert response.status_code == 200

    Returns:
        Callable: Function that creates TestClient from FastAPI app

    Example:
        def test_health_check(test_client, app):
            client = test_client(app)
            response = client.get("/health")
            assert response.status_code == 200
    """
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi not installed - install with: pip install fastapi")

    def _create_test_client(app):
        return TestClient(app)

    return _create_test_client


@pytest.fixture
def mock_response():
    """
    Mock HTTP response object for unit testing.

    Provides configurable mock response without actual HTTP requests.
    Use for testing HTTP client error handling and response parsing.

    Returns:
        MagicMock: Mock HTTP response

    Example:
        def test_response_parsing(mock_response):
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}

            result = parse_api_response(mock_response)
            assert result["data"] == "test"
    """
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {}
    response.text = ""
    response.content = b""
    response.ok = True
    return response


@pytest.fixture
def mock_async_client():
    """
    Mock httpx AsyncClient for unit testing without HTTP requests.

    Provides mock async client for testing code that uses httpx
    without making actual network calls.

    Returns:
        MagicMock: Mock async HTTP client

    Example:
        @pytest.mark.asyncio
        async def test_api_service(mock_async_client):
            from unittest.mock import AsyncMock

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"users": []}

            mock_async_client.get = AsyncMock(return_value=mock_response)

            service = ApiService(mock_async_client)
            users = await service.get_users()
            assert users == []
    """
    from unittest.mock import AsyncMock

    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    client.head = AsyncMock()
    client.options = AsyncMock()

    return client


@pytest.fixture
def auth_headers(sample_jwt_claims, rsa_key_pair) -> dict:
    """
    Create authorization headers with JWT token.

    Generates headers dictionary with Bearer token for authenticated requests.
    Note: Contains placeholder token - tests should generate real token if needed.

    Args:
        sample_jwt_claims: JWT claims fixture
        rsa_key_pair: RSA key pair fixture

    Returns:
        dict: Headers with Authorization

    Example:
        @pytest.mark.asyncio
        async def test_authenticated_request(async_client, auth_headers):
            response = await async_client.get("/api/protected", headers=auth_headers)
            assert response.status_code == 200
    """
    return {
        "Authorization": "Bearer test-jwt-token-placeholder",
        "Content-Type": "application/json"
    }


@pytest.fixture
def api_key_headers() -> dict:
    """
    Create headers with API key authentication.

    Returns:
        dict: Headers with X-API-Key

    Example:
        @pytest.mark.asyncio
        async def test_api_key_request(async_client, api_key_headers):
            response = await async_client.get("/api/service", headers=api_key_headers)
            assert response.status_code == 200
    """
    return {
        "X-API-Key": "test-api-key-12345",
        "Content-Type": "application/json"
    }


@pytest.fixture
def multipart_headers() -> dict:
    """
    Create headers for multipart form data uploads.

    Returns:
        dict: Headers for multipart requests

    Example:
        @pytest.mark.asyncio
        async def test_file_upload(async_client, multipart_headers):
            files = {"file": ("test.txt", b"content", "text/plain")}
            response = await async_client.post(
                "/api/upload",
                files=files,
                headers=multipart_headers
            )
            assert response.status_code == 200
    """
    return {
        "Content-Type": "multipart/form-data"
    }


@pytest.fixture
def mock_httpx_transport():
    """
    Mock httpx transport for controlling request/response flow.

    Use for testing retry logic, timeout handling, and network errors
    without actual network calls.

    Returns:
        MagicMock: Mock httpx transport

    Example:
        def test_retry_logic(mock_httpx_transport):
            from httpx import ConnectError

            mock_httpx_transport.handle_request.side_effect = [
                ConnectError("Connection failed"),
                ConnectError("Connection failed"),
                MagicMock(status_code=200)  # Success on 3rd try
            ]

            # Test that client retries and eventually succeeds
    """
    transport = MagicMock()
    return transport
