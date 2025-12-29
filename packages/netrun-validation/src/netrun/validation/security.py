"""
Security-focused validators for passwords, secrets, and API keys.

This module provides validators to ensure security best practices for
sensitive credentials and authentication tokens.
"""

import math
import re
from typing import Optional


def calculate_entropy(s: str) -> float:
    """
    Calculate the Shannon entropy of a string (password strength metric).

    Args:
        s: The string to analyze

    Returns:
        float: Entropy value (higher is better, typically 0-8 bits per character)

    Example:
        >>> round(calculate_entropy("password"), 2)
        2.75
        >>> round(calculate_entropy("P@ssw0rd!123"), 2)
        3.34
    """
    if not s:
        return 0.0

    # Count character frequencies
    frequencies = {}
    for char in s:
        frequencies[char] = frequencies.get(char, 0) + 1

    # Calculate entropy
    length = len(s)
    entropy = 0.0

    for count in frequencies.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)

    return entropy


def validate_secret_key(
    v: str,
    min_length: int = 32,
    field_name: str = "secret_key",
) -> str:
    """
    Validate that a secret key meets minimum security requirements.

    Args:
        v: The secret key to validate
        min_length: Minimum required length (default: 32 characters)
        field_name: Name of the field being validated (for error messages)

    Returns:
        str: The validated secret key

    Raises:
        ValueError: If secret key doesn't meet requirements

    Example:
        >>> key = "a" * 32
        >>> validate_secret_key(key) == key
        True
        >>> validate_secret_key("short", min_length=32)
        Traceback (most recent call last):
        ...
        ValueError: secret_key must be at least 32 characters long. Got: 5 characters
    """
    if not v or not v.strip():
        raise ValueError(f"{field_name} is required")

    if len(v) < min_length:
        raise ValueError(
            f"{field_name} must be at least {min_length} characters long. "
            f"Got: {len(v)} characters"
        )

    return v


def validate_password_strength(
    v: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False,
    min_entropy: Optional[float] = None,
) -> str:
    """
    Validate password strength based on configurable requirements.

    Args:
        v: The password to validate
        min_length: Minimum password length
        require_uppercase: Require at least one uppercase letter
        require_lowercase: Require at least one lowercase letter
        require_digit: Require at least one digit
        require_special: Require at least one special character
        min_entropy: Minimum Shannon entropy (optional)

    Returns:
        str: The validated password

    Raises:
        ValueError: If password doesn't meet requirements

    Example:
        >>> validate_password_strength("P@ssw0rd!")
        'P@ssw0rd!'
        >>> validate_password_strength("weak")
        Traceback (most recent call last):
        ...
        ValueError: Password must be at least 8 characters long
    """
    if not v:
        raise ValueError("Password is required")

    # Check minimum length
    if len(v) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters long")

    errors = []

    # Check uppercase requirement
    if require_uppercase and not re.search(r"[A-Z]", v):
        errors.append("at least one uppercase letter")

    # Check lowercase requirement
    if require_lowercase and not re.search(r"[a-z]", v):
        errors.append("at least one lowercase letter")

    # Check digit requirement
    if require_digit and not re.search(r"\d", v):
        errors.append("at least one digit")

    # Check special character requirement
    if require_special and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", v):
        errors.append("at least one special character")

    # Check entropy requirement
    if min_entropy is not None:
        entropy = calculate_entropy(v)
        if entropy < min_entropy:
            errors.append(
                f"higher complexity (entropy: {entropy:.2f}, required: {min_entropy:.2f})"
            )

    if errors:
        raise ValueError(f"Password must contain {', '.join(errors)}")

    return v


def validate_api_key_format(
    v: str,
    prefix: Optional[str] = None,
    min_length: int = 20,
) -> str:
    """
    Validate API key format.

    Args:
        v: The API key to validate
        prefix: Optional required prefix (e.g., "sk-", "pk_")
        min_length: Minimum key length (excluding prefix)

    Returns:
        str: The validated API key

    Raises:
        ValueError: If API key doesn't meet requirements

    Example:
        >>> validate_api_key_format("sk-" + "a" * 20, prefix="sk-")
        'sk-aaaaaaaaaaaaaaaaaaaa'
        >>> validate_api_key_format("invalid", prefix="sk-")
        Traceback (most recent call last):
        ...
        ValueError: API key must start with 'sk-'
    """
    if not v or not v.strip():
        raise ValueError("API key is required")

    # Check prefix if specified
    if prefix and not v.startswith(prefix):
        raise ValueError(f"API key must start with '{prefix}'")

    # Check minimum length (excluding prefix)
    key_without_prefix = v[len(prefix):] if prefix else v
    if len(key_without_prefix) < min_length:
        raise ValueError(
            f"API key must be at least {min_length} characters long "
            f"(excluding prefix). Got: {len(key_without_prefix)} characters"
        )

    return v


def validate_jwt_secret(v: str) -> str:
    """
    Validate JWT secret key.

    Args:
        v: The JWT secret to validate

    Returns:
        str: The validated JWT secret

    Raises:
        ValueError: If JWT secret doesn't meet requirements

    Example:
        >>> secret = "a" * 32
        >>> validate_jwt_secret(secret) == secret
        True
    """
    return validate_secret_key(v, min_length=32, field_name="JWT secret")


def validate_encryption_key(v: str) -> str:
    """
    Validate encryption key.

    Args:
        v: The encryption key to validate

    Returns:
        str: The validated encryption key

    Raises:
        ValueError: If encryption key doesn't meet requirements

    Example:
        >>> key = "a" * 32
        >>> validate_encryption_key(key) == key
        True
    """
    return validate_secret_key(v, min_length=32, field_name="encryption key")
