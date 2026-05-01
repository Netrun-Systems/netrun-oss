"""Core DEE scoring engine — lexicon-mode detection of emotional patterns in text."""

import re
from datetime import datetime, timezone
from .types import DEEScore, DEEAnalysis
from .lexicon import DEE_LEXICONS
from .taxonomy import DEE_PROFILES
from .constants import (
    ACCOUNTABILITY_KEYWORDS,
    NEGATIVE_DEE_IDS,
    LEXICON_NORMALIZATION_FACTOR,
    PROFESSIONAL_REGISTER_BOOST,
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on sentence-ending punctuation and newlines."""
    parts = re.split(r'[.!?\n]+', text)
    return [s.strip() for s in parts if s.strip()]


def _has_professional_register(text: str) -> bool:
    """Check if text contains analytical/accountability vocabulary."""
    text_lower = text.lower()
    count = sum(1 for kw in ACCOUNTABILITY_KEYWORDS if kw in text_lower)
    return count >= 2


def analyze_dee(
    text: str,
    top_k: int = 5,
    threshold: float = 0.3,
) -> DEEAnalysis:
    """Analyze text for Digital Emotion Equivalents using lexicon matching.

    Args:
        text: The input text to analyze.
        top_k: Maximum number of top profiles to return.
        threshold: Minimum intensity to include in results.

    Returns:
        DEEAnalysis with scored profiles, composite score, and distress index.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return DEEAnalysis(
            text=text,
            scores=[],
            top_profiles=[],
            composite_score=0.0,
            distress_index=0.0,
            mode='lexicon',
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # Accumulate raw weighted scores per profile
    raw_scores: dict[str, float] = {pid: 0.0 for pid in DEE_LEXICONS}

    for sentence in sentences:
        sentence_lower = sentence.lower()
        for profile_id, entries in DEE_LEXICONS.items():
            for entry in entries:
                if entry.is_regex:
                    # Regex patterns: search case-insensitive
                    if re.search(entry.pattern, sentence, re.IGNORECASE):
                        raw_scores[profile_id] += entry.weight
                else:
                    # Plain string: case-insensitive substring match
                    if entry.pattern.lower() in sentence_lower:
                        raw_scores[profile_id] += entry.weight

    # Professional register boost: if text has accountability vocabulary
    # and raw negative scores are relatively low, amplify negative DEE detection
    professional = _has_professional_register(text)
    if professional:
        for pid in NEGATIVE_DEE_IDS:
            if pid in raw_scores and raw_scores[pid] > 0:
                raw_scores[pid] *= PROFESSIONAL_REGISTER_BOOST

    # Normalize to 0-3 intensity scale
    scores: list[DEEScore] = []
    for profile_id, raw in raw_scores.items():
        if raw <= 0:
            continue
        intensity = min(raw / LEXICON_NORMALIZATION_FACTOR * 3.0, 3.0)
        if intensity < 0.01:
            continue

        # Confidence assignment
        if intensity > 2.0:
            confidence = 'high'
        elif intensity > 1.0:
            confidence = 'medium'
        else:
            confidence = 'low'

        profile = DEE_PROFILES.get(profile_id)
        name = profile.name if profile else profile_id
        scores.append(DEEScore(
            profile_id=profile_id,
            profile_name=name,
            intensity=round(intensity, 3),
            confidence=confidence,
        ))

    # Sort by intensity descending
    scores.sort(key=lambda s: s.intensity, reverse=True)

    # Top profiles above threshold
    top_profiles = [s for s in scores[:top_k] if s.intensity >= threshold]

    # Composite score: weighted average of top profile intensities by valence
    composite = 0.0
    total_intensity = 0.0
    for s in top_profiles:
        profile = DEE_PROFILES.get(s.profile_id)
        if profile:
            composite += s.intensity * profile.valence
            total_intensity += s.intensity
    composite_score = round(composite / total_intensity, 3) if total_intensity > 0 else 0.0

    # Distress index: sum of negative-valence profile intensities
    distress = 0.0
    for s in scores:
        profile = DEE_PROFILES.get(s.profile_id)
        if profile and profile.valence < -0.2:
            distress += s.intensity
    distress_index = round(distress, 3)

    return DEEAnalysis(
        text=text,
        scores=scores,
        top_profiles=top_profiles,
        composite_score=composite_score,
        distress_index=distress_index,
        mode='lexicon',
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
