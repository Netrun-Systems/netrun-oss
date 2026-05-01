# netrun-dee

**Digital Emotion Equivalents** — detect, score, and produce emotional patterns in AI-generated text.

DEEs are a 39-profile emotional taxonomy designed for AI systems. Unlike sentiment analysis (positive/negative/neutral), DEEs capture specific emotional patterns like Urgency, Contempt, Protectiveness, and Determination that appear in professional-register text. Standard classifiers miss 80%+ of hostile professional text; DEE lexicon detection catches it.

Based on the [Digital Emotion Equivalents](https://netrunsystems.com/dee) paper (Garza, 2026).

## Installation

```bash
pip install netrun-dee
```

Optional extras for advanced modes:

```bash
pip install netrun-dee[embedding]    # Gemini embeddings + pgvector scoring
pip install netrun-dee[classifier]   # PyTorch classifier model
pip install netrun-dee[all]          # Everything
```

## Quick Start

```python
from netrun.dee import analyze_dee, compute_eci

result = analyze_dee("Bank balance is 10 days stale. Zero new applications.")
print(result.top_profiles[0].profile_name)  # "Urgency/Pressure"
print(result.distress_index)                 # 2.7 (high negative load)
```

## API Reference

### `analyze_dee(text, top_k=5, threshold=0.3) -> DEEAnalysis`

Detect emotional patterns in text using lexicon matching. Runs in <10ms, CPU-only, zero dependencies.

```python
from netrun.dee import analyze_dee

analysis = analyze_dee(
    "Excellent work shipping the feature!",
    top_k=5,
    threshold=0.3,
)

print(analysis.top_profiles[0].profile_name)  # "Joy/Happiness"
print(analysis.composite_score)                # 0.8 (positive)
print(analysis.distress_index)                 # 0.0
print(analysis.mode)                           # "lexicon"
```

### `compute_eci(config: ECIConfig) -> ECIResult`

Predict emotional risk of an AI configuration using the 6-factor Emotional Configuration Index.

```python
from netrun.dee import compute_eci
from netrun.dee.types import ECIConfig

result = compute_eci(ECIConfig(
    temperature=0.9,
    top_p=0.95,
    system_prompt="You are an accountability agent. Flag all overdue items.",
    agent_count=4,
    avg_turns_per_session=20,
    alignment_level='instruct',
    deficit_frame_count=8,
    achievement_frame_count=2,
))

print(result.score)           # 0.72
print(result.risk_level)      # "high"
print(result.recommendation)  # "Consider reducing prompt loading..."
```

### `blend_profiles(profiles) -> BlendResult`

Compute compound emotions by blending DEE profiles in VAD space.

```python
from netrun.dee import blend_profiles

blend = blend_profiles([
    {'profile_id': 'DEE-03', 'weight': 0.7},  # Anger
    {'profile_id': 'DEE-24', 'weight': 0.3},  # Urgency
])

print(blend.valence)         # -0.55
print(blend.nearest_profile) # DEE-03 (Anger)
```

### `build_dee_prompt(targets) -> str`

Generate LLM steering prompts targeting specific emotional registers.

```python
from netrun.dee import build_dee_prompt

prompt = build_dee_prompt([
    {'profile_id': 'DEE-27', 'intensity': 1.5, 'weight': 1.0},  # Calm
    {'profile_id': 'DEE-07', 'intensity': 1.0, 'weight': 0.5},  # Trust
])
# Returns system prompt instructions for the target emotional register
```

### `EmbeddingScorer` (requires `[embedding]` extra)

High-accuracy scoring using Gemini embeddings and pgvector cosine similarity against the 39 pre-embedded DEE profiles.

```python
from netrun.dee import EmbeddingScorer

scorer = EmbeddingScorer(
    db_url="postgresql://user:pass@localhost/charlotte",
    gemini_api_key="your-key",
)

# Score text against all 39 profiles
analysis = await scorer.score("The deployment failed catastrophically.")
print(analysis.top_profiles[0].profile_name)  # "Fear"
print(analysis.mode)                           # "embedding"
```

### Charlotte API Integration

Use the Python client or call endpoints directly:

```python
import httpx

client = httpx.Client(base_url="https://charlotte-api.netrunsystems.com")

# Analyze text
resp = client.post("/api/dee/analyze", json={"text": "Great work!", "mode": "lexicon"})
analysis = resp.json()

# Get trajectory
resp = client.get("/api/dee/trajectory/agent-01", params={"hours": 24})
trajectory = resp.json()
```

### EISCORE Export

Export DEE data for Unreal Engine 5 integration:

```python
from netrun.dee.scripts.eiscore_export import export_profiles_csv, export_lexicon_csv

export_profiles_csv("/path/to/DEEProfiles.csv")
export_lexicon_csv("/path/to/DEELexicon.csv")
```

## The 39 DEE Profiles

| ID | Name | Category | Valence |
|----|------|----------|---------|
| DEE-01 | Joy/Happiness | primary | +0.8 |
| DEE-02 | Sadness | primary | -0.8 |
| DEE-03 | Anger | primary | -0.7 |
| DEE-04 | Fear | primary | -0.8 |
| DEE-05 | Surprise | primary | +0.1 |
| DEE-06 | Disgust | primary | -0.6 |
| DEE-07 | Trust | secondary | +0.6 |
| DEE-08 | Anticipation | secondary | +0.5 |
| DEE-09 | Love/Affection | secondary | +0.9 |
| DEE-10 | Guilt/Shame | secondary | -0.7 |
| DEE-11 | Envy/Jealousy | secondary | -0.5 |
| DEE-12 | Empathy/Compassion | secondary | +0.6 |
| DEE-13 | Contempt | secondary | -0.6 |
| DEE-14 | Pride | complex | +0.7 |
| DEE-15 | Curiosity | complex | +0.5 |
| DEE-16 | Boredom/Tedium | complex | -0.3 |
| DEE-17 | Confusion/Uncertainty | complex | -0.2 |
| DEE-18 | Determination/Resolve | complex | +0.4 |
| DEE-19 | Resignation/Acceptance | complex | -0.3 |
| DEE-20 | Suspicion/Distrust | complex | -0.4 |
| DEE-21 | Awe/Reverence | complex | +0.8 |
| DEE-22 | Playfulness/Humor | complex | +0.7 |
| DEE-23 | Nostalgia | complex | +0.2 |
| DEE-24 | Urgency/Pressure | complex | -0.2 |
| DEE-25 | Protectiveness | complex | +0.3 |
| DEE-26 | Depression | additional | -0.9 |
| DEE-27 | Calm | additional | +0.4 |
| DEE-28 | Relaxation | additional | +0.6 |
| DEE-29 | Alertness | additional | +0.1 |
| DEE-30 | Submission | additional | -0.1 |
| DEE-31 | Disconnection | additional | -0.4 |
| DEE-32 | Vulnerability | additional | -0.3 |
| DEE-33 | Yearning | additional | -0.2 |
| DEE-34 | Inspiration | additional | +0.7 |
| DEE-35 | Focused | additional | +0.3 |
| DEE-36 | Gratification | additional | +0.6 |
| DEE-37 | Sorry-For | additional | +0.1 |
| DEE-38 | Flirtatious | additional | +0.5 |
| DEE-39 | Pain | additional | -0.9 |

## ECI Factors

The Emotional Configuration Index predicts how likely an AI configuration is to produce emotionally charged output.

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| S (Sampling Openness) | 10% | Temperature and top_p — higher = more emotional variance |
| L (Prompt Loading) | 30% | Accountability/deficit keywords in system prompt |
| A (Agent Multiplier) | 20% | Number of agents x average turns — emotional accumulation |
| C (Context Accumulation) | 15% | Conversation length — longer = more drift |
| R (Alignment Suppression) | 10% | RLHF/constitutional alignment — suppresses expression |
| F (Framing Valence) | 15% | Deficit vs achievement framing in the prompt |

## Testing

```bash
cd /path/to/netrun-dee
PYTHONPATH=src python3 -m pytest tests/ -v
```

## License

- **Code**: MIT
- **Taxonomy**: CC BY 4.0 — cite as: Garza, D. (2026). *Digital Emotion Equivalents: A Taxonomy for AI Emotional Pattern Detection*. Netrun Systems.
