# netrun-validation

Comprehensive Pydantic validators and custom types for Netrun Systems portfolio applications.

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic](https://img.shields.io/badge/pydantic-2.0+-green.svg)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Features

- **Generic Validators**: Reusable validators for common patterns (enum values, ranges, non-empty strings, etc.)
- **Environment Validators**: Validate environment names, log levels, and provider selections
- **Security Validators**: Password strength, secret keys, API keys, JWT tokens with entropy calculation
- **Network Validators**: URLs, database URLs, IP addresses, ports, CORS origins
- **DateTime Validators**: ISO timestamps, timezones, date ranges, future/past dates
- **Custom Pydantic Types**: Auto-validated types for Email, URLs, Passwords, Secrets, and more
- **Decorators**: Function input/output validation and sanitization

## Installation

```bash
pip install netrun-validation
```

## Quick Start

### Using Custom Types (Auto-Validated)

```python
from pydantic import BaseModel
from netrun.validation import Email, SecureURL, StrongPassword, PortNumber

class User(BaseModel):
    email: Email
    website: SecureURL
    password: StrongPassword

class ServerConfig(BaseModel):
    port: PortNumber
    allowed_origins: list[str]

# Auto-validation on instantiation
user = User(
    email="user@example.com",
    website="https://example.com",  # Must be HTTPS
    password="P@ssw0rd123"  # Must meet strength requirements
)

config = ServerConfig(
    port=8080,  # Must be 1-65535
    allowed_origins=["https://app.example.com"]
)
```

### Using Validators with Field Validators

```python
from pydantic import BaseModel, field_validator
from netrun.validation import validate_environment, validate_database_url

class Settings(BaseModel):
    environment: str
    database_url: str

    @field_validator("environment")
    @classmethod
    def check_environment(cls, v):
        return validate_environment(v)

    @field_validator("database_url")
    @classmethod
    def check_database_url(cls, v):
        return validate_database_url(v)

# Valid instantiation
settings = Settings(
    environment="production",  # Validates against allowed environments
    database_url="postgresql://user:pass@localhost:5432/db"
)
```

## Custom Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `Email` | Valid email address | `user@example.com` |
| `SecureURL` | HTTPS-only URL | `https://api.example.com` |
| `HttpURL` | HTTP/HTTPS URL | `http://example.com` |
| `DatabaseURL` | Database connection URL | `postgresql://...` |
| `StrongPassword` | 8+ chars, upper, lower, digit | `P@ssw0rd123` |
| `SecretKey` | 32+ character secret | `abcdef...` (32+ chars) |
| `JWTSecret` | JWT secret key (32+ chars) | `abcdef...` (32+ chars) |
| `EncryptionKey` | Encryption key (32+ chars) | `abcdef...` (32+ chars) |
| `PortNumber` | Network port (1-65535) | `8080` |
| `IPAddress` | IPv4/IPv6 address | `192.168.1.1` |
| `PositiveInt` | Integer >= 1 | `10` |
| `NonNegativeInt` | Integer >= 0 | `0` |
| `Environment` | Literal environment type | `"production"` |
| `LogLevel` | Literal log level type | `"INFO"` |

## Validators Reference

### Generic Validators

```python
from netrun.validation import (
    validate_enum_value,
    validate_range,
    validate_non_empty,
    validate_list_from_csv,
    validate_positive_int,
    validate_percentage,
)

# Enum validation
env = validate_enum_value("production", ["dev", "staging", "production"], "environment")

# Range validation
temperature = validate_range(0.7, 0.0, 2.0, "temperature")

# Non-empty string
name = validate_non_empty("John Doe", "name")

# CSV to list
origins = validate_list_from_csv("http://localhost:3000,https://example.com")
# Returns: ['http://localhost:3000', 'https://example.com']

# Positive integer
pool_size = validate_positive_int(10, "pool_size")

# Percentage
completion = validate_percentage(75.5, "completion")
```

### Environment Validators

```python
from netrun.validation import (
    validate_environment,
    validate_log_level,
    validate_llm_provider,
    validate_voice_provider,
)

env = validate_environment("production")  # Validates against standard environments
log_level = validate_log_level("INFO")  # Validates against Python log levels
llm = validate_llm_provider("openai")  # Validates LLM provider
voice = validate_voice_provider("azure")  # Validates voice provider
```

### Security Validators

```python
from netrun.validation import (
    validate_secret_key,
    validate_password_strength,
    validate_api_key_format,
    calculate_entropy,
)

# Secret key (32+ characters)
secret = validate_secret_key("a" * 32)

# Password strength
password = validate_password_strength(
    "P@ssw0rd123",
    min_length=8,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=False,
)

# API key format
api_key = validate_api_key_format("sk-" + "a" * 20, prefix="sk-", min_length=20)

# Calculate password entropy
entropy = calculate_entropy("P@ssw0rd123")  # Returns float (bits per character)
```

### Network Validators

```python
from netrun.validation import (
    validate_url,
    validate_database_url,
    validate_redis_url,
    validate_ip_address,
    validate_port,
    validate_cors_origins,
)

# URL validation
url = validate_url("https://api.example.com", require_https=True)

# Database URL
db_url = validate_database_url("postgresql://user:pass@localhost:5432/db")

# Redis URL
redis_url = validate_redis_url("redis://localhost:6379/0")

# IP address
ip = validate_ip_address("192.168.1.1")

# Port number
port = validate_port(8080)

# CORS origins
origins = validate_cors_origins("http://localhost:3000,https://example.com")
# Returns: ['http://localhost:3000', 'https://example.com']
```

### DateTime Validators

```python
from datetime import datetime
from netrun.validation import (
    validate_iso_timestamp,
    validate_timezone,
    validate_date_range,
    validate_future_date,
    validate_past_date,
)

# ISO timestamp
dt = validate_iso_timestamp("2025-01-15T10:30:00Z")

# Timezone
tz = validate_timezone("America/New_York")

# Date range
dt = validate_date_range(
    datetime(2025, 1, 15),
    min_date=datetime(2025, 1, 1),
    max_date=datetime(2025, 12, 31)
)

# Future date
future = validate_future_date(datetime(2026, 1, 1))

# Past date
past = validate_past_date(datetime(2024, 1, 1))
```

## Decorators

### Function Input Validation

```python
from netrun.validation import validate_input, validate_non_empty

@validate_input(validate_non_empty)
def greet(name: str) -> str:
    return f"Hello, {name}!"

greet("Alice")  # OK
greet("")  # Raises ValueError
```

### Output Sanitization

```python
from netrun.validation import sanitize_output

@sanitize_output(["password", "secret"])
def get_user() -> dict:
    return {
        "name": "Alice",
        "password": "secret123",
        "email": "alice@example.com"
    }

result = get_user()
# Returns: {"name": "Alice", "password": "***REDACTED***", "email": "alice@example.com"}
```

### Type Validation

```python
from netrun.validation import validate_type

@validate_type(name=str, age=int)
def create_user(name: str, age: int) -> dict:
    return {"name": name, "age": age}

create_user(name="Alice", age=30)  # OK
create_user(name="Alice", age="30")  # Raises TypeError
```

## Real-World Example

```python
from pydantic import BaseModel, field_validator
from netrun.validation import (
    Email,
    SecureURL,
    DatabaseURL,
    JWTSecret,
    PortNumber,
    PositiveInt,
    Environment,
    LogLevel,
    validate_cors_origins,
)

class WilburSettings(BaseModel):
    # Application Configuration
    app_name: str = "Wilbur AI Assistant"
    app_environment: Environment = "development"
    app_port: PortNumber = 8080

    # Security
    app_secret_key: JWTSecret
    jwt_secret_key: JWTSecret

    # Database
    database_url: DatabaseURL
    database_pool_size: PositiveInt = 10

    # API Configuration
    api_endpoint: SecureURL
    admin_email: Email

    # CORS
    cors_origins: list[str]

    # Logging
    log_level: LogLevel = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors(cls, v):
        return validate_cors_origins(v)

# Usage
settings = WilburSettings(
    app_environment="production",
    app_port=8000,
    app_secret_key="a" * 32,
    jwt_secret_key="b" * 32,
    database_url="postgresql://user:pass@localhost:5432/wilbur",
    database_pool_size=20,
    api_endpoint="https://api.wilbur.ai",
    admin_email="admin@wilbur.ai",
    cors_origins="https://app.wilbur.ai,https://admin.wilbur.ai",
    log_level="INFO",
)
```

## Testing

Run tests with pytest:

```bash
cd /data/workspace/github/Netrun_Service_Library_v2/packages/netrun-validation
pytest tests/ -v --cov=netrun.validation --cov-report=term-missing
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests with coverage
pytest tests/ -v --cov=netrun.validation --cov-report=html

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Daniel Garza**
Netrun Systems
daniel@netrunsystems.com

## Links

- [Documentation](https://docs.netrunsystems.com/validation)
- [GitHub Repository](https://github.com/netrunsystems/netrun-validation)
- [Issue Tracker](https://github.com/netrunsystems/netrun-validation/issues)
