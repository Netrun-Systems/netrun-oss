"""
Netrun Site Integration Template
Marketing website API logging (Next.js API routes)

Usage:
1. Copy logging functions to NetrunnewSite/lib/logging.ts (adapt to TypeScript)
2. Or use in Python backend if applicable
"""

import os
from netrun_logging import configure_logging, get_logger

def configure_site_logging():
    """Configure logging for Netrun marketing site."""
    configure_logging(
        app_name="netrun-site",
        environment=os.getenv("ENVIRONMENT", "production"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

def log_page_view(page: str, referrer: str = None, user_agent: str = None):
    """Log page view analytics."""
    logger = get_logger("site.analytics")
    logger.info("Page view", extra={
        "page": page,
        "referrer": referrer,
        "user_agent": user_agent,
        "event_type": "page_view",
    })

def log_contact_form(email: str, subject: str, source_page: str):
    """Log contact form submissions."""
    logger = get_logger("site.contact")
    logger.info("Contact form submitted", extra={
        "email_domain": email.split("@")[-1] if "@" in email else "unknown",
        "subject": subject,
        "source_page": source_page,
        "event_type": "contact_form",
    })
