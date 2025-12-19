# Netrun Namespace Package Import Tests

Comprehensive test suite for validating the Netrun Service Library namespace package structure, ensuring proper package discovery, import mechanisms, backwards compatibility, and cross-package dependencies.

## Overview

This test suite validates that the Netrun Service Library namespace package architecture works correctly across:

- **Namespace Discovery**: Proper PEP 420 namespace package detection
- **Individual Package Imports**: Each package exports expected symbols
- **Backwards Compatibility**: Old import style (`netrun_auth`) still works
- **Cross-Package Dependencies**: Packages can import from each other
- **Type Checking**: PEP 561 compliance with `py.typed` markers
- **Python Version Compatibility**: Works on Python 3.10, 3.11, 3.12

## Quick Start

### Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Install packages you want to test (example)
pip install -e ../netrun-auth
pip install -e ../netrun-config
pip install -e ../netrun-errors
```

### Running Tests

```bash
# Run all tests
pytest test_namespace_imports.py -v

# Run specific test categories
pytest -m namespace           # Namespace-specific tests
pytest -m integration         # Integration tests
pytest -m backwards_compat    # Backwards compatibility tests
pytest -m pep561             # Type checking compliance tests

# Run with coverage
pytest --cov=. --cov-report=html

# Run in parallel (faster)
pytest -n auto

# Run specific test class
pytest test_namespace_imports.py::TestBasicNamespace -v

# Run specific test
pytest test_namespace_imports.py::TestBasicNamespace::test_netrun_namespace_exists -v
```

## Test Categories

### 1. Basic Namespace Tests (`TestBasicNamespace`)

Tests fundamental namespace package functionality:

- `test_netrun_namespace_exists`: Verify `netrun` namespace is importable
- `test_namespace_package_discovery`: Check `__path__` extension mechanism
- `test_namespace_is_not_regular_package`: Verify it's a namespace, not regular package
- `test_namespace_path_contains_packages`: Validate discovered package locations

**Run:**
```bash
pytest test_namespace_imports.py::TestBasicNamespace -v
```

### 2. Individual Package Import Tests

Parameterized tests validating each package's API:

- `test_package_imports`: Verify expected exports for each package
- `test_netrun_auth_complete_api`: Full API validation for netrun.auth
- `test_netrun_config_complete_api`: Full API validation for netrun.config
- `test_netrun_errors_complete_api`: Full API validation for netrun.errors

**Run:**
```bash
pytest -k "test_package_imports or complete_api" -v
```

### 3. Backwards Compatibility Tests (`TestBackwardsCompatibility`)

Ensures old import style still works:

- `test_deprecated_import_warning_netrun_auth`: Old imports trigger warnings
- `test_deprecated_import_still_works`: Old and new imports reference same code
- `test_old_style_netrun_config`: netrun_config compatibility
- `test_old_style_netrun_errors`: netrun_errors compatibility

**Run:**
```bash
pytest -m backwards_compat -v
```

### 4. Cross-Package Dependency Tests (`TestCrossPackageDependencies`)

Validates inter-package imports:

- `test_config_can_import_errors`: Optional dependency resolution
- `test_auth_can_import_logging`: Graceful handling of optional deps
- `test_no_circular_imports`: Circular dependency detection
- `test_auth_config_integration`: Integration patterns

**Run:**
```bash
pytest -m integration -v
```

### 5. PEP 561 Type Checking Tests (`TestPEP561Compliance`)

Validates type checker support:

- `test_netrun_auth_py_typed_marker`: Check for py.typed file
- `test_netrun_config_py_typed_marker`: Config package type support
- `test_py_typed_exists_all_packages`: Parameterized check across packages

**Run:**
```bash
pytest -m pep561 -v
```

### 6. Python Version Compatibility Tests (`TestPythonVersionCompatibility`)

Tests across Python versions:

- `test_current_python_version_imports`: Works on current version
- `test_python_310_compatibility`: Python 3.10 support
- `test_python_311_compatibility`: Python 3.11 support (with tomllib)
- `test_python_312_compatibility`: Python 3.12 support

**Run:**
```bash
pytest -m "py310 or py311 or py312" -v
```

### 7. Package Metadata Tests (`TestPackageMetadata`)

Validates version and metadata:

- `test_netrun_auth_version`: Version string validation
- `test_package_has_metadata`: __version__ and __all__ existence

**Run:**
```bash
pytest test_namespace_imports.py::TestPackageMetadata -v
```

### 8. Dynamic Import Tests (`TestDynamicImports`)

Tests runtime import mechanisms:

- `test_dynamic_subpackage_import`: importlib.import_module()
- `test_lazy_import_optional_dependencies`: Lazy loading patterns
- `test_getattr_dynamic_loading`: __getattr__ hook testing

**Run:**
```bash
pytest test_namespace_imports.py::TestDynamicImports -v
```

### 9. Error Handling Tests (`TestErrorHandling`)

Validates error scenarios:

- `test_import_nonexistent_subpackage`: Proper ImportError
- `test_import_nonexistent_symbol`: Symbol-level errors
- `test_partial_import_failure`: Mixed success/failure imports

**Run:**
```bash
pytest test_namespace_imports.py::TestErrorHandling -v
```

### 10. Namespace Discovery Tests (`TestNamespaceDiscovery`)

Low-level discovery mechanisms:

- `test_find_spec_returns_namespace`: importlib.util.find_spec()
- `test_pkgutil_iter_modules`: pkgutil module discovery
- `test_namespace_path_extension`: Path extension validation

**Run:**
```bash
pytest test_namespace_imports.py::TestNamespaceDiscovery -v
```

## Test Markers

Use markers to filter tests:

```bash
# Namespace-specific tests
pytest -m namespace

# Integration tests (require multiple packages)
pytest -m integration

# Slow tests (can be excluded for quick runs)
pytest -m "not slow"

# Backwards compatibility
pytest -m backwards_compat

# Type checking compliance
pytest -m pep561

# Cross-package dependency tests
pytest -m cross_package

# Python version-specific
pytest -m py310
pytest -m py311
pytest -m py312
```

## Coverage Reports

Generate coverage reports:

```bash
# Terminal report
pytest --cov=. --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=. --cov-report=html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows

# XML report (for CI/CD)
pytest --cov=. --cov-report=xml

# Multiple report formats
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Namespace Package Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r packages/tests/requirements-test.txt
          pip install -e packages/netrun-auth
          pip install -e packages/netrun-config
          pip install -e packages/netrun-errors

      - name: Run tests
        run: |
          cd packages/tests
          pytest -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./packages/tests/coverage.xml
```

### Tox Configuration Example

```ini
# tox.ini
[tox]
envlist = py310,py311,py312
isolated_build = True

[testenv]
deps =
    -r{toxinidir}/requirements-test.txt
commands =
    pytest {posargs}
changedir = {toxinidir}/packages/tests
```

**Run with tox:**
```bash
tox
tox -e py311  # Specific version
```

## Troubleshooting

### Test Failures

**Issue: "No module named 'netrun'"**
- **Solution**: Install at least one netrun package: `pip install -e ../netrun-auth`

**Issue: "Package not installed" skips**
- **Solution**: Install the packages you want to test
- Tests automatically skip if packages aren't installed

**Issue: "Circular import detected"**
- **Solution**: Check package dependencies, ensure no circular imports
- Review `test_no_circular_imports` output for details

### Import Errors

**Issue: Old import style doesn't work**
- **Solution**: Ensure backwards compatibility layer is implemented
- Check that old package names (netrun_auth) are still available

**Issue: Type checking tests fail**
- **Solution**: Add `py.typed` marker file to package directory
- File should be empty or contain "partial\n" for partial typing

### Coverage Issues

**Issue: Coverage below threshold**
- **Solution**: Review htmlcov/index.html for uncovered lines
- Add tests for missing branches/conditions

**Issue: Coverage not detecting imports**
- **Solution**: Use `--cov=netrun.auth` instead of `--cov=.`
- Ensure packages are installed in editable mode (`-e`)

## Advanced Usage

### Performance Testing

```bash
# Measure import times
pytest --benchmark-only

# Show slowest tests
pytest --durations=10

# Profile memory usage (Python 3.11+)
pytest --memray
```

### Parallel Execution

```bash
# Auto-detect CPU count
pytest -n auto

# Specific worker count
pytest -n 4

# Distributed testing across machines
pytest -d --tx popen//python=python3.11 --tx popen//python=python3.12
```

### Randomized Testing

```bash
# Randomize test order
pytest --randomly-seed=12345

# Repeat tests to catch intermittent failures
pytest --count=100

# Stop on first failure
pytest -x
```

### Filtering Tests

```bash
# Run only failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff

# Run tests matching expression
pytest -k "auth and not slow"

# Exclude specific tests
pytest -k "not integration"
```

## File Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest fixtures and configuration
├── pytest.ini                   # Pytest configuration
├── requirements-test.txt        # Test dependencies
├── test_namespace_imports.py    # Main test suite
├── htmlcov/                     # Coverage HTML reports (generated)
├── .coverage                    # Coverage data (generated)
├── coverage.xml                 # Coverage XML report (generated)
└── pytest.log                   # Test execution logs (generated)
```

## Contributing

When adding new tests:

1. **Follow naming convention**: `test_*` for functions, `Test*` for classes
2. **Add markers**: Use appropriate markers (@pytest.mark.namespace, etc.)
3. **Document tests**: Add docstrings explaining what's being tested
4. **Handle missing packages**: Use `check_module_exists` and `pytest.skip()`
5. **Update this README**: Add new test categories to documentation

## Support

- **Issues**: Report in main repository issue tracker
- **Questions**: Contact engineering@netrunsystems.com
- **Documentation**: See individual package READMEs

## License

MIT License - Copyright (c) 2024-2025 Netrun Systems, Inc.

---

**Last Updated**: December 18, 2025
**Maintained By**: Netrun Systems QA Team
**Status**: Production Ready
