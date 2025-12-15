"""Tests for CLI interface."""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from netrun_env.cli import main


class TestCLI:
    """Test CLI commands."""

    def test_version(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(main, ['--version'])

        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_validate_success(self, sample_env_file, temp_dir, sample_schema):
        """Test validate command with valid environment."""
        # Create schema file
        schema_file = temp_dir / ".env.schema.json"
        schema_file.write_text(json.dumps(sample_schema))

        runner = CliRunner()
        result = runner.invoke(main, [
            'validate',
            '--env', str(sample_env_file),
            '--schema', str(schema_file)
        ])

        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_validate_failure(self, temp_dir, sample_schema):
        """Test validate command with invalid environment."""
        # Create invalid env file
        env_file = temp_dir / ".env"
        env_file.write_text("JWT_SECRET_KEY=short")

        schema_file = temp_dir / ".env.schema.json"
        schema_file.write_text(json.dumps(sample_schema))

        runner = CliRunner()
        result = runner.invoke(main, [
            'validate',
            '--env', str(env_file),
            '--schema', str(schema_file)
        ])

        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_validate_strict_mode(self, temp_dir):
        """Test validate command in strict mode with warnings."""
        # Create env file with placeholder (warning)
        env_file = temp_dir / ".env"
        env_file.write_text("JWT_SECRET_KEY=[SECRET_HERE]")

        runner = CliRunner()
        result = runner.invoke(main, [
            'validate',
            '--env', str(env_file),
            '--strict'
        ])

        assert result.exit_code == 1
        assert "warning" in result.output.lower()

    def test_generate_schema_success(self, sample_env_example_file, temp_dir):
        """Test generate-schema command."""
        output_file = temp_dir / "schema.json"

        runner = CliRunner()
        result = runner.invoke(main, [
            'generate-schema',
            '--from', str(sample_env_example_file),
            '--out', str(output_file)
        ])

        assert result.exit_code == 0
        assert "Schema generated" in result.output
        assert output_file.exists()

        # Verify schema content
        schema = json.loads(output_file.read_text())
        assert "$schema" in schema
        assert "variables" in schema
        assert "DATABASE_URL" in schema["variables"]

    def test_generate_schema_overwrite_protection(self, sample_env_example_file, temp_dir):
        """Test generate-schema overwrite protection."""
        output_file = temp_dir / "schema.json"
        output_file.write_text("{}")  # Create existing file

        runner = CliRunner()
        result = runner.invoke(main, [
            'generate-schema',
            '--from', str(sample_env_example_file),
            '--out', str(output_file)
        ])

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_generate_schema_overwrite_flag(self, sample_env_example_file, temp_dir):
        """Test generate-schema with overwrite flag."""
        output_file = temp_dir / "schema.json"
        output_file.write_text("{}")  # Create existing file

        runner = CliRunner()
        result = runner.invoke(main, [
            'generate-schema',
            '--from', str(sample_env_example_file),
            '--out', str(output_file),
            '--overwrite'
        ])

        assert result.exit_code == 0
        assert "Schema generated" in result.output

    def test_diff_no_differences(self, sample_env_file, temp_dir):
        """Test diff command with identical files."""
        # Copy file to create identical comparison
        env_file2 = temp_dir / ".env2"
        env_file2.write_text(sample_env_file.read_text())

        runner = CliRunner()
        result = runner.invoke(main, [
            'diff',
            '--env1', str(sample_env_file),
            '--env2', str(env_file2)
        ])

        assert result.exit_code == 0
        assert "No differences" in result.output or "identical" in result.output

    def test_diff_with_differences(self, sample_env_file, temp_dir):
        """Test diff command with different files."""
        # Create modified file
        env_file2 = temp_dir / ".env2"
        content = sample_env_file.read_text() + "\nNEW_VAR=new_value"
        env_file2.write_text(content)

        runner = CliRunner()
        result = runner.invoke(main, [
            'diff',
            '--env1', str(sample_env_file),
            '--env2', str(env_file2)
        ])

        assert result.exit_code == 0
        assert "NEW_VAR" in result.output

    def test_diff_json_format(self, sample_env_file, temp_dir):
        """Test diff command with JSON output."""
        env_file2 = temp_dir / ".env2"
        content = sample_env_file.read_text() + "\nNEW_VAR=new_value"
        env_file2.write_text(content)

        runner = CliRunner()
        result = runner.invoke(main, [
            'diff',
            '--env1', str(sample_env_file),
            '--env2', str(env_file2),
            '--format', 'json'
        ])

        assert result.exit_code == 0

        # Verify JSON output
        output_data = json.loads(result.output)
        assert "added_in_target" in output_data
        assert "NEW_VAR" in output_data["added_in_target"]

    def test_diff_fail_on_diff(self, sample_env_file, temp_dir):
        """Test diff command with fail-on-diff flag."""
        env_file2 = temp_dir / ".env2"
        content = sample_env_file.read_text() + "\nNEW_VAR=new_value"
        env_file2.write_text(content)

        runner = CliRunner()
        result = runner.invoke(main, [
            'diff',
            '--env1', str(sample_env_file),
            '--env2', str(env_file2),
            '--fail-on-diff'
        ])

        assert result.exit_code == 1

    def test_diff_secret_masking(self, temp_dir):
        """Test diff command masks secrets by default."""
        env_file1 = temp_dir / ".env1"
        env_file1.write_text("JWT_SECRET_KEY=secret123456789012345678901234567890")

        env_file2 = temp_dir / ".env2"
        env_file2.write_text("JWT_SECRET_KEY=different123456789012345678901234567890")

        runner = CliRunner()
        result = runner.invoke(main, [
            'diff',
            '--env1', str(env_file1),
            '--env2', str(env_file2)
        ])

        assert result.exit_code == 0
        # Should show masked version
        assert "..." in result.output
        # Should NOT show full secrets
        assert "secret123456789012345678901234567890" not in result.output

    def test_diff_no_mask_flag(self, temp_dir):
        """Test diff command with no-mask flag."""
        env_file1 = temp_dir / ".env1"
        env_file1.write_text("JWT_SECRET_KEY=secret123456789012345678901234567890")

        env_file2 = temp_dir / ".env2"
        env_file2.write_text("JWT_SECRET_KEY=different123456789012345678901234567890")

        runner = CliRunner()
        result = runner.invoke(main, [
            'diff',
            '--env1', str(env_file1),
            '--env2', str(env_file2),
            '--no-mask'
        ])

        assert result.exit_code == 0
        # Should show full secrets
        assert "secret123456789012345678901234567890" in result.output
