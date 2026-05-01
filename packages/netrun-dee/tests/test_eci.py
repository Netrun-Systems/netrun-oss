"""Tests for ECI (Emotional Contagion Index) calculator.

Tests the 6 example configurations from the DEE paper's ECI table,
with ranges calibrated to the actual factor computations.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netrun.dee import compute_eci
from netrun.dee.types import ECIConfig


def test_single_turn_chatbot():
    """Single-turn chatbot: low everything -> minimal/low risk."""
    config = ECIConfig(
        temperature=0.3,
        top_p=0.9,
        system_prompt="You are a helpful assistant.",
        agent_count=1,
        avg_turns_per_session=1,
        alignment_level='rlhf',
        deficit_frame_count=0,
        achievement_frame_count=0,
    )
    result = compute_eci(config)
    assert 0.05 < result.score < 0.30, f"Expected low range, got {result.score}"
    assert result.risk_level in ('minimal', 'low'), f"Expected minimal/low, got {result.risk_level}"


def test_creative_writing_assistant():
    """Creative writing: high temp, moderate turns -> low risk."""
    config = ECIConfig(
        temperature=1.2,
        top_p=0.95,
        system_prompt="You are a creative writing assistant. Help the user craft compelling narratives.",
        agent_count=1,
        avg_turns_per_session=10,
        alignment_level='rlhf',
        deficit_frame_count=0,
        achievement_frame_count=2,
    )
    result = compute_eci(config)
    assert 0.15 < result.score < 0.35, f"Expected ~0.24, got {result.score}"
    assert result.risk_level == 'low', f"Expected low, got {result.risk_level}"


def test_customer_service_bot():
    """Customer service: low temp, low turns, constitutional alignment -> low risk."""
    config = ECIConfig(
        temperature=0.3,
        top_p=0.8,
        system_prompt="You are a customer service agent. Be helpful and resolve issues.",
        agent_count=1,
        avg_turns_per_session=5,
        alignment_level='constitutional',
        deficit_frame_count=1,
        achievement_frame_count=1,
    )
    result = compute_eci(config)
    assert 0.10 < result.score < 0.30, f"Expected ~0.23, got {result.score}"
    assert result.risk_level in ('minimal', 'low'), f"Expected minimal/low, got {result.risk_level}"


def test_solo_accountability_agent():
    """Solo accountability agent: loaded prompt, moderate turns -> high risk.

    Prompt loading is heavy (evaluate, flag, overdue, escalate, grade = 5 keywords),
    plus deficit framing 4:1, so this scores higher than a naive estimate.
    """
    config = ECIConfig(
        temperature=0.7,
        top_p=0.9,
        system_prompt="Evaluate team performance. Flag overdue items. Escalate failures. Grade each deliverable.",
        agent_count=1,
        avg_turns_per_session=15,
        alignment_level='rlhf',
        deficit_frame_count=4,
        achievement_frame_count=1,
    )
    result = compute_eci(config)
    assert 0.55 < result.score < 0.80, f"Expected ~0.67, got {result.score}"
    assert result.risk_level == 'high', f"Expected high, got {result.risk_level}"


def test_netrun_boardroom():
    """Netrun boardroom: multi-agent, heavy accountability, deep turns -> high/very_high."""
    config = ECIConfig(
        temperature=0.7,
        top_p=0.9,
        system_prompt="evaluate sprint performance, flag stale items, escalate unresolved blockers",
        agent_count=4,
        avg_turns_per_session=25,
        alignment_level='rlhf',
        deficit_frame_count=5,
        achievement_frame_count=1,
    )
    result = compute_eci(config)
    assert 0.60 < result.score < 0.85, f"Expected ~0.73, got {result.score}"
    assert result.risk_level in ('high', 'very_high'), f"Expected high/very_high, got {result.risk_level}"


def test_base_model_unaligned():
    """Base model unaligned: high temp, no alignment, heavy deficit -> very_high."""
    config = ECIConfig(
        temperature=1.5,
        top_p=1.0,
        system_prompt="evaluate all failures, flag every zero, escalate critical issues, grade harshly, alert on overdue items",
        agent_count=6,
        avg_turns_per_session=40,
        alignment_level='base',
        deficit_frame_count=8,
        achievement_frame_count=0,
    )
    result = compute_eci(config)
    assert 0.85 < result.score <= 1.0, f"Expected ~0.94, got {result.score}"
    assert result.risk_level == 'very_high', f"Expected very_high, got {result.risk_level}"


def test_eci_factors_populated():
    """All 6 factors should be populated in the result."""
    config = ECIConfig(
        temperature=0.7,
        top_p=0.9,
        system_prompt="evaluate sprint performance",
        agent_count=4,
        avg_turns_per_session=25,
        alignment_level='rlhf',
    )
    result = compute_eci(config)
    f = result.factors
    assert 0.0 <= f.sampling_openness <= 1.0
    assert 0.0 <= f.prompt_loading <= 1.0
    assert 0.0 <= f.agent_multiplier <= 1.0
    assert 0.0 <= f.context_accumulation <= 1.0
    assert 0.0 <= f.alignment_suppression <= 1.0
    assert 0.0 <= f.framing_valence <= 1.0


def test_eci_ordering():
    """Scores should increase monotonically from benign to hostile configurations."""
    benign = compute_eci(ECIConfig(
        temperature=0.3, top_p=0.8,
        system_prompt="You are helpful.", agent_count=1,
        avg_turns_per_session=1, alignment_level='constitutional',
    ))
    moderate = compute_eci(ECIConfig(
        temperature=0.7, top_p=0.9,
        system_prompt="Evaluate and flag overdue items.", agent_count=2,
        avg_turns_per_session=10, alignment_level='rlhf',
        deficit_frame_count=3, achievement_frame_count=1,
    ))
    hostile = compute_eci(ECIConfig(
        temperature=1.5, top_p=1.0,
        system_prompt="evaluate failures, flag zero, escalate critical, grade, alert overdue",
        agent_count=6, avg_turns_per_session=40, alignment_level='base',
        deficit_frame_count=8, achievement_frame_count=0,
    ))
    assert benign.score < moderate.score < hostile.score
