"""
Generic Pydantic validators for common validation patterns.

This module provides reusable validators that can be used across Netrun Systems
portfolio applications to ensure consistent validation behavior.
"""

from typing import Any, List, Optional, Union


def validate_enum_value(
    v: Any, allowed: List[str], field_name: str, case_sensitive: bool = False
) -> str:
    """
    Validate that a value is in a list of allowed values.

    Args:
        v: The value to validate
        allowed: List of allowed values
        field_name: Name of the field being validated (for error messages)
        case_sensitive: Whether comparison should be case-sensitive

    Returns:
        str: The validated value (normalized to match allowed values)

    Raises:
        ValueError: If value is not in allowed list

    Example:
        >>> validate_enum_value("production", ["dev", "staging", "production"], "environment")
        'production'
        >>> validate_enum_value("PRODUCTION", ["dev", "staging", "production"], "environment", case_sensitive=False)
        'production'
    """
    if not v:
        raise ValueError(f"{field_name} cannot be empty")

    str_value = str(v).strip()

    if case_sensitive:
        if str_value not in allowed:
            raise ValueError(
                f"{field_name} must be one of: {', '.join(allowed)}. Got: {str_value}"
            )
        return str_value
    else:
        # Case-insensitive comparison
        lower_allowed = {val.lower(): val for val in allowed}
        lower_value = str_value.lower()

        if lower_value not in lower_allowed:
            raise ValueError(
                f"{field_name} must be one of: {', '.join(allowed)}. Got: {str_value}"
            )
        return lower_allowed[lower_value]


def validate_range(
    v: Union[int, float],
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
    field_name: str = "value",
) -> Union[int, float]:
    """
    Validate that a numeric value is within a specified range.

    Args:
        v: The value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        field_name: Name of the field being validated (for error messages)

    Returns:
        Union[int, float]: The validated value

    Raises:
        ValueError: If value is outside the allowed range

    Example:
        >>> validate_range(0.7, 0.0, 2.0, "temperature")
        0.7
        >>> validate_range(5, min_val=1, field_name="pool_size")
        5
    """
    if min_val is not None and v < min_val:
        raise ValueError(f"{field_name} must be at least {min_val}. Got: {v}")

    if max_val is not None and v > max_val:
        raise ValueError(f"{field_name} must be at most {max_val}. Got: {v}")

    return v


def validate_non_empty(v: Any, field_name: str = "value") -> str:
    """
    Validate that a string value is not empty.

    Args:
        v: The value to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        str: The validated value (stripped of whitespace)

    Raises:
        ValueError: If value is empty or only whitespace

    Example:
        >>> validate_non_empty("hello", "name")
        'hello'
        >>> validate_non_empty("  world  ", "name")
        'world'
    """
    if v is None:
        raise ValueError(f"{field_name} is required")

    str_value = str(v).strip()

    if not str_value:
        raise ValueError(f"{field_name} cannot be empty")

    return str_value


def validate_list_from_csv(v: Union[str, List[str]]) -> List[str]:
    """
    Convert a comma-separated string to a list of strings.

    Args:
        v: Either a CSV string or an existing list

    Returns:
        List[str]: List of string values (stripped of whitespace)

    Example:
        >>> validate_list_from_csv("value1, value2, value3")
        ['value1', 'value2', 'value3']
        >>> validate_list_from_csv(["value1", "value2"])
        ['value1', 'value2']
    """
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v


def validate_positive_int(v: int, field_name: str = "value") -> int:
    """
    Validate that an integer is positive (greater than 0).

    Args:
        v: The value to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        int: The validated value

    Raises:
        ValueError: If value is not positive

    Example:
        >>> validate_positive_int(10, "pool_size")
        10
    """
    if v < 1:
        raise ValueError(f"{field_name} must be at least 1. Got: {v}")
    return v


def validate_non_negative_int(v: int, field_name: str = "value") -> int:
    """
    Validate that an integer is non-negative (>= 0).

    Args:
        v: The value to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        int: The validated value

    Raises:
        ValueError: If value is negative

    Example:
        >>> validate_non_negative_int(0, "retry_count")
        0
    """
    if v < 0:
        raise ValueError(f"{field_name} must be at least 0. Got: {v}")
    return v


def validate_percentage(v: Union[int, float], field_name: str = "value") -> float:
    """
    Validate that a value is a valid percentage (0.0 to 100.0).

    Args:
        v: The value to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        float: The validated value

    Raises:
        ValueError: If value is outside 0-100 range

    Example:
        >>> validate_percentage(75.5, "completion")
        75.5
    """
    return float(validate_range(v, 0.0, 100.0, field_name))
