"""
Intirkon Integration Template
Multi-tenant Azure BI platform with cross-tenant logging

Usage:
1. Copy to intirkon/backend/app/core/logging_config.py
2. Import and call configure_intirkon_logging() in main.py
3. Remove existing logging setup
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.context import set_context

def configure_intirkon_logging():
    """Configure logging for Intirkon multi-tenant platform."""
    configure_logging(
        app_name="intirkon",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )

def setup_tenant_context(tenant_id: str, user_id: str = None):
    """Set tenant context for all subsequent logs."""
    set_context(
        tenant_id=tenant_id,
        user_id=user_id,
        app_name="intirkon",
    )

# FastAPI integration
def setup_fastapi_app(app):
    """Add logging middleware to FastAPI app."""
    from fastapi import FastAPI
    add_logging_middleware(app)

# Example usage in main.py:
# from app.core.logging_config import configure_intirkon_logging, setup_fastapi_app
# configure_intirkon_logging()
# app = FastAPI()
# setup_fastapi_app(app)
