# Netrun Auth Test Suite
Service #59 Unified Authentication - Comprehensive Test Coverage

## Test Suite Overview

Total: **219 tests** across 8 test modules

### Test Breakdown by Module

| Module | Tests | Focus Area |
|--------|-------|------------|
| `test_jwt.py` | 49 | JWT token generation, validation, refresh, blacklisting |
| `test_middleware.py` | 37 | Authentication middleware, path exemption, context injection |
| `test_rbac.py` | 33 | Role-based access control, permissions, role hierarchy |
| `test_dependencies.py` | 26 | FastAPI dependencies, role/permission enforcement |
| `test_password.py` | 22 | Argon2 password hashing, verification, strength validation |
| `test_integration.py` | 21 | End-to-end flows, FastAPI integration, multi-tenant isolation |
| `test_types.py` | 18 | Pydantic models, validation, type checking |
| `test_config.py` | 13 | Configuration loading, environment variables, Key Vault |

## Running Tests

### Prerequisites

```bash
# Install development dependencies
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=netrun_auth --cov-report=html
```

### Run Specific Test Modules

```bash
# JWT tests only
pytest tests/test_jwt.py

# Middleware tests only
pytest tests/test_middleware.py

# Integration tests only
pytest tests/test_integration.py
```

### Run Tests by Category

```bash
# Unit tests only (no external dependencies)
pytest -m unit

# Integration tests only
pytest -m integration

# Fast tests only (exclude slow tests)
pytest -m "not slow"
```

## Test Structure

### Shared Fixtures (`conftest.py`)

- `rsa_key_pair`: RSA keys for JWT testing
- `mock_redis`: Mock Redis client
- `sample_claims`: Standard JWT claims
- `test_user`, `admin_user`, `superadmin_user`: User fixtures
- `mock_request`: Mock FastAPI request objects
- `test_config`: Configuration fixtures

### Test Organization

Each test module follows the pattern:

```python
class TestFeatureCategory:
    """Test specific feature category."""

    def test_specific_behavior(self, fixtures):
        """
        Test specific behavior with clear documentation.

        Expected behavior documented in docstring.
        """
        pytest.skip("Waiting for netrun_auth.module")
```

## Coverage Goals

- **Target**: 80% minimum coverage (enforced by pytest)
- **Current**: Tests ready, awaiting core implementation
- **Focus Areas**:
  - Critical paths: JWT validation, RBAC enforcement
  - Security features: Token blacklisting, password hashing
  - Error handling: All exception paths tested

## Test Execution Flow

### Current Status

All tests are currently **skipped** with `pytest.skip("Waiting for netrun_auth.module")` because the core `netrun_auth` package is being built concurrently by the backend-developer agent.

### Activation Plan

Once core modules are available:

1. **Phase 1**: Remove skips from `test_jwt.py`, `test_password.py`, `test_types.py`
2. **Phase 2**: Remove skips from `test_rbac.py`, `test_config.py`
3. **Phase 3**: Remove skips from `test_middleware.py`, `test_dependencies.py`
4. **Phase 4**: Remove skips from `test_integration.py`

### Continuous Integration

Tests are designed for CI/CD pipeline integration:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pytest --cov=netrun_auth --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Test Patterns

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function(self, mock_redis):
    """Test async functions with pytest-asyncio."""
    result = await some_async_function(mock_redis)
    assert result is not None
```

### Mock Testing

```python
def test_with_mocks(self, mock_redis, monkeypatch):
    """Test with mocked dependencies."""
    mock_redis.get.return_value = b"cached_value"
    result = function_using_redis(mock_redis)
    mock_redis.get.assert_called_once()
```

### Exception Testing

```python
def test_raises_error(self):
    """Test that specific errors are raised."""
    with pytest.raises(ValidationError):
        invalid_operation()
```

## Adding New Tests

### Test Naming Convention

- Test files: `test_<module>.py`
- Test classes: `Test<FeatureCategory>`
- Test functions: `test_<specific_behavior>`

### Test Documentation

Every test must include:

1. **Docstring**: Clear description of what is being tested
2. **Expected behavior**: Document expected outcome
3. **Edge cases**: Note any special conditions

### Example Test Template

```python
class TestNewFeature:
    """Test new feature functionality."""

    def test_normal_operation(self, fixtures):
        """
        Test that feature works under normal conditions.

        Expected: Function returns expected value without errors.
        """
        result = new_feature(input_data)
        assert result == expected_output

    def test_edge_case(self, fixtures):
        """
        Test that feature handles edge case correctly.

        Expected: Function raises SpecificError for invalid input.
        """
        with pytest.raises(SpecificError):
            new_feature(invalid_input)
```

## Test Quality Standards

### All Tests Must

- [ ] Have clear, descriptive names
- [ ] Include comprehensive docstrings
- [ ] Use appropriate fixtures
- [ ] Test one specific behavior
- [ ] Include both positive and negative cases
- [ ] Be independent (no test order dependencies)
- [ ] Clean up resources (fixtures handle this)

### Test Coverage Requirements

- **Critical paths**: 100% coverage required
  - JWT validation
  - Token blacklisting
  - Password hashing
  - RBAC enforcement

- **Standard paths**: 80% coverage minimum
  - Middleware
  - Dependencies
  - Configuration

- **Edge cases**: All error paths tested
  - Invalid inputs
  - Missing data
  - Connection failures

## Troubleshooting

### Common Issues

**Issue**: Tests fail with "module not found"
**Solution**: Install package in editable mode: `pip install -e .`

**Issue**: Async tests not running
**Solution**: Ensure `pytest-asyncio` installed and `asyncio_mode = "auto"` in pyproject.toml

**Issue**: Mock not working as expected
**Solution**: Verify mock setup in conftest.py fixtures

**Issue**: Coverage below threshold
**Solution**: Identify uncovered lines with `pytest --cov=netrun_auth --cov-report=term-missing`

## Security Testing Notes

### Password Security

- Tests verify Argon2id variant (not Argon2i or Argon2d)
- Tests verify proper salt generation
- Tests verify timing-safe comparison

### JWT Security

- Tests verify RS256 algorithm enforcement
- Tests verify token expiry validation
- Tests verify signature validation
- Tests verify blacklist enforcement

### Multi-Tenant Security

- Tests verify organization isolation
- Tests verify cross-tenant access prevention
- Tests verify superadmin bypass capabilities

## Performance Testing

### Password Hashing

Target: 0.1-0.5 seconds per hash (balance security vs UX)

### JWT Operations

- Generation: < 50ms
- Validation: < 10ms
- Blacklist check: < 5ms (Redis lookup)

## Contributing

When adding new tests:

1. Follow existing test structure and patterns
2. Add tests for both success and failure cases
3. Include edge case testing
4. Update this README if adding new test categories
5. Ensure all tests pass before committing

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pydantic Testing Best Practices](https://docs.pydantic.dev/latest/concepts/testing/)

---

**Last Updated**: 2025-11-25
**Status**: Ready for core implementation integration
**Test Count**: 219 tests across 8 modules
**Coverage Target**: 80% minimum (enforced)
