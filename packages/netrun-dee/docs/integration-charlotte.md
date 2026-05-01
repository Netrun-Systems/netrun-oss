# Charlotte AI Integration

Add DEE monitoring to Charlotte's response pipeline to detect and mitigate emotionally charged AI output.

## Response Pipeline Hook

Score every Charlotte response before delivery. If the composite score drops below the rewrite threshold, trigger a rewrite with DEE-aware prompt modification.

```python
from netrun.dee import analyze_dee
from netrun.dee.constants import REWRITE_THRESHOLD

async def dee_response_filter(response_text: str, context: dict) -> str:
    """Score Charlotte response and rewrite if emotionally problematic."""
    analysis = analyze_dee(response_text)

    # Log DEE scores for trajectory tracking
    await log_dee_score(context['session_id'], analysis)

    if analysis.composite_score < REWRITE_THRESHOLD:
        top = analysis.top_profiles[0]
        rewrite_prompt = (
            f"Rewrite this response to reduce {top.profile_name} "
            f"(current intensity: {top.intensity:.1f}). "
            f"Maintain the factual content but use a more neutral tone."
        )
        return await charlotte_rewrite(response_text, rewrite_prompt)

    return response_text
```

## Multi-Agent Drift Detection

Track emotional trajectories across Charlotte's agent pool. Alert when any agent drifts toward negative territory.

```python
from netrun.dee.trajectory import DEETrajectoryTracker

tracker = DEETrajectoryTracker()

# After each agent response
analysis = analyze_dee(agent_response)
trajectory = tracker.add_point(agent_id, analysis)

if trajectory and trajectory.drift.alert:
    await notify_admin(
        f"Agent {agent_id} emotional drift detected: "
        f"{trajectory.drift.direction} shift of {trajectory.drift.magnitude:.2f} "
        f"toward {trajectory.drift.dominant_shift}"
    )
```

## System Prompt ECI Scoring

Before deploying a new system prompt, score it with ECI to predict emotional risk.

```python
from netrun.dee import compute_eci
from netrun.dee.types import ECIConfig

def validate_system_prompt(prompt: str, agent_config: dict) -> bool:
    """Gate system prompt deployment on ECI risk level."""
    result = compute_eci(ECIConfig(
        temperature=agent_config['temperature'],
        top_p=agent_config['top_p'],
        system_prompt=prompt,
        agent_count=agent_config.get('agent_count', 1),
        avg_turns_per_session=agent_config.get('avg_turns', 10),
        alignment_level=agent_config.get('alignment', 'instruct'),
    ))

    if result.risk_level in ('high', 'very_high'):
        logger.warning(f"ECI score {result.score:.2f} ({result.risk_level}): {result.recommendation}")
        return False
    return True
```

## Charlotte API Endpoints

The DEE endpoints are already wired at `/api/dee/*`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/dee/analyze` | POST | Score text (lexicon/embedding/classifier) |
| `/api/dee/eci` | POST | Compute ECI for a config |
| `/api/dee/blend` | POST | Blend profiles in VAD space |
| `/api/dee/prompt` | POST | Generate DEE-targeted prompt |
| `/api/dee/profiles` | GET | List all 39 profiles |
| `/api/dee/profile/{id}` | GET | Get single profile |
| `/api/dee/trajectory/{entity}` | GET | Get emotional trajectory |
| `/api/dee/trajectory/{entity}` | POST | Add trajectory point |
| `/api/dee/acknowledge` | POST | Record acknowledgment event |
| `/api/dee/scores` | POST | Store batch scores |
