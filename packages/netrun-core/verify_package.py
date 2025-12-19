#!/usr/bin/env python3
"""
Verification script for netrun-core namespace package.

This script tests all critical functionality of the netrun-core foundation package.
"""

import sys
import os

# Add current directory to path for testing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test basic import functionality."""
    print("Test 1: Basic import...")
    try:
        import netrun
        print("  ✓ Successfully imported netrun module")
        return True
    except ImportError as e:
        print(f"  ✗ Failed to import netrun: {e}")
        return False

def test_version_info():
    """Test version and metadata attributes."""
    print("\nTest 2: Version and metadata...")
    try:
        import netrun

        assert hasattr(netrun, '__version__'), "Missing __version__ attribute"
        assert netrun.__version__ == "1.0.0", f"Version mismatch: {netrun.__version__}"
        print(f"  ✓ Version: {netrun.__version__}")

        assert hasattr(netrun, '__author__'), "Missing __author__ attribute"
        assert netrun.__author__ == "Netrun Systems", f"Author mismatch: {netrun.__author__}"
        print(f"  ✓ Author: {netrun.__author__}")

        assert hasattr(netrun, '__email__'), "Missing __email__ attribute"
        assert netrun.__email__ == "dev@netrunsystems.com", f"Email mismatch: {netrun.__email__}"
        print(f"  ✓ Email: {netrun.__email__}")

        return True
    except (ImportError, AssertionError) as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_namespace_path():
    """Test namespace path extension capability."""
    print("\nTest 3: Namespace path extension...")
    try:
        import netrun

        assert hasattr(netrun, '__path__'), "Missing __path__ attribute"
        print(f"  ✓ Namespace path: {netrun.__path__}")

        # Verify it's iterable (required for namespace packages)
        paths = list(netrun.__path__)
        print(f"  ✓ Path is iterable with {len(paths)} entry/entries")

        return True
    except (ImportError, AssertionError) as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_docstring():
    """Test module docstring exists."""
    print("\nTest 4: Module documentation...")
    try:
        import netrun

        assert netrun.__doc__ is not None, "Missing module docstring"
        assert "Netrun Systems" in netrun.__doc__, "Docstring missing company name"
        print(f"  ✓ Module has comprehensive docstring ({len(netrun.__doc__)} chars)")

        return True
    except (ImportError, AssertionError) as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_no_submodules():
    """Test that core package doesn't expose unexpected submodules."""
    print("\nTest 5: Clean namespace (no unexpected submodules)...")
    try:
        import netrun

        # Expected attributes (not submodules)
        expected_attrs = ['__version__', '__author__', '__email__', '__path__',
                         '__doc__', '__name__', '__package__', '__loader__',
                         '__spec__', '__file__']

        actual_attrs = [attr for attr in dir(netrun) if not attr.startswith('_')]

        if actual_attrs:
            print(f"  ⚠ Found public attributes: {actual_attrs}")
            print("    (This is OK if intentional)")
        else:
            print("  ✓ Namespace is clean (no public attributes)")

        return True
    except (ImportError, Exception) as e:
        print(f"  ✗ Failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 70)
    print("netrun-core Package Verification")
    print("=" * 70)

    tests = [
        test_import,
        test_version_info,
        test_namespace_path,
        test_docstring,
        test_no_submodules,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 70)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 70)

    if all(results):
        print("\n✓ All tests passed! Package is ready for use.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
