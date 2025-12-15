"""
Netrun CRM Integration Template
CRM platform with lead scoring and email assistant logging

Usage:
1. Copy to netrun-crm/backend/app/core/logging.py
2. Import and call configure_crm_logging() in main.py
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.correlation import correlation_id_context

def configure_crm_logging():
    """Configure logging for Netrun CRM."""
    configure_logging(
        app_name="netrun-crm",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )

def log_lead_scoring_event(lead_id: str, score: float, factors: dict):
    """Log lead scoring event with structured data."""
    logger = get_logger("crm.lead_scoring")
    logger.info("Lead scored", extra={
        "lead_id": lead_id,
        "score": score,
        "factors": factors,
        "event_type": "lead_scoring",
    })

def log_email_assistant_event(contact_id: str, action: str, email_subject: str = None):
    """Log email assistant activity."""
    logger = get_logger("crm.email_assistant")
    logger.info(f"Email assistant: {action}", extra={
        "contact_id": contact_id,
        "action": action,
        "email_subject": email_subject,
        "event_type": "email_assistant",
    })

# FastAPI setup
def setup_fastapi_app(app):
    add_logging_middleware(app)
