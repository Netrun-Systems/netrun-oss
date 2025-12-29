"""
Custom Pydantic types with built-in validation.

This module provides custom Pydantic types that automatically validate
values using the validators from this package.
"""

from typing import Annotated, Literal
from pydantic import BeforeValidator, Field
from pydantic_core import PydanticCustomError
from email_validator import validate_email as email_validate, EmailNotValidError

from .security import (
    validate_secret_key,
    validate_password_strength,
    validate_jwt_secret,
    validate_encryption_key,
)
from .network import (
    validate_url,
    validate_database_url,
    validate_port,
    validate_ip_address,
)
from .validators import validate_positive_int, validate_non_negative_int


# Email validation wrapper
def _validate_email(v: str) -> str:
    """Validate email address."""
    try:
        validation = email_validate(v, check_deliverability=False)
        return validation.normalized
    except EmailNotValidError as e:
        raise PydanticCustomError("email_invalid", str(e))


# URL validation wrappers
def _validate_secure_url(v: str) -> str:
    """Validate HTTPS-only URL."""
    return validate_url(v, require_https=True)


def _validate_http_url(v: str) -> str:
    """Validate HTTP/HTTPS URL."""
    return validate_url(v, allowed_schemes=["http", "https"])


# Database URL validation wrapper
def _validate_db_url(v: str) -> str:
    """Validate database URL."""
    return validate_database_url(v)


# Password validation wrapper
def _validate_strong_password(v: str) -> str:
    """Validate strong password."""
    return validate_password_strength(
        v,
        min_length=8,
        require_uppercase=True,
        require_lowercase=True,
        require_digit=True,
        require_special=False,
    )


# Secret key validation wrappers
def _validate_secret(v: str) -> str:
    """Validate secret key (32+ chars)."""
    return validate_secret_key(v, min_length=32)


def _validate_jwt(v: str) -> str:
    """Validate JWT secret."""
    return validate_jwt_secret(v)


def _validate_encryption(v: str) -> str:
    """Validate encryption key."""
    return validate_encryption_key(v)


# Port validation wrapper
def _validate_port_number(v: int) -> int:
    """Validate port number."""
    return validate_port(v)


# IP address validation wrapper
def _validate_ip(v: str) -> str:
    """Validate IP address."""
    return validate_ip_address(v)


# Positive integer wrapper
def _validate_positive(v: int) -> int:
    """Validate positive integer."""
    return validate_positive_int(v)


# Non-negative integer wrapper
def _validate_non_negative(v: int) -> int:
    """Validate non-negative integer."""
    return validate_non_negative_int(v)


# Custom Types
Email = Annotated[str, BeforeValidator(_validate_email)]
"""
Email address with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import Email
    >>> class User(BaseModel):
    ...     email: Email
    >>> user = User(email="user@example.com")
    >>> user.email
    'user@example.com'
"""

SecureURL = Annotated[str, BeforeValidator(_validate_secure_url)]
"""
HTTPS-only URL with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import SecureURL
    >>> class Config(BaseModel):
    ...     api_endpoint: SecureURL
    >>> config = Config(api_endpoint="https://api.example.com")
    >>> config.api_endpoint
    'https://api.example.com'
"""

HttpURL = Annotated[str, BeforeValidator(_validate_http_url)]
"""
HTTP/HTTPS URL with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import HttpURL
    >>> class Config(BaseModel):
    ...     website: HttpURL
    >>> config = Config(website="http://example.com")
    >>> config.website
    'http://example.com'
"""

DatabaseURL = Annotated[str, BeforeValidator(_validate_db_url)]
"""
Database connection URL with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import DatabaseURL
    >>> class Config(BaseModel):
    ...     db_url: DatabaseURL
    >>> config = Config(db_url="postgresql://user:pass@localhost:5432/db")
    >>> config.db_url
    'postgresql://user:pass@localhost:5432/db'
"""

StrongPassword = Annotated[str, BeforeValidator(_validate_strong_password)]
"""
Strong password with automatic validation (8+ chars, uppercase, lowercase, digit).

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import StrongPassword
    >>> class User(BaseModel):
    ...     password: StrongPassword
    >>> user = User(password="P@ssw0rd")
    >>> user.password
    'P@ssw0rd'
"""

SecretKey = Annotated[str, BeforeValidator(_validate_secret)]
"""
Secret key with minimum 32 character validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import SecretKey
    >>> class Config(BaseModel):
    ...     app_secret: SecretKey
    >>> config = Config(app_secret="a" * 32)
    >>> len(config.app_secret)
    32
"""

JWTSecret = Annotated[str, BeforeValidator(_validate_jwt)]
"""
JWT secret key with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import JWTSecret
    >>> class Config(BaseModel):
    ...     jwt_secret: JWTSecret
    >>> config = Config(jwt_secret="a" * 32)
    >>> len(config.jwt_secret)
    32
"""

EncryptionKey = Annotated[str, BeforeValidator(_validate_encryption)]
"""
Encryption key with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import EncryptionKey
    >>> class Config(BaseModel):
    ...     encryption_key: EncryptionKey
    >>> config = Config(encryption_key="a" * 32)
    >>> len(config.encryption_key)
    32
"""

PortNumber = Annotated[int, BeforeValidator(_validate_port_number)]
"""
Network port number (1-65535) with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import PortNumber
    >>> class Config(BaseModel):
    ...     port: PortNumber
    >>> config = Config(port=8080)
    >>> config.port
    8080
"""

IPAddress = Annotated[str, BeforeValidator(_validate_ip)]
"""
IPv4 or IPv6 address with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import IPAddress
    >>> class Config(BaseModel):
    ...     server_ip: IPAddress
    >>> config = Config(server_ip="192.168.1.1")
    >>> config.server_ip
    '192.168.1.1'
"""

PositiveInt = Annotated[int, BeforeValidator(_validate_positive)]
"""
Positive integer (>= 1) with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import PositiveInt
    >>> class Config(BaseModel):
    ...     pool_size: PositiveInt
    >>> config = Config(pool_size=10)
    >>> config.pool_size
    10
"""

NonNegativeInt = Annotated[int, BeforeValidator(_validate_non_negative)]
"""
Non-negative integer (>= 0) with validation.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import NonNegativeInt
    >>> class Config(BaseModel):
    ...     retry_count: NonNegativeInt
    >>> config = Config(retry_count=0)
    >>> config.retry_count
    0
"""

# Environment literal type
Environment = Literal["development", "staging", "production", "testing"]
"""
Environment literal type for type-safe environment values.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import Environment
    >>> class Config(BaseModel):
    ...     env: Environment
    >>> config = Config(env="production")
    >>> config.env
    'production'
"""

# Log level literal type
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
"""
Log level literal type for type-safe log level values.

Example:
    >>> from pydantic import BaseModel
    >>> from netrun.validation import LogLevel
    >>> class Config(BaseModel):
    ...     log_level: LogLevel
    >>> config = Config(log_level="INFO")
    >>> config.log_level
    'INFO'
"""
