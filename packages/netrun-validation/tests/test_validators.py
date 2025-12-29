"""Tests for generic validators."""

import pytest
from netrun.validation.validators import (
    validate_enum_value,
    validate_range,
    validate_non_empty,
    validate_list_from_csv,
    validate_positive_int,
    validate_non_negative_int,
    validate_percentage,
)


class TestValidateEnumValue:
    """Tests for validate_enum_value."""

    def test_valid_value(self):
        """Test validation with valid value."""
        result = validate_enum_value("production", ["dev", "staging", "production"], "env")
        assert result == "production"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        result = validate_enum_value("PRODUCTION", ["dev", "staging", "production"], "env")
        assert result == "production"

    def test_case_sensitive(self):
        """Test case-sensitive validation."""
        result = validate_enum_value("PRODUCTION", ["DEV", "STAGING", "PRODUCTION"], "env", case_sensitive=True)
        assert result == "PRODUCTION"

    def test_invalid_value(self):
        """Test validation with invalid value."""
        with pytest.raises(ValueError, match="env must be one of"):
            validate_enum_value("invalid", ["dev", "staging", "production"], "env")

    def test_empty_value(self):
        """Test validation with empty value."""
        with pytest.raises(ValueError, match="env cannot be empty"):
            validate_enum_value("", ["dev", "staging", "production"], "env")


class TestValidateRange:
    """Tests for validate_range."""

    def test_within_range(self):
        """Test value within range."""
        assert validate_range(5, 1, 10, "value") == 5

    def test_at_min(self):
        """Test value at minimum."""
        assert validate_range(1, 1, 10, "value") == 1

    def test_at_max(self):
        """Test value at maximum."""
        assert validate_range(10, 1, 10, "value") == 10

    def test_below_min(self):
        """Test value below minimum."""
        with pytest.raises(ValueError, match="value must be at least 1"):
            validate_range(0, 1, 10, "value")

    def test_above_max(self):
        """Test value above maximum."""
        with pytest.raises(ValueError, match="value must be at most 10"):
            validate_range(11, 1, 10, "value")

    def test_min_only(self):
        """Test validation with minimum only."""
        assert validate_range(100, min_val=1) == 100

    def test_max_only(self):
        """Test validation with maximum only."""
        assert validate_range(5, max_val=10) == 5

    def test_float_values(self):
        """Test validation with float values."""
        assert validate_range(0.7, 0.0, 2.0, "temperature") == 0.7


class TestValidateNonEmpty:
    """Tests for validate_non_empty."""

    def test_valid_string(self):
        """Test validation with valid string."""
        assert validate_non_empty("hello", "name") == "hello"

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed."""
        assert validate_non_empty("  world  ", "name") == "world"

    def test_empty_string(self):
        """Test validation with empty string."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            validate_non_empty("", "name")

    def test_whitespace_only(self):
        """Test validation with whitespace only."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            validate_non_empty("   ", "name")

    def test_none_value(self):
        """Test validation with None."""
        with pytest.raises(ValueError, match="name is required"):
            validate_non_empty(None, "name")


class TestValidateListFromCSV:
    """Tests for validate_list_from_csv."""

    def test_csv_string(self):
        """Test conversion from CSV string."""
        result = validate_list_from_csv("value1, value2, value3")
        assert result == ["value1", "value2", "value3"]

    def test_csv_with_spaces(self):
        """Test CSV with extra spaces."""
        result = validate_list_from_csv("  value1  ,  value2  ,  value3  ")
        assert result == ["value1", "value2", "value3"]

    def test_existing_list(self):
        """Test with existing list."""
        result = validate_list_from_csv(["value1", "value2"])
        assert result == ["value1", "value2"]

    def test_empty_items(self):
        """Test CSV with empty items."""
        result = validate_list_from_csv("value1,,value2")
        assert result == ["value1", "value2"]


class TestValidatePositiveInt:
    """Tests for validate_positive_int."""

    def test_positive_value(self):
        """Test validation with positive value."""
        assert validate_positive_int(10, "pool_size") == 10

    def test_one(self):
        """Test validation with 1."""
        assert validate_positive_int(1, "pool_size") == 1

    def test_zero(self):
        """Test validation with 0."""
        with pytest.raises(ValueError, match="pool_size must be at least 1"):
            validate_positive_int(0, "pool_size")

    def test_negative(self):
        """Test validation with negative value."""
        with pytest.raises(ValueError, match="pool_size must be at least 1"):
            validate_positive_int(-1, "pool_size")


class TestValidateNonNegativeInt:
    """Tests for validate_non_negative_int."""

    def test_positive_value(self):
        """Test validation with positive value."""
        assert validate_non_negative_int(10, "retry_count") == 10

    def test_zero(self):
        """Test validation with 0."""
        assert validate_non_negative_int(0, "retry_count") == 0

    def test_negative(self):
        """Test validation with negative value."""
        with pytest.raises(ValueError, match="retry_count must be at least 0"):
            validate_non_negative_int(-1, "retry_count")


class TestValidatePercentage:
    """Tests for validate_percentage."""

    def test_valid_percentage(self):
        """Test validation with valid percentage."""
        assert validate_percentage(75.5, "completion") == 75.5

    def test_zero(self):
        """Test validation with 0."""
        assert validate_percentage(0, "completion") == 0.0

    def test_hundred(self):
        """Test validation with 100."""
        assert validate_percentage(100, "completion") == 100.0

    def test_negative(self):
        """Test validation with negative value."""
        with pytest.raises(ValueError, match="completion must be at least 0.0"):
            validate_percentage(-1, "completion")

    def test_above_hundred(self):
        """Test validation with value above 100."""
        with pytest.raises(ValueError, match="completion must be at most 100.0"):
            validate_percentage(101, "completion")
