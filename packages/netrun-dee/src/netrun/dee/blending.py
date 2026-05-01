"""DEE profile blending — weighted combination of multiple profiles."""

import math
from .types import DEEProfile, BlendResult
from .taxonomy import DEE_PROFILES_LIST


def blend_profiles(profiles: list[dict]) -> BlendResult:
    """Blend multiple DEE profiles with weights into a combined emotional state.

    Args:
        profiles: List of dicts with 'profile_id' and 'weight' keys.
                  Example: [{"profile_id": "DEE-01", "weight": 0.6},
                            {"profile_id": "DEE-03", "weight": 0.4}]

    Returns:
        BlendResult with blended valence/arousal/dominance and nearest profile.

    Raises:
        ValueError: If no valid profiles provided or weights sum to zero.
    """
    from .taxonomy import DEE_PROFILES

    total_weight = 0.0
    blended_v = 0.0
    blended_a = 0.0
    blended_d = 0.0

    for entry in profiles:
        pid = entry.get('profile_id', '')
        weight = float(entry.get('weight', 0.0))
        profile = DEE_PROFILES.get(pid)
        if profile is None or weight <= 0:
            continue
        blended_v += profile.valence * weight
        blended_a += profile.arousal * weight
        blended_d += profile.dominance * weight
        total_weight += weight

    if total_weight == 0:
        raise ValueError("No valid profiles with positive weights provided.")

    blended_v /= total_weight
    blended_a /= total_weight
    blended_d /= total_weight

    # Find nearest profile by Euclidean distance in VAD space
    best_profile = DEE_PROFILES_LIST[0]
    best_dist = float('inf')

    for p in DEE_PROFILES_LIST:
        dist = math.sqrt(
            (p.valence - blended_v) ** 2 +
            (p.arousal - blended_a) ** 2 +
            (p.dominance - blended_d) ** 2
        )
        if dist < best_dist:
            best_dist = dist
            best_profile = p

    # Similarity: 1.0 = identical, 0.0 = max distance (sqrt(12) ~= 3.46 for -1..1 range)
    max_dist = math.sqrt(12.0)
    similarity = round(1.0 - (best_dist / max_dist), 4)

    return BlendResult(
        valence=round(blended_v, 4),
        arousal=round(blended_a, 4),
        dominance=round(blended_d, 4),
        nearest_profile=best_profile,
        similarity=similarity,
    )
