"""Tests for security validators."""

import pytest
from netrun.validation.security import (
    calculate_entropy,
    validate_secret_key,
    validate_password_strength,
    validate_api_key_format,
    validate_jwt_secret,
    validate_encryption_key,
)


class TestCalculateEntropy:
    """Tests for calculate_entropy."""

    def test_weak_password(self):
        """Test entropy calculation for weak password."""
        entropy = calculate_entropy("password")
        assert entropy < 3.0  # Low entropy

    def test_strong_password(self):
        """Test entropy calculation for strong password."""
        entropy = calculate_entropy("P@ssw0rd!123XyZ")
        assert entropy > 3.0  # Higher entropy

    def test_empty_string(self):
        """Test entropy calculation for empty string."""
        entropy = calculate_entropy("")
        assert entropy == 0.0


class TestValidateSecretKey:
    """Tests for validate_secret_key."""

    def test_valid_key(self):
        """Test validation with valid key."""
        key = "a" * 32
        assert validate_secret_key(key) == key

    def test_longer_key(self):
        """Test validation with longer key."""
        key = "a" * 64
        assert validate_secret_key(key) == key

    def test_short_key(self):
        """Test validation with short key."""
        with pytest.raises(ValueError, match="secret_key must be at least 32 characters long"):
            validate_secret_key("short")

    def test_empty_key(self):
        """Test validation with empty key."""
        with pytest.raises(ValueError, match="secret_key is required"):
            validate_secret_key("")

    def test_custom_min_length(self):
        """Test validation with custom minimum length."""
        key = "a" * 64
        assert validate_secret_key(key, min_length=64) == key

    def test_custom_field_name(self):
        """Test validation with custom field name."""
        with pytest.raises(ValueError, match="api_key must be at least 32 characters long"):
            validate_secret_key("short", field_name="api_key")


class TestValidatePasswordStrength:
    """Tests for validate_password_strength."""

    def test_strong_password(self):
        """Test validation with strong password."""
        password = "P@ssw0rd123"
        assert validate_password_strength(password) == password

    def test_minimum_requirements(self):
        """Test password with minimum requirements."""
        password = "Passw0rd"
        assert validate_password_strength(password) == password

    def test_too_short(self):
        """Test password that's too short."""
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            validate_password_strength("Pass1")

    def test_missing_uppercase(self):
        """Test password missing uppercase letter."""
        with pytest.raises(ValueError, match="at least one uppercase letter"):
            validate_password_strength("password123")

    def test_missing_lowercase(self):
        """Test password missing lowercase letter."""
        with pytest.raises(ValueError, match="at least one lowercase letter"):
            validate_password_strength("PASSWORD123")

    def test_missing_digit(self):
        """Test password missing digit."""
        with pytest.raises(ValueError, match="at least one digit"):
            validate_password_strength("Password")

    def test_require_special(self):
        """Test password with special character requirement."""
        with pytest.raises(ValueError, match="at least one special character"):
            validate_password_strength("Password123", require_special=True)

    def test_with_special_character(self):
        """Test password with special character."""
        password = "P@ssw0rd"
        assert validate_password_strength(password, require_special=True) == password

    def test_custom_min_length(self):
        """Test password with custom minimum length."""
        password = "Password12345"
        assert validate_password_strength(password, min_length=12) == password

    def test_empty_password(self):
        """Test validation with empty password."""
        with pytest.raises(ValueError, match="Password is required"):
            validate_password_strength("")

    def test_min_entropy(self):
        """Test password with minimum entropy requirement."""
        # Strong password should pass
        password = "P@ssw0rd!123XyZ"
        assert validate_password_strength(password, min_entropy=3.0) == password

        # Weak password should fail
        with pytest.raises(ValueError, match="higher complexity"):
            validate_password_strength("aaaa", min_entropy=3.0, min_length=4,
                                     require_uppercase=False, require_lowercase=False,
                                     require_digit=False)


class TestValidateApiKeyFormat:
    """Tests for validate_api_key_format."""

    def test_valid_key_with_prefix(self):
        """Test validation with valid key and prefix."""
        key = "sk-" + "a" * 20
        assert validate_api_key_format(key, prefix="sk-") == key

    def test_valid_key_without_prefix(self):
        """Test validation without prefix requirement."""
        key = "a" * 20
        assert validate_api_key_format(key) == key

    def test_wrong_prefix(self):
        """Test validation with wrong prefix."""
        with pytest.raises(ValueError, match="API key must start with 'sk-'"):
            validate_api_key_format("pk-" + "a" * 20, prefix="sk-")

    def test_too_short(self):
        """Test validation with key too short."""
        with pytest.raises(ValueError, match="API key must be at least 20 characters long"):
            validate_api_key_format("sk-short", prefix="sk-")

    def test_empty_key(self):
        """Test validation with empty key."""
        with pytest.raises(ValueError, match="API key is required"):
            validate_api_key_format("")

    def test_custom_min_length(self):
        """Test validation with custom minimum length."""
        key = "sk-" + "a" * 32
        assert validate_api_key_format(key, prefix="sk-", min_length=32) == key


class TestValidateJWTSecret:
    """Tests for validate_jwt_secret."""

    def test_valid_jwt_secret(self):
        """Test validation with valid JWT secret."""
        secret = "a" * 32
        assert validate_jwt_secret(secret) == secret

    def test_short_jwt_secret(self):
        """Test validation with short JWT secret."""
        with pytest.raises(ValueError, match="JWT secret must be at least 32 characters long"):
            validate_jwt_secret("short")


class TestValidateEncryptionKey:
    """Tests for validate_encryption_key."""

    def test_valid_encryption_key(self):
        """Test validation with valid encryption key."""
        key = "a" * 32
        assert validate_encryption_key(key) == key

    def test_short_encryption_key(self):
        """Test validation with short encryption key."""
        with pytest.raises(ValueError, match="encryption key must be at least 32 characters long"):
            validate_encryption_key("short")
