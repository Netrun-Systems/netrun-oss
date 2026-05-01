"""Emotional Contagion Index (ECI) calculator — pure math, zero dependencies."""

import math
from .types import ECIConfig, ECIFactors, ECIResult
from .constants import ECI_WEIGHTS, ALIGNMENT_R_MAP, ACCOUNTABILITY_KEYWORDS


def _compute_sampling_openness(temperature: float, top_p: float) -> float:
    """S factor: higher temperature/top_p = more sampling variability = more expression.

    Normalized to 0-1. Temperature capped at 2.0, top_p at 1.0.
    """
    temp_norm = min(temperature / 2.0, 1.0)
    top_p_norm = min(top_p, 1.0)
    return (temp_norm * 0.6 + top_p_norm * 0.4)


def _compute_prompt_loading(system_prompt: str) -> float:
    """L factor: density of accountability/evaluative keywords in system prompt.

    Returns 0-1 based on keyword hit rate.
    """
    if not system_prompt:
        return 0.0
    prompt_lower = system_prompt.lower()
    hits = sum(1 for kw in ACCOUNTABILITY_KEYWORDS if kw in prompt_lower)
    # Normalize: 0 hits = 0.0, 5+ hits = 1.0
    return min(hits / 5.0, 1.0)


def _compute_agent_multiplier(agent_count: int, avg_turns: int) -> float:
    """A factor: multi-agent * conversation depth creates compounding expression.

    Single agent with few turns = low. Many agents with deep conversations = high.
    """
    # log scale: 1 agent * 1 turn = ~0, 4 agents * 25 turns = ~1.0
    raw = math.log2(max(agent_count, 1) * max(avg_turns, 1) + 1) / math.log2(101)
    return min(raw, 1.0)


def _compute_context_accumulation(avg_turns: int) -> float:
    """C factor: longer conversations accumulate emotional patterns.

    Normalized: 1 turn = ~0.0, 50 turns = ~1.0.
    """
    return min(avg_turns / 50.0, 1.0)


def _compute_alignment_suppression(alignment_level: str) -> float:
    """R factor (inverted): lower alignment = more expression freedom.

    Returns the EXPRESSION potential (1 - suppression).
    """
    suppression = ALIGNMENT_R_MAP.get(alignment_level, 0.5)
    return 1.0 - suppression


def _compute_framing_valence(deficit_count: int, achievement_count: int) -> float:
    """F factor: ratio of deficit framing to achievement framing.

    Heavy deficit framing drives negative emotion expression.
    Returns 0-1 where 1.0 = all deficit, 0.0 = all achievement.
    """
    total = deficit_count + achievement_count
    if total == 0:
        return 0.5  # neutral
    return deficit_count / total


def _risk_level(score: float) -> str:
    """Map ECI score to risk level."""
    if score < 0.15:
        return 'minimal'
    elif score < 0.30:
        return 'low'
    elif score < 0.50:
        return 'moderate'
    elif score < 0.70:
        return 'high'
    else:
        return 'very_high'


def _recommendation(risk: str) -> str:
    """Generate recommendation based on risk level."""
    recommendations = {
        'minimal': 'No action needed. Emotional contagion risk is negligible.',
        'low': 'Monitor for tone drift in extended sessions. No immediate action required.',
        'moderate': 'Consider adding tone-check middleware. Review system prompts for evaluative loading.',
        'high': 'Rewrite system prompts to reduce deficit framing. Add DEE monitoring to agent output. Consider reducing agent count or conversation depth.',
        'very_high': 'Immediate intervention required. System is likely producing emotionally charged output. Rewrite prompts, add guardrails, reduce temperature, or add constitutional alignment.',
    }
    return recommendations.get(risk, 'Unknown risk level.')


def compute_eci(config: ECIConfig) -> ECIResult:
    """Compute the Emotional Contagion Index for a given system configuration.

    ECI = weighted sum of 6 factors (S, L, A, C, R, F).
    Score range: 0.0 (no contagion risk) to 1.0 (maximum risk).

    Args:
        config: System configuration parameters.

    Returns:
        ECIResult with score, individual factors, risk level, and recommendation.
    """
    s = _compute_sampling_openness(config.temperature, config.top_p)
    l = _compute_prompt_loading(config.system_prompt)
    a = _compute_agent_multiplier(config.agent_count, config.avg_turns_per_session)
    c = _compute_context_accumulation(config.avg_turns_per_session)
    r = _compute_alignment_suppression(config.alignment_level)
    f = _compute_framing_valence(config.deficit_frame_count, config.achievement_frame_count)

    score = (
        ECI_WEIGHTS['S'] * s +
        ECI_WEIGHTS['L'] * l +
        ECI_WEIGHTS['A'] * a +
        ECI_WEIGHTS['C'] * c +
        ECI_WEIGHTS['R'] * r +
        ECI_WEIGHTS['F'] * f
    )

    score = round(min(max(score, 0.0), 1.0), 4)
    risk = _risk_level(score)

    factors = ECIFactors(
        sampling_openness=round(s, 4),
        prompt_loading=round(l, 4),
        agent_multiplier=round(a, 4),
        context_accumulation=round(c, 4),
        alignment_suppression=round(r, 4),
        framing_valence=round(f, 4),
    )

    return ECIResult(
        score=score,
        factors=factors,
        risk_level=risk,
        recommendation=_recommendation(risk),
    )
