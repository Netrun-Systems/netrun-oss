"""
Intirkast Integration Template
Content creator SaaS platform logging

Usage:
1. Copy to Intirkast/src/backend/app/core/logging.py
2. Import and call configure_intirkast_logging() in main.py
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.context import set_context

def configure_intirkast_logging():
    """Configure logging for Intirkast content platform."""
    configure_logging(
        app_name="intirkast",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )

def log_content_event(content_id: str, action: str, creator_id: str = None):
    """Log content lifecycle events."""
    logger = get_logger("intirkast.content")
    logger.info(f"Content {action}", extra={
        "content_id": content_id,
        "action": action,
        "creator_id": creator_id,
        "event_type": "content_lifecycle",
    })

def log_video_generation(video_id: str, status: str, duration_ms: float = None):
    """Log video generation progress."""
    logger = get_logger("intirkast.video")
    logger.info(f"Video generation: {status}", extra={
        "video_id": video_id,
        "status": status,
        "duration_ms": duration_ms,
        "event_type": "video_generation",
    })

def setup_fastapi_app(app):
    add_logging_middleware(app)
