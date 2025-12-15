"""
Core environment validation logic.

Combines schema validation and security checks to provide
comprehensive environment variable validation.
"""

from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass

from .schema import SchemaGenerator
from .security import SecurityValidator, SecurityLevel

# Optional netrun-logging integration
_use_netrun_logging = False
_logger = None

try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


def _log(level: str, message: str, **kwargs) -> None:
    """Log message using netrun-logging if available, otherwise standard logging."""
    if _use_netrun_logging:
        log_method = getattr(_logger, level, _logger.info)
        log_method(message, **kwargs)
    else:
        log_method = getattr(_logger, level, _logger.info)
        log_method(f"{message} {kwargs}" if kwargs else message)


@dataclass
class ValidationResult:
    """Result of environment validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def __str__(self) -> str:
        """Format validation result as string."""
        lines = []

        if self.is_valid:
            lines.append("[OK] Validation passed")
        else:
            lines.append("[ERROR] Validation failed")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  - {error}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


class EnvValidator:
    """Validates environment files against schemas with security checks."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        """
        Initialize environment validator.

        Args:
            security_level: Security level to enforce
        """
        self.schema_generator = SchemaGenerator()
        self.security_validator = SecurityValidator(security_level)

    def validate_file(
        self,
        env_file: Path,
        schema_file: Optional[Path] = None
    ) -> ValidationResult:
        """
        Validate environment file against schema.

        Args:
            env_file: Path to .env file
            schema_file: Path to .env.schema.json file (optional)

        Returns:
            ValidationResult with errors and warnings
        """
        _log("info", f"Starting validation of environment file", env_file=str(env_file))
        errors = []
        warnings = []

        # Parse environment file
        try:
            variables = self.schema_generator.parse_env_file(env_file)
            _log("debug", f"Parsed {len(variables)} environment variables", count=len(variables))
        except Exception as e:
            _log("error", f"Failed to parse environment file", error=str(e))
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to parse environment file: {e}"],
                warnings=[]
            )

        # Schema validation (if schema provided)
        if schema_file and schema_file.exists():
            _log("info", f"Validating against schema", schema_file=str(schema_file))
            try:
                schema = self.schema_generator.load_schema(schema_file)
                schema_errors = self.schema_generator.validate_against_schema(variables, schema)
                errors.extend(schema_errors)
                if schema_errors:
                    _log("warning", f"Schema validation found {len(schema_errors)} errors", error_count=len(schema_errors))
            except Exception as e:
                _log("error", f"Failed to load or validate schema", error=str(e))
                errors.append(f"Failed to load or validate schema: {e}")

        # Security validation
        try:
            security_errors = self.security_validator.validate_all(variables)
            errors.extend(security_errors)
            if security_errors:
                _log("warning", f"Security validation found {len(security_errors)} errors", error_count=len(security_errors))

            # Check for exposed secrets (warnings only)
            exposed_warnings = self.security_validator.check_exposed_secrets(variables)
            warnings.extend(exposed_warnings)
            if exposed_warnings:
                _log("warning", f"Found {len(exposed_warnings)} potential secret exposure warnings", warning_count=len(exposed_warnings))
        except Exception as e:
            _log("error", f"Security validation failed", error=str(e))
            errors.append(f"Security validation failed: {e}")

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        _log("info", f"Validation complete", is_valid=result.is_valid, errors=len(errors), warnings=len(warnings))
        return result

    def validate_variables(
        self,
        variables: Dict[str, str],
        schema: Optional[Dict] = None
    ) -> ValidationResult:
        """
        Validate a dictionary of variables.

        Args:
            variables: Dictionary of environment variables
            schema: Optional schema dictionary

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Schema validation (if schema provided)
        if schema:
            try:
                schema_errors = self.schema_generator.validate_against_schema(variables, schema)
                errors.extend(schema_errors)
            except Exception as e:
                errors.append(f"Schema validation failed: {e}")

        # Security validation
        try:
            security_errors = self.security_validator.validate_all(variables)
            errors.extend(security_errors)

            exposed_warnings = self.security_validator.check_exposed_secrets(variables)
            warnings.extend(exposed_warnings)
        except Exception as e:
            errors.append(f"Security validation failed: {e}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
