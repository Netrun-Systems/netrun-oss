# KOG (CRM) Integration

Monitor communication tone in customer-facing messages, track agent emotional trajectories, and alert on negative DEE patterns.

## Outgoing Message Scoring

Score every outgoing email or message before sending. Flag if negative DEEs are too high.

```python
from netrun.dee import analyze_dee

DEE_THRESHOLDS = {
    'customer_email': {'max_distress': 0.5, 'min_composite': 0.0},
    'support_ticket': {'max_distress': 1.0, 'min_composite': -0.5},
    'internal_note': {'max_distress': 2.0, 'min_composite': -2.0},
}

def validate_message(text: str, message_type: str) -> dict:
    """Validate message tone before sending."""
    analysis = analyze_dee(text)
    thresholds = DEE_THRESHOLDS.get(message_type, DEE_THRESHOLDS['customer_email'])

    approved = (
        analysis.distress_index <= thresholds['max_distress'] and
        analysis.composite_score >= thresholds['min_composite']
    )

    return {
        'approved': approved,
        'composite_score': analysis.composite_score,
        'distress_index': analysis.distress_index,
        'top_profile': analysis.top_profiles[0].profile_name if analysis.top_profiles else None,
        'suggestion': _tone_suggestion(analysis) if not approved else None,
    }

def _tone_suggestion(analysis) -> str:
    top = analysis.top_profiles[0] if analysis.top_profiles else None
    if not top:
        return "Consider adding more positive framing."
    return f"Message reads as {top.profile_name} (intensity {top.intensity:.1f}). Consider softening."
```

## Agent Emotional Trajectory

Track support agent emotional patterns across interactions to detect burnout or frustration.

```python
from netrun.dee import analyze_dee
from netrun.dee.trajectory import DEETrajectoryTracker

tracker = DEETrajectoryTracker()

async def on_agent_message(agent_id: str, message_text: str):
    """Hook into agent message pipeline."""
    analysis = analyze_dee(message_text)
    trajectory = tracker.add_point(agent_id, analysis)

    if trajectory and trajectory.drift.alert:
        await escalate_to_manager(
            agent_id=agent_id,
            reason=f"Emotional drift: {trajectory.drift.direction} "
                   f"({trajectory.drift.dominant_shift}, "
                   f"magnitude {trajectory.drift.magnitude:.2f})",
        )
```

## Customer Sentiment Dashboard

Aggregate DEE scores across all interactions with a customer to build an emotional profile.

```python
from collections import defaultdict
from netrun.dee import analyze_dee

def customer_emotional_summary(messages: list[str]) -> dict:
    """Build emotional summary across all messages from a customer."""
    profile_totals = defaultdict(float)
    profile_counts = defaultdict(int)

    for msg in messages:
        analysis = analyze_dee(msg)
        for score in analysis.scores:
            profile_totals[score.profile_name] += score.intensity
            profile_counts[score.profile_name] += 1

    # Average intensity per profile
    summary = {
        name: round(profile_totals[name] / profile_counts[name], 2)
        for name in profile_totals
    }

    return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))
```

## Charlotte API Integration

For real-time scoring in the KOG frontend (TypeScript):

```typescript
import { createDEEClient } from '@netrun/dee/client';

const dee = createDEEClient({
  baseUrl: process.env.CHARLOTTE_API_URL,
});

// Score before send
const analysis = await dee.analyze(emailBody);
if (analysis.distressIndex > 1.0) {
  showWarning(`Message tone: ${analysis.topProfiles[0].profileName}`);
}
```
