"""
Validation decorators for function inputs and outputs.

This module provides decorators for validating function inputs and
sanitizing outputs (e.g., removing sensitive fields).
"""

from functools import wraps
from typing import Any, Callable, List, Dict, TypeVar, Optional

F = TypeVar("F", bound=Callable[..., Any])


def validate_input(*validators: Callable[[Any], Any]) -> Callable[[F], F]:
    """
    Decorator to validate function inputs using provided validators.

    Args:
        *validators: Validator functions to apply to arguments

    Returns:
        Decorated function with input validation

    Example:
        >>> from netrun.validation import validate_input, validate_non_empty
        >>> @validate_input(validate_non_empty)
        ... def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>> greet("Alice")
        'Hello, Alice!'
        >>> greet("")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: value cannot be empty
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate positional arguments
            validated_args = []
            for i, arg in enumerate(args):
                if i < len(validators):
                    validated_args.append(validators[i](arg))
                else:
                    validated_args.append(arg)

            return func(*validated_args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def sanitize_output(
    fields: List[str],
    replacement: str = "***REDACTED***",
) -> Callable[[F], F]:
    """
    Decorator to sanitize function output by removing/masking sensitive fields.

    Args:
        fields: List of field names to sanitize
        replacement: Replacement value for sensitive fields

    Returns:
        Decorated function with output sanitization

    Example:
        >>> from netrun.validation import sanitize_output
        >>> @sanitize_output(["password", "secret"])
        ... def get_user() -> dict:
        ...     return {"name": "Alice", "password": "secret123", "email": "alice@example.com"}
        >>> result = get_user()
        >>> result["password"]
        '***REDACTED***'
        >>> result["name"]
        'Alice'
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Sanitize dict output
            if isinstance(result, dict):
                return _sanitize_dict(result, fields, replacement)

            # Sanitize list of dicts
            elif isinstance(result, list):
                return [
                    _sanitize_dict(item, fields, replacement)
                    if isinstance(item, dict)
                    else item
                    for item in result
                ]

            return result

        return wrapper  # type: ignore

    return decorator


def _sanitize_dict(
    data: Dict[str, Any],
    fields: List[str],
    replacement: str,
) -> Dict[str, Any]:
    """
    Sanitize a dictionary by replacing sensitive field values.

    Args:
        data: Dictionary to sanitize
        fields: List of field names to sanitize
        replacement: Replacement value for sensitive fields

    Returns:
        Sanitized dictionary (new copy)
    """
    sanitized = data.copy()

    for field in fields:
        if field in sanitized:
            sanitized[field] = replacement

    return sanitized


def validate_non_null(*arg_names: str) -> Callable[[F], F]:
    """
    Decorator to validate that specified arguments are not None.

    Args:
        *arg_names: Names of keyword arguments to validate

    Returns:
        Decorated function with non-null validation

    Example:
        >>> from netrun.validation import validate_non_null
        >>> @validate_non_null("name", "email")
        ... def create_user(name: str, email: str, age: int = None) -> dict:
        ...     return {"name": name, "email": email, "age": age}
        >>> create_user(name="Alice", email="alice@example.com")
        {'name': 'Alice', 'email': 'alice@example.com', 'age': None}
        >>> create_user(name=None, email="alice@example.com")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Argument 'name' cannot be None
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg_name in arg_names:
                if arg_name in kwargs and kwargs[arg_name] is None:
                    raise ValueError(f"Argument '{arg_name}' cannot be None")

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def validate_type(**type_specs: type) -> Callable[[F], F]:
    """
    Decorator to validate that arguments match expected types.

    Args:
        **type_specs: Mapping of argument names to expected types

    Returns:
        Decorated function with type validation

    Example:
        >>> from netrun.validation import validate_type
        >>> @validate_type(name=str, age=int)
        ... def create_user(name: str, age: int) -> dict:
        ...     return {"name": name, "age": age}
        >>> create_user(name="Alice", age=30)
        {'name': 'Alice', 'age': 30}
        >>> create_user(name="Alice", age="30")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        TypeError: Argument 'age' must be of type <class 'int'>, got <class 'str'>
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg_name, expected_type in type_specs.items():
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if value is not None and not isinstance(value, expected_type):
                        raise TypeError(
                            f"Argument '{arg_name}' must be of type {expected_type}, "
                            f"got {type(value)}"
                        )

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def validate_range_decorator(
    arg_name: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> Callable[[F], F]:
    """
    Decorator to validate that an argument is within a specified range.

    Args:
        arg_name: Name of the argument to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)

    Returns:
        Decorated function with range validation

    Example:
        >>> from netrun.validation import validate_range_decorator
        >>> @validate_range_decorator("temperature", min_val=0.0, max_val=2.0)
        ... def set_temperature(temperature: float) -> float:
        ...     return temperature
        >>> set_temperature(temperature=0.7)
        0.7
        >>> set_temperature(temperature=3.0)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Argument 'temperature' must be at most 2.0. Got: 3.0
    """
    from .validators import validate_range

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if arg_name in kwargs:
                value = kwargs[arg_name]
                kwargs[arg_name] = validate_range(value, min_val, max_val, arg_name)

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
