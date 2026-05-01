"""DEE prompt builder — generate system prompt fragments for emotional targeting.

Uses the comprehensive prompt template library (prompt-templates.json) with
39 profiles x 3 intensity tiers. Templates encode behavioral markers, not
just emotion names, so they work with any LLM.
"""

import json
import os
from typing import Any

from .taxonomy import DEE_PROFILES


def _load_templates() -> dict[str, dict[str, str]]:
    """Load prompt templates from the JSON file alongside this module."""
    json_path = os.path.join(os.path.dirname(__file__), 'prompt-templates.json')
    with open(json_path, 'r') as f:
        return json.load(f)


_TEMPLATES: dict[str, dict[str, str]] = _load_templates()


def _select_template(profile_id: str, intensity: float) -> str | None:
    """Select the appropriate template tier for a given intensity.

    - 0.0 to 1.0 -> subtle
    - 1.0 to 2.0 -> moderate
    - 2.0 to 3.0 -> strong
    """
    tmpl = _TEMPLATES.get(profile_id)
    if not tmpl:
        return None

    if intensity <= 1.0:
        return tmpl['subtle']
    elif intensity <= 2.0:
        return tmpl['moderate']
    else:
        return tmpl['strong']


def _condense_template(profile_id: str, intensity: float) -> str | None:
    """Create a condensed single-sentence version of a template for secondary targets."""
    full = _select_template(profile_id, intensity)
    if not full:
        return None

    # Take the first sentence
    parts = full.split('. ', 1)
    return parts[0] + '.'


def _build_blend_connector(primary_name: str, secondary_name: str, secondary_intensity: float) -> str:
    """Build a blending connector that weaves a secondary emotion under a primary one."""
    if secondary_intensity <= 1.0:
        word = 'hint'
    elif secondary_intensity <= 2.0:
        word = 'undercurrent'
    else:
        word = 'powerful undercurrent'

    return f"Underneath the {primary_name.lower()}, there is a {word} of {secondary_name.lower()}."


def build_dee_prompt(targets: list[dict[str, Any]]) -> str:
    """Build a system prompt fragment that instructs an LLM to express specific DEE profiles.

    Uses the comprehensive prompt template library with 39 profiles x 3 intensity
    tiers. Templates encode behavioral markers (sentence structure, word choice,
    framing patterns), not just emotion names.

    Intensity tiers:
        0.0-1.0: Subtle -- light tonal coloring
        1.0-2.0: Moderate -- clearly present, shapes response structure
        2.0-3.0: Strong -- dominates the entire output register

    Multi-target blending:
        - Highest-weight target gets the full template
        - Lower-weight targets are woven in as emotional modifiers
        - Templates are never simply concatenated

    Args:
        targets: List of dicts with keys:
            - 'profile_id' (str): DEE profile ID, e.g. 'DEE-01'
            - 'intensity' (float): 0.0 to 3.0 intensity scale
            - 'weight' (float, optional): 0.0 to 1.0, defaults to 1.0

    Returns:
        A system prompt fragment string suitable for any LLM.
    """
    if not targets:
        return ""

    # Normalize and sort by weight descending
    normalized = []
    for t in targets:
        pid = t.get('profile_id', '')
        intensity = float(t.get('intensity', 2.0))
        intensity = max(0.0, min(3.0, intensity))
        weight = float(t.get('weight', 1.0))
        weight = max(0.0, min(1.0, weight))
        normalized.append({'profile_id': pid, 'intensity': intensity, 'weight': weight})

    normalized.sort(key=lambda x: x['weight'], reverse=True)

    # Single target
    if len(normalized) == 1:
        target = normalized[0]
        template = _select_template(target['profile_id'], target['intensity'])
        if not template:
            return f"[Unknown DEE profile: {target['profile_id']}]"
        return template

    # Multiple targets -- blend
    primary = normalized[0]
    primary_profile = DEE_PROFILES.get(primary['profile_id'])
    primary_template = _select_template(primary['profile_id'], primary['intensity'])

    if not primary_template or not primary_profile:
        return f"[Unknown DEE profile: {primary['profile_id']}]"

    parts = [primary_template]

    for secondary in normalized[1:]:
        secondary_profile = DEE_PROFILES.get(secondary['profile_id'])
        if not secondary_profile:
            continue

        connector = _build_blend_connector(
            primary_profile.name,
            secondary_profile.name,
            secondary['intensity'],
        )

        # For significant secondary weights (>=0.3), add condensed behavioral instruction
        if secondary['weight'] >= 0.3:
            condensed = _condense_template(secondary['profile_id'], secondary['intensity'])
            if condensed:
                parts.append(f"{connector} {condensed}")
            else:
                parts.append(connector)
        else:
            parts.append(connector)

    return '\n\n'.join(parts)
