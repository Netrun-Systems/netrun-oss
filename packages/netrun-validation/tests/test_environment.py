"""Tests for environment validators."""

import pytest
from netrun.validation.environment import (
    validate_environment,
    validate_log_level,
    validate_provider,
    validate_llm_provider,
    validate_voice_provider,
    validate_database_provider,
    validate_cloud_provider,
)


class TestValidateEnvironment:
    """Tests for validate_environment."""

    def test_valid_environment(self):
        """Test validation with valid environment."""
        assert validate_environment("production") == "production"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_environment("PRODUCTION") == "production"

    def test_development(self):
        """Test development environment."""
        assert validate_environment("development") == "development"

    def test_staging(self):
        """Test staging environment."""
        assert validate_environment("staging") == "staging"

    def test_testing(self):
        """Test testing environment."""
        assert validate_environment("testing") == "testing"

    def test_custom_allowed(self):
        """Test validation with custom allowed environments."""
        assert validate_environment("local", allowed=["local", "dev", "prod"]) == "local"

    def test_invalid_environment(self):
        """Test validation with invalid environment."""
        with pytest.raises(ValueError, match="environment must be one of"):
            validate_environment("invalid")


class TestValidateLogLevel:
    """Tests for validate_log_level."""

    def test_info(self):
        """Test INFO log level."""
        assert validate_log_level("INFO") == "INFO"

    def test_debug(self):
        """Test DEBUG log level."""
        assert validate_log_level("DEBUG") == "DEBUG"

    def test_warning(self):
        """Test WARNING log level."""
        assert validate_log_level("WARNING") == "WARNING"

    def test_error(self):
        """Test ERROR log level."""
        assert validate_log_level("ERROR") == "ERROR"

    def test_critical(self):
        """Test CRITICAL log level."""
        assert validate_log_level("CRITICAL") == "CRITICAL"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_log_level("info") == "INFO"

    def test_custom_allowed(self):
        """Test validation with custom allowed log levels."""
        assert validate_log_level("TRACE", allowed=["TRACE", "DEBUG"]) == "TRACE"

    def test_invalid_log_level(self):
        """Test validation with invalid log level."""
        with pytest.raises(ValueError, match="log_level must be one of"):
            validate_log_level("INVALID")


class TestValidateProvider:
    """Tests for validate_provider."""

    def test_valid_provider(self):
        """Test validation with valid provider."""
        result = validate_provider("openai", ["local", "openai", "azure"], "LLM")
        assert result == "openai"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        result = validate_provider("OPENAI", ["local", "openai", "azure"], "LLM")
        assert result == "openai"

    def test_invalid_provider(self):
        """Test validation with invalid provider."""
        with pytest.raises(ValueError, match="LLM provider must be one of"):
            validate_provider("invalid", ["local", "openai", "azure"], "LLM")


class TestValidateLLMProvider:
    """Tests for validate_llm_provider."""

    def test_local(self):
        """Test local LLM provider."""
        assert validate_llm_provider("local") == "local"

    def test_openai(self):
        """Test OpenAI provider."""
        assert validate_llm_provider("openai") == "openai"

    def test_azure_openai(self):
        """Test Azure OpenAI provider."""
        assert validate_llm_provider("azure_openai") == "azure_openai"

    def test_anthropic(self):
        """Test Anthropic provider."""
        assert validate_llm_provider("anthropic") == "anthropic"

    def test_ollama(self):
        """Test Ollama provider."""
        assert validate_llm_provider("ollama") == "ollama"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_llm_provider("OPENAI") == "openai"

    def test_invalid_provider(self):
        """Test validation with invalid provider."""
        with pytest.raises(ValueError, match="LLM provider must be one of"):
            validate_llm_provider("invalid")


class TestValidateVoiceProvider:
    """Tests for validate_voice_provider."""

    def test_azure(self):
        """Test Azure voice provider."""
        assert validate_voice_provider("azure") == "azure"

    def test_local(self):
        """Test local voice provider."""
        assert validate_voice_provider("local") == "local"

    def test_whisper(self):
        """Test Whisper provider."""
        assert validate_voice_provider("whisper") == "whisper"

    def test_elevenlabs(self):
        """Test ElevenLabs provider."""
        assert validate_voice_provider("elevenlabs") == "elevenlabs"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_voice_provider("AZURE") == "azure"

    def test_invalid_provider(self):
        """Test validation with invalid provider."""
        with pytest.raises(ValueError, match="voice provider must be one of"):
            validate_voice_provider("invalid")


class TestValidateDatabaseProvider:
    """Tests for validate_database_provider."""

    def test_postgresql(self):
        """Test PostgreSQL provider."""
        assert validate_database_provider("postgresql") == "postgresql"

    def test_mysql(self):
        """Test MySQL provider."""
        assert validate_database_provider("mysql") == "mysql"

    def test_sqlite(self):
        """Test SQLite provider."""
        assert validate_database_provider("sqlite") == "sqlite"

    def test_mssql(self):
        """Test MSSQL provider."""
        assert validate_database_provider("mssql") == "mssql"

    def test_mongodb(self):
        """Test MongoDB provider."""
        assert validate_database_provider("mongodb") == "mongodb"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_database_provider("POSTGRESQL") == "postgresql"

    def test_invalid_provider(self):
        """Test validation with invalid provider."""
        with pytest.raises(ValueError, match="database provider must be one of"):
            validate_database_provider("invalid")


class TestValidateCloudProvider:
    """Tests for validate_cloud_provider."""

    def test_azure(self):
        """Test Azure cloud provider."""
        assert validate_cloud_provider("azure") == "azure"

    def test_aws(self):
        """Test AWS provider."""
        assert validate_cloud_provider("aws") == "aws"

    def test_gcp(self):
        """Test GCP provider."""
        assert validate_cloud_provider("gcp") == "gcp"

    def test_local(self):
        """Test local provider."""
        assert validate_cloud_provider("local") == "local"

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_cloud_provider("AZURE") == "azure"

    def test_invalid_provider(self):
        """Test validation with invalid provider."""
        with pytest.raises(ValueError, match="cloud provider must be one of"):
            validate_cloud_provider("invalid")
