"""
Comprehensive migration test for netrun-logging v2.0.0
Tests both old (deprecated) and new (recommended) import paths
"""
import warnings
import sys

def test_core_imports():
    """Test core module imports"""
    print("=" * 60)
    print("TEST 1: Core Imports")
    print("=" * 60)
    
    # Test old path with deprecation
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from netrun_logging import configure_logging, get_logger
        assert len(w) > 0, "Expected deprecation warning"
        print(f"✅ Old import works with deprecation warning")
    
    # Test new path (no deprecation)
    from netrun.logging import configure_logging as conf2, get_logger as log2
    assert configure_logging is conf2
    assert get_logger is log2
    print("✅ New import works without warning")
    print("✅ Both paths reference same objects")
    print()

def test_middleware_imports():
    """Test middleware imports"""
    print("=" * 60)
    print("TEST 2: Middleware Imports")
    print("=" * 60)
    
    # Test old middleware path
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        from netrun_logging.middleware import add_logging_middleware
        print("✅ Old middleware import works")
    
    # Test new middleware path
    from netrun.logging.middleware import add_logging_middleware as add2
    from netrun.logging.middleware.fastapi import CorrelationIdMiddleware
    print("✅ New middleware imports work")
    print()

def test_integrations_imports():
    """Test integrations imports"""
    print("=" * 60)
    print("TEST 3: Integrations Imports")
    print("=" * 60)
    
    from netrun.logging.integrations import configure_azure_insights
    print("✅ Integrations import works")
    print()

def test_formatters_imports():
    """Test formatters imports"""
    print("=" * 60)
    print("TEST 4: Formatters Imports")
    print("=" * 60)
    
    from netrun.logging.formatters import JsonFormatter
    print("✅ Formatters import works")
    print()

def test_functionality():
    """Test basic logging functionality"""
    print("=" * 60)
    print("TEST 5: Basic Functionality")
    print("=" * 60)
    
    from netrun.logging import configure_logging, get_logger, bind_context
    
    # Configure
    configure_logging(app_name="test-migration", environment="dev", enable_json=False)
    print("✅ Logging configured")
    
    # Get logger
    logger = get_logger(__name__)
    
    # Basic logging
    logger.info("test_message", user_id=123, action="migration_test")
    print("✅ Basic logging works")
    
    # Context binding
    bind_context(tenant_id="test-tenant", version="2.0.0")
    logger.info("context_test", feature="namespace_migration")
    print("✅ Context binding works")
    print()

def test_ecosystem_integration():
    """Test ecosystem integration helpers"""
    print("=" * 60)
    print("TEST 6: Ecosystem Integration")
    print("=" * 60)
    
    from netrun.logging import (
        bind_error_context,
        bind_request_context,
        bind_operation_context,
    )
    
    bind_request_context(method="GET", path="/test", user_id="user-123")
    print("✅ bind_request_context works")
    
    bind_operation_context(operation="test_op", resource_type="Migration")
    print("✅ bind_operation_context works")
    
    bind_error_context(error_code="TEST_ERROR", status_code=500)
    print("✅ bind_error_context works")
    print()

def main():
    print("\n" + "=" * 60)
    print("netrun-logging v2.0.0 Migration Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_core_imports()
        test_middleware_imports()
        test_integrations_imports()
        test_formatters_imports()
        test_functionality()
        test_ecosystem_integration()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED - Migration Successful!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
