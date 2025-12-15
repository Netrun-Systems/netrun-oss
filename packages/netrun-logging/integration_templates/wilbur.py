"""
Wilbur Integration Template
Charlotte AI bridge service logging

Usage:
1. Copy to wilbur/app/core/logging.py
2. Import and call configure_wilbur_logging() in main.py
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.correlation import correlation_id_context

def configure_wilbur_logging():
    """Configure logging for Wilbur Charlotte bridge."""
    configure_logging(
        app_name="wilbur",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "DEBUG"),  # Debug for AI interactions
    )

def log_charlotte_interaction(session_id: str, action: str, agent: str = None):
    """Log Charlotte AI interactions."""
    logger = get_logger("wilbur.charlotte")
    logger.info(f"Charlotte: {action}", extra={
        "session_id": session_id,
        "action": action,
        "agent": agent,
        "event_type": "charlotte_interaction",
    })

def log_agent_delegation(source_agent: str, target_agent: str, task: str):
    """Log agent-to-agent delegation."""
    logger = get_logger("wilbur.delegation")
    logger.info("Agent delegation", extra={
        "source_agent": source_agent,
        "target_agent": target_agent,
        "task": task,
        "event_type": "agent_delegation",
    })

def setup_fastapi_app(app):
    add_logging_middleware(app)
