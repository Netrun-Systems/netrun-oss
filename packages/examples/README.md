# Netrun Service Library - Examples

This directory contains working examples demonstrating how to use the Netrun Service Library packages.

## Quick Start

```bash
# Install core packages
pip install netrun-logging netrun-errors netrun-auth netrun-cors
pip install fastapi uvicorn

# Run the quick start example
uvicorn quick_start_example:app --reload
```

## Available Examples

### 1. Quick Start Example (`quick_start_example.py`)

Minimal FastAPI application demonstrating core packages:
- Structured logging with netrun-logging
- Exception handling with netrun-errors
- JWT authentication with netrun-auth
- CORS middleware with netrun-cors

```bash
uvicorn quick_start_example:app --reload
curl http://localhost:8000/health
```

### 2. Logging Example (`logging_example.py`)

Comprehensive demonstration of netrun-logging features:
- Basic structured logging
- Request context binding
- Operation timing (context manager and decorator)
- Audit logging for security events
- Async-safe logging
- Automatic sensitive data redaction

```bash
python logging_example.py
```

### 3. Authentication Example (`auth_example.py`)

Complete authentication system demonstration:
- JWT token creation and validation
- RBAC with Casbin (role-based access control)
- Password hashing with Argon2
- MFA/TOTP for two-factor authentication
- FastAPI middleware integration

```bash
# Standalone demo
python auth_example.py

# As FastAPI server
uvicorn auth_example:app --reload
```

### 4. Full Integration Example (`full_integration_example.py`)

Production-grade FastAPI application using all packages:
- Complete logging configuration
- Error handling with custom exceptions
- Configuration management
- JWT authentication with dependency injection
- CORS middleware
- Database pool (optional)
- Audit logging

```bash
uvicorn full_integration_example:app --reload
```

### 5. Testing Example (`test_example.py`)

Pytest test suite demonstrating netrun-pytest-fixtures:
- JWT token fixtures
- Mock Redis client
- Async database sessions
- HTTP client mocking
- Environment isolation
- Log capture

```bash
pytest test_example.py -v
```

## Package Requirements

Each example lists its specific requirements. Here's the full installation for all examples:

```bash
# All packages
pip install netrun-auth[all] netrun-logging netrun-config[all] netrun-errors[logging]
pip install netrun-cors netrun-db-pool netrun-llm[all] netrun-env[logging]
pip install netrun-pytest-fixtures[all] netrun-ratelimit

# FastAPI and testing
pip install fastapi uvicorn httpx pytest pytest-asyncio
```

## Testing the Examples

```bash
# Run all tests
pytest test_example.py -v

# Run specific test class
pytest test_example.py::TestJWTFixtures -v

# Run with coverage
pytest test_example.py -v --cov=.
```

## API Endpoints (Quick Start)

After running `uvicorn quick_start_example:app --reload`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/login` | POST | Authenticate and get JWT |
| `/protected` | GET | Protected endpoint example |

### Example Requests

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"password"}'

# Access protected endpoint (with token)
curl http://localhost:8000/protected \
  -H "Authorization: Bearer <token>"
```

## Documentation

- [Technical Reference](../../docs/NETRUN_SERVICE_LIBRARY_TECHNICAL_REFERENCE.md)
- [PyPI Packages](https://pypi.org/search/?q=netrun-)
- [GitHub Repository](https://github.com/netrun-systems/netrun-service-library)

## Support

Questions? Open an issue on GitHub or contact sales@netrunsystems.com.
