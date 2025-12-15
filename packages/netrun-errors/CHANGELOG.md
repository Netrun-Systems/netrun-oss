# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-04

### Added
- Initial stable release of netrun-errors
- Unified error response format with structured JSON output
- Automatic correlation ID generation and injection for request tracking
- Machine-readable error codes for frontend error classification
- Global exception handlers for FastAPI applications
- Error logging middleware with request/response tracking
- Support for authentication errors (401 Unauthorized)
- Support for authorization errors (403 Forbidden)
- Support for resource errors (404 Not Found, 409 Conflict)
- Support for service errors (503 Service Unavailable)
- Custom details support for context-specific error information
- Correlation ID tracking across requests and logs
- Performance tracking with request duration measurement
- Full type safety with mypy strict mode support
- Comprehensive test coverage (90%+)
- Support for Python 3.11 and 3.12

### Exception Types

#### Authentication (401 Unauthorized)
- `InvalidCredentialsError`: Invalid email/password combination
- `TokenExpiredError`: Authentication token has expired
- `TokenInvalidError`: Malformed or invalid token
- `TokenRevokedError`: Token has been explicitly revoked
- `AuthenticationRequiredError`: Endpoint requires authentication

#### Authorization (403 Forbidden)
- `InsufficientPermissionsError`: User lacks required permissions
- `TenantAccessDeniedError`: Cross-tenant access attempt

#### Resource (404 Not Found, 409 Conflict)
- `ResourceNotFoundError`: Requested resource does not exist
- `ResourceConflictError`: Operation conflicts with existing state

#### Service (503 Service Unavailable)
- `ServiceUnavailableError`: Service or dependency unavailable
- `TemporalUnavailableError`: Workflow engine unavailable

### Features
- **Structured Error Responses**: Consistent JSON format across all services with code, message, details, correlation_id, timestamp, path
- **Automatic Correlation IDs**: Unique identifiers for request tracking and distributed tracing
- **Machine-Readable Error Codes**: Frontend-friendly error classification (e.g., AUTH_INVALID_CREDENTIALS)
- **Global Exception Handlers**: NetrunException, RequestValidationError, HTTPException, and unhandled exceptions
- **Request/Response Logging**: Structured logs with correlation IDs, duration tracking, and performance metrics
- **Type Safety**: Full typing support with mypy strict mode

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { "additional": "context" },
    "correlation_id": "req-20251125-143210-a8f3c9",
    "timestamp": "2025-11-25T14:32:10.523Z",
    "path": "/api/v1/endpoint"
  }
}
```

### Dependencies
- fastapi >= 0.115.0
- starlette >= 0.41.0

### Optional Dependencies
- pytest >= 8.3.0, pytest-cov >= 6.0.0, pytest-asyncio >= 0.24.0 (testing)
- httpx >= 0.27.0 (HTTP client for testing)
- black >= 24.8.0 (code formatting)
- ruff >= 0.7.0 (linting)
- mypy >= 1.13.0 (type checking)

### Integration Functions
- `install_exception_handlers(app)`: Register all exception handlers
- `install_error_logging_middleware(app)`: Add error logging middleware
- Available in `request.state.correlation_id` for middleware access

---

## Release Notes

### What's Included

This initial release provides unified error handling for Netrun Systems FastAPI applications. It standardizes error responses, enables request correlation for distributed tracing, and provides comprehensive request/response logging with performance metrics.

### Key Benefits

- **Standardized Responses**: Consistent JSON format enables predictable client-side error handling
- **Request Correlation**: Unique correlation IDs track requests across distributed systems
- **Security**: Prevents information leakage while providing helpful error messages
- **Performance Tracking**: Built-in request duration measurement for monitoring
- **Developer Friendly**: Comprehensive error types for common scenarios

### Compatibility

- Python: 3.11, 3.12
- FastAPI: 0.115+
- Starlette: 0.41+

### Installation

```bash
pip install netrun-errors
pip install netrun-errors[dev]  # With development dependencies
```

### Quick Start

```python
from fastapi import FastAPI
from netrun_errors import (
    install_exception_handlers,
    install_error_logging_middleware,
    ResourceNotFoundError
)

app = FastAPI()
install_exception_handlers(app)
install_error_logging_middleware(app)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    if user_id == "999":
        raise ResourceNotFoundError(
            resource_type="User",
            resource_id=user_id
        )
    return {"user_id": user_id}
```

### Error Handling

- All exceptions include automatic correlation IDs
- Request state contains `correlation_id` for logging
- HTTP headers include `X-Correlation-ID` for distributed tracing
- Full traceback logging for debugging

### Support

- Documentation: https://github.com/netrun-systems/netrun-errors
- GitHub: https://github.com/netrun-systems/netrun-errors
- Issues: https://github.com/netrun-systems/netrun-errors/issues
- Email: dev@netrunsystems.com
- Website: https://www.netrunsystems.com

---

**[1.0.0] - 2025-12-04**
