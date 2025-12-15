"""
EISCORE Integration Template
Unreal Engine project with Python scripting logging

Usage:
1. Copy to EISCORE 5.6/Content/Python/core/logging.py
2. Import in Unreal Python scripts
"""

import os
from netrun_logging import configure_logging, get_logger

def configure_eiscore_logging():
    """Configure logging for EISCORE Unreal project."""
    configure_logging(
        app_name="eiscore",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    )

def log_game_event(event_type: str, actor: str = None, location: tuple = None):
    """Log game events from Unreal."""
    logger = get_logger("eiscore.game")
    logger.info(f"Game event: {event_type}", extra={
        "event_type": event_type,
        "actor": actor,
        "location": location,
    })

def log_ai_decision(agent_id: str, decision: str, confidence: float):
    """Log AI agent decisions."""
    logger = get_logger("eiscore.ai")
    logger.info("AI decision", extra={
        "agent_id": agent_id,
        "decision": decision,
        "confidence": confidence,
        "event_type": "ai_decision",
    })

def log_performance_metric(metric_name: str, value: float, unit: str):
    """Log performance metrics for profiling."""
    logger = get_logger("eiscore.performance")
    logger.debug("Performance metric", extra={
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "event_type": "performance",
    })
