"""
Tests for validators module.

Comprehensive test suite for all validator functions in netrun-config.
"""

import pytest

from netrun.config.validators import (
    parse_cors_origins,
    validate_database_url,
    validate_environment,
    validate_log_level,
    validate_positive_int,
    validate_secret_key,
)


class TestEnvironmentValidator:
    """Tests for environment validation."""

    @pytest.mark.parametrize("env", [
        "development",
        "staging",
        "production",
        "testing",
    ])
    def test_valid_environments(self, env):
        """Test that valid environments pass validation."""
        assert validate_environment(env) == env

    @pytest.mark.parametrize("invalid_env", [
        "invalid",
        "dev",
        "prod",
        "test",
        "PRODUCTION",
        "Development",
        "local",
        "",
        "prod-east",
    ])
    def test_invalid_environment(self, invalid_env):
        """Test that invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="Environment must be one of"):
            validate_environment(invalid_env)

    def test_case_sensitive(self):
        """Test that environment validation is case-sensitive."""
        with pytest.raises(ValueError):
            validate_environment("PRODUCTION")


class TestSecretKeyValidator:
    """Tests for secret key validation."""

    @pytest.mark.parametrize("key_length", [32, 33, 48, 64, 128, 256])
    def test_valid_secret_key_lengths(self, key_length):
        """Test that valid secret keys (32+ chars) pass validation."""
        valid_key = "a" * key_length
        assert validate_secret_key(valid_key) == valid_key

    @pytest.mark.parametrize("key_length", [0, 1, 10, 20, 31])
    def test_short_secret_keys(self, key_length):
        """Test that short secret keys raise ValueError."""
        short_key = "a" * key_length if key_length > 0 else ""
        with pytest.raises(ValueError, match="must be at least 32 characters"):
            validate_secret_key(short_key)

    def test_none_secret_key(self):
        """Test that None secret key passes validation."""
        assert validate_secret_key(None) is None

    def test_exact_32_char_key(self):
        """Test boundary condition: exactly 32 characters."""
        key = "a" * 32  # Exactly 32 characters
        assert len(key) == 32
        assert validate_secret_key(key) == key


class TestCorsOriginsParser:
    """Tests for CORS origins parsing."""

    @pytest.mark.parametrize("input_str,expected", [
        ("http://localhost:3000", ["http://localhost:3000"]),
        ("http://localhost:3000,http://example.com",
         ["http://localhost:3000", "http://example.com"]),
        ("http://localhost:3000, http://example.com",
         ["http://localhost:3000", "http://example.com"]),
        ("  http://localhost:3000  ,  http://example.com  ",
         ["http://localhost:3000", "http://example.com"]),
        ("http://a.com,http://b.com,http://c.com",
         ["http://a.com", "http://b.com", "http://c.com"]),
        ("", []),
        ("   ", []),
    ])
    def test_parse_string_origins(self, input_str, expected):
        """Test parsing various string formats."""
        assert parse_cors_origins(input_str) == expected

    @pytest.mark.parametrize("input_list", [
        ["http://localhost:3000"],
        ["http://localhost:3000", "http://example.com"],
        ["http://a.com", "http://b.com", "http://c.com"],
        [],
    ])
    def test_parse_list_origins(self, input_list):
        """Test that lists pass through unchanged."""
        assert parse_cors_origins(input_list) == input_list

    def test_parse_none(self):
        """Test parsing None."""
        assert parse_cors_origins(None) == []

    def test_parse_empty_string_with_commas(self):
        """Test parsing string with only commas."""
        assert parse_cors_origins(",,,") == []

    def test_parse_mixed_whitespace(self):
        """Test parsing with tabs and multiple spaces."""
        result = parse_cors_origins("\thttp://a.com\t,\t  http://b.com  ")
        assert result == ["http://a.com", "http://b.com"]


class TestLogLevelValidator:
    """Tests for log level validation."""

    @pytest.mark.parametrize("level", [
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ])
    def test_valid_log_levels_uppercase(self, level):
        """Test that valid uppercase log levels pass validation."""
        assert validate_log_level(level) == level

    @pytest.mark.parametrize("level,expected", [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
        ("error", "ERROR"),
        ("critical", "CRITICAL"),
    ])
    def test_lowercase_log_levels_converted(self, level, expected):
        """Test that lowercase log levels are converted to uppercase."""
        assert validate_log_level(level) == expected

    @pytest.mark.parametrize("level,expected", [
        ("Debug", "DEBUG"),
        ("Info", "INFO"),
        ("Warning", "WARNING"),
    ])
    def test_mixed_case_log_levels(self, level, expected):
        """Test that mixed-case log levels are converted to uppercase."""
        assert validate_log_level(level) == expected

    @pytest.mark.parametrize("invalid_level", [
        "INVALID", "TRACE", "VERBOSE", "FATAL", "", "WARN", "ERR"
    ])
    def test_invalid_log_levels(self, invalid_level):
        """Test that invalid log levels raise ValueError."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            validate_log_level(invalid_level)


class TestDatabaseUrlValidator:
    """Tests for database URL validation."""

    @pytest.mark.parametrize("url", [
        "postgresql://user:pass@localhost:5432/dbname",
        "postgresql://user:pass@host.com:5432/db?sslmode=require",
        "postgresql+asyncpg://user:pass@localhost:5432/db",
        "mysql://user:pass@localhost:3306/db",
        "mysql+pymysql://user:pass@localhost:3306/db",
        "sqlite:///./test.db",
        "sqlite:///absolute/path/to/db.sqlite",
        "mongodb://user:pass@localhost:27017/db",
    ])
    def test_valid_database_urls(self, url):
        """Test that valid database URLs pass validation."""
        assert validate_database_url(url) == url

    @pytest.mark.parametrize("invalid_url", [
        "localhost:5432/dbname",
        "user:pass@localhost:5432/dbname",
        "just-a-hostname",
        "missing-scheme.com/database",
    ])
    def test_invalid_urls_no_scheme(self, invalid_url):
        """Test that URLs without scheme raise ValueError."""
        with pytest.raises(ValueError, match="must include scheme"):
            validate_database_url(invalid_url)

    def test_none_url(self):
        """Test that None URL passes validation."""
        assert validate_database_url(None) is None

    def test_empty_string_url(self):
        """Test that empty string URL raises ValueError."""
        with pytest.raises(ValueError, match="must include scheme"):
            validate_database_url("")


class TestPositiveIntValidator:
    """Tests for positive integer validation."""

    @pytest.mark.parametrize("value", [1, 2, 5, 10, 50, 100, 1000, 999999])
    def test_valid_positive_integers(self, value):
        """Test that positive integers pass validation."""
        assert validate_positive_int(value) == value

    @pytest.mark.parametrize("value", [0, -1, -5, -10, -100, -999])
    def test_zero_and_negative_rejected(self, value):
        """Test that zero and negative integers are rejected."""
        with pytest.raises(ValueError, match="must be at least 1"):
            validate_positive_int(value)

    def test_boundary_condition_one(self):
        """Test boundary: value of 1 is valid."""
        assert validate_positive_int(1) == 1
