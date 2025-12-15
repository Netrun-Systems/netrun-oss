"""Test script to validate netrun-config installation."""

from netrun_config import BaseConfig, Field, get_settings

class TestConfig(BaseConfig):
    """Test configuration class."""
    app_name: str = Field(default="test-app")
    custom_setting: str = Field(default="custom-value")

def main():
    """Run installation validation tests."""
    print("Testing netrun-config installation...")

    # Test 1: Basic configuration
    config = get_settings(TestConfig)
    assert config.app_name == "test-app"
    assert config.custom_setting == "custom-value"
    print("  [PASS] Basic configuration")

    # Test 2: Environment detection
    assert config.app_environment in ["development", "staging", "production", "testing"]
    print(f"  [PASS] Environment detection: {config.app_environment}")

    # Test 3: Debug mode
    assert isinstance(config.app_debug, bool)
    print(f"  [PASS] Debug mode: {config.app_debug}")

    # Test 4: Version
    import netrun_config
    print(f"  [PASS] Package version: {netrun_config.__version__}")

    print("\nAll tests passed! netrun-config is properly installed.")

if __name__ == "__main__":
    main()
