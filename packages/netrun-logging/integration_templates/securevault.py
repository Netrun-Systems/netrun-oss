"""
SecureVault Integration Template
Secrets management service with audit logging

Usage:
1. Copy to SecureVault/app/core/logging.py
2. Import and call configure_securevault_logging() in main.py
"""

import os
import logging
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

def configure_securevault_logging():
    """Configure logging for SecureVault secrets management."""
    configure_logging(
        app_name="securevault",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )

def log_secret_access(secret_id: str, action: str, user_id: str, success: bool):
    """Log secret access with audit trail."""
    logger = get_logger("securevault.audit")
    level = "INFO" if success else "WARNING"
    logger.log(
        getattr(logging, level),
        f"Secret {action}: {'success' if success else 'denied'}",
        extra={
            "secret_id": secret_id,
            "action": action,
            "user_id": user_id,
            "success": success,
            "event_type": "secret_access",
            "audit": True,
        }
    )

def log_encryption_event(operation: str, key_id: str, success: bool):
    """Log encryption operations."""
    logger = get_logger("securevault.crypto")
    logger.info(f"Encryption {operation}", extra={
        "operation": operation,
        "key_id": key_id,
        "success": success,
        "event_type": "encryption",
    })

def setup_fastapi_app(app):
    add_logging_middleware(app)
