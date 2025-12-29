"""
Netrun Validation - Comprehensive Pydantic validators and custom types.

This package provides reusable validators and custom Pydantic types for
Netrun Systems portfolio applications.

Example:
    >>> from netrun.validation import Email, SecureURL, validate_environment
    >>> from pydantic import BaseModel, field_validator
    >>>
    >>> class Settings(BaseModel):
    ...     environment: str
    ...     api_endpoint: SecureURL
    ...     admin_email: Email
    ...
    ...     @field_validator("environment")
    ...     @classmethod
    ...     def check_environment(cls, v):
    ...         return validate_environment(v)
"""

__version__ = "1.0.0"

# Generic validators
from .validators import (
    validate_enum_value,
    validate_range,
    validate_non_empty,
    validate_list_from_csv,
    validate_positive_int,
    validate_non_negative_int,
    validate_percentage,
)

# Environment validators
from .environment import (
    validate_environment,
    validate_log_level,
    validate_provider,
    validate_llm_provider,
    validate_voice_provider,
    validate_database_provider,
    validate_cloud_provider,
)

# Security validators
from .security import (
    calculate_entropy,
    validate_secret_key,
    validate_password_strength,
    validate_api_key_format,
    validate_jwt_secret,
    validate_encryption_key,
)

# Network validators
from .network import (
    validate_url,
    validate_database_url,
    validate_redis_url,
    validate_ip_address,
    validate_port,
    validate_cors_origins,
    validate_hostname,
)

# DateTime validators
from .datetime_utils import (
    validate_iso_timestamp,
    validate_timezone,
    validate_date_range,
    validate_future_date,
    validate_past_date,
    validate_date_not_before,
    validate_unix_timestamp,
)

# Custom Pydantic types
from .custom_types import (
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

# Decorators
from .decorators import (
    validate_input,
    sanitize_output,
    validate_non_null,
    validate_type,
    validate_range_decorator,
)

__all__ = [
    # Version
    "__version__",
    # Generic validators
    "validate_enum_value",
    "validate_range",
    "validate_non_empty",
    "validate_list_from_csv",
    "validate_positive_int",
    "validate_non_negative_int",
    "validate_percentage",
    # Environment validators
    "validate_environment",
    "validate_log_level",
    "validate_provider",
    "validate_llm_provider",
    "validate_voice_provider",
    "validate_database_provider",
    "validate_cloud_provider",
    # Security validators
    "calculate_entropy",
    "validate_secret_key",
    "validate_password_strength",
    "validate_api_key_format",
    "validate_jwt_secret",
    "validate_encryption_key",
    # Network validators
    "validate_url",
    "validate_database_url",
    "validate_redis_url",
    "validate_ip_address",
    "validate_port",
    "validate_cors_origins",
    "validate_hostname",
    # DateTime validators
    "validate_iso_timestamp",
    "validate_timezone",
    "validate_date_range",
    "validate_future_date",
    "validate_past_date",
    "validate_date_not_before",
    "validate_unix_timestamp",
    # Custom types
    "Email",
    "SecureURL",
    "HttpURL",
    "DatabaseURL",
    "StrongPassword",
    "SecretKey",
    "JWTSecret",
    "EncryptionKey",
    "PortNumber",
    "IPAddress",
    "PositiveInt",
    "NonNegativeInt",
    "Environment",
    "LogLevel",
    # Decorators
    "validate_input",
    "sanitize_output",
    "validate_non_null",
    "validate_type",
    "validate_range_decorator",
]
