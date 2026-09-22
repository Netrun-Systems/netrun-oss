"""
Safe HTTP error helper — never echo raw exception text to clients.

Upstream exceptions can embed secret bytes. For example, an ``httpx``
``ValueError`` raised on an ``x-goog-api-key`` header rejection carries the raw
API key in its message. Returning ``f"...: {e}"`` / ``f"...: {str(e)[:200]}"``
in an ``HTTPException`` detail leaks those secrets to anonymous callers over
public endpoints — the same class as the 2026-06-10 Gemini-key incident.

This helper centralizes the safe pattern: log the full exception server-side
with a short correlation id, and return a generic detail carrying only that id.

Back-ported (2026-09-22, B1) from ``wilbur:charlotte/api/_safe_errors.py`` where
it has 21 production usages. Generalized here as the public
``netrun.errors.safe_http_error`` surface so applications stop rolling their own
and getting it wrong.

Usage::

    from netrun.errors import safe_http_error

    try:
        ...
    except HTTPException:
        raise                       # preserve explicit client-validation errors
    except Exception as exc:
        raise safe_http_error(502, "Embedding analysis failed", exc)
"""

import logging
import uuid

from fastapi import HTTPException

# Optional netrun-logging integration for correlation-id consistency with the
# rest of the package's handlers/middleware. Falls back to stdlib logging.
_use_structlog = False
_structlog_logger = None
try:  # pragma: no cover - exercised only when netrun-logging is installed
    from netrun_logging import get_logger as _get_structlog_logger

    _structlog_logger = _get_structlog_logger(__name__)
    _use_structlog = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

__all__ = ["safe_http_error"]


def safe_http_error(
    status: int,
    public_prefix: str,
    exc: Exception,
) -> HTTPException:
    """Build an ``HTTPException`` that never leaks raw exception text.

    The full exception (type + traceback) is logged server-side with a fresh
    12-hex correlation id. The returned client-facing detail is
    ``"<public_prefix> (ref: <id>)"`` only — it NEVER contains ``str(exc)`` or
    any substring of it, so provider secrets embedded in upstream exception
    messages cannot escape to the caller.

    Args:
        status: HTTP status code for the returned ``HTTPException``.
        public_prefix: Safe, human-readable message shown to the client. MUST
            NOT be built from ``str(exc)``.
        exc: The caught exception. Logged in full server-side; never echoed.

    Returns:
        An ``HTTPException`` with a leak-free ``detail``. The caller ``raise``\\ s it.
    """
    ref = uuid.uuid4().hex[:12]
    message = f"{public_prefix} [{ref}]: {type(exc).__name__}"
    if _use_structlog and _structlog_logger is not None:
        # structlog path: pass the exception for structured capture, never the
        # rendered string into the public detail.
        _structlog_logger.error(message, correlation_id=ref, exc_info=exc)
    else:
        logger.exception("%s", message)
    return HTTPException(status_code=status, detail=f"{public_prefix} (ref: {ref})")
