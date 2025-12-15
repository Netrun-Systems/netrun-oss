"""Tests for core validation functionality."""

import pytest
from pathlib import Path

from netrun_env.validator import EnvValidator, ValidationResult
from netrun_env.security import SecurityLevel


class TestEnvValidator:
    """Test EnvValidator class."""

    def test_validate_file_success(self, sample_env_file, temp_dir, sample_schema):
        """Test successful validation of environment file."""
        # Create schema file
        schema_file = temp_dir / ".env.schema.json"
        import json
        schema_file.write_text(json.dumps(sample_schema))

        # Validate
        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_file(sample_env_file, schema_file)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_file_missing_required(self, temp_dir, sample_schema):
        """Test validation failure with missing required variable."""
        # Create incomplete env file
        env_file = temp_dir / ".env"
        env_file.write_text("DATABASE_URL=postgresql://localhost/db")

        schema_file = temp_dir / ".env.schema.json"
        import json
        schema_file.write_text(json.dumps(sample_schema))

        # Validate
        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_file(env_file, schema_file)

        assert not result.is_valid
        assert any("JWT_SECRET_KEY" in error for error in result.errors)

    def test_validate_file_weak_secret(self, temp_dir):
        """Test validation failure with weak secret."""
        # Create env file with weak secret
        env_file = temp_dir / ".env"
        env_file.write_text("JWT_SECRET_KEY=short")

        # Validate
        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_file(env_file)

        assert not result.is_valid
        assert any("32 characters" in error for error in result.errors)

    def test_validate_file_forbidden_jwt_algorithm(self, temp_dir):
        """Test validation failure with forbidden JWT algorithm."""
        # Create env file with HS256
        env_file = temp_dir / ".env"
        content = """
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=this-is-a-very-long-secret-key-that-meets-requirements-32-chars
"""
        env_file.write_text(content.strip())

        # Validate
        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_file(env_file)

        assert not result.is_valid
        assert any("Forbidden JWT algorithm" in error for error in result.errors)

    def test_validate_file_http_in_production(self, temp_dir):
        """Test validation failure with HTTP in production."""
        # Create env file with HTTP URL
        env_file = temp_dir / ".env"
        env_file.write_text("API_URL=http://api.example.com")

        # Validate with production security level
        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_file(env_file)

        assert not result.is_valid
        assert any("must use HTTPS" in error for error in result.errors)

    def test_validate_file_http_in_development(self, temp_dir):
        """Test HTTP allowed in development."""
        # Create env file with HTTP URL
        env_file = temp_dir / ".env"
        env_file.write_text("API_URL=http://localhost:3000")

        # Validate with development security level
        validator = EnvValidator(security_level=SecurityLevel.DEVELOPMENT)
        result = validator.validate_file(env_file)

        assert result.is_valid

    def test_validate_variables_success(self, sample_variables, sample_schema):
        """Test successful validation of variables dictionary."""
        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_variables(sample_variables, sample_schema)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_variables_type_error(self, sample_schema):
        """Test validation failure with type error."""
        variables = {
            "DATABASE_URL": "postgresql://localhost/db",
            "DATABASE_POOL_SIZE": "not_an_integer",  # Type error
            "JWT_SECRET_KEY": "this-is-a-very-long-secret-key-that-meets-requirements-32-chars",
            "JWT_ALGORITHM": "RS256",
            "API_BASE_URL": "https://api.example.com",
            "API_TIMEOUT": "30",
            "DEBUG": "false",
            "ADMIN_EMAIL": "admin@example.com"
        }

        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_variables(variables, sample_schema)

        assert not result.is_valid
        assert any("must be an integer" in error for error in result.errors)

    def test_validate_placeholder_warning(self, sample_schema):
        """Test warning for placeholder secrets."""
        variables = {
            "DATABASE_URL": "postgresql://localhost/db",
            "DATABASE_POOL_SIZE": "10",
            "JWT_SECRET_KEY": "[SECRET_KEY_HERE]",  # Placeholder
            "JWT_ALGORITHM": "RS256",
            "API_BASE_URL": "https://api.example.com",
            "API_TIMEOUT": "30",
            "DEBUG": "false",
            "ADMIN_EMAIL": "admin@example.com"
        }

        validator = EnvValidator(security_level=SecurityLevel.PRODUCTION)
        result = validator.validate_variables(variables, sample_schema)

        # Should have warnings about placeholder
        assert len(result.warnings) > 0
        assert any("placeholder" in warning.lower() for warning in result.warnings)

    def test_validation_result_str(self):
        """Test ValidationResult string formatting."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )

        result_str = str(result)
        assert "[ERROR] Validation failed" in result_str
        assert "Error 1" in result_str
        assert "Error 2" in result_str
        assert "Warning 1" in result_str

        # Test success case
        result_success = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert "[OK] Validation passed" in str(result_success)
