"""
Comprehensive tests for GeminiAdapter.

Tests cover:
    - Adapter initialization
    - Free tier quota tracking
    - Execute method with mocked Gemini client
    - Error handling (rate limits, authentication, quota)
    - Cost calculation (free tier vs paid)
    - Availability checking
    - Quota management
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

from netrun.llm.adapters.gemini import GeminiAdapter, FREE_TIER_DAILY_LIMIT, DEFAULT_MODEL
from netrun.llm.adapters.base import LLMResponse, AdapterTier


@pytest.fixture
def mock_gemini_available():
    """Mock Gemini as available."""
    with patch("netrun.llm.adapters.gemini.GEMINI_AVAILABLE", True):
        with patch("netrun.llm.adapters.gemini.genai") as mock_genai:
            with patch("netrun.llm.adapters.gemini.GenerationConfig") as mock_config:
                yield mock_genai, mock_config


class TestGeminiAdapterInitialization:
    """Test Gemini adapter initialization."""

    def test_default_initialization(self, mock_gemini_available, monkeypatch):
        """Test adapter initializes with defaults."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        adapter = GeminiAdapter()

        assert adapter.adapter_name == "Gemini-API"
        assert adapter.tier == AdapterTier.API
        assert adapter.reliability_score == 1.0
        assert adapter.default_model == DEFAULT_MODEL
        assert adapter.use_free_tier is True

    def test_initialization_without_gemini_package(self):
        """Test initialization fails when package not installed."""
        with patch("netrun.llm.adapters.gemini.GEMINI_AVAILABLE", False):
            with pytest.raises(ImportError):
                GeminiAdapter()

    def test_initialization_without_api_key(self, mock_gemini_available, monkeypatch):
        """Test adapter behavior when no API key provided.

        Note: Implementation falls back to GEMINI_API_KEY env var (line 119),
        so we need to clear the environment to test true no-key behavior.
        """
        # Clear environment variable to prevent fallback
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        adapter = GeminiAdapter(api_key=None)

        # Without api_key and without env var, adapter should be disabled (line 137)
        assert adapter.enabled is False


class TestGeminiQuotaTracking:
    """Test Gemini quota tracking."""

    def test_load_quota_data_new_file(self, mock_gemini_available, tmp_path):
        """Test loading quota data when file doesn't exist."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        quota_data = adapter.quota_data

        assert quota_data["requests_today"] == 0
        assert "date" in quota_data

    def test_load_quota_data_existing_file(
        self, mock_gemini_available, tmp_path, monkeypatch
    ):
        """Test loading quota data from existing file."""
        from datetime import datetime

        quota_file = tmp_path / "quota.json"
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Write quota file
        quota_file.write_text(
            json.dumps({"date": current_date, "requests_today": 10})
        )

        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        assert adapter.quota_data["requests_today"] == 10

    def test_quota_resets_on_new_day(self, mock_gemini_available, tmp_path):
        """Test quota resets when date changes."""
        quota_file = tmp_path / "quota.json"

        # Write old date
        quota_file.write_text(
            json.dumps({"date": "2024-01-01", "requests_today": 100})
        )

        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        # Should reset to 0 because date is old
        assert adapter.quota_data["requests_today"] == 0

    def test_check_quota_allows_request(self, mock_gemini_available, tmp_path):
        """Test quota check allows request under limit."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=True,
            quota_file_path=str(quota_file),
        )

        adapter.quota_data["requests_today"] = 100

        assert adapter._check_quota() is True

    def test_check_quota_blocks_when_exceeded(
        self, mock_gemini_available, tmp_path
    ):
        """Test quota check blocks when limit reached or exceeded.

        Implementation: _check_quota() reloads quota_data from file (line 179),
        then returns True if requests_today < limit (line 181).
        So when requests_today == limit (1500), the check 1500 < 1500 = False (blocked).
        Must save to file for changes to persist.
        """
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=True,
            quota_file_path=str(quota_file),
        )

        # Just under the limit - still allowed
        adapter.quota_data["requests_today"] = FREE_TIER_DAILY_LIMIT - 1
        adapter._save_quota_data()
        assert adapter._check_quota() is True

        # At the limit (1500) - blocked (1500 < 1500 = False)
        adapter.quota_data["requests_today"] = FREE_TIER_DAILY_LIMIT
        adapter._save_quota_data()
        assert adapter._check_quota() is False

        # Over the limit - also blocked
        adapter.quota_data["requests_today"] = FREE_TIER_DAILY_LIMIT + 1
        adapter._save_quota_data()
        assert adapter._check_quota() is False

    def test_check_quota_ignores_limit_on_paid_tier(
        self, mock_gemini_available, tmp_path
    ):
        """Test quota check ignores limit on paid tier."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=False,
            quota_file_path=str(quota_file),
        )

        adapter.quota_data["requests_today"] = FREE_TIER_DAILY_LIMIT + 100

        assert adapter._check_quota() is True

    def test_increment_quota(self, mock_gemini_available, tmp_path):
        """Test incrementing quota counter."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        initial_count = adapter.quota_data["requests_today"]
        adapter._increment_quota()

        assert adapter.quota_data["requests_today"] == initial_count + 1


class TestGeminiExecution:
    """Test Gemini execute method."""

    @pytest.fixture
    def mock_gemini_response(self):
        """Create mock Gemini API response."""
        mock_response = Mock()
        mock_response.text = "This is a test response"
        mock_response.usage_metadata = Mock(
            prompt_token_count=100, candidates_token_count=200
        )
        mock_response.candidates = [Mock(finish_reason=Mock(name="STOP"))]
        return mock_response

    def test_execute_success(
        self, mock_gemini_available, tmp_path, mock_gemini_response
    ):
        """Test successful execution."""
        mock_genai, mock_config = mock_gemini_available

        # Setup mock model
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_gemini_response
        mock_genai.GenerativeModel.return_value = mock_model

        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        response = adapter.execute("Test prompt")

        # Verify response
        assert response.is_success is True
        assert response.content == "This is a test response"
        assert response.tokens_input == 100
        assert response.tokens_output == 200

        # Verify quota incremented
        assert adapter.quota_data["requests_today"] == 1

    def test_execute_quota_exceeded(self, mock_gemini_available, tmp_path):
        """Test execution when quota exceeded.

        Implementation: execute() checks _check_quota() which reloads from file
        and returns False when requests_today >= FREE_TIER_DAILY_LIMIT.
        Must save to file for changes to persist.
        """
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=True,
            quota_file_path=str(quota_file),
        )

        # Set quota over the limit and save to file
        adapter.quota_data["requests_today"] = FREE_TIER_DAILY_LIMIT + 1
        adapter._save_quota_data()

        response = adapter.execute("Test prompt")

        assert response.status == "rate_limited"
        assert "quota exceeded" in response.error.lower()

    def test_execute_with_circuit_breaker_open(
        self, mock_gemini_available, tmp_path
    ):
        """Test execution when circuit breaker is open.

        Note: GeminiAdapter.__init__() doesn't accept circuit_breaker_threshold parameter.
        We need to manually set the threshold after initialization, or trigger enough
        failures to open it with the default threshold (5).
        """
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        # Manually set threshold to 1 for easier testing
        adapter._circuit_breaker_threshold = 1

        # Open circuit breaker by recording failure
        adapter._record_failure()

        response = adapter.execute("Test prompt")

        assert response.is_success is False
        assert "Circuit breaker open" in response.error


class TestGeminiCostCalculation:
    """Test Gemini cost calculation."""

    def test_calculate_cost_free_tier(self, mock_gemini_available, tmp_path):
        """Test cost calculation on free tier."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=True,
            quota_file_path=str(quota_file),
        )

        cost = adapter._calculate_actual_cost("gemini-1.5-flash", 1000, 2000)

        assert cost == 0.0

    def test_calculate_cost_paid_tier(self, mock_gemini_available, tmp_path):
        """Test cost calculation on paid tier."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=False,
            quota_file_path=str(quota_file),
        )

        cost = adapter._calculate_actual_cost("gemini-1.5-flash", 1000, 2000)

        # Expected: (1000/1M * $0.075) + (2000/1M * $0.30) = $0.000075 + $0.0006
        assert cost > 0

    def test_estimate_cost_free_tier(self, mock_gemini_available, tmp_path):
        """Test cost estimation on free tier."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            use_free_tier=True,
            quota_file_path=str(quota_file),
        )

        cost = adapter.estimate_cost("Test prompt")

        assert cost == 0.0


class TestGeminiAvailability:
    """Test Gemini availability checking."""

    def test_check_availability_healthy(self, mock_gemini_available, tmp_path):
        """Test availability when healthy."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        assert adapter.check_availability() is True

    def test_check_availability_quota_exceeded(
        self, mock_gemini_available, tmp_path
    ):
        """Test availability when quota exceeded.

        Implementation: check_availability() calls _check_quota() which reloads
        from file and returns True when requests_today < limit.
        Must save to file for changes to persist.
        """
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        # Set quota OVER the limit and save to make it unavailable
        adapter.quota_data["requests_today"] = FREE_TIER_DAILY_LIMIT + 1
        adapter._save_quota_data()

        assert adapter.check_availability() is False


class TestGeminiMetadata:
    """Test Gemini metadata retrieval."""

    def test_get_metadata(self, mock_gemini_available, tmp_path):
        """Test metadata includes all expected fields."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        adapter._record_success(100, 0.0)

        metadata = adapter.get_metadata()

        assert metadata["name"] == "Gemini-API"
        assert metadata["tier"] == "API"
        assert metadata["use_free_tier"] is True
        assert "quota" in metadata
        assert metadata["quota"]["daily_limit"] == FREE_TIER_DAILY_LIMIT

    def test_get_quota_status_free_tier(self, mock_gemini_available, tmp_path):
        """Test quota status on free tier.

        Implementation: get_quota_status() reloads quota_data from file (line 459),
        so setting adapter.quota_data directly won't persist unless we save it first.
        """
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        # Set and save quota data so it persists through reload
        adapter.quota_data["requests_today"] = 500
        adapter._save_quota_data()

        status = adapter.get_quota_status()

        assert status["tier"] == "free"
        assert status["requests_today"] == 500
        assert status["requests_remaining"] == FREE_TIER_DAILY_LIMIT - 500
        assert status["quota_exceeded"] is False

    def test_reset_quota(self, mock_gemini_available, tmp_path):
        """Test quota reset."""
        quota_file = tmp_path / "quota.json"
        adapter = GeminiAdapter(
            api_key="test-key",
            quota_file_path=str(quota_file),
        )

        adapter.quota_data["requests_today"] = 500
        adapter.reset_quota()

        assert adapter.quota_data["requests_today"] == 0
