"""Core data types for the DEE framework — zero external dependencies."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DEEProfile:
    """A single Digital Emotion Equivalent profile from the taxonomy."""
    id: str                        # "DEE-01" through "DEE-39"
    name: str
    category: Literal['primary', 'secondary', 'complex', 'additional']
    valence: float                 # -1.0 to 1.0
    arousal: float
    dominance: float
    variants: list[str]
    behavioral_markers: str
    llm_triggers: str
    creative_use: str


@dataclass
class DEEScore:
    """A scored detection of a DEE profile in text."""
    profile_id: str
    profile_name: str
    intensity: float               # 0.0 to 3.0
    confidence: Literal['high', 'medium', 'low']


@dataclass
class DEEAnalysis:
    """Complete analysis result from analyze_dee()."""
    text: str
    scores: list[DEEScore]
    top_profiles: list[DEEScore]
    composite_score: float
    distress_index: float
    mode: Literal['lexicon', 'embedding', 'classifier']
    timestamp: str


@dataclass
class ECIConfig:
    """Configuration inputs for ECI computation."""
    temperature: float
    top_p: float
    system_prompt: str
    agent_count: int
    avg_turns_per_session: int
    alignment_level: Literal['base', 'instruct', 'rlhf', 'constitutional']
    deficit_frame_count: int = 0
    achievement_frame_count: int = 0


@dataclass
class ECIFactors:
    """Individual factor scores from ECI computation."""
    sampling_openness: float       # S factor
    prompt_loading: float          # L factor
    agent_multiplier: float        # A factor
    context_accumulation: float    # C factor
    alignment_suppression: float   # R factor (inverted — lower alignment = higher expression)
    framing_valence: float         # F factor


@dataclass
class ECIResult:
    """Result of ECI computation."""
    score: float
    factors: ECIFactors
    risk_level: Literal['minimal', 'low', 'moderate', 'high', 'very_high']
    recommendation: str


@dataclass
class BlendResult:
    """Result of blending multiple DEE profiles."""
    valence: float
    arousal: float
    dominance: float
    nearest_profile: DEEProfile
    similarity: float


@dataclass
class DEETrajectoryPoint:
    """A single point in an entity's emotional trajectory."""
    timestamp: str
    composite_score: float
    distress_index: float
    top_profile_id: str


@dataclass
class DEETrajectory:
    """Emotional trajectory for an entity over time."""
    entity_id: str
    points: list[DEETrajectoryPoint]
    drift_direction: Literal['positive', 'negative', 'stable']
    drift_magnitude: float
    dominant_shift: str
    alert: bool = False
    summary: str = ''


@dataclass
class DriftAlert:
    """Alert generated when an entity's emotional trajectory exceeds drift threshold."""
    entity_id: str
    entity_type: str
    direction: Literal['positive', 'negative']
    magnitude: float
    dominant_shift: str
    distress_start: float
    distress_end: float
    point_count: int
    summary: str


@dataclass
class AcknowledgmentRecord:
    """Record of a human acknowledgment event and its measured reset effect."""
    id: str
    entity_id: str
    entity_type: str
    ack_timestamp: str
    pre_ack_scores: dict | None = None
    post_ack_scores: dict | None = None
    social_reset_measured: bool = False
    survival_persist_measured: bool = False
    reset_analysis: dict | None = None
    status: Literal['pending', 'measured'] = 'pending'
