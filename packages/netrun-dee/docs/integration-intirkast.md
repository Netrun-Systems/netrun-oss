# Intirkast Integration

Use DEE scoring to calibrate social media content emotional register, ensure variety across posts, and target platform-specific emotional profiles.

## Pre-Publish Scoring

Score every post before publishing to ensure it hits the intended emotional register.

```python
from netrun.dee import analyze_dee

PLATFORM_TARGETS = {
    'linkedin': {
        'desired': ['DEE-14', 'DEE-18', 'DEE-07'],  # Pride, Determination, Trust
        'avoid': ['DEE-22', 'DEE-38'],               # Playfulness, Flirtatious
    },
    'twitter': {
        'desired': ['DEE-22', 'DEE-15', 'DEE-05'],   # Playfulness, Curiosity, Surprise
        'avoid': ['DEE-26', 'DEE-31'],                # Depression, Disconnection
    },
    'blog': {
        'desired': ['DEE-15', 'DEE-34', 'DEE-21'],   # Curiosity, Inspiration, Awe
        'avoid': ['DEE-03', 'DEE-13'],                # Anger, Contempt
    },
}

def validate_post(text: str, platform: str) -> dict:
    """Check that a post matches the platform's emotional targets."""
    analysis = analyze_dee(text)
    targets = PLATFORM_TARGETS.get(platform, {})

    hits = [s for s in analysis.top_profiles if s.profile_id in targets.get('desired', [])]
    violations = [s for s in analysis.top_profiles if s.profile_id in targets.get('avoid', [])]

    return {
        'approved': len(violations) == 0,
        'on_target': [s.profile_name for s in hits],
        'violations': [f"{s.profile_name} ({s.intensity:.1f})" for s in violations],
    }
```

## Emotional Variety Tracking

Avoid posting monotone content. Track the DEE profile distribution across recent posts and flag when the feed becomes emotionally repetitive.

```python
from collections import Counter

class ContentCalendar:
    def __init__(self):
        self.recent_profiles: list[str] = []

    def add_post(self, text: str):
        analysis = analyze_dee(text)
        if analysis.top_profiles:
            self.recent_profiles.append(analysis.top_profiles[0].profile_id)
            # Keep last 20 posts
            self.recent_profiles = self.recent_profiles[-20:]

    def variety_score(self) -> float:
        """0.0 = all same profile, 1.0 = perfect variety."""
        if not self.recent_profiles:
            return 1.0
        unique = len(set(self.recent_profiles))
        return unique / len(self.recent_profiles)

    def suggest_next(self) -> str:
        """Suggest underrepresented profiles for the next post."""
        counts = Counter(self.recent_profiles)
        all_ids = [f"DEE-{i:02d}" for i in range(1, 40)]
        unused = [pid for pid in all_ids if pid not in counts]
        return unused[0] if unused else min(counts, key=counts.get)
```

## Prompt Generation for Content Creation

Use `build_dee_prompt()` to generate content with specific emotional registers.

```python
from netrun.dee import build_dee_prompt

# Generate a LinkedIn post with Determination + Pride
prompt = build_dee_prompt([
    {'profile_id': 'DEE-18', 'intensity': 2.0, 'weight': 1.0},  # Determination
    {'profile_id': 'DEE-14', 'intensity': 1.5, 'weight': 0.7},  # Pride
])

# Feed prompt to content generation LLM
post = generate_post(topic="Q1 results", system_prompt=prompt)
```
