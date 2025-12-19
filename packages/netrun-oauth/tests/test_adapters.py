"""
Tests for OAuth adapters

Part of: netrun-oauth v1.0.0
"""

import pytest
from netrun_oauth import (
    MicrosoftAdapter,
    GoogleAdapter,
    PostResult,
    TokenData,
)


def test_microsoft_adapter_initialization():
    """Test Microsoft adapter initializes correctly"""
    adapter = MicrosoftAdapter(
        client_id="test_client_id",
        client_secret="test_client_secret"
    )
    assert adapter.platform_name == "microsoft"
    assert adapter.client_id == "test_client_id"
    assert adapter.client_secret == "test_client_secret"


def test_google_adapter_initialization():
    """Test Google adapter initializes correctly"""
    adapter = GoogleAdapter(
        client_id="test_client_id",
        client_secret="test_client_secret"
    )
    assert adapter.platform_name == "google"
    assert adapter.client_id == "test_client_id"
    assert adapter.client_secret == "test_client_secret"


def test_adapter_validate_content_length():
    """Test content validation helper"""
    adapter = MicrosoftAdapter()

    # Content within limit
    short_content = "a" * 100
    result = adapter._validate_content_length(short_content, 200)
    assert result == short_content

    # Content exceeding limit with truncation
    long_content = "a" * 300
    result = adapter._validate_content_length(long_content, 200, truncate=True)
    assert len(result) == 200
    assert result.endswith("...")

    # Content exceeding limit without truncation should raise
    from netrun_oauth.exceptions import ValidationError
    with pytest.raises(ValidationError):
        adapter._validate_content_length(long_content, 200, truncate=False)


def test_adapter_check_rate_limit_response():
    """Test rate limit detection"""
    adapter = MicrosoftAdapter()

    # Normal response (no rate limit)
    adapter._check_rate_limit_response(200, {})

    # Rate limit response
    from netrun_oauth.exceptions import RateLimitError
    with pytest.raises(RateLimitError) as exc_info:
        adapter._check_rate_limit_response(429, {"Retry-After": "60"})

    assert exc_info.value.retry_after_seconds == 60


def test_adapter_check_authentication_response():
    """Test authentication error detection"""
    adapter = MicrosoftAdapter()

    # Normal response (authenticated)
    adapter._check_authentication_response(200)

    # Authentication failure (401)
    from netrun_oauth.exceptions import AuthenticationError
    with pytest.raises(AuthenticationError):
        adapter._check_authentication_response(401)

    # Authorization failure (403)
    with pytest.raises(AuthenticationError):
        adapter._check_authentication_response(403)


def test_post_result_dataclass():
    """Test PostResult dataclass"""
    result = PostResult(
        success=True,
        platform="microsoft",
        post_id="12345",
        post_url="https://example.com/posts/12345"
    )
    assert result.success is True
    assert result.platform == "microsoft"
    assert result.post_id == "12345"
    assert result.error_message is None


def test_token_data_dataclass():
    """Test TokenData dataclass"""
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)

    token = TokenData(
        access_token="access_token_123",
        refresh_token="refresh_token_456",
        expires_at=expires_at,
        token_type="Bearer",
        scope="User.Read"
    )
    assert token.access_token == "access_token_123"
    assert token.refresh_token == "refresh_token_456"
    assert token.token_type == "Bearer"
    assert token.scope == "User.Read"
