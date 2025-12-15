"""
DungeonMaster Integration Template
Game server with session and combat logging

Usage:
1. Copy to DungeonMaster/server/core/logging.py
2. Import and call configure_dm_logging() in main.py
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware

def configure_dm_logging():
    """Configure logging for DungeonMaster game server."""
    configure_logging(
        app_name="dungeonmaster",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

def log_game_session(session_id: str, action: str, player_count: int = None):
    """Log game session events."""
    logger = get_logger("dm.session")
    logger.info(f"Game session: {action}", extra={
        "session_id": session_id,
        "action": action,
        "player_count": player_count,
        "event_type": "game_session",
    })

def log_combat_event(session_id: str, attacker: str, target: str, damage: int):
    """Log combat events for replay/analytics."""
    logger = get_logger("dm.combat")
    logger.info("Combat action", extra={
        "session_id": session_id,
        "attacker": attacker,
        "target": target,
        "damage": damage,
        "event_type": "combat",
    })

def setup_fastapi_app(app):
    add_logging_middleware(app)
