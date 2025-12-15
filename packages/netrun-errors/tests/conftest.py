"""
Pytest configuration and fixtures for netrun-errors tests.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from netrun_errors import install_exception_handlers, install_error_logging_middleware


@pytest.fixture
def app() -> FastAPI:
    """
    Create a FastAPI application with exception handlers installed.

    Returns:
        FastAPI application instance
    """
    application = FastAPI()
    install_exception_handlers(application)
    install_error_logging_middleware(application)
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """
    Create a test client for the FastAPI application.

    Args:
        app: FastAPI application fixture

    Returns:
        TestClient instance
    """
    return TestClient(app)
