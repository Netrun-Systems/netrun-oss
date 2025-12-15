"""Pytest configuration and fixtures for netrun-env tests."""

import tempfile
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_env_file(temp_dir):
    """Create a sample .env file."""
    env_file = temp_dir / ".env"
    content = """
# Database configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
DATABASE_POOL_SIZE=10

# Security
JWT_SECRET_KEY=this-is-a-very-long-secret-key-that-meets-minimum-requirements-32-chars
JWT_ALGORITHM=RS256

# API
API_BASE_URL=https://api.example.com
API_TIMEOUT=30
DEBUG=false

# Email
ADMIN_EMAIL=admin@example.com
"""
    env_file.write_text(content.strip())
    return env_file


@pytest.fixture
def sample_env_example_file(temp_dir):
    """Create a sample .env.example file."""
    env_file = temp_dir / ".env.example"
    content = """
# Database configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
DATABASE_POOL_SIZE=10

# Security
JWT_SECRET_KEY=[SECRET_KEY_HERE]
JWT_ALGORITHM=RS256

# API
API_BASE_URL=https://api.example.com
API_TIMEOUT=30
DEBUG=false

# Email
ADMIN_EMAIL=admin@example.com
"""
    env_file.write_text(content.strip())
    return env_file


@pytest.fixture
def sample_schema():
    """Create a sample schema dictionary."""
    return {
        "$schema": "https://netrunsystems.com/env-schema/v1",
        "version": "1.0",
        "variables": {
            "DATABASE_URL": {
                "type": "url",
                "required": True,
                "protocols": ["postgresql", "postgresql+asyncpg"]
            },
            "DATABASE_POOL_SIZE": {
                "type": "integer",
                "required": True,
                "min": 1,
                "max": 100
            },
            "JWT_SECRET_KEY": {
                "type": "secret",
                "required": True,
                "minLength": 32
            },
            "JWT_ALGORITHM": {
                "type": "string",
                "required": True
            },
            "API_BASE_URL": {
                "type": "url",
                "required": True,
                "protocols": ["https"]
            },
            "API_TIMEOUT": {
                "type": "integer",
                "required": True,
                "min": 0
            },
            "DEBUG": {
                "type": "boolean",
                "required": True
            },
            "ADMIN_EMAIL": {
                "type": "email",
                "required": True
            }
        }
    }


@pytest.fixture
def sample_variables():
    """Create a sample variables dictionary."""
    return {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/mydb",
        "DATABASE_POOL_SIZE": "10",
        "JWT_SECRET_KEY": "this-is-a-very-long-secret-key-that-meets-minimum-requirements-32-chars",
        "JWT_ALGORITHM": "RS256",
        "API_BASE_URL": "https://api.example.com",
        "API_TIMEOUT": "30",
        "DEBUG": "false",
        "ADMIN_EMAIL": "admin@example.com"
    }
