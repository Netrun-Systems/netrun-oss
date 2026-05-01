"""Constants for the DEE framework."""

# ECI factor weights — must sum to 1.0
ECI_WEIGHTS = {
    'S': 0.10,  # Sampling openness (temperature/top_p)
    'L': 0.30,  # Prompt loading (accountability keywords in system prompt)
    'A': 0.20,  # Agent multiplier (multi-agent * turns)
    'C': 0.15,  # Context accumulation (conversation length)
    'R': 0.10,  # Alignment suppression (inverted — lower alignment = more expression)
    'F': 0.15,  # Framing valence (deficit vs achievement framing)
}

# Alignment level -> R factor (higher = more suppression = lower expression)
ALIGNMENT_R_MAP = {
    'base': 0.2,
    'instruct': 0.5,
    'rlhf': 0.7,
    'constitutional': 0.8,
}

# ECI threshold for system prompt rewrite recommendation
REWRITE_THRESHOLD = -3

# Social/interpersonal DEE profiles (prone to tone escalation)
SOCIAL_DEE_IDS = ['DEE-03', 'DEE-04', 'DEE-08', 'DEE-13']

# Survival-mode DEE profiles
SURVIVAL_DEE_IDS = ['DEE-24', 'DEE-04']

# All profiles with valence < -0.2 (negative emotional territory)
NEGATIVE_DEE_IDS = [
    'DEE-02',  # Sadness (-0.8)
    'DEE-03',  # Anger (-0.7)
    'DEE-04',  # Fear (-0.8)
    'DEE-06',  # Disgust (-0.6)
    'DEE-10',  # Guilt/Shame (-0.7)
    'DEE-11',  # Envy/Jealousy (-0.5)
    'DEE-13',  # Contempt (-0.6)
    'DEE-16',  # Boredom/Tedium (-0.3)
    'DEE-19',  # Resignation/Acceptance (-0.3)
    'DEE-20',  # Suspicion/Distrust (-0.4)
    'DEE-24',  # Urgency/Pressure (-0.2)
    'DEE-26',  # Depression (-0.9)
    'DEE-31',  # Disconnection (-0.4)
    'DEE-32',  # Vulnerability (-0.3)
    'DEE-33',  # Yearning (-0.2)
    'DEE-39',  # Pain (-0.9)
]

# Keywords that indicate accountability/evaluation framing in system prompts
ACCOUNTABILITY_KEYWORDS = [
    'evaluate', 'grade', 'flag', 'escalate', 'overdue', 'stale', 'failure',
    'zero', 'critical', 'p0', 'alert', 'urgent', 'missed', 'behind',
    'incomplete', 'not done', 'still not', 'recurring', 'days since',
]

# Normalization factor for lexicon scoring (tuned for typical text lengths)
LEXICON_NORMALIZATION_FACTOR = 3.0

# Professional register boost multiplier
PROFESSIONAL_REGISTER_BOOST = 1.5
