# Test Examples and Common Scenarios

This document provides practical examples of using the namespace package import tests for common scenarios.

## Table of Contents

1. [Quick Validation](#quick-validation)
2. [New Package Integration](#new-package-integration)
3. [Debugging Import Issues](#debugging-import-issues)
4. [CI/CD Integration](#cicd-integration)
5. [Testing Migration to Namespace Packages](#testing-migration-to-namespace-packages)
6. [Performance Testing](#performance-testing)

---

## Quick Validation

### Verify All Installed Packages

```bash
# Install packages you want to test
pip install -e ../netrun-auth
pip install -e ../netrun-config
pip install -e ../netrun-errors

# Run quick validation
pytest test_namespace_imports.py -v -m "not slow"

# Check results
echo $?  # 0 = all tests passed
```

### Validate Single Package

```bash
# Test only netrun.auth
pytest test_namespace_imports.py::test_netrun_auth_complete_api -v

# Test only netrun.config
pytest test_namespace_imports.py::test_netrun_config_complete_api -v

# Test only netrun.errors
pytest test_namespace_imports.py::test_netrun_errors_complete_api -v
```

---

## New Package Integration

### Adding a New Package to the Test Suite

When creating a new package (e.g., `netrun-monitoring`):

**Step 1**: Add exports to `PACKAGE_EXPORTS` in `test_namespace_imports.py`

```python
# In test_namespace_imports.py
PACKAGE_EXPORTS = {
    # ... existing packages ...
    "netrun.monitoring": [
        "MetricsCollector",
        "HealthChecker",
        "AlertManager",
        "configure_monitoring",
    ],
}
```

**Step 2**: Create comprehensive API test

```python
@pytest.mark.namespace
def test_netrun_monitoring_complete_api(check_module_exists):
    """Comprehensive API validation for netrun.monitoring package."""
    if not check_module_exists("netrun.monitoring"):
        pytest.skip("netrun.monitoring is not installed")

    from netrun.monitoring import (
        MetricsCollector,
        HealthChecker,
        AlertManager,
        configure_monitoring,
    )

    # Verify all imports succeeded
    assert MetricsCollector is not None
    assert callable(configure_monitoring)
```

**Step 3**: Add to type checking tests

```python
@pytest.mark.parametrize(
    "package",
    [
        "netrun.auth",
        "netrun.config",
        "netrun.errors",
        "netrun.monitoring",  # Add new package
    ],
)
def test_py_typed_exists_all_packages(self, package: str, check_module_exists):
    # ... existing test code ...
```

**Step 4**: Run tests

```bash
# Install new package
pip install -e ../netrun-monitoring

# Run tests
pytest test_namespace_imports.py -k monitoring -v
```

---

## Debugging Import Issues

### Issue: Package Not Found

**Scenario**: Getting "No module named 'netrun.auth'" error

```bash
# Debug step 1: Check if package is installed
pip list | grep netrun

# Debug step 2: Check if it's in the right location
python3 -c "import sys; print('\n'.join(sys.path))"

# Debug step 3: Try manual import
python3 -c "import netrun.auth; print(netrun.auth.__file__)"

# Debug step 4: Check namespace path
python3 -c "import netrun; print(list(netrun.__path__))"

# Fix: Install in editable mode
pip install -e /path/to/netrun-auth
```

### Issue: Circular Import Detected

**Scenario**: Tests report circular import between packages

```bash
# Run circular import detection test
pytest test_namespace_imports.py::TestCrossPackageDependencies::test_no_circular_imports -v

# If it fails, check import order manually
python3 << 'EOF'
import sys
sys.path.insert(0, '../netrun-auth')
sys.path.insert(0, '../netrun-config')

# This will show where circular import occurs
import netrun.auth
import netrun.config
EOF

# Fix: Review package dependencies in pyproject.toml
# Remove or make optional any circular dependencies
```

### Issue: Old Import Style Doesn't Work

**Scenario**: `import netrun_auth` fails but `import netrun.auth` works

```bash
# Check if backwards compatibility is installed
python3 -c "import netrun_auth; print('Old style works')" || echo "Old style broken"

# Debug: Check what's installed
pip show netrun-auth

# Fix: Ensure package is installed with both import styles
# Add to package __init__.py:
# sys.modules['netrun_auth'] = sys.modules['netrun.auth']
```

---

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/test-namespace.yml`:

```yaml
name: Namespace Package Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'packages/**'
  pull_request:
    branches: [main]
    paths:
      - 'packages/**'

jobs:
  test-namespace:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip packages
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('packages/tests/requirements-test.txt') }}

      - name: Install test dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r packages/tests/requirements-test.txt

      - name: Install packages
        run: |
          pip install -e packages/netrun-auth
          pip install -e packages/netrun-config
          pip install -e packages/netrun-errors
          pip install -e packages/netrun-logging

      - name: Run namespace tests
        run: |
          cd packages/tests
          pytest test_namespace_imports.py \
            -v \
            --cov=. \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=junit.xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./packages/tests/coverage.xml
          flags: namespace-tests
          name: ${{ matrix.os }}-${{ matrix.python-version }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results-${{ matrix.os }}-${{ matrix.python-version }}
          path: packages/tests/junit.xml
```

### GitLab CI/CD

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

.test-template: &test-template
  stage: test
  before_script:
    - python --version
    - pip install virtualenv
    - virtualenv venv
    - source venv/bin/activate
    - pip install -r packages/tests/requirements-test.txt
    - pip install -e packages/netrun-auth
    - pip install -e packages/netrun-config
    - pip install -e packages/netrun-errors
  script:
    - cd packages/tests
    - pytest test_namespace_imports.py -v --cov=. --cov-report=xml --cov-report=term
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: packages/tests/coverage.xml
    paths:
      - packages/tests/htmlcov

test-python-3.10:
  <<: *test-template
  image: python:3.10

test-python-3.11:
  <<: *test-template
  image: python:3.11

test-python-3.12:
  <<: *test-template
  image: python:3.12
```

---

## Testing Migration to Namespace Packages

### Scenario: Migrating from `netrun_auth` to `netrun.auth`

**Step 1**: Install both old and new versions

```bash
# Assume old version is still available
pip install netrun-auth==0.9.0  # Old style

# Install new version in editable mode
pip install -e ../netrun-auth  # New namespace style
```

**Step 2**: Run backwards compatibility tests

```bash
pytest test_namespace_imports.py::TestBackwardsCompatibility -v
```

**Step 3**: Verify both import styles work

```python
# test_migration.py
import pytest

def test_both_import_styles():
    """Verify both old and new import styles work during migration."""

    # Old style
    import netrun_auth
    assert hasattr(netrun_auth, 'JWTManager')

    # New style
    from netrun.auth import JWTManager

    # They should be the same
    assert netrun_auth.JWTManager is JWTManager

def test_deprecated_warning():
    """Ensure old style triggers deprecation warning."""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        import netrun_auth  # noqa: F401

        # Should have deprecation warning
        assert len(w) > 0
        assert issubclass(w[0].category, DeprecationWarning)
```

**Step 4**: Create migration guide

```bash
# Create MIGRATION.md in your package
cat > ../netrun-auth/MIGRATION.md << 'EOF'
# Migration from netrun_auth to netrun.auth

## Old Import Style (Deprecated)
```python
from netrun_auth import JWTManager  # Will show deprecation warning
```

## New Import Style (Recommended)
```python
from netrun.auth import JWTManager  # Namespace package
```

## Backwards Compatibility
Both import styles will work until v2.0.0
EOF
```

---

## Performance Testing

### Measure Import Time

```python
# test_import_performance.py
import pytest
import time

@pytest.mark.benchmark
def test_import_time_netrun_auth(benchmark):
    """Benchmark import time for netrun.auth."""

    def import_auth():
        import netrun.auth
        return netrun.auth

    result = benchmark(import_auth)
    assert result is not None

@pytest.mark.benchmark
def test_lazy_loading_performance(benchmark):
    """Benchmark lazy loading of optional dependencies."""

    def import_with_optional():
        from netrun.auth import JWTManager
        return JWTManager

    result = benchmark(import_with_optional)
    assert result is not None
```

**Run benchmarks:**

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run performance tests
pytest test_import_performance.py --benchmark-only

# Save baseline
pytest test_import_performance.py --benchmark-save=baseline

# Compare against baseline
pytest test_import_performance.py --benchmark-compare=baseline
```

### Memory Profiling

```python
# test_import_memory.py
import pytest

@pytest.mark.memray
@pytest.mark.skipif(sys.version_info < (3, 11), reason="memray requires Python 3.11+")
def test_import_memory_usage():
    """Profile memory usage during import."""
    import netrun.auth
    import netrun.config
    import netrun.errors

    # Memory profiling will be done by pytest-memray
    assert True
```

**Run memory profiling:**

```bash
# Install pytest-memray (Python 3.11+ only)
pip install pytest-memray

# Run with memory profiling
pytest test_import_memory.py --memray
```

---

## Continuous Monitoring

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Pre-commit hook to run namespace tests

echo "Running namespace package tests..."

cd packages/tests

# Run fast tests only
pytest test_namespace_imports.py -m "not slow" -q

if [ $? -ne 0 ]; then
    echo "❌ Namespace tests failed. Commit aborted."
    exit 1
fi

echo "✅ Namespace tests passed"
exit 0
```

**Enable hook:**

```bash
chmod +x .git/hooks/pre-commit
```

### Nightly Test Schedule

```bash
# crontab -e
0 2 * * * cd /path/to/Netrun_Service_Library_v2/packages/tests && ./run_tests.sh --coverage >> /var/log/namespace-tests.log 2>&1
```

---

## Troubleshooting Common Scenarios

### Scenario 1: Tests Pass Locally But Fail in CI

**Cause**: Different Python versions or missing dependencies

**Solution**:
```bash
# Match CI environment locally
docker run -it python:3.11 bash
cd /path/to/tests
pip install -r requirements-test.txt
pytest test_namespace_imports.py -v
```

### Scenario 2: Type Checking Tests Fail

**Cause**: Missing `py.typed` marker file

**Solution**:
```bash
# Add py.typed to package
cd ../netrun-auth/netrun_auth
touch py.typed

# Rebuild package
cd ..
pip install -e .

# Re-run tests
cd ../tests
pytest test_namespace_imports.py::TestPEP561Compliance -v
```

### Scenario 3: Cross-Package Tests Fail

**Cause**: Circular dependencies or import order issues

**Solution**:
```bash
# Check import order
python3 << 'EOF'
import sys
# Enable import debugging
import importlib
importlib.import_module.__debug__ = True

import netrun.config  # This might try to import netrun.errors
import netrun.errors  # Which might try to import netrun.config
EOF

# Fix: Make dependencies optional in code
```

---

**Last Updated**: December 18, 2025
**Maintained By**: Netrun Systems QA Team
