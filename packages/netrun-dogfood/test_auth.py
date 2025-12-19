#!/usr/bin/env python3
"""
Test script for netrun-dogfood authentication and NetrunSite tools.

This script verifies:
1. Azure AD authentication configuration
2. Token acquisition
3. NetrunSite API health check
4. Blog post listing

Usage:
    python test_auth.py

Prerequisites:
    - Azure AD credentials configured (env vars or Key Vault)
    - netrun-dogfood package installed
"""

import asyncio
import sys
from datetime import datetime
from netrun_dogfood.auth import get_auth
from netrun_dogfood.config import get_config
from netrun_dogfood.tools import netrunsite


def print_header(text: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print('='*80)


def print_status(label: str, status: bool, details: str = "") -> None:
    """Print status line with checkmark or cross."""
    icon = "[PASS]" if status else "[FAIL]"
    print(f"{icon} {label}: {details}")


async def test_configuration():
    """Test configuration loading."""
    print_header("Configuration Test")

    config = get_config()

    print(f"USE_KEYVAULT_AUTH: {config.use_keyvault_auth}")
    print(f"AZURE_KEYVAULT_URL: {config.azure_keyvault_url or 'Not set'}")
    print()

    print_status(
        "Azure Tenant ID",
        bool(config.azure_tenant_id),
        "SET" if config.azure_tenant_id else "NOT SET"
    )
    print_status(
        "Azure Client ID",
        bool(config.azure_client_id),
        "SET" if config.azure_client_id else "NOT SET"
    )
    print_status(
        "Azure Client Secret",
        bool(config.azure_client_secret),
        "SET" if config.azure_client_secret else "NOT SET"
    )

    all_configured = all([
        config.azure_tenant_id,
        config.azure_client_id,
        config.azure_client_secret
    ])

    print()
    print_status("Authentication Configured", all_configured)

    return all_configured


async def test_authentication():
    """Test Azure AD token acquisition."""
    print_header("Authentication Test")

    auth = get_auth()

    if not auth.is_configured:
        print_status("Authentication", False, "Not configured")
        print("\n[WARNING] Please configure Azure AD credentials:")
        print("   Option 1: Set environment variables")
        print("     export AZURE_TENANT_ID='<tenant-id>'")
        print("     export AZURE_CLIENT_ID='<client-id>'")
        print("     export AZURE_CLIENT_SECRET='<client-secret>'")
        print()
        print("   Option 2: Use Azure Key Vault")
        print("     export AZURE_KEYVAULT_URL='https://netrun-keyvault.vault.azure.net'")
        print("     export USE_KEYVAULT_AUTH='true'")
        return False

    try:
        token = await auth.get_token("netrunsite")
        print_status("Token Acquisition", True, f"Token acquired ({len(token)} chars)")
        print(f"   Token preview: {token[:30]}...")
        return True
    except Exception as e:
        print_status("Token Acquisition", False, str(e))
        return False


async def test_netrunsite_health():
    """Test NetrunSite API health check."""
    print_header("NetrunSite Health Check")

    auth = get_auth()

    try:
        result = await netrunsite.handle_tool("netrunsite_health", {}, auth)

        # Parse result
        for r in result:
            print(r.text)

        print_status("NetrunSite API", True, "Healthy")
        return True
    except Exception as e:
        print_status("NetrunSite API", False, str(e))
        return False


async def test_list_posts():
    """Test listing blog posts."""
    print_header("List Blog Posts Test")

    auth = get_auth()

    try:
        result = await netrunsite.handle_tool("netrunsite_list_posts", {}, auth)

        posts = []
        for r in result:
            print(r.text)
            # Try to count posts (simple text parsing)
            if "posts found" in r.text.lower() or "post" in r.text.lower():
                posts.append(r.text)

        if posts:
            print_status("List Posts", True, f"{len(posts)} results returned")
        else:
            print_status("List Posts", True, "No posts found or unknown format")

        return True
    except Exception as e:
        print_status("List Posts", False, str(e))
        return False


async def main():
    """Run all tests."""
    print(f"\n{'='*80}")
    print("  NetrunSite MCP Tool Authentication Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*80)

    results = []

    # Test 1: Configuration
    results.append(("Configuration", await test_configuration()))

    if not results[0][1]:
        print("\n[WARNING] Authentication not configured. Skipping remaining tests.")
        print_summary(results)
        return 1

    # Test 2: Authentication
    results.append(("Authentication", await test_authentication()))

    if not results[1][1]:
        print("\n[WARNING] Authentication failed. Skipping API tests.")
        print_summary(results)
        return 1

    # Test 3: Health check
    results.append(("Health Check", await test_netrunsite_health()))

    # Test 4: List posts
    results.append(("List Posts", await test_list_posts()))

    # Print summary
    print_summary(results)

    # Return exit code
    all_passed = all(result[1] for result in results)
    return 0 if all_passed else 1


def print_summary(results):
    """Print test summary."""
    print_header("Test Summary")

    for test_name, passed in results:
        print_status(test_name, passed, "PASS" if passed else "FAIL")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print()
    print(f"Tests passed: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[FAILED] {total_count - passed_count} test(s) failed")

    print('='*80)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
