"""Tests for datetime validators."""

import pytest
from datetime import datetime, timezone, timedelta
from netrun.validation.datetime_utils import (
    validate_iso_timestamp,
    validate_timezone,
    validate_date_range,
    validate_future_date,
    validate_past_date,
    validate_date_not_before,
    validate_unix_timestamp,
)


class TestValidateISOTimestamp:
    """Tests for validate_iso_timestamp."""

    def test_valid_timestamp_z(self):
        """Test validation with Z timezone."""
        result = validate_iso_timestamp("2025-01-15T10:30:00Z")
        assert isinstance(result, datetime)

    def test_valid_timestamp_offset(self):
        """Test validation with timezone offset."""
        result = validate_iso_timestamp("2025-01-15T10:30:00+00:00")
        assert isinstance(result, datetime)

    def test_datetime_input(self):
        """Test validation with datetime input."""
        dt = datetime.now(timezone.utc)
        result = validate_iso_timestamp(dt)
        assert result == dt

    def test_invalid_timestamp(self):
        """Test validation with invalid timestamp."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 timestamp format"):
            validate_iso_timestamp("invalid")

    def test_empty_timestamp(self):
        """Test validation with empty timestamp."""
        with pytest.raises(ValueError, match="Timestamp is required"):
            validate_iso_timestamp("")


class TestValidateTimezone:
    """Tests for validate_timezone."""

    def test_utc(self):
        """Test UTC timezone."""
        assert validate_timezone("UTC") == "UTC"

    def test_gmt(self):
        """Test GMT timezone."""
        assert validate_timezone("GMT") == "GMT"

    def test_area_location(self):
        """Test Area/Location format."""
        assert validate_timezone("America/New_York") == "America/New_York"

    def test_invalid_timezone(self):
        """Test validation with invalid timezone."""
        with pytest.raises(ValueError, match="Invalid timezone format"):
            validate_timezone("invalid-timezone")

    def test_empty_timezone(self):
        """Test validation with empty timezone."""
        with pytest.raises(ValueError, match="Timezone is required"):
            validate_timezone("")


class TestValidateDateRange:
    """Tests for validate_date_range."""

    def test_within_range(self):
        """Test date within range."""
        dt = datetime(2025, 6, 15)
        min_dt = datetime(2025, 1, 1)
        max_dt = datetime(2025, 12, 31)
        assert validate_date_range(dt, min_dt, max_dt) == dt

    def test_at_min(self):
        """Test date at minimum."""
        dt = datetime(2025, 1, 1)
        min_dt = datetime(2025, 1, 1)
        max_dt = datetime(2025, 12, 31)
        assert validate_date_range(dt, min_dt, max_dt) == dt

    def test_at_max(self):
        """Test date at maximum."""
        dt = datetime(2025, 12, 31)
        min_dt = datetime(2025, 1, 1)
        max_dt = datetime(2025, 12, 31)
        assert validate_date_range(dt, min_dt, max_dt) == dt

    def test_before_min(self):
        """Test date before minimum."""
        dt = datetime(2024, 12, 31)
        min_dt = datetime(2025, 1, 1)
        with pytest.raises(ValueError, match="date must be after"):
            validate_date_range(dt, min_dt)

    def test_after_max(self):
        """Test date after maximum."""
        dt = datetime(2026, 1, 1)
        max_dt = datetime(2025, 12, 31)
        with pytest.raises(ValueError, match="date must be before"):
            validate_date_range(dt, max_date=max_dt)


class TestValidateFutureDate:
    """Tests for validate_future_date."""

    def test_future_date(self):
        """Test validation with future date."""
        future = datetime.now(timezone.utc) + timedelta(days=1)
        result = validate_future_date(future)
        assert isinstance(result, datetime)

    def test_past_date(self):
        """Test validation with past date."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        with pytest.raises(ValueError, match="date must be in the future"):
            validate_future_date(past)

    def test_naive_datetime(self):
        """Test validation with naive datetime."""
        future = datetime.now() + timedelta(days=1)
        result = validate_future_date(future)
        assert isinstance(result, datetime)


class TestValidatePastDate:
    """Tests for validate_past_date."""

    def test_past_date(self):
        """Test validation with past date."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        result = validate_past_date(past)
        assert isinstance(result, datetime)

    def test_future_date(self):
        """Test validation with future date."""
        future = datetime.now(timezone.utc) + timedelta(days=1)
        with pytest.raises(ValueError, match="date must be in the past"):
            validate_past_date(future)

    def test_naive_datetime(self):
        """Test validation with naive datetime."""
        past = datetime.now() - timedelta(days=1)
        result = validate_past_date(past)
        assert isinstance(result, datetime)


class TestValidateDateNotBefore:
    """Tests for validate_date_not_before."""

    def test_after_reference(self):
        """Test date after reference."""
        dt = datetime(2025, 1, 15)
        ref = datetime(2025, 1, 1)
        assert validate_date_not_before(dt, ref) == dt

    def test_equal_to_reference(self):
        """Test date equal to reference."""
        dt = datetime(2025, 1, 1)
        ref = datetime(2025, 1, 1)
        assert validate_date_not_before(dt, ref) == dt

    def test_before_reference(self):
        """Test date before reference."""
        dt = datetime(2024, 12, 31)
        ref = datetime(2025, 1, 1)
        with pytest.raises(ValueError, match="date cannot be before"):
            validate_date_not_before(dt, ref)


class TestValidateUnixTimestamp:
    """Tests for validate_unix_timestamp."""

    def test_valid_timestamp(self):
        """Test validation with valid timestamp."""
        ts = 1704067200  # 2024-01-01
        assert validate_unix_timestamp(ts) == 1704067200

    def test_zero_timestamp(self):
        """Test validation with zero timestamp."""
        assert validate_unix_timestamp(0) == 0

    def test_negative_timestamp(self):
        """Test validation with negative timestamp."""
        with pytest.raises(ValueError, match="Unix timestamp must be non-negative"):
            validate_unix_timestamp(-1)

    def test_too_far_future(self):
        """Test validation with timestamp too far in future."""
        with pytest.raises(ValueError, match="Unix timestamp appears to be too far in the future"):
            validate_unix_timestamp(5000000000)

    def test_float_timestamp(self):
        """Test validation with float timestamp."""
        ts = 1704067200.5
        assert validate_unix_timestamp(ts) == 1704067200
