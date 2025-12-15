"""
Netrun Authentication - Password Hashing
=========================================

Secure password hashing and validation using Argon2id algorithm.

Changelog:
- v1.2.0: Integrated netrun-logging with password operation logging
- v1.0.0: Initial release with Argon2id hashing

Author: Netrun Systems
Version: 1.2.0
Date: 2025-12-05
"""

import re
from typing import Optional, List, Tuple
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from .config import AuthConfig
from .exceptions import AuthenticationError

# Graceful netrun-logging integration
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)

logger = _logger


class PasswordManager:
    """
    Password hashing and validation manager.

    Uses Argon2id algorithm (OWASP recommended) with constant-time comparison.
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize password manager.

        Args:
            config: Authentication configuration (uses defaults if None)
        """
        self.config = config or AuthConfig()

        # Initialize pwdlib with Argon2id hasher
        self.password_hash = PasswordHash((
            Argon2Hasher(
                time_cost=3,        # Number of iterations (OWASP minimum: 2)
                memory_cost=65536,  # Memory in KiB (OWASP minimum: 37 MiB = 37888 KiB)
                parallelism=4,      # Degree of parallelism
                hash_len=32,        # Hash length in bytes
                salt_len=16         # Salt length in bytes
            ),
        ))

    def hash_password(self, password: str) -> str:
        """
        Hash a password using Argon2id.

        Args:
            password: Plain text password

        Returns:
            Hashed password string

        Raises:
            AuthenticationError: If password does not meet requirements
        """
        # Validate password strength
        is_valid, errors = self.validate_password_strength(password)
        if not is_valid:
            if _use_netrun_logging:
                logger.warning(
                    "password_validation_failed",
                    validation_errors=errors,
                    operation="hash_password"
                )
            raise AuthenticationError(
                message="Password does not meet security requirements",
                error_code="PASSWORD_WEAK",
                details={"validation_errors": errors}
            )

        if _use_netrun_logging:
            logger.debug("password_hashed", operation="hash_password", algorithm="argon2id")

        return self.password_hash.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash using constant-time comparison.

        Args:
            password: Plain text password to verify
            password_hash: Hashed password to compare against

        Returns:
            True if password matches hash, False otherwise
        """
        try:
            result = self.password_hash.verify(password, password_hash)
            if _use_netrun_logging:
                logger.debug(
                    "password_verified",
                    verification_result=result,
                    operation="verify_password"
                )
            return result
        except Exception as e:
            if _use_netrun_logging:
                logger.warning(
                    "password_verification_error",
                    error_type=type(e).__name__,
                    operation="verify_password"
                )
            # Return False for any verification errors (invalid hash format, etc.)
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """
        Check if password hash needs rehashing with updated parameters.

        Args:
            password_hash: Hashed password to check

        Returns:
            True if hash should be updated, False otherwise
        """
        try:
            return self.password_hash.needs_rehash(password_hash)
        except Exception:
            # If we can't parse the hash, it definitely needs rehashing
            return True

    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password meets security requirements.

        Args:
            password: Plain text password to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check minimum length
        if len(password) < self.config.password_min_length:
            errors.append(
                f"Password must be at least {self.config.password_min_length} characters long"
            )

        # Check for uppercase letters
        if self.config.password_require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        # Check for lowercase letters
        if self.config.password_require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        # Check for digits
        if self.config.password_require_digits and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        # Check for special characters
        if self.config.password_require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")

        # Check for common weak passwords
        if self._is_common_password(password):
            errors.append("Password is too common and easily guessable")

        return (len(errors) == 0, errors)

    def _is_common_password(self, password: str) -> bool:
        """
        Check if password is in list of commonly used weak passwords.

        Args:
            password: Password to check

        Returns:
            True if password is common, False otherwise
        """
        # Top 20 most common passwords (basic check)
        # In production, use a comprehensive dictionary like HaveIBeenPwned
        common_passwords = {
            "password", "123456", "12345678", "qwerty", "abc123",
            "monkey", "1234567", "letmein", "trustno1", "dragon",
            "baseball", "111111", "iloveyou", "master", "sunshine",
            "ashley", "bailey", "passw0rd", "shadow", "123123"
        }
        return password.lower() in common_passwords

    def generate_password_reset_token(self, user_id: str) -> str:
        """
        Generate a secure password reset token.

        Args:
            user_id: User ID for password reset

        Returns:
            Secure random token string

        Note:
            Token should be stored with expiration (typically 1 hour).
            Use secrets.token_urlsafe() for cryptographically secure tokens.
        """
        import secrets
        # Generate 32-byte random token (43 characters in base64)
        token = secrets.token_urlsafe(32)
        # In production, store token hash with user_id and expiration in Redis/DB
        return token


# Singleton instance for convenience
_password_manager: Optional[PasswordManager] = None


def get_password_manager(config: Optional[AuthConfig] = None) -> PasswordManager:
    """
    Get singleton password manager instance.

    Args:
        config: Authentication configuration (uses defaults if None)

    Returns:
        PasswordManager instance
    """
    global _password_manager
    if _password_manager is None:
        _password_manager = PasswordManager(config)
    return _password_manager
