"""Test configuration for netrun-pytest-fixtures tests."""

import pytest

# Note: The package auto-registers as a pytest plugin via pyproject.toml entry_points
# No need for pytest_plugins - it causes double registration errors
# Fixtures are automatically available when package is installed
