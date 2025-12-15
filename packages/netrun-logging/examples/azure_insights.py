"""
Azure Application Insights Example - netrun-logging

Demonstrates Azure integration for cloud logging.
Requires: APPLICATIONINSIGHTS_CONNECTION_STRING environment variable
"""

import os
from netrun_logging import configure_logging, get_logger
from netrun_logging.integrations.azure_insights import is_azure_configured

# Check for Azure connection string
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

if not connection_string:
    print("[WARNING] APPLICATIONINSIGHTS_CONNECTION_STRING not set")
    print("    Set this environment variable to enable Azure logging")
    print("    Example: export APPLICATIONINSIGHTS_CONNECTION_STRING='InstrumentationKey=...'")
    print()

# Configure logging with Azure integration
configure_logging(
    app_name="azure-example",
    environment="production",
    log_level="INFO",
    azure_insights_connection_string=connection_string,
)

logger = get_logger(__name__)

# Log messages (will appear in Azure if configured)
logger.info("Application started with Azure integration")
logger.info("User action", extra={
    "user_id": "user-123",
    "action": "login",
    "client_ip": "10.0.0.1",
})

if is_azure_configured():
    print("[SUCCESS] Azure Application Insights configured successfully")
    print("   Logs will appear in Azure portal within 1-2 minutes")
else:
    print("[INFO] Running in local-only mode (no Azure connection)")

print("\n[SUCCESS] Azure logging example complete!")
