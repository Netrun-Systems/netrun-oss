"""
Netrun LLM - Secret redaction for exception/error paths (B6 back-port).

Upstream provider errors can embed secret bytes in their exception messages.
The 2026-06-10 incident: an ``httpx`` header-rejection raised a ``ValueError``
that carried the raw ``x-goog-api-key`` (Gemini API key); the fallback chain
stored ``str(exc)`` in its error map and it bubbled out of
``LLMFallbackChain.execute()`` to the caller.

This module centralizes the redaction of known secret shapes so they never
escape adapter exception paths. Same conceptual fix as netrun-errors'
``safe_http_error`` (audit row B1), scoped to the LLM adapter layer (row B6).

Back-ported from the redaction pattern in
``wilbur:charlotte/api/_safe_errors.py`` (which fixed the same leak class at
the FastAPI handler level), applied here at ``chain.execute()``.

Usage:
    from netrun.llm.redaction import redact_secrets, redact_exception
    safe = redact_secrets(str(exc))          # scrub a string
    safe = redact_exception(exc)             # scrub str(exc)
"""

import re
from typing import Match

REDACTED = "[REDACTED]"

# Ordered list of (compiled pattern, replacement). Replacements may be a string
# (with backrefs) or a callable. Patterns that carry a label keep the label and
# redact only the secret value so the message stays diagnostically useful.
_SECRET_PATTERNS = [
    # Google API keys (AIza...) — the exact shape leaked in the 2026-06-10 incident.
    (re.compile(r"AIza[0-9A-Za-z_\-]{10,}"), REDACTED),
    # OpenAI / Anthropic style keys (sk-, sk-proj-, sk-ant-...).
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), REDACTED),
    # AWS access key IDs.
    (re.compile(r"AKIA[0-9A-Z]{16}"), REDACTED),
    # Bearer tokens — keep the "Bearer " label, redact the token.
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"), r"\1" + REDACTED),
    # Header / kwarg style:  x-goog-api-key: VALUE | authorization=VALUE | api_key: 'VALUE'
    # The negative lookahead keeps an auth *scheme* word (Bearer/Basic/Token)
    # intact — the bearer pattern above already redacts the token that follows it.
    (
        re.compile(
            r"(?i)(x-goog-api-key|x-api-key|authorization|api[_-]?key|apikey)"
            r"(\s*[:=]\s*)(['\"]?)((?!bearer\b|basic\b|token\b)[^'\"\s,;)}&]+)"
        ),
        None,  # handled by _redact_labeled below
    ),
    # Query-param style:  ?api_key=VALUE&...  or  key=VALUE
    (re.compile(r"(?i)(api[_-]?key=|[?&]key=)([^&\s'\"]+)"), r"\1" + REDACTED),
]


def _redact_labeled(m: "Match[str]") -> str:
    """Keep label + separator + opening quote, redact the value."""
    return f"{m.group(1)}{m.group(2)}{m.group(3)}{REDACTED}"


def redact_secrets(text: str) -> str:
    """Return ``text`` with known secret shapes replaced by ``[REDACTED]``.

    Idempotent: running it twice yields the same result. Safe on non-secret
    strings (returns them unchanged). Never raises on ordinary input.
    """
    if not text:
        return text
    result = str(text)
    for pattern, replacement in _SECRET_PATTERNS:
        if replacement is None:
            result = pattern.sub(_redact_labeled, result)
        else:
            result = pattern.sub(replacement, result)
    return result


def redact_exception(exc: BaseException) -> str:
    """Return ``str(exc)`` with any embedded secrets redacted."""
    try:
        return redact_secrets(str(exc))
    except Exception:  # noqa: BLE001 — redaction must never itself raise
        return REDACTED
