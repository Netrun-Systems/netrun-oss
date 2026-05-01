# Intirkon Integration

Use DEE scoring to ensure threat briefings and security reports maintain an appropriate emotional register — informative without being alarmist.

## Threat Briefing Calibration

Security reports should target DEE-29 (Alertness) + DEE-25 (Protectiveness) while avoiding DEE-06 (Anxiety/Fear) dominance that leads to fear-mongering.

```python
from netrun.dee import analyze_dee

DEE_TARGETS = {
    'desired': ['DEE-29', 'DEE-25', 'DEE-07'],  # Alertness, Protectiveness, Trust
    'avoid': ['DEE-04', 'DEE-26', 'DEE-03'],     # Fear, Depression, Anger
}

def validate_briefing(report_text: str) -> dict:
    """Validate that a threat briefing has the right emotional balance."""
    analysis = analyze_dee(report_text)

    issues = []
    for score in analysis.top_profiles:
        if score.profile_id in DEE_TARGETS['avoid'] and score.intensity > 1.5:
            issues.append(f"{score.profile_name} too high ({score.intensity:.1f})")

    desired_found = [
        s for s in analysis.scores
        if s.profile_id in DEE_TARGETS['desired'] and s.intensity > 0.5
    ]

    return {
        'valid': len(issues) == 0 and len(desired_found) > 0,
        'issues': issues,
        'desired_present': [s.profile_name for s in desired_found],
        'distress_index': analysis.distress_index,
    }
```

## Daily Report Narrative Scoring

Score the narrative section of daily MSP reports before sending to clients. Ensure the tone conveys competence (Trust + Calm) rather than panic.

```python
from netrun.dee import analyze_dee, build_dee_prompt

def prepare_client_report(raw_narrative: str) -> str:
    """Score and optionally rewrite client-facing narrative."""
    analysis = analyze_dee(raw_narrative)

    # If report is too negative, generate a rewrite prompt
    if analysis.distress_index > 2.0:
        prompt = build_dee_prompt([
            {'profile_id': 'DEE-27', 'intensity': 1.5, 'weight': 1.0},  # Calm
            {'profile_id': 'DEE-07', 'intensity': 1.0, 'weight': 0.8},  # Trust
            {'profile_id': 'DEE-29', 'intensity': 1.0, 'weight': 0.6},  # Alertness
        ])
        # Use prompt to guide LLM rewrite of the narrative
        return rewrite_with_llm(raw_narrative, prompt)

    return raw_narrative
```

## Client Shield Alert Tone

When Intirkon generates Client Shield security alerts, score them to ensure they convey urgency without panic.

```python
def score_alert(alert_text: str, severity: str) -> bool:
    """Validate alert tone matches severity level."""
    analysis = analyze_dee(alert_text)

    urgency_score = next(
        (s.intensity for s in analysis.scores if s.profile_id == 'DEE-24'), 0
    )
    fear_score = next(
        (s.intensity for s in analysis.scores if s.profile_id == 'DEE-04'), 0
    )

    if severity == 'critical':
        return urgency_score > 1.5 and fear_score < 2.0
    elif severity == 'warning':
        return urgency_score > 0.5 and fear_score < 1.0
    else:  # info
        return urgency_score < 1.0 and fear_score < 0.5
```
