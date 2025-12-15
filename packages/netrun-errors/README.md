# netrun-errors

Unified error handling for Netrun Systems FastAPI applications.

## Features

- **Structured Error Responses**: Consistent JSON error format across all services
- **Automatic Correlation IDs**: Request tracking with unique identifiers
- **Machine-Readable Error Codes**: Frontend-friendly error classification
- **Global Exception Handlers**: FastAPI integration with comprehensive error handling
- **Request/Response Logging**: Middleware with performance tracking
- **Type Safety**: Full typing support with mypy strict mode
- **Comprehensive Testing**: 90%+ test coverage

## Installation

```bash
pip install netrun-errors
```

## Quick Start

```python
from fastapi import FastAPI
from netrun_errors import (
    install_exception_handlers,
    install_error_logging_middleware,
    InvalidCredentialsError,
    ResourceNotFoundError,
)

# Create FastAPI app
app = FastAPI()

# Install error handlers and middleware
install_exception_handlers(app)
install_error_logging_middleware(app)

# Use exceptions in your routes
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    if user_id == "999":
        raise ResourceNotFoundError(
            resource_type="User",
            resource_id=user_id
        )
    return {"user_id": user_id}

@app.post("/auth/login")
async def login(email: str, password: str):
    if not validate_credentials(email, password):
        raise InvalidCredentialsError()
    return {"token": "..."}
```

## Error Response Format

All errors return structured JSON responses:

```json
{
    "error": {
        "code": "AUTH_INVALID_CREDENTIALS",
        "message": "Invalid email or password",
        "details": {},
        "correlation_id": "req-20251125-143210-a8f3c9",
        "timestamp": "2025-11-25T14:32:10.523Z",
        "path": "/api/v1/auth/login"
    }
}
```

## Available Exceptions

### Authentication (401 Unauthorized)

- **InvalidCredentialsError**: Invalid email/password combination
- **TokenExpiredError**: Authentication token has expired
- **TokenInvalidError**: Malformed or invalid token
- **TokenRevokedError**: Token has been explicitly revoked
- **AuthenticationRequiredError**: Endpoint requires authentication

```python
from netrun_errors import InvalidCredentialsError, TokenExpiredError

# Example usage
raise InvalidCredentialsError()
raise TokenExpiredError(message="Your session has expired")
```

### Authorization (403 Forbidden)

- **InsufficientPermissionsError**: User lacks required permissions
- **TenantAccessDeniedError**: Cross-tenant access attempt

```python
from netrun_errors import InsufficientPermissionsError, TenantAccessDeniedError

# Example usage
raise InsufficientPermissionsError(
    message="You need admin role to perform this action",
    details={"required_role": "admin", "user_role": "member"}
)

raise TenantAccessDeniedError(
    details={"user_tenant_id": "123", "resource_tenant_id": "456"}
)
```

### Resource (404 Not Found, 409 Conflict)

- **ResourceNotFoundError**: Requested resource does not exist
- **ResourceConflictError**: Operation conflicts with existing state

```python
from netrun_errors import ResourceNotFoundError, ResourceConflictError

# Example usage
raise ResourceNotFoundError(
    resource_type="Product",
    resource_id="SKU-12345"
)

raise ResourceConflictError(
    message="Email address already registered",
    details={"email": "user@example.com"}
)
```

### Service (503 Service Unavailable)

- **ServiceUnavailableError**: Service or dependency unavailable
- **TemporalUnavailableError**: Workflow engine unavailable

```python
from netrun_errors import ServiceUnavailableError, TemporalUnavailableError

# Example usage
raise ServiceUnavailableError(
    message="Database connection failed",
    details={"retry_after": 30}
)

raise TemporalUnavailableError(
    message="Unable to start workflow",
    details={"workflow_id": "user-onboarding-123"}
)
```

## Correlation IDs

Every exception automatically generates a unique correlation ID for request tracking:

```python
from netrun_errors import ResourceNotFoundError

try:
    raise ResourceNotFoundError(resource_type="User", resource_id="123")
except ResourceNotFoundError as exc:
    print(exc.correlation_id)  # req-20251125-143210-a8f3c9
```

Correlation IDs are also:
- Injected into response headers as `X-Correlation-ID`
- Available in request state for logging: `request.state.correlation_id`
- Included in all log messages for distributed tracing

## Custom Details

Add context-specific information to error responses:

```python
from netrun_errors import InvalidCredentialsError

raise InvalidCredentialsError(
    message="Invalid credentials",
    details={
        "attempt_number": 3,
        "max_attempts": 5,
        "lockout_duration": 300,
    }
)
```

## Global Exception Handlers

The `install_exception_handlers()` function registers handlers for:

- **NetrunException**: All custom Netrun exceptions
- **RequestValidationError**: FastAPI validation errors
- **HTTPException**: Generic HTTP exceptions
- **Exception**: Unhandled exceptions (500 errors)

All handlers return consistent JSON format with correlation IDs.

## Error Logging Middleware

The `install_error_logging_middleware()` function provides:

- **Request/response logging**: Structured logs with correlation IDs
- **Performance tracking**: Duration measurement for all requests
- **Automatic correlation ID injection**: Available in `request.state.correlation_id`
- **Exception logging**: Full traceback logging for errors

```python
from fastapi import FastAPI, Request
from netrun_errors import install_error_logging_middleware
import logging

app = FastAPI()
install_error_logging_middleware(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@app.get("/example")
async def example(request: Request):
    # Access correlation ID
    correlation_id = request.state.correlation_id
    logger.info(f"Processing request: {correlation_id}")
    return {"status": "ok"}
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/netrun-systems/netrun-errors.git
cd netrun-errors

# Install development dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests with coverage
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_exceptions.py

# Generate HTML coverage report
pytest --cov-report=html
```

### Code Quality

```bash
# Format code with black
black netrun_errors tests

# Lint with ruff
ruff check netrun_errors tests

# Type check with mypy
mypy netrun_errors
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please submit pull requests to the main repository.

## Support

For issues, questions, or feature requests, please contact:
- **Email**: dev@netrunsystems.com
- **Website**: https://www.netrunsystems.com

---

**Version**: 1.0.0
**Author**: Netrun Systems
**Python**: 3.11+
**Framework**: FastAPI 0.115+
