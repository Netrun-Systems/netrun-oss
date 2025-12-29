"""Tests for custom Pydantic types."""

import pytest
from pydantic import BaseModel, ValidationError
from netrun.validation import (
    Email,
    SecureURL,
    HttpURL,
    DatabaseURL,
    StrongPassword,
    SecretKey,
    JWTSecret,
    EncryptionKey,
    PortNumber,
    IPAddress,
    PositiveInt,
    NonNegativeInt,
    Environment,
    LogLevel,
)


class TestEmail:
    """Tests for Email custom type."""

    def test_valid_email(self):
        """Test validation with valid email."""
        class User(BaseModel):
            email: Email

        user = User(email="user@example.com")
        assert user.email == "user@example.com"

    def test_normalized_email(self):
        """Test email normalization."""
        class User(BaseModel):
            email: Email

        user = User(email="USER@EXAMPLE.COM")
        # email-validator normalizes the domain to lowercase
        assert "@example.com" in user.email.lower()

    def test_invalid_email(self):
        """Test validation with invalid email."""
        class User(BaseModel):
            email: Email

        with pytest.raises(ValidationError):
            User(email="invalid-email")


class TestSecureURL:
    """Tests for SecureURL custom type."""

    def test_valid_https_url(self):
        """Test validation with valid HTTPS URL."""
        class Config(BaseModel):
            api_endpoint: SecureURL

        config = Config(api_endpoint="https://api.example.com")
        assert config.api_endpoint == "https://api.example.com"

    def test_http_url_rejected(self):
        """Test that HTTP URL is rejected."""
        class Config(BaseModel):
            api_endpoint: SecureURL

        with pytest.raises(ValidationError, match="URL must use HTTPS scheme"):
            Config(api_endpoint="http://api.example.com")


class TestHttpURL:
    """Tests for HttpURL custom type."""

    def test_valid_http_url(self):
        """Test validation with valid HTTP URL."""
        class Config(BaseModel):
            website: HttpURL

        config = Config(website="http://example.com")
        assert config.website == "http://example.com"

    def test_valid_https_url(self):
        """Test validation with valid HTTPS URL."""
        class Config(BaseModel):
            website: HttpURL

        config = Config(website="https://example.com")
        assert config.website == "https://example.com"


class TestDatabaseURL:
    """Tests for DatabaseURL custom type."""

    def test_valid_postgresql_url(self):
        """Test validation with valid PostgreSQL URL."""
        class Config(BaseModel):
            db_url: DatabaseURL

        config = Config(db_url="postgresql://user:pass@localhost:5432/db")
        assert config.db_url == "postgresql://user:pass@localhost:5432/db"

    def test_valid_mysql_url(self):
        """Test validation with valid MySQL URL."""
        class Config(BaseModel):
            db_url: DatabaseURL

        config = Config(db_url="mysql://user:pass@localhost:3306/db")
        assert config.db_url == "mysql://user:pass@localhost:3306/db"


class TestStrongPassword:
    """Tests for StrongPassword custom type."""

    def test_valid_password(self):
        """Test validation with valid password."""
        class User(BaseModel):
            password: StrongPassword

        user = User(password="P@ssw0rd123")
        assert user.password == "P@ssw0rd123"

    def test_weak_password(self):
        """Test validation with weak password."""
        class User(BaseModel):
            password: StrongPassword

        with pytest.raises(ValidationError):
            User(password="weak")


class TestSecretKey:
    """Tests for SecretKey custom type."""

    def test_valid_secret(self):
        """Test validation with valid secret."""
        class Config(BaseModel):
            app_secret: SecretKey

        secret = "a" * 32
        config = Config(app_secret=secret)
        assert config.app_secret == secret

    def test_short_secret(self):
        """Test validation with short secret."""
        class Config(BaseModel):
            app_secret: SecretKey

        with pytest.raises(ValidationError):
            Config(app_secret="short")


class TestJWTSecret:
    """Tests for JWTSecret custom type."""

    def test_valid_jwt_secret(self):
        """Test validation with valid JWT secret."""
        class Config(BaseModel):
            jwt_secret: JWTSecret

        secret = "a" * 32
        config = Config(jwt_secret=secret)
        assert config.jwt_secret == secret

    def test_short_jwt_secret(self):
        """Test validation with short JWT secret."""
        class Config(BaseModel):
            jwt_secret: JWTSecret

        with pytest.raises(ValidationError):
            Config(jwt_secret="short")


class TestEncryptionKey:
    """Tests for EncryptionKey custom type."""

    def test_valid_encryption_key(self):
        """Test validation with valid encryption key."""
        class Config(BaseModel):
            encryption_key: EncryptionKey

        key = "a" * 32
        config = Config(encryption_key=key)
        assert config.encryption_key == key

    def test_short_encryption_key(self):
        """Test validation with short encryption key."""
        class Config(BaseModel):
            encryption_key: EncryptionKey

        with pytest.raises(ValidationError):
            Config(encryption_key="short")


class TestPortNumber:
    """Tests for PortNumber custom type."""

    def test_valid_port(self):
        """Test validation with valid port."""
        class Config(BaseModel):
            port: PortNumber

        config = Config(port=8080)
        assert config.port == 8080

    def test_invalid_port(self):
        """Test validation with invalid port."""
        class Config(BaseModel):
            port: PortNumber

        with pytest.raises(ValidationError):
            Config(port=70000)


class TestIPAddress:
    """Tests for IPAddress custom type."""

    def test_valid_ipv4(self):
        """Test validation with valid IPv4."""
        class Config(BaseModel):
            server_ip: IPAddress

        config = Config(server_ip="192.168.1.1")
        assert config.server_ip == "192.168.1.1"

    def test_invalid_ip(self):
        """Test validation with invalid IP."""
        class Config(BaseModel):
            server_ip: IPAddress

        with pytest.raises(ValidationError):
            Config(server_ip="invalid")


class TestPositiveInt:
    """Tests for PositiveInt custom type."""

    def test_valid_positive_int(self):
        """Test validation with valid positive integer."""
        class Config(BaseModel):
            pool_size: PositiveInt

        config = Config(pool_size=10)
        assert config.pool_size == 10

    def test_zero(self):
        """Test validation with zero."""
        class Config(BaseModel):
            pool_size: PositiveInt

        with pytest.raises(ValidationError):
            Config(pool_size=0)

    def test_negative(self):
        """Test validation with negative value."""
        class Config(BaseModel):
            pool_size: PositiveInt

        with pytest.raises(ValidationError):
            Config(pool_size=-1)


class TestNonNegativeInt:
    """Tests for NonNegativeInt custom type."""

    def test_valid_non_negative_int(self):
        """Test validation with valid non-negative integer."""
        class Config(BaseModel):
            retry_count: NonNegativeInt

        config = Config(retry_count=5)
        assert config.retry_count == 5

    def test_zero(self):
        """Test validation with zero."""
        class Config(BaseModel):
            retry_count: NonNegativeInt

        config = Config(retry_count=0)
        assert config.retry_count == 0

    def test_negative(self):
        """Test validation with negative value."""
        class Config(BaseModel):
            retry_count: NonNegativeInt

        with pytest.raises(ValidationError):
            Config(retry_count=-1)


class TestEnvironment:
    """Tests for Environment literal type."""

    def test_valid_environments(self):
        """Test validation with valid environments."""
        class Config(BaseModel):
            env: Environment

        for env in ["development", "staging", "production", "testing"]:
            config = Config(env=env)  # type: ignore
            assert config.env == env

    def test_invalid_environment(self):
        """Test validation with invalid environment."""
        class Config(BaseModel):
            env: Environment

        with pytest.raises(ValidationError):
            Config(env="invalid")  # type: ignore


class TestLogLevel:
    """Tests for LogLevel literal type."""

    def test_valid_log_levels(self):
        """Test validation with valid log levels."""
        class Config(BaseModel):
            log_level: LogLevel

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = Config(log_level=level)  # type: ignore
            assert config.log_level == level

    def test_invalid_log_level(self):
        """Test validation with invalid log level."""
        class Config(BaseModel):
            log_level: LogLevel

        with pytest.raises(ValidationError):
            Config(log_level="INVALID")  # type: ignore


class TestIntegration:
    """Integration tests combining multiple custom types."""

    def test_complex_config(self):
        """Test validation with complex configuration."""
        class AppConfig(BaseModel):
            env: Environment
            log_level: LogLevel
            database_url: DatabaseURL
            api_endpoint: SecureURL
            admin_email: Email
            jwt_secret: JWTSecret
            port: PortNumber
            pool_size: PositiveInt

        config = AppConfig(
            env="production",
            log_level="INFO",
            database_url="postgresql://user:pass@localhost:5432/db",
            api_endpoint="https://api.example.com",
            admin_email="admin@example.com",
            jwt_secret="a" * 32,
            port=8080,
            pool_size=10,
        )

        assert config.env == "production"
        assert config.log_level == "INFO"
        assert config.port == 8080
        assert config.pool_size == 10
