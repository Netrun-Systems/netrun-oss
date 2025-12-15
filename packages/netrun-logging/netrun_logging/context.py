"""
Log Context Management
Application and request context for log enrichment
"""

import contextvars
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class LogContext:
    """Application logging context with metadata."""
    app_name: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

# Thread-safe context storage
_log_context: contextvars.ContextVar[LogContext] = contextvars.ContextVar(
    "log_context", default=LogContext()
)

def get_context() -> LogContext:
    """Get the current log context."""
    return _log_context.get()

def set_context(
    app_name: Optional[str] = None,
    environment: Optional[str] = None,
    version: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """
    Set log context values.

    Args:
        app_name: Application name
        environment: Environment (dev, staging, prod)
        version: Application version
        user_id: Current user ID
        tenant_id: Current tenant ID
        **extra: Additional context fields
    """
    ctx = _log_context.get()
    if app_name is not None:
        ctx.app_name = app_name
    if environment is not None:
        ctx.environment = environment
    if version is not None:
        ctx.version = version
    if user_id is not None:
        ctx.user_id = user_id
    if tenant_id is not None:
        ctx.tenant_id = tenant_id
    ctx.extra.update(extra)
    _log_context.set(ctx)

def clear_context() -> None:
    """Clear all log context values."""
    _log_context.set(LogContext())
