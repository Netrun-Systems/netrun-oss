"""
Tests for netrun.llm.redaction (B6 back-port).

Verifies known secret shapes are scrubbed from strings and exceptions so they
can never escape adapter exception paths (2026-06-10 Gemini-key leak class).
"""

import pytest

from netrun.llm.redaction import redact_secrets, redact_exception, REDACTED

# Realistic-shaped but fake secrets (not live credentials).
FAKE_GOOGLE_KEY = "AIzaSyD-FAKE1234567890abcdefghijKLMNOPqrst"
FAKE_OPENAI_KEY = "sk-FAKEabcdefghijklmnop1234567890"
FAKE_ANTHROPIC_KEY = "sk-ant-FAKEabcdefghijklmnop1234567890"
FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"


class TestRedactSecrets:
    def test_google_api_key_redacted(self):
        out = redact_secrets(f"boom: {FAKE_GOOGLE_KEY}")
        assert FAKE_GOOGLE_KEY not in out
        assert REDACTED in out

    def test_openai_key_redacted(self):
        out = redact_secrets(f"auth failed with {FAKE_OPENAI_KEY}")
        assert FAKE_OPENAI_KEY not in out
        assert REDACTED in out

    def test_anthropic_key_redacted(self):
        out = redact_secrets(f"key={FAKE_ANTHROPIC_KEY}")
        assert FAKE_ANTHROPIC_KEY not in out

    def test_aws_key_redacted(self):
        out = redact_secrets(f"creds {FAKE_AWS_KEY} rejected")
        assert FAKE_AWS_KEY not in out
        assert REDACTED in out

    def test_bearer_token_redacted_label_kept(self):
        out = redact_secrets("Authorization: Bearer abcDEF123456ghijkl")
        assert "abcDEF123456ghijkl" not in out
        assert "Bearer" in out  # label preserved for diagnostics

    def test_x_goog_api_key_header_redacted(self):
        # The exact shape from the 2026-06-10 httpx rejection.
        msg = (
            "Illegal header value b'x-goog-api-key: "
            f"{FAKE_GOOGLE_KEY}'"
        )
        out = redact_secrets(msg)
        assert FAKE_GOOGLE_KEY not in out
        assert "x-goog-api-key" in out  # label kept

    def test_query_param_api_key_redacted(self):
        out = redact_secrets("GET /v1/models?api_key=SECRETVALUE123&x=1")
        assert "SECRETVALUE123" not in out
        assert REDACTED in out

    def test_non_secret_string_unchanged(self):
        msg = "Connection timed out after 30s talking to the model endpoint"
        assert redact_secrets(msg) == msg

    def test_empty_and_none_safe(self):
        assert redact_secrets("") == ""
        assert redact_secrets(None) is None

    def test_idempotent(self):
        once = redact_secrets(f"leak {FAKE_GOOGLE_KEY}")
        twice = redact_secrets(once)
        assert once == twice


class TestRedactException:
    def test_redacts_exception_message(self):
        exc = ValueError(f"Illegal header value: x-goog-api-key={FAKE_GOOGLE_KEY}")
        out = redact_exception(exc)
        assert FAKE_GOOGLE_KEY not in out

    def test_never_raises(self):
        class Weird(Exception):
            def __str__(self):
                raise RuntimeError("cannot stringify")

        # Must degrade to [REDACTED], not propagate.
        assert redact_exception(Weird()) == REDACTED
