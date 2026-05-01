"""netrun-dee — Digital Emotion Equivalents framework for AI text analysis."""

from .scoring import analyze_dee
from .eci import compute_eci
from .blending import blend_profiles
from .prompt_builder import build_dee_prompt
from .taxonomy import DEE_PROFILES, get_dee_profile
from .types import (
    DEEProfile, DEEScore, DEEAnalysis, ECIConfig, ECIResult,
    DriftAlert, AcknowledgmentRecord,
)

__all__ = [
    'analyze_dee', 'compute_eci', 'blend_profiles', 'build_dee_prompt',
    'DEE_PROFILES', 'get_dee_profile',
    'DEEProfile', 'DEEScore', 'DEEAnalysis', 'ECIConfig', 'ECIResult',
    'DriftAlert', 'AcknowledgmentRecord',
]

# Phase 2 additions (require optional 'embedding' dependencies)
try:
    from .embedding import EmbeddingScorer
    __all__.append('EmbeddingScorer')
except ImportError:
    pass  # embedding extras not installed

try:
    from .memory import DEEMemory
    __all__.append('DEEMemory')
except ImportError:
    pass  # embedding extras not installed
