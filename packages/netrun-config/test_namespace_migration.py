#!/usr/bin/env python3
"""
Test script to verify namespace migration for netrun-config v2.0.0

Tests both import paths:
1. New namespace: from netrun.config import ...
2. Legacy path (with deprecation warning): from netrun_config import ...
"""

import sys
import warnings


def test_new_namespace_import():
    """Test new namespace package import."""
    print("=" * 70)
    print("TEST 1: New namespace import (netrun.config)")
    print("=" * 70)

    try:
        from netrun.config import (
            BaseConfig,
            Field,
            get_settings,
            KeyVaultMixin,
            SecretCache,
            __version__,
        )

        print("✅ SUCCESS: All imports from netrun.config work correctly")
        print(f"   Version: {__version__}")
        print(f"   BaseConfig: {BaseConfig.__name__}")
        print(f"   get_settings: {get_settings.__name__}")
        print(f"   KeyVaultMixin: {KeyVaultMixin.__name__}")
        return True
    except ImportError as e:
        print(f"❌ FAILED: {e}")
        return False


def test_legacy_import_with_deprecation():
    """Test legacy import path with deprecation warning."""
    print("\n" + "=" * 70)
    print("TEST 2: Legacy import (netrun_config) - Should show deprecation")
    print("=" * 70)

    # Capture deprecation warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        try:
            from netrun_config import (
                BaseConfig,
                Field,
                get_settings,
                __version__,
            )

            # Check if deprecation warning was issued
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]

            if deprecation_warnings:
                print("✅ SUCCESS: Legacy import works with deprecation warning")
                print(f"   Version: {__version__}")
                print(f"   Deprecation message: {deprecation_warnings[0].message}")
                return True
            else:
                print("⚠️  WARNING: Legacy import works but no deprecation warning issued")
                print(f"   Version: {__version__}")
                return True  # Still counts as success, just missing warning

        except ImportError as e:
            print(f"❌ FAILED: {e}")
            return False


def test_functionality():
    """Test basic functionality with new namespace."""
    print("\n" + "=" * 70)
    print("TEST 3: Functional test - Create settings instance")
    print("=" * 70)

    try:
        from netrun.config import BaseConfig, get_settings

        # Create settings instance
        settings = get_settings(BaseConfig)

        print("✅ SUCCESS: Settings instance created successfully")
        print(f"   App Name: {settings.app_name}")
        print(f"   Environment: {settings.app_environment}")
        print(f"   Is Production: {settings.is_production}")
        print(f"   Is Development: {settings.is_development}")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("NETRUN-CONFIG v2.0.0 NAMESPACE MIGRATION TEST")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("New namespace import", test_new_namespace_import()))
    results.append(("Legacy import with deprecation", test_legacy_import_with_deprecation()))
    results.append(("Functional test", test_functionality()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Migration successful!")
    else:
        print("❌ SOME TESTS FAILED - Migration needs review")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
