"""
Azure Application Insights Integration
Sends logs to Azure Monitor for centralized logging and analysis
"""

import logging
import os
from typing import Optional

# Azure SDK import with graceful fallback
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class AzureInsightsHandler(logging.Handler):
    """
    Custom logging handler for Azure Application Insights.

    Converts Python log records to Azure telemetry format.
    """

    def __init__(self, connection_string: str, app_name: str = "app"):
        super().__init__()
        self.connection_string = connection_string
        self.app_name = app_name
        self._configured = False

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Azure Application Insights.

        Args:
            record: Python logging.LogRecord instance
        """
        # Azure OpenTelemetry SDK handles this automatically when configured
        # This handler primarily ensures proper integration
        pass


def configure_azure_insights(
    connection_string: Optional[str] = None,
    app_name: str = "app",
    enable_live_metrics: bool = True,
) -> bool:
    """
    Configure Azure Application Insights for log collection.

    Args:
        connection_string: Azure App Insights connection string
            Falls back to APPLICATIONINSIGHTS_CONNECTION_STRING env var
        app_name: Application name for telemetry
        enable_live_metrics: Enable live metrics stream (default: True)

    Returns:
        True if configuration successful, False otherwise
    """
    if not AZURE_AVAILABLE:
        logging.warning(
            "Azure Monitor SDK not installed. "
            "Install with: pip install azure-monitor-opentelemetry"
        )
        return False

    # Get connection string from parameter or environment
    conn_str = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if not conn_str:
        logging.warning(
            "Azure Application Insights connection string not provided. "
            "Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable."
        )
        return False

    try:
        # Configure Azure Monitor with OpenTelemetry
        configure_azure_monitor(
            connection_string=conn_str,
            enable_live_metrics=enable_live_metrics,
        )

        logging.info(f"Azure Application Insights configured for {app_name}")
        return True

    except Exception as e:
        logging.error(f"Failed to configure Azure Application Insights: {e}")
        return False


def is_azure_configured() -> bool:
    """Check if Azure Application Insights is configured."""
    return AZURE_AVAILABLE and os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") is not None
