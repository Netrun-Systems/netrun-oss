"""Pytest configuration and fixtures for netrun-cors tests."""

import pytest
from fastapi import FastAPI


@pytest.fixture
def app():
    """Create a minimal FastAPI application for testing."""
    return FastAPI(title="Test App")


@pytest.fixture
def test_origins():
    """Standard test origins for testing."""
    return [
        "https://app.example.com",
        "https://www.example.com",
    ]


@pytest.fixture
def oauth_platforms():
    """Standard OAuth platforms for testing."""
    return ["google", "twitter", "linkedin"]
