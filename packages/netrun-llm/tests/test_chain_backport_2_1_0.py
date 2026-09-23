"""
Tests for the v2.1.0 back-ports in LLMFallbackChain:
  - B6: adapter-exception secret redaction (no key substring escapes execute()).
  - B4: opt-in long-context escalation (Flash -> Pro past the recall window).

All adapters are mocked — no real provider/HTTP calls.
"""

from typing import Any, Dict, Optional

import pytest

from netrun.llm import LLMFallbackChain
from netrun.llm.adapters.base import BaseLLMAdapter, AdapterTier, LLMResponse
from netrun.llm.exceptions import AllAdaptersFailedError

# Fake, non-live secret shaped like the one leaked on 2026-06-10.
FAKE_GOOGLE_KEY = "AIzaSyD-FAKE1234567890abcdefghijKLMNOPqrst"


class _BaseMock(BaseLLMAdapter):
    def __init__(self, name="Mock", available=True):
        super().__init__(adapter_name=name, tier=AdapterTier.API, reliability_score=1.0)
        self._available = available

    def estimate_cost(self, prompt, context=None):
        return 0.0

    def check_availability(self):
        return self._available

    def get_metadata(self):
        return {"name": self.adapter_name}

    async def execute_async(self, prompt, context=None):
        return self.execute(prompt, context)


class RaisingSecretAdapter(_BaseMock):
    """Raises an exception whose message embeds an API key (httpx-style)."""

    def execute(self, prompt, context=None):
        raise ValueError(
            "Illegal header value b'x-goog-api-key: " + FAKE_GOOGLE_KEY + "'"
        )

    async def execute_async(self, prompt, context=None):
        raise ValueError(
            "Illegal header value b'x-goog-api-key: " + FAKE_GOOGLE_KEY + "'"
        )


class SecretErrorResponseAdapter(_BaseMock):
    """Returns a non-success LLMResponse whose error field embeds a key."""

    def execute(self, prompt, context=None):
        self._record_failure()
        return LLMResponse(
            status="error",
            error=f"Auth rejected: api_key={FAKE_GOOGLE_KEY}",
            adapter_name=self.adapter_name,
            latency_ms=1,
        )


class RecordingAdapter(_BaseMock):
    """Records the model it was asked to run and returns success."""

    def __init__(self, name="Recorder"):
        super().__init__(name=name)
        self.seen_model: Optional[str] = None

    def execute(self, prompt, context=None):
        self.seen_model = (context or {}).get("model")
        self._record_success(1, 0.0)
        return LLMResponse(
            status="success",
            content="ok",
            adapter_name=self.adapter_name,
            model_used=self.seen_model,
            latency_ms=1,
        )


class TestB6ExceptionRedaction:
    def test_raised_exception_key_never_escapes(self):
        chain = LLMFallbackChain(adapters=[RaisingSecretAdapter("G")])
        with pytest.raises(AllAdaptersFailedError) as ei:
            chain.execute("hi")
        # The key must appear nowhere in the raised error or its error map.
        assert FAKE_GOOGLE_KEY not in str(ei.value)
        for v in ei.value.errors.values():
            assert FAKE_GOOGLE_KEY not in v
        assert any("[REDACTED]" in v for v in ei.value.errors.values())

    def test_error_response_key_never_escapes(self):
        chain = LLMFallbackChain(adapters=[SecretErrorResponseAdapter("G")])
        with pytest.raises(AllAdaptersFailedError) as ei:
            chain.execute("hi")
        assert FAKE_GOOGLE_KEY not in str(ei.value)
        for v in ei.value.errors.values():
            assert FAKE_GOOGLE_KEY not in v

    @pytest.mark.asyncio
    async def test_async_raised_exception_key_never_escapes(self):
        chain = LLMFallbackChain(adapters=[RaisingSecretAdapter("G")])
        with pytest.raises(AllAdaptersFailedError) as ei:
            await chain.execute_async("hi")
        assert FAKE_GOOGLE_KEY not in str(ei.value)
        for v in ei.value.errors.values():
            assert FAKE_GOOGLE_KEY not in v

    def test_normal_error_still_propagates_message(self):
        class PlainError(_BaseMock):
            def execute(self, prompt, context=None):
                self._record_failure()
                return LLMResponse(
                    status="error", error="upstream 503", adapter_name=self.adapter_name
                )

        chain = LLMFallbackChain(adapters=[PlainError("P")])
        with pytest.raises(AllAdaptersFailedError) as ei:
            chain.execute("hi")
        assert ei.value.errors["P"] == "upstream 503"


class TestB4LongContextEscalation:
    def test_escalates_flash_to_pro_past_threshold(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(adapters=[rec], long_context_escalation=True)
        chain.execute(
            "big prompt",
            context={"input_tokens": 600_000, "model": "gemini-2.5-flash"},
        )
        assert rec.seen_model == "gemini-2.5-pro"
        assert len(chain.escalation_events) == 1
        ev = chain.escalation_events[0]
        assert ev["reason"] == "long_ctx"
        assert ev["from"] == "gemini-2.5-flash"
        assert ev["to"] == "gemini-2.5-pro"
        assert ev["tokens"] == 600_000

    def test_no_escalation_under_threshold(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(adapters=[rec], long_context_escalation=True)
        chain.execute(
            "small",
            context={"input_tokens": 100_000, "model": "gemini-2.5-flash"},
        )
        assert rec.seen_model == "gemini-2.5-flash"
        assert chain.escalation_events == []

    def test_disabled_by_default(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(adapters=[rec])  # escalation off
        chain.execute(
            "big prompt",
            context={"input_tokens": 900_000, "model": "gemini-2.5-flash"},
        )
        assert rec.seen_model == "gemini-2.5-flash"
        assert chain.escalation_events == []

    def test_generic_flash_substring_transform(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(adapters=[rec], long_context_escalation=True)
        chain.execute(
            "big",
            context={"input_tokens": 600_000, "model": "gemini-3.0-flash"},
        )
        assert rec.seen_model == "gemini-3.0-pro"

    def test_char_heuristic_when_no_explicit_tokens(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(
            adapters=[rec], long_context_escalation=True, long_context_threshold=10
        )
        # ~4 chars/token; 80 chars -> ~20 tokens > 10 threshold.
        chain.execute("x" * 80, context={"model": "gemini-2.5-flash"})
        assert rec.seen_model == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_async_escalation(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(adapters=[rec], long_context_escalation=True)
        await chain.execute_async(
            "big prompt",
            context={"input_tokens": 600_000, "model": "gemini-2.5-flash"},
        )
        assert rec.seen_model == "gemini-2.5-pro"
        assert len(chain.escalation_events) == 1

    def test_non_flash_model_not_escalated(self):
        rec = RecordingAdapter()
        chain = LLMFallbackChain(adapters=[rec], long_context_escalation=True)
        chain.execute(
            "big", context={"input_tokens": 600_000, "model": "claude-sonnet-4-5"}
        )
        assert rec.seen_model == "claude-sonnet-4-5"
        assert chain.escalation_events == []
