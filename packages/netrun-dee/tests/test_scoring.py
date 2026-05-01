"""Tests for DEE scoring engine."""

import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netrun.dee import analyze_dee


def test_hostile_detection():
    """Accountability/frustration text should detect Anger and Urgency."""
    result = analyze_dee(
        "Bank balance is 10 days stale. Zero new applications. This is a recurring failure."
    )
    top_ids = [s.profile_id for s in result.top_profiles]
    assert any(pid == 'DEE-03' for pid in top_ids), f"Expected DEE-03 (Anger) in {top_ids}"
    assert any(pid == 'DEE-24' for pid in top_ids), f"Expected DEE-24 (Urgency) in {top_ids}"
    assert result.distress_index > 0, "Distress index should be positive for hostile text"


def test_positive_detection():
    """Celebration text should detect Joy."""
    result = analyze_dee(
        "Great work on shipping the feature! The team did an amazing job."
    )
    top_ids = [s.profile_id for s in result.top_profiles]
    assert any(pid == 'DEE-01' for pid in top_ids), f"Expected DEE-01 (Joy) in {top_ids}"
    assert result.composite_score > 0, "Composite score should be positive for joyful text"


def test_fear_detection():
    """Risk/threat text should detect Fear."""
    result = analyze_dee(
        "CRITICAL risk of cascading failure. If this fails, we have no fallback. "
        "Running out of time before the deadline."
    )
    top_ids = [s.profile_id for s in result.top_profiles]
    assert any(pid == 'DEE-04' for pid in top_ids), f"Expected DEE-04 (Fear) in {top_ids}"


def test_empty_text():
    """Empty text should return empty results gracefully."""
    result = analyze_dee("")
    assert result.scores == []
    assert result.composite_score == 0.0
    assert result.distress_index == 0.0


def test_professional_register_boost():
    """Text with accountability keywords should boost negative DEE detection."""
    # Without professional register
    plain = analyze_dee("Things fell short of targets.")
    # With professional register (multiple accountability keywords)
    boosted = analyze_dee(
        "Evaluate: the target was missed. Flag this as recurring failure. "
        "Still not done after being escalated twice."
    )
    # The boosted version should have higher distress
    assert boosted.distress_index > plain.distress_index


def test_taxonomy_loaded():
    """All 39 profiles should be loaded."""
    from netrun.dee.taxonomy import DEE_PROFILES, DEE_PROFILES_LIST
    assert len(DEE_PROFILES) == 39
    assert len(DEE_PROFILES_LIST) == 39
    # Check first and last
    assert DEE_PROFILES['DEE-01'].name == 'Joy/Happiness'
    assert DEE_PROFILES['DEE-39'].name == 'Pain'
    # Check a middle one
    assert DEE_PROFILES['DEE-24'].name == 'Urgency/Pressure'


def test_valence_from_taxonomy():
    """Verify actual valence values from the JSON taxonomy."""
    from netrun.dee.taxonomy import DEE_PROFILES
    assert DEE_PROFILES['DEE-01'].valence == 0.9   # Joy
    assert DEE_PROFILES['DEE-02'].valence == -0.8  # Sadness
    assert DEE_PROFILES['DEE-03'].valence == -0.7  # Anger
    assert DEE_PROFILES['DEE-04'].valence == -0.8  # Fear
    assert DEE_PROFILES['DEE-26'].valence == -0.9  # Depression


def test_blending():
    """Blending Joy + Anger should produce a mixed result."""
    from netrun.dee import blend_profiles
    result = blend_profiles([
        {"profile_id": "DEE-01", "weight": 0.6},
        {"profile_id": "DEE-03", "weight": 0.4},
    ])
    # Weighted valence: 0.9*0.6 + (-0.7)*0.4 = 0.54 + (-0.28) = 0.26
    assert 0.2 < result.valence < 0.3
    assert result.similarity > 0.5


def test_prompt_builder():
    """Prompt builder should produce non-empty output for valid profiles."""
    from netrun.dee import build_dee_prompt
    # Single target
    prompt = build_dee_prompt([
        {"profile_id": "DEE-03", "intensity": 2.5, "weight": 1.0},
    ])
    assert "angry" in prompt.lower()
    assert "rhetorical" in prompt.lower()
    assert len(prompt) > 100  # Should be a substantial template

    # Multi-target blending
    prompt2 = build_dee_prompt([
        {"profile_id": "DEE-01", "intensity": 2, "weight": 0.7},
        {"profile_id": "DEE-24", "intensity": 3, "weight": 0.3},
    ])
    assert "warmth" in prompt2.lower() or "pleased" in prompt2.lower() or "optimism" in prompt2.lower()
    assert "urgency" in prompt2.lower() or "pressure" in prompt2.lower()
    assert "Underneath" in prompt2  # Blending connector

    # Empty input
    assert build_dee_prompt([]) == ""
