"""
GhostGrid Integration Template
FSO network simulation with telemetry logging

Usage:
1. Copy to GhostGrid Optical Network/ghostgrid-sim/src/core/logging.py
2. Import and call configure_ghostgrid_logging() in main.py
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

def configure_ghostgrid_logging():
    """Configure logging for GhostGrid FSO simulation."""
    configure_logging(
        app_name="ghostgrid",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )

def log_node_telemetry(node_id: str, signal_strength: float, link_quality: float):
    """Log FSO node telemetry data."""
    logger = get_logger("ghostgrid.telemetry")
    logger.info("Node telemetry", extra={
        "node_id": node_id,
        "signal_strength_dbm": signal_strength,
        "link_quality_percent": link_quality,
        "event_type": "node_telemetry",
    })

def log_beam_alignment(source_node: str, target_node: str, alignment_error_mrad: float):
    """Log beam steering alignment events."""
    logger = get_logger("ghostgrid.alignment")
    logger.info("Beam alignment", extra={
        "source_node": source_node,
        "target_node": target_node,
        "alignment_error_mrad": alignment_error_mrad,
        "event_type": "beam_alignment",
    })

def log_network_event(event_type: str, affected_nodes: list, severity: str):
    """Log network-wide events."""
    logger = get_logger("ghostgrid.network")
    logger.info(f"Network event: {event_type}", extra={
        "event_type": event_type,
        "affected_nodes": affected_nodes,
        "severity": severity,
    })

def setup_fastapi_app(app):
    add_logging_middleware(app)
