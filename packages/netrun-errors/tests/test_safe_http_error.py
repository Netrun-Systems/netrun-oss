"""
Regression tests for netrun.errors.safe_http_error (B1, v2.1.0).

Core guarantee under test: the client-facing HTTPException.detail NEVER contains
any substring of str(exc). This is the leak class that motivated the helper —
upstream exception messages can embed provider secrets (e.g. an httpx ValueError
carrying a raw x-goog-api-key), and echoing them into the response detail leaks
those secrets to anonymous callers.
"""

import re

import pytest
from fastapi import HTTPException

from netrun.errors import safe_http_error


# A deliberately secret-bearing exception message, mirroring the 2026-06-10
# Gemini-key incident (httpx embedding the rejected API key in the error text).
_SECRET = "AIzaSyD-EXAMPLE-SECRET-KEY-0123456789abcdef"
_EXC_MESSAGE = f"header x-goog-api-key rejected: {_SECRET} is invalid"


def test_returns_httpexception_with_expected_status():
    exc = ValueError(_EXC_MESSAGE)
    result = safe_http_error(502, "Embedding analysis failed", exc)
    assert isinstance(result, HTTPException)
    assert result.status_code == 502


def test_detail_never_contains_secret_or_exception_text():
    """The response body must contain NO substring of str(exc)."""
    exc = ValueError(_EXC_MESSAGE)
    result = safe_http_error(502, "Embedding analysis failed", exc)
    detail = result.detail

    # The full exception string must not appear.
    assert str(exc) not in detail
    # The embedded secret must not appear anywhere in the detail.
    assert _SECRET not in detail
    # Guard against partial leakage: no token of length >= 8 from the exception
    # message (that isn't part of the safe prefix) should appear in the detail.
    prefix_tokens = set(re.findall(r"\w+", "Embedding analysis failed"))
    exc_tokens = [t for t in re.findall(r"\w+", str(exc)) if len(t) >= 8]
    leaked = [t for t in exc_tokens if t in detail and t not in prefix_tokens]
    assert leaked == [], f"exception tokens leaked into detail: {leaked}"


def test_detail_carries_public_prefix_and_correlation_ref():
    exc = RuntimeError(_EXC_MESSAGE)
    result = safe_http_error(500, "Widget processing failed", exc)
    detail = result.detail
    assert detail.startswith("Widget processing failed")
    # A 12-hex correlation ref is included as "(ref: <id>)".
    match = re.search(r"\(ref: ([0-9a-f]{12})\)", detail)
    assert match is not None, f"no 12-hex ref found in detail: {detail!r}"


def test_correlation_ref_is_unique_per_call():
    exc = ValueError(_EXC_MESSAGE)
    refs = set()
    for _ in range(20):
        detail = safe_http_error(500, "boom", exc).detail
        m = re.search(r"\(ref: ([0-9a-f]{12})\)", detail)
        assert m is not None
        refs.add(m.group(1))
    # Overwhelmingly likely to be all-unique; assert no accidental constant.
    assert len(refs) > 1


@pytest.mark.parametrize("status", [400, 429, 500, 502, 503, 504])
def test_preserves_arbitrary_status_codes(status):
    result = safe_http_error(status, "op failed", ValueError(_EXC_MESSAGE))
    assert result.status_code == status
    assert _SECRET not in result.detail
