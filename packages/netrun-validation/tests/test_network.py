"""Tests for network validators."""

import pytest
from netrun.validation.network import (
    validate_url,
    validate_database_url,
    validate_redis_url,
    validate_ip_address,
    validate_port,
    validate_cors_origins,
    validate_hostname,
)


class TestValidateURL:
    """Tests for validate_url."""

    def test_valid_http_url(self):
        """Test validation with valid HTTP URL."""
        url = "http://example.com"
        assert validate_url(url) == url

    def test_valid_https_url(self):
        """Test validation with valid HTTPS URL."""
        url = "https://example.com"
        assert validate_url(url) == url

    def test_url_with_path(self):
        """Test validation with URL containing path."""
        url = "https://example.com/api/v1"
        assert validate_url(url) == url

    def test_url_with_port(self):
        """Test validation with URL containing port."""
        url = "https://example.com:8080"
        assert validate_url(url) == url

    def test_require_https(self):
        """Test validation requiring HTTPS."""
        assert validate_url("https://example.com", require_https=True) == "https://example.com"

    def test_http_with_require_https(self):
        """Test HTTP URL when HTTPS is required."""
        with pytest.raises(ValueError, match="URL must use HTTPS scheme"):
            validate_url("http://example.com", require_https=True)

    def test_allowed_schemes(self):
        """Test validation with allowed schemes."""
        assert validate_url("ftp://example.com", allowed_schemes=["ftp"]) == "ftp://example.com"

    def test_invalid_scheme(self):
        """Test validation with invalid scheme."""
        with pytest.raises(ValueError, match="URL scheme must be one of"):
            validate_url("ftp://example.com", allowed_schemes=["http", "https"])

    def test_missing_scheme(self):
        """Test validation with missing scheme."""
        with pytest.raises(ValueError, match="URL must include a scheme"):
            validate_url("example.com")

    def test_empty_url(self):
        """Test validation with empty URL."""
        with pytest.raises(ValueError, match="URL is required"):
            validate_url("")


class TestValidateDatabaseURL:
    """Tests for validate_database_url."""

    def test_postgresql_url(self):
        """Test validation with PostgreSQL URL."""
        url = "postgresql://user:pass@localhost:5432/db"
        assert validate_database_url(url) == url

    def test_postgresql_asyncpg(self):
        """Test validation with PostgreSQL+asyncpg URL."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/db"
        assert validate_database_url(url) == url

    def test_mysql_url(self):
        """Test validation with MySQL URL."""
        url = "mysql://user:pass@localhost:3306/db"
        assert validate_database_url(url) == url

    def test_sqlite_url(self):
        """Test validation with SQLite URL."""
        url = "sqlite:///path/to/db.sqlite"
        assert validate_database_url(url) == url

    def test_invalid_scheme(self):
        """Test validation with invalid scheme."""
        with pytest.raises(ValueError, match="Database URL scheme must be one of"):
            validate_database_url("invalid://user:pass@localhost/db")

    def test_empty_url(self):
        """Test validation with empty URL."""
        with pytest.raises(ValueError, match="Database URL is required"):
            validate_database_url("")


class TestValidateRedisURL:
    """Tests for validate_redis_url."""

    def test_redis_url(self):
        """Test validation with Redis URL."""
        url = "redis://localhost:6379/0"
        assert validate_redis_url(url) == url

    def test_rediss_url(self):
        """Test validation with Redis SSL URL."""
        url = "rediss://localhost:6380/1"
        assert validate_redis_url(url) == url

    def test_invalid_scheme(self):
        """Test validation with invalid scheme."""
        with pytest.raises(ValueError, match="URL scheme must be one of"):
            validate_redis_url("http://localhost:6379")


class TestValidateIPAddress:
    """Tests for validate_ip_address."""

    def test_valid_ipv4(self):
        """Test validation with valid IPv4."""
        assert validate_ip_address("192.168.1.1") == "192.168.1.1"

    def test_valid_ipv4_localhost(self):
        """Test validation with localhost IPv4."""
        assert validate_ip_address("127.0.0.1") == "127.0.0.1"

    def test_valid_ipv4_zero(self):
        """Test validation with 0.0.0.0."""
        assert validate_ip_address("0.0.0.0") == "0.0.0.0"

    def test_valid_ipv6_localhost(self):
        """Test validation with IPv6 localhost."""
        assert validate_ip_address("::1") == "::1"

    def test_invalid_ip(self):
        """Test validation with invalid IP."""
        with pytest.raises(ValueError, match="Invalid IP address format"):
            validate_ip_address("invalid")

    def test_invalid_ipv4(self):
        """Test validation with invalid IPv4."""
        with pytest.raises(ValueError, match="Invalid IP address format"):
            validate_ip_address("256.256.256.256")

    def test_empty_ip(self):
        """Test validation with empty IP."""
        with pytest.raises(ValueError, match="IP address is required"):
            validate_ip_address("")


class TestValidatePort:
    """Tests for validate_port."""

    def test_valid_port(self):
        """Test validation with valid port."""
        assert validate_port(8080) == 8080

    def test_port_80(self):
        """Test validation with port 80."""
        assert validate_port(80) == 80

    def test_port_443(self):
        """Test validation with port 443."""
        assert validate_port(443) == 443

    def test_max_port(self):
        """Test validation with maximum port."""
        assert validate_port(65535) == 65535

    def test_min_port(self):
        """Test validation with minimum port."""
        assert validate_port(1) == 1

    def test_port_zero(self):
        """Test validation with port 0."""
        with pytest.raises(ValueError, match="port must be at least 1"):
            validate_port(0)

    def test_port_too_high(self):
        """Test validation with port too high."""
        with pytest.raises(ValueError, match="port must be at most 65535"):
            validate_port(70000)

    def test_custom_range(self):
        """Test validation with custom port range."""
        assert validate_port(8080, min_port=8000, max_port=9000) == 8080


class TestValidateCORSOrigins:
    """Tests for validate_cors_origins."""

    def test_csv_string(self):
        """Test validation with CSV string."""
        origins = validate_cors_origins("http://localhost:3000,https://example.com")
        assert origins == ["http://localhost:3000", "https://example.com"]

    def test_list_input(self):
        """Test validation with list input."""
        origins = validate_cors_origins(["http://localhost:3000"])
        assert origins == ["http://localhost:3000"]

    def test_wildcard(self):
        """Test validation with wildcard."""
        origins = validate_cors_origins("*")
        assert origins == ["*"]

    def test_wildcard_in_list(self):
        """Test validation with wildcard in list."""
        origins = validate_cors_origins(["*"])
        assert origins == ["*"]


class TestValidateHostname:
    """Tests for validate_hostname."""

    def test_localhost(self):
        """Test validation with localhost."""
        assert validate_hostname("localhost") == "localhost"

    def test_domain(self):
        """Test validation with domain."""
        assert validate_hostname("example.com") == "example.com"

    def test_subdomain(self):
        """Test validation with subdomain."""
        assert validate_hostname("sub.example.com") == "sub.example.com"

    def test_hyphenated(self):
        """Test validation with hyphenated hostname."""
        assert validate_hostname("my-server") == "my-server"

    def test_invalid_hostname(self):
        """Test validation with invalid hostname."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("invalid_hostname")

    def test_empty_hostname(self):
        """Test validation with empty hostname."""
        with pytest.raises(ValueError, match="Hostname is required"):
            validate_hostname("")
