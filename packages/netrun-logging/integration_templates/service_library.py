"""
Service Library Integration Template
Documentation scripts and tooling logging

Usage:
1. Copy to Netrun_Service_Library_v2/scripts/logging_config.py
2. Import in documentation generation scripts
"""

import os
import logging
from netrun_logging import configure_logging, get_logger

def configure_library_logging():
    """Configure logging for Service Library scripts."""
    configure_logging(
        app_name="service-library",
        environment="development",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

def log_doc_generation(service_id: int, doc_type: str, success: bool):
    """Log documentation generation events."""
    logger = get_logger("library.docs")
    logger.info(f"Documentation generated: Service #{service_id}", extra={
        "service_id": service_id,
        "doc_type": doc_type,
        "success": success,
        "event_type": "doc_generation",
    })

def log_validation_result(file_path: str, valid: bool, errors: list = None):
    """Log validation results."""
    logger = get_logger("library.validation")
    level = "INFO" if valid else "WARNING"
    logger.log(getattr(logging, level), f"Validation: {'passed' if valid else 'failed'}", extra={
        "file_path": file_path,
        "valid": valid,
        "errors": errors or [],
        "event_type": "validation",
    })
