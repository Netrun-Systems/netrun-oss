"""
JSON schema generation and validation for environment variables.

Implements schema generation from .env.example files and validation
of .env files against schemas.
"""

import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

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


class VarType(Enum):
    """Supported environment variable types."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    URL = "url"
    SECRET = "secret"
    EMAIL = "email"
    PATH = "path"


class SchemaGenerator:
    """Generates and validates JSON schemas for environment variables."""

    SCHEMA_VERSION = "https://netrunsystems.com/env-schema/v1"

    # Type inference patterns
    URL_PATTERN = re.compile(r'^https?://', re.IGNORECASE)
    DB_URL_PATTERN = re.compile(
        r'^(postgresql|mysql|redis|mongodb|sqlite|oracle|mssql|mariadb)',
        re.IGNORECASE
    )
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PATH_PATTERN = re.compile(r'^(/|[A-Za-z]:\\|\.{1,2}/)')
    INTEGER_PATTERN = re.compile(r'^\d+$')
    BOOLEAN_PATTERN = re.compile(r'^(true|false|yes|no|1|0)$', re.IGNORECASE)

    # Secret detection patterns
    SECRET_KEYWORDS = [
        'secret', 'key', 'token', 'password', 'credential', 'api_key',
        'private_key', 'auth', 'jwt_secret'
    ]

    def infer_type(self, var_name: str, value: str) -> VarType:
        """
        Infer variable type from name and value.

        Args:
            var_name: Environment variable name
            value: Environment variable value

        Returns:
            Inferred VarType
        """
        var_name_lower = var_name.lower()

        # Check for secret keywords
        if any(keyword in var_name_lower for keyword in self.SECRET_KEYWORDS):
            return VarType.SECRET

        # Check patterns in order of specificity
        if self.EMAIL_PATTERN.match(value):
            return VarType.EMAIL

        if self.URL_PATTERN.match(value) or self.DB_URL_PATTERN.match(value):
            return VarType.URL

        if self.PATH_PATTERN.match(value):
            return VarType.PATH

        if self.BOOLEAN_PATTERN.match(value):
            return VarType.BOOLEAN

        if self.INTEGER_PATTERN.match(value):
            return VarType.INTEGER

        return VarType.STRING

    def parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """
        Parse environment file into key-value pairs.

        Args:
            file_path: Path to .env file

        Returns:
            Dictionary of environment variables
        """
        variables = {}

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                        value = value[1:-1]

                    variables[key] = value

        return variables

    def generate_schema(self, example_file: Path) -> Dict[str, Any]:
        """
        Generate JSON schema from .env.example file.

        Args:
            example_file: Path to .env.example file

        Returns:
            JSON schema dictionary
        """
        _log("info", f"Generating schema from example file", example_file=str(example_file))
        variables = self.parse_env_file(example_file)
        _log("debug", f"Found {len(variables)} variables in example file", count=len(variables))

        schema = {
            "$schema": self.SCHEMA_VERSION,
            "version": "1.0",
            "variables": {}
        }

        for var_name, value in variables.items():
            var_type = self.infer_type(var_name, value)

            var_schema: Dict[str, Any] = {
                "type": var_type.value,
                "required": True,  # All variables in .example are required by default
            }

            # Add type-specific constraints
            if var_type == VarType.SECRET:
                var_schema["minLength"] = 32

            elif var_type == VarType.URL:
                # Infer allowed protocols from example
                if value.startswith('postgresql'):
                    var_schema["protocols"] = ["postgresql", "postgresql+asyncpg"]
                elif value.startswith('mysql'):
                    var_schema["protocols"] = ["mysql", "mysql+pymysql"]
                elif value.startswith('redis'):
                    var_schema["protocols"] = ["redis", "rediss"]
                elif value.startswith('https'):
                    var_schema["protocols"] = ["https"]
                elif value.startswith('http'):
                    var_schema["protocols"] = ["http", "https"]

            elif var_type == VarType.INTEGER:
                # Add min/max if variable name suggests bounds
                if 'port' in var_name.lower():
                    var_schema["min"] = 1
                    var_schema["max"] = 65535
                elif 'timeout' in var_name.lower():
                    var_schema["min"] = 0

            elif var_type == VarType.BOOLEAN:
                var_schema["allowed_values"] = ["true", "false", "yes", "no", "1", "0"]

            # Add example value (sanitized for secrets)
            if var_type == VarType.SECRET:
                var_schema["example"] = "[SECRET_VALUE]"
            else:
                var_schema["example"] = value

            schema["variables"][var_name] = var_schema

        return schema

    def save_schema(self, schema: Dict[str, Any], output_file: Path) -> None:
        """
        Save schema to JSON file.

        Args:
            schema: Schema dictionary
            output_file: Path to output .json file
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2)

    def load_schema(self, schema_file: Path) -> Dict[str, Any]:
        """
        Load schema from JSON file.

        Args:
            schema_file: Path to schema .json file

        Returns:
            Schema dictionary
        """
        with open(schema_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate_against_schema(
        self,
        variables: Dict[str, str],
        schema: Dict[str, Any]
    ) -> List[str]:
        """
        Validate environment variables against schema.

        Args:
            variables: Dictionary of environment variables
            schema: Schema dictionary

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        schema_vars = schema.get("variables", {})

        # Check required variables
        for var_name, var_schema in schema_vars.items():
            if var_schema.get("required", False) and var_name not in variables:
                errors.append(f"Required variable '{var_name}' is missing")

        # Validate present variables
        for var_name, value in variables.items():
            if var_name not in schema_vars:
                # Variable not in schema (warning, not error)
                continue

            var_schema = schema_vars[var_name]
            var_type = var_schema.get("type")

            # Type-specific validation
            if var_type == "integer":
                if not self.INTEGER_PATTERN.match(value):
                    errors.append(f"Variable '{var_name}' must be an integer (found: '{value}')")
                else:
                    int_value = int(value)
                    if "min" in var_schema and int_value < var_schema["min"]:
                        errors.append(
                            f"Variable '{var_name}' must be >= {var_schema['min']} (found: {int_value})"
                        )
                    if "max" in var_schema and int_value > var_schema["max"]:
                        errors.append(
                            f"Variable '{var_name}' must be <= {var_schema['max']} (found: {int_value})"
                        )

            elif var_type == "boolean":
                allowed = var_schema.get("allowed_values", ["true", "false", "yes", "no", "1", "0"])
                if value.lower() not in [v.lower() for v in allowed]:
                    errors.append(
                        f"Variable '{var_name}' must be one of {allowed} (found: '{value}')"
                    )

            elif var_type == "url":
                # Allow both HTTP(S) URLs and database URLs
                is_http_url = self.URL_PATTERN.match(value)
                is_db_url = self.DB_URL_PATTERN.match(value)

                if not (is_http_url or is_db_url):
                    errors.append(f"Variable '{var_name}' must be a valid URL (found: '{value}')")
                elif "protocols" in var_schema:
                    allowed_protocols = var_schema["protocols"]
                    if not any(value.startswith(f"{proto}://") for proto in allowed_protocols):
                        errors.append(
                            f"Variable '{var_name}' must use one of {allowed_protocols} "
                            f"(found: '{value[:20]}...')"
                        )

            elif var_type == "email":
                if not self.EMAIL_PATTERN.match(value):
                    errors.append(f"Variable '{var_name}' must be a valid email (found: '{value}')")

            elif var_type == "secret":
                min_length = var_schema.get("minLength", 32)
                if len(value) < min_length:
                    errors.append(
                        f"Secret '{var_name}' must be at least {min_length} characters "
                        f"(current: {len(value)} characters)"
                    )

        return errors
