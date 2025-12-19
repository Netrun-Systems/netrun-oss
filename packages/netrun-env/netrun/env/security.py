"""
Security validation for environment variables.

Implements checks for:
- Secret strength (minimum length requirements)
- JWT algorithm whitelisting
- URL protocol validation (HTTPS enforcement)
- Sensitive data exposure detection
"""

import re
from typing import Dict, List, Optional, Tuple
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


class SecurityLevel(Enum):
    """Security levels for environment validation."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class SecurityValidator:
    """Validates security constraints for environment variables."""

    # Minimum secret length requirements
    MIN_SECRET_LENGTH = 32
    MIN_PASSWORD_LENGTH = 16

    # JWT algorithm whitelist (asymmetric only for production)
    ALLOWED_JWT_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
    FORBIDDEN_JWT_ALGORITHMS = {"HS256", "HS384", "HS512", "none"}

    # URL patterns
    HTTPS_PATTERN = re.compile(r'^https://', re.IGNORECASE)
    HTTP_PATTERN = re.compile(r'^http://', re.IGNORECASE)

    # Variable name patterns for sensitive data
    SECRET_PATTERNS = [
        r'.*_SECRET.*',
        r'.*_KEY$',
        r'.*_TOKEN$',
        r'.*_PASSWORD$',
        r'.*_CREDENTIAL.*',
        r'.*_API_KEY$',
    ]

    def __init__(self, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        """
        Initialize security validator.

        Args:
            security_level: Security level to enforce (development/staging/production)
        """
        self.security_level = security_level
        self.secret_pattern = re.compile('|'.join(self.SECRET_PATTERNS), re.IGNORECASE)

    def validate_secret_strength(self, var_name: str, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate secret strength based on variable name.

        Args:
            var_name: Environment variable name
            value: Environment variable value

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.secret_pattern.match(var_name):
            return True, None

        # Check minimum length
        min_length = self.MIN_SECRET_LENGTH
        if 'PASSWORD' in var_name.upper():
            min_length = self.MIN_PASSWORD_LENGTH

        if len(value) < min_length:
            return False, (
                f"Secret '{var_name}' must be at least {min_length} characters "
                f"(current: {len(value)} characters)"
            )

        # Check for common weak patterns
        weak_patterns = [
            (r'^password\d*$', "Common password pattern detected"),
            (r'^123456', "Sequential number pattern detected"),
            (r'^qwerty', "Keyboard pattern detected"),
            (r'^(admin|root|test)', "Common default value detected"),
        ]

        for pattern, message in weak_patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return False, f"Weak secret detected in '{var_name}': {message}"

        return True, None

    def validate_jwt_algorithm(self, algorithm: str) -> Tuple[bool, Optional[str]]:
        """
        Validate JWT algorithm against whitelist.

        Args:
            algorithm: JWT algorithm name (e.g., 'RS256', 'HS256')

        Returns:
            Tuple of (is_valid, error_message)
        """
        algorithm = algorithm.upper().strip()

        if algorithm in self.FORBIDDEN_JWT_ALGORITHMS:
            return False, (
                f"Forbidden JWT algorithm '{algorithm}'. "
                f"Use asymmetric algorithms: {', '.join(sorted(self.ALLOWED_JWT_ALGORITHMS))}"
            )

        if algorithm not in self.ALLOWED_JWT_ALGORITHMS:
            return False, (
                f"Unknown JWT algorithm '{algorithm}'. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_JWT_ALGORITHMS))}"
            )

        return True, None

    def validate_url_protocol(self, var_name: str, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL protocol based on security level.

        Args:
            var_name: Environment variable name
            url: URL value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Allow HTTP in development only
        if self.security_level == SecurityLevel.DEVELOPMENT:
            return True, None

        # Staging and Production require HTTPS
        if self.HTTP_PATTERN.match(url) and not self.HTTPS_PATTERN.match(url):
            return False, (
                f"URL '{var_name}' must use HTTPS in {self.security_level.value} "
                f"(found: {url[:50]}...)"
            )

        return True, None

    def validate_all(self, variables: Dict[str, str]) -> List[str]:
        """
        Validate all security constraints for a set of variables.

        Args:
            variables: Dictionary of environment variables

        Returns:
            List of validation error messages (empty if all valid)
        """
        _log("info", f"Starting security validation", variable_count=len(variables), security_level=self.security_level.value)
        errors = []

        for var_name, value in variables.items():
            # Secret strength validation
            is_valid, error = self.validate_secret_strength(var_name, value)
            if not is_valid:
                _log("warning", f"Secret strength validation failed", variable=var_name)
                errors.append(error)

            # JWT algorithm validation
            if 'JWT_ALGORITHM' in var_name.upper():
                is_valid, error = self.validate_jwt_algorithm(value)
                if not is_valid:
                    _log("warning", f"JWT algorithm validation failed", variable=var_name, algorithm=value)
                    errors.append(error)

            # URL protocol validation
            if value.startswith(('http://', 'https://')):
                is_valid, error = self.validate_url_protocol(var_name, value)
                if not is_valid:
                    _log("warning", f"URL protocol validation failed", variable=var_name)
                    errors.append(error)

        _log("info", f"Security validation complete", error_count=len(errors))
        return errors

    def check_exposed_secrets(self, variables: Dict[str, str]) -> List[str]:
        """
        Check for potentially exposed secrets (placeholders, defaults, etc.).

        Args:
            variables: Dictionary of environment variables

        Returns:
            List of warning messages for exposed secrets
        """
        warnings = []

        placeholder_patterns = [
            r'\[.*\]',  # [PLACEHOLDER]
            r'<.*>',    # <PLACEHOLDER>
            r'your-.*-here',  # your-secret-here
            r'changeme',
            r'TODO',
        ]

        combined_pattern = re.compile('|'.join(placeholder_patterns), re.IGNORECASE)

        for var_name, value in variables.items():
            if self.secret_pattern.match(var_name):
                if combined_pattern.search(value):
                    warnings.append(
                        f"Secret '{var_name}' appears to contain a placeholder value"
                    )

        return warnings
