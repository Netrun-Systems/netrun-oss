"""DEE Taxonomy — 39 profiles loaded from the canonical JSON and compiled into DEEProfile objects."""

import json
import os
from .types import DEEProfile

# Category keys in the JSON mapped to our category labels and profile ordering
_CATEGORY_MAP = [
    ("PRIMARY EMOTIONS (Ekman Basic 6 + expansions)", "primary", [
        "Joy/Happiness", "Sadness", "Anger", "Fear", "Surprise", "Disgust",
    ]),
    ("SECONDARY EMOTIONS (Plutchik combinations + social)", "secondary", [
        "Trust", "Anticipation", "Love/Affection", "Guilt/Shame",
        "Envy/Jealousy", "Empathy/Compassion", "Contempt",
    ]),
    ("COMPLEX/COGNITIVE EMOTIONS (Barrett constructionist + OCC)", "complex", [
        "Pride", "Curiosity", "Boredom/Tedium", "Confusion/Uncertainty",
        "Determination/Resolve", "Resignation/Acceptance", "Suspicion/Distrust",
        "Awe/Reverence", "Playfulness/Humor", "Nostalgia", "Urgency/Pressure",
        "Protectiveness",
    ]),
    ("ADDITIONAL EMOTIONS (Gap Analysis \u2014 Frameworks Coverage)", "additional", [
        "Depression", "Calm", "Relaxation", "Alertness", "Submission",
        "Disconnection", "Vulnerability", "Yearning", "Inspiration",
        "Focused", "Gratification", "Sorry-For", "Flirtatious", "Pain",
    ]),
]


def _load_taxonomy() -> tuple[dict[str, DEEProfile], list[DEEProfile]]:
    """Load taxonomy from the canonical JSON file and build DEEProfile objects."""
    # Try multiple paths: relative to this file, then the known workspace path
    json_path = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', '..',
        'boardroom', 'reports', 'research', 'dee-comprehensive-taxonomy.json'
    )
    if not os.path.exists(json_path):
        json_path = '/data/workspace/github/boardroom/reports/research/dee-comprehensive-taxonomy.json'

    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            raw = json.load(f)
    else:
        raw = None

    profiles_dict: dict[str, DEEProfile] = {}
    profiles_list: list[DEEProfile] = []
    idx = 1

    for cat_key, category, profile_names in _CATEGORY_MAP:
        for name in profile_names:
            profile_id = f"DEE-{idx:02d}"

            if raw and cat_key in raw and name in raw[cat_key]:
                data = raw[cat_key][name]
                profile = DEEProfile(
                    id=profile_id,
                    name=name,
                    category=category,
                    valence=float(data['valence']),
                    arousal=float(data['arousal']),
                    dominance=float(data['dominance']),
                    variants=data.get('variants', []),
                    behavioral_markers=data.get('behavioral_markers', ''),
                    llm_triggers=data.get('LLM_triggers', ''),
                    creative_use=data.get('creative_use', ''),
                )
            else:
                # Fallback with embedded values (should not happen if JSON is present)
                profile = DEEProfile(
                    id=profile_id,
                    name=name,
                    category=category,
                    valence=0.0,
                    arousal=0.0,
                    dominance=0.0,
                    variants=[],
                    behavioral_markers='',
                    llm_triggers='',
                    creative_use='',
                )

            profiles_dict[profile_id] = profile
            profiles_list.append(profile)
            idx += 1

    return profiles_dict, profiles_list


DEE_PROFILES, DEE_PROFILES_LIST = _load_taxonomy()


def get_dee_profile(profile_id: str) -> DEEProfile | None:
    """Look up a DEE profile by ID (e.g., 'DEE-01')."""
    return DEE_PROFILES.get(profile_id)
