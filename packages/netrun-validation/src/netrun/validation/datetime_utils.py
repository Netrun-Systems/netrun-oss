"""
Date and time validators for Netrun Systems applications.

This module provides validators for timestamps, dates, timezones, and
date range validation.
"""

from datetime import datetime, timezone
from typing import Optional, Union
import re


def validate_iso_timestamp(v: Union[str, datetime]) -> datetime:
    """
    Validate ISO 8601 timestamp format.

    Args:
        v: The timestamp to validate (string or datetime object)

    Returns:
        datetime: The validated datetime object

    Raises:
        ValueError: If timestamp is invalid

    Example:
        >>> dt = validate_iso_timestamp("2025-01-15T10:30:00Z")
        >>> isinstance(dt, datetime)
        True
        >>> dt = validate_iso_timestamp("2025-01-15T10:30:00+00:00")
        >>> isinstance(dt, datetime)
        True
    """
    if isinstance(v, datetime):
        return v

    if not v or not isinstance(v, str):
        raise ValueError("Timestamp is required")

    try:
        # Try parsing ISO 8601 format
        if v.endswith("Z"):
            # Replace Z with +00:00 for Python's fromisoformat
            v = v[:-1] + "+00:00"

        return datetime.fromisoformat(v)
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 timestamp format: {v}. Error: {e}")


def validate_timezone(v: str) -> str:
    """
    Validate timezone string format.

    Args:
        v: The timezone string to validate (e.g., "UTC", "America/New_York")

    Returns:
        str: The validated timezone string

    Raises:
        ValueError: If timezone is invalid

    Example:
        >>> validate_timezone("UTC")
        'UTC'
        >>> validate_timezone("America/New_York")
        'America/New_York'
    """
    if not v or not v.strip():
        raise ValueError("Timezone is required")

    # Common timezone pattern (Area/Location or abbreviation)
    # Pattern allows Area/Location format like "America/New_York" or abbreviations like "UTC"
    tz_pattern = r"^([A-Z][a-zA-Z]+/[A-Z][a-zA-Z_]+|UTC|GMT|[A-Z]{3,4})$"

    if not re.match(tz_pattern, v):
        raise ValueError(
            f"Invalid timezone format. Expected format: 'Area/Location' or 'UTC'. Got: {v}"
        )

    return v


def validate_date_range(
    v: datetime,
    min_date: Optional[datetime] = None,
    max_date: Optional[datetime] = None,
    field_name: str = "date",
) -> datetime:
    """
    Validate that a datetime is within a specified range.

    Args:
        v: The datetime to validate
        min_date: Minimum allowed date (inclusive)
        max_date: Maximum allowed date (inclusive)
        field_name: Name of the field being validated (for error messages)

    Returns:
        datetime: The validated datetime

    Raises:
        ValueError: If datetime is outside the allowed range

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 1, 15)
        >>> min_dt = datetime(2025, 1, 1)
        >>> max_dt = datetime(2025, 12, 31)
        >>> validate_date_range(dt, min_dt, max_dt) == dt
        True
    """
    if min_date and v < min_date:
        raise ValueError(
            f"{field_name} must be after {min_date.isoformat()}. Got: {v.isoformat()}"
        )

    if max_date and v > max_date:
        raise ValueError(
            f"{field_name} must be before {max_date.isoformat()}. Got: {v.isoformat()}"
        )

    return v


def validate_future_date(
    v: datetime,
    field_name: str = "date",
) -> datetime:
    """
    Validate that a datetime is in the future.

    Args:
        v: The datetime to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        datetime: The validated datetime

    Raises:
        ValueError: If datetime is not in the future

    Example:
        >>> from datetime import datetime, timedelta
        >>> future = datetime.now(timezone.utc) + timedelta(days=1)
        >>> validate_future_date(future)  # doctest: +ELLIPSIS
        datetime.datetime(...)
    """
    now = datetime.now(timezone.utc)

    # Make v timezone-aware if it's naive
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)

    if v <= now:
        raise ValueError(
            f"{field_name} must be in the future. Got: {v.isoformat()}, "
            f"Current time: {now.isoformat()}"
        )

    return v


def validate_past_date(
    v: datetime,
    field_name: str = "date",
) -> datetime:
    """
    Validate that a datetime is in the past.

    Args:
        v: The datetime to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        datetime: The validated datetime

    Raises:
        ValueError: If datetime is not in the past

    Example:
        >>> from datetime import datetime, timedelta
        >>> past = datetime.now(timezone.utc) - timedelta(days=1)
        >>> validate_past_date(past)  # doctest: +ELLIPSIS
        datetime.datetime(...)
    """
    now = datetime.now(timezone.utc)

    # Make v timezone-aware if it's naive
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)

    if v >= now:
        raise ValueError(
            f"{field_name} must be in the past. Got: {v.isoformat()}, "
            f"Current time: {now.isoformat()}"
        )

    return v


def validate_date_not_before(
    v: datetime,
    reference_date: datetime,
    field_name: str = "date",
) -> datetime:
    """
    Validate that a datetime is not before a reference date.

    Args:
        v: The datetime to validate
        reference_date: The reference date to compare against
        field_name: Name of the field being validated (for error messages)

    Returns:
        datetime: The validated datetime

    Raises:
        ValueError: If datetime is before reference date

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 1, 15)
        >>> ref = datetime(2025, 1, 1)
        >>> validate_date_not_before(dt, ref) == dt
        True
    """
    if v < reference_date:
        raise ValueError(
            f"{field_name} cannot be before {reference_date.isoformat()}. "
            f"Got: {v.isoformat()}"
        )

    return v


def validate_unix_timestamp(v: Union[int, float]) -> int:
    """
    Validate Unix timestamp (seconds since epoch).

    Args:
        v: The Unix timestamp to validate

    Returns:
        int: The validated Unix timestamp

    Raises:
        ValueError: If timestamp is invalid

    Example:
        >>> validate_unix_timestamp(1704067200)  # 2024-01-01 00:00:00 UTC
        1704067200
    """
    if v < 0:
        raise ValueError(f"Unix timestamp must be non-negative. Got: {v}")

    # Check if timestamp is reasonable (between 1970 and 2100)
    if v > 4102444800:  # 2100-01-01 00:00:00 UTC
        raise ValueError(
            f"Unix timestamp appears to be too far in the future. Got: {v}"
        )

    return int(v)
