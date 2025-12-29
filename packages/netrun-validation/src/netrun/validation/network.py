"""
Network and URL validators for Netrun Systems applications.

This module provides validators for URLs, IP addresses, ports, and
database connection strings.
"""

import re
from typing import List, Optional, Union
from urllib.parse import urlparse

from .validators import validate_list_from_csv, validate_range


def validate_url(
    v: str,
    require_https: bool = False,
    allowed_schemes: Optional[List[str]] = None,
) -> str:
    """
    Validate URL format.

    Args:
        v: The URL to validate
        require_https: Whether to require HTTPS scheme
        allowed_schemes: Optional list of allowed schemes

    Returns:
        str: The validated URL

    Raises:
        ValueError: If URL is invalid or doesn't meet requirements

    Example:
        >>> validate_url("https://example.com")
        'https://example.com'
        >>> validate_url("http://example.com", require_https=True)
        Traceback (most recent call last):
        ...
        ValueError: URL must use HTTPS scheme. Got: http
    """
    if not v or not v.strip():
        raise ValueError("URL is required")

    try:
        parsed = urlparse(v)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    if not parsed.scheme:
        raise ValueError("URL must include a scheme (e.g., https://)")

    if not parsed.netloc:
        raise ValueError("URL must include a hostname")

    # Check HTTPS requirement
    if require_https and parsed.scheme != "https":
        raise ValueError(f"URL must use HTTPS scheme. Got: {parsed.scheme}")

    # Check allowed schemes
    if allowed_schemes and parsed.scheme not in allowed_schemes:
        raise ValueError(
            f"URL scheme must be one of: {', '.join(allowed_schemes)}. "
            f"Got: {parsed.scheme}"
        )

    return v


def validate_database_url(
    v: str,
    allowed_schemes: Optional[List[str]] = None,
) -> str:
    """
    Validate database connection URL.

    Args:
        v: The database URL to validate
        allowed_schemes: Optional list of allowed database schemes

    Returns:
        str: The validated database URL

    Raises:
        ValueError: If database URL is invalid

    Example:
        >>> validate_database_url("postgresql://user:pass@localhost:5432/db")
        'postgresql://user:pass@localhost:5432/db'
        >>> validate_database_url("invalid://url")
        Traceback (most recent call last):
        ...
        ValueError: Database URL scheme must be one of: postgresql, mysql, sqlite, mssql, mongodb. Got: invalid
    """
    if not v or not v.strip():
        raise ValueError("Database URL is required")

    if allowed_schemes is None:
        allowed_schemes = ["postgresql", "mysql", "sqlite", "mssql", "mongodb"]

    # Add common variants
    extended_schemes = []
    for scheme in allowed_schemes:
        extended_schemes.append(scheme)
        # Add common variants (postgresql+asyncpg, etc.)
        extended_schemes.append(f"{scheme}+asyncpg")
        extended_schemes.append(f"{scheme}+psycopg2")
        extended_schemes.append(f"{scheme}+pymysql")

    try:
        parsed = urlparse(v)
    except Exception as e:
        raise ValueError(f"Invalid database URL format: {e}")

    if not parsed.scheme:
        raise ValueError("Database URL must include a scheme (e.g., postgresql://)")

    # Extract base scheme (postgresql from postgresql+asyncpg)
    base_scheme = parsed.scheme.split("+")[0]

    if base_scheme not in allowed_schemes and parsed.scheme not in extended_schemes:
        raise ValueError(
            f"Database URL scheme must be one of: {', '.join(allowed_schemes)}. "
            f"Got: {parsed.scheme}"
        )

    return v


def validate_redis_url(v: str) -> str:
    """
    Validate Redis connection URL.

    Args:
        v: The Redis URL to validate

    Returns:
        str: The validated Redis URL

    Raises:
        ValueError: If Redis URL is invalid

    Example:
        >>> validate_redis_url("redis://localhost:6379/0")
        'redis://localhost:6379/0'
        >>> validate_redis_url("rediss://localhost:6380/1")
        'rediss://localhost:6380/1'
    """
    return validate_url(v, allowed_schemes=["redis", "rediss"])


def validate_ip_address(v: str) -> str:
    """
    Validate IPv4 or IPv6 address.

    Args:
        v: The IP address to validate

    Returns:
        str: The validated IP address

    Raises:
        ValueError: If IP address is invalid

    Example:
        >>> validate_ip_address("192.168.1.1")
        '192.168.1.1'
        >>> validate_ip_address("::1")
        '::1'
        >>> validate_ip_address("invalid")
        Traceback (most recent call last):
        ...
        ValueError: Invalid IP address format
    """
    if not v or not v.strip():
        raise ValueError("IP address is required")

    # IPv4 pattern
    ipv4_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    # IPv6 pattern (simplified)
    ipv6_pattern = r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$"

    if re.match(ipv4_pattern, v) or re.match(ipv6_pattern, v):
        return v

    raise ValueError("Invalid IP address format")


def validate_port(
    v: int,
    min_port: int = 1,
    max_port: int = 65535,
) -> int:
    """
    Validate network port number.

    Args:
        v: The port number to validate
        min_port: Minimum allowed port (default: 1)
        max_port: Maximum allowed port (default: 65535)

    Returns:
        int: The validated port number

    Raises:
        ValueError: If port is outside valid range

    Example:
        >>> validate_port(8080)
        8080
        >>> validate_port(80)
        80
        >>> validate_port(70000)
        Traceback (most recent call last):
        ...
        ValueError: port must be at most 65535. Got: 70000
    """
    return int(validate_range(v, min_port, max_port, "port"))


def validate_cors_origins(v: Union[str, List[str]]) -> List[str]:
    """
    Validate CORS origins list.

    Args:
        v: Either a comma-separated string or a list of origins

    Returns:
        List[str]: List of validated origin URLs

    Raises:
        ValueError: If any origin is invalid

    Example:
        >>> validate_cors_origins("http://localhost:3000,https://example.com")
        ['http://localhost:3000', 'https://example.com']
        >>> validate_cors_origins(["http://localhost:3000"])
        ['http://localhost:3000']
    """
    # Convert CSV string to list if needed
    origins = validate_list_from_csv(v)

    # Special case: wildcard
    if origins == ["*"]:
        return origins

    # Validate each origin
    validated_origins = []
    for origin in origins:
        if origin == "*":
            validated_origins.append(origin)
        else:
            # Validate as URL
            validated_origins.append(validate_url(origin))

    return validated_origins


def validate_hostname(v: str) -> str:
    """
    Validate hostname format.

    Args:
        v: The hostname to validate

    Returns:
        str: The validated hostname

    Raises:
        ValueError: If hostname is invalid

    Example:
        >>> validate_hostname("localhost")
        'localhost'
        >>> validate_hostname("example.com")
        'example.com'
        >>> validate_hostname("sub.example.com")
        'sub.example.com'
    """
    if not v or not v.strip():
        raise ValueError("Hostname is required")

    # Hostname pattern (simplified)
    hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"

    if not re.match(hostname_pattern, v):
        raise ValueError(f"Invalid hostname format: {v}")

    return v
