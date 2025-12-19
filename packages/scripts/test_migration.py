#!/usr/bin/env python3
"""
Test suite for namespace migration script.

Tests the migration process on a temporary test package to ensure
correctness before running on production packages.

Author: Netrun Systems
Version: 1.0.0
License: MIT
"""

import shutil
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest


def create_test_package(base_dir: Path, package_name: str) -> Path:
    """
    Create a test package structure.

    Args:
        base_dir: Base directory for test packages
        package_name: Name of test package (e.g., "netrun-test")

    Returns:
        Path to created package directory
    """
    pkg_dir = base_dir / package_name
    pkg_dir.mkdir(parents=True)

    # Derive module name
    module_name = package_name.replace("netrun-", "netrun_")

    # Create source directory
    src_dir = pkg_dir / module_name
    src_dir.mkdir()

    # Create __init__.py
    init_file = src_dir / "__init__.py"
    init_file.write_text(dedent(f'''
        """Test package for namespace migration."""

        __version__ = "1.0.0"

        from .core import TestClass
        from .utils import helper_function

        __all__ = ["TestClass", "helper_function"]
    '''))

    # Create core.py
    core_file = src_dir / "core.py"
    core_file.write_text(dedent(f'''
        """Core module."""

        from {module_name}.utils import helper_function


        class TestClass:
            """Test class."""

            def __init__(self, name: str):
                self.name = name

            def greet(self) -> str:
                return helper_function(self.name)
    '''))

    # Create utils.py
    utils_file = src_dir / "utils.py"
    utils_file.write_text(dedent(f'''
        """Utility module."""


        def helper_function(name: str) -> str:
            """Helper function."""
            return f"Hello, {{name}}!"
    '''))

    # Create pyproject.toml
    pyproject_file = pkg_dir / "pyproject.toml"
    pyproject_file.write_text(dedent(f'''
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "{package_name}"
        version = "1.0.0"
        description = "Test package"
        requires-python = ">=3.11"
        dependencies = [
            "fastapi>=0.115.0",
        ]

        [tool.hatch.build.targets.wheel]
        packages = ["{module_name}"]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        addopts = [
            "--verbose",
            "--cov={module_name}",
        ]

        [tool.coverage.run]
        source = ["{module_name}"]
    '''))

    # Create README.md with import examples
    readme_file = pkg_dir / "README.md"
    readme_file.write_text(dedent(f'''
        # Test Package

        ## Usage

        ```python
        from {module_name} import TestClass

        obj = TestClass("World")
        print(obj.greet())
        ```
    '''))

    # Create tests directory
    tests_dir = pkg_dir / "tests"
    tests_dir.mkdir()

    test_file = tests_dir / "test_core.py"
    test_file.write_text(dedent(f'''
        """Tests for core module."""

        import pytest
        from {module_name} import TestClass


        def test_test_class():
            """Test TestClass."""
            obj = TestClass("Test")
            assert obj.name == "Test"
            assert obj.greet() == "Hello, Test!"
    '''))

    return pkg_dir


@pytest.fixture
def temp_packages_dir():
    """Create temporary packages directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_package_discovery(temp_packages_dir):
    """Test package discovery."""
    from migrate_to_namespace import discover_packages

    # Create test packages
    create_test_package(temp_packages_dir, "netrun-test1")
    create_test_package(temp_packages_dir, "netrun-test2")
    create_test_package(temp_packages_dir, "other-package")

    packages = discover_packages(temp_packages_dir)

    assert len(packages) == 2
    assert all(p.name.startswith("netrun-") for p in packages)


def test_migration_dry_run(temp_packages_dir):
    """Test dry run migration."""
    from migrate_to_namespace import PackageMigrator

    pkg_dir = create_test_package(temp_packages_dir, "netrun-test")

    migrator = PackageMigrator(
        package_dir=pkg_dir,
        dry_run=True,
        skip_shim=False,
    )

    # Should succeed without making changes
    assert migrator.migrate()

    # Old structure should still exist
    old_src_dir = pkg_dir / "netrun_test"
    assert old_src_dir.exists()

    # New structure should NOT exist
    new_src_dir = pkg_dir / "netrun" / "test"
    assert not new_src_dir.exists()


def test_migration_full(temp_packages_dir):
    """Test full migration."""
    from migrate_to_namespace import PackageMigrator

    pkg_dir = create_test_package(temp_packages_dir, "netrun-test")

    migrator = PackageMigrator(
        package_dir=pkg_dir,
        dry_run=False,
        skip_shim=False,
    )

    assert migrator.migrate()

    # Check new structure exists
    new_src_dir = pkg_dir / "netrun" / "test"
    assert new_src_dir.exists()
    assert (new_src_dir / "__init__.py").exists()
    assert (new_src_dir / "core.py").exists()
    assert (new_src_dir / "utils.py").exists()

    # Check namespace __init__.py
    namespace_init = pkg_dir / "netrun" / "__init__.py"
    assert namespace_init.exists()
    assert "__path__" in namespace_init.read_text()

    # Check compatibility shim exists
    shim_dir = pkg_dir / "netrun_test"
    assert shim_dir.exists()
    shim_init = shim_dir / "__init__.py"
    assert shim_init.exists()
    assert "DeprecationWarning" in shim_init.read_text()

    # Check imports were updated
    core_content = (new_src_dir / "core.py").read_text()
    assert "from netrun.test.utils import" in core_content
    assert "from netrun_test.utils" not in core_content

    # Check pyproject.toml was updated
    pyproject_content = (pkg_dir / "pyproject.toml").read_text()
    assert 'packages = ["netrun/test"]' in pyproject_content
    assert 'version = "2.0.0"' in pyproject_content
    assert "netrun-core>=1.0.0" in pyproject_content

    # Check test files were updated
    test_content = (pkg_dir / "tests" / "test_core.py").read_text()
    assert "from netrun.test import" in test_content
    assert "from netrun_test import" not in test_content

    # Verify backup was created
    backup_dirs = list(pkg_dir.parent.glob("netrun-test.backup.*"))
    assert len(backup_dirs) == 1


def test_migration_skip_shim(temp_packages_dir):
    """Test migration without compatibility shim."""
    from migrate_to_namespace import PackageMigrator

    pkg_dir = create_test_package(temp_packages_dir, "netrun-test")

    migrator = PackageMigrator(
        package_dir=pkg_dir,
        dry_run=False,
        skip_shim=True,
    )

    assert migrator.migrate()

    # Check new structure exists
    new_src_dir = pkg_dir / "netrun" / "test"
    assert new_src_dir.exists()

    # Check shim does NOT exist
    shim_dir = pkg_dir / "netrun_test"
    assert not shim_dir.exists()


def test_validation_syntax_error(temp_packages_dir):
    """Test validation catches syntax errors."""
    from migrate_to_namespace import PackageMigrator

    pkg_dir = create_test_package(temp_packages_dir, "netrun-test")

    # Create file with syntax error
    bad_file = pkg_dir / "netrun_test" / "bad.py"
    bad_file.write_text("def invalid syntax here")

    migrator = PackageMigrator(
        package_dir=pkg_dir,
        dry_run=False,
        skip_shim=False,
    )

    # Migration should fail validation
    assert not migrator.migrate()
    assert len(migrator.errors) > 0


def test_import_rewriting_patterns(temp_packages_dir):
    """Test various import rewriting patterns."""
    from migrate_to_namespace import PackageMigrator

    pkg_dir = create_test_package(temp_packages_dir, "netrun-test")

    # Create file with various import patterns
    test_imports = pkg_dir / "netrun_test" / "imports_test.py"
    test_imports.write_text(dedent('''
        """Test various import patterns."""

        # Pattern 1: from netrun_test import
        from netrun_test import TestClass

        # Pattern 2: from netrun_test.module import
        from netrun_test.core import TestClass

        # Pattern 3: import netrun_test
        import netrun_test

        # Pattern 4: import netrun_test.module
        import netrun_test.utils

        # Pattern 5: Multiple imports
        from netrun_test import TestClass, helper_function
    '''))

    migrator = PackageMigrator(
        package_dir=pkg_dir,
        dry_run=False,
        skip_shim=False,
    )

    assert migrator.migrate()

    # Check imports were rewritten
    new_imports = pkg_dir / "netrun" / "test" / "imports_test.py"
    content = new_imports.read_text()

    assert "from netrun.test import TestClass" in content
    assert "from netrun.test.core import TestClass" in content
    assert "import netrun.test" in content
    assert "import netrun.test.utils" in content
    assert "from netrun.test import TestClass, helper_function" in content

    # Should not contain old imports
    assert "from netrun_test" not in content
    assert "import netrun_test" not in content


def test_rollback(temp_packages_dir):
    """Test migration rollback."""
    from migrate_to_namespace import PackageMigrator

    pkg_dir = create_test_package(temp_packages_dir, "netrun-test")

    # Store original content
    original_init = (pkg_dir / "netrun_test" / "__init__.py").read_text()

    migrator = PackageMigrator(
        package_dir=pkg_dir,
        dry_run=False,
        skip_shim=False,
    )

    assert migrator.migrate()

    # Verify migration occurred
    new_src_dir = pkg_dir / "netrun" / "test"
    assert new_src_dir.exists()

    # Rollback
    assert migrator.rollback()

    # Check old structure is restored
    old_src_dir = pkg_dir / "netrun_test"
    assert old_src_dir.exists()
    assert (old_src_dir / "__init__.py").read_text() == original_init

    # Check new structure is removed
    new_src_dir = pkg_dir / "netrun" / "test"
    assert not new_src_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
