#!/usr/bin/env python3
"""
Validate Test Setup

This script checks that the test environment is properly configured
and all required dependencies are available.

Usage:
    python validate_setup.py
    python validate_setup.py --verbose
"""

import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version >= (3, 10):
        return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} (3.10+ required) ✗"


def check_package_installed(package_name: str) -> bool:
    """Check if a package is installed."""
    try:
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        # Package or its parent namespace is not installed
        return False


def check_required_dependencies() -> List[Tuple[str, bool, str]]:
    """Check required test dependencies."""
    dependencies = [
        ("pytest", "Core testing framework"),
        ("pytest_asyncio", "Async test support"),
        ("pytest_cov", "Coverage reporting"),
    ]

    results = []
    for pkg_name, description in dependencies:
        installed = check_package_installed(pkg_name)
        status = "✓" if installed else "✗"
        results.append((pkg_name, installed, f"{description} {status}"))

    return results


def check_optional_dependencies() -> List[Tuple[str, bool, str]]:
    """Check optional test dependencies."""
    dependencies = [
        ("pytest_xdist", "Parallel test execution"),
        ("pytest_benchmark", "Performance benchmarking"),
        ("pytest_timeout", "Test timeout support"),
        ("pytest_mock", "Enhanced mocking"),
        ("mypy", "Static type checking"),
    ]

    results = []
    for pkg_name, description in dependencies:
        installed = check_package_installed(pkg_name)
        status = "✓" if installed else "○"  # Circle for optional
        results.append((pkg_name, installed, f"{description} {status}"))

    return results


def check_netrun_packages() -> List[Tuple[str, bool, str]]:
    """Check installed Netrun packages."""
    packages = [
        ("netrun.auth", "Authentication & authorization"),
        ("netrun.config", "Configuration management"),
        ("netrun.errors", "Error handling"),
        ("netrun.logging", "Structured logging"),
        ("netrun.cors", "CORS middleware"),
        ("netrun.db_pool", "Database connection pooling"),
        ("netrun.env", "Environment validation"),
        ("netrun.llm", "LLM orchestration"),
        ("netrun.oauth", "OAuth adapters"),
        ("netrun.rbac", "RBAC & RLS"),
    ]

    results = []
    for pkg_name, description in packages:
        installed = check_package_installed(pkg_name)
        status = "✓" if installed else "○"
        results.append((pkg_name, installed, f"{description} {status}"))

    return results


def check_test_files() -> List[Tuple[str, bool, str]]:
    """Check if test files exist."""
    test_files = [
        ("test_namespace_imports.py", "Main test suite"),
        ("conftest.py", "Pytest configuration"),
        ("pytest.ini", "Pytest settings"),
        ("requirements-test.txt", "Test dependencies"),
    ]

    test_dir = Path(__file__).parent
    results = []

    for filename, description in test_files:
        file_path = test_dir / filename
        exists = file_path.exists()
        status = "✓" if exists else "✗"
        results.append((filename, exists, f"{description} {status}"))

    return results


def print_section(title: str, results: List[Tuple[str, bool, str]], verbose: bool = False):
    """Print a section of results."""
    print(f"\n{title}")
    print("=" * len(title))

    for name, installed, message in results:
        if verbose or not installed:
            print(f"  {message}")
        elif installed and "✓" in message:
            # In non-verbose mode, just show installed count
            continue

    # Show summary
    installed_count = sum(1 for _, installed, _ in results if installed)
    total_count = len(results)

    if installed_count == total_count:
        print(f"  All {total_count} items present ✓")
    else:
        print(f"  {installed_count}/{total_count} items present")


def main():
    """Main validation function."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("Netrun Namespace Package Test Setup Validation")
    print("=" * 50)

    # Check Python version
    python_ok, python_msg = check_python_version()
    print(f"\nPython Version: {python_msg}")

    if not python_ok:
        print("\n❌ ERROR: Python 3.10+ is required for namespace package tests")
        print("   Please upgrade your Python version.")
        return 1

    # Check test files
    test_files = check_test_files()
    print_section("Test Files", test_files, verbose)

    # Check required dependencies
    required_deps = check_required_dependencies()
    print_section("Required Dependencies", required_deps, verbose)

    # Check optional dependencies
    optional_deps = check_optional_dependencies()
    print_section("Optional Dependencies", optional_deps, verbose)

    # Check Netrun packages
    netrun_packages = check_netrun_packages()
    print_section("Netrun Packages", netrun_packages, verbose)

    # Final summary
    print("\n" + "=" * 50)

    # Check if all required items are present
    all_test_files = all(exists for _, exists, _ in test_files)
    all_required = all(installed for _, installed, _ in required_deps)

    if all_test_files and all_required:
        print("✅ Test environment is properly configured!")
        print("\nYou can now run tests:")
        print("  pytest test_namespace_imports.py -v")
        print("  ./run_tests.sh")
        print("  ./run_tests.sh --coverage")

        # Check if any Netrun packages are installed
        netrun_installed = any(installed for _, installed, _ in netrun_packages)
        if netrun_installed:
            print("\n📦 Netrun packages detected:")
            installed_pkgs = [name for name, installed, _ in netrun_packages if installed]
            for pkg in installed_pkgs:
                print(f"  - {pkg}")
        else:
            print("\n⚠️  No Netrun packages installed yet.")
            print("   Install packages to test:")
            print("   pip install -e ../netrun-auth")
            print("   pip install -e ../netrun-config")

        return 0
    else:
        print("❌ Test environment has missing components!")

        if not all_test_files:
            print("\nMissing test files:")
            for name, exists, _ in test_files:
                if not exists:
                    print(f"  - {name}")

        if not all_required:
            print("\nMissing required dependencies:")
            for name, installed, _ in required_deps:
                if not installed:
                    print(f"  - {name}")
            print("\nInstall missing dependencies:")
            print("  pip install -r requirements-test.txt")

        return 1


if __name__ == "__main__":
    sys.exit(main())
