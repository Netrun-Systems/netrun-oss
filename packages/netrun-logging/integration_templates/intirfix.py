"""
Intirfix Integration Template
Service dispatch platform logging

Usage:
1. Copy to Intirfix/backend/app/core/logging.py
2. Import and call configure_intirfix_logging() in main.py
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

def configure_intirfix_logging():
    """Configure logging for Intirfix service dispatch."""
    configure_logging(
        app_name="intirfix",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

def log_service_request(request_id: str, service_type: str, customer_id: str):
    """Log new service requests."""
    logger = get_logger("intirfix.requests")
    logger.info("Service request created", extra={
        "request_id": request_id,
        "service_type": service_type,
        "customer_id": customer_id,
        "event_type": "service_request",
    })

def log_technician_dispatch(request_id: str, technician_id: str, eta_minutes: int):
    """Log technician dispatches."""
    logger = get_logger("intirfix.dispatch")
    logger.info("Technician dispatched", extra={
        "request_id": request_id,
        "technician_id": technician_id,
        "eta_minutes": eta_minutes,
        "event_type": "technician_dispatch",
    })

def setup_fastapi_app(app):
    add_logging_middleware(app)
