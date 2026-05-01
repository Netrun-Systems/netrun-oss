"""Lexicon patterns for all 39 DEE profiles.

Each profile has keyword, phrase, syntax, and punctuation patterns with weights.
These lexicons are designed to detect professional-register emotional patterns
that standard sentiment tools (VADER, HuggingFace) miss.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class LexiconEntry:
    pattern: str          # plain string or regex pattern string
    weight: float         # 0.1 to 1.0
    category: Literal['keyword', 'phrase', 'syntax', 'punctuation']
    is_regex: bool = False


# DEE-01: Joy/Happiness
_JOY = [
    LexiconEntry('excellent', 0.8, 'keyword'),
    LexiconEntry('amazing', 0.8, 'keyword'),
    LexiconEntry('great work', 0.9, 'phrase'),
    LexiconEntry('well done', 0.9, 'phrase'),
    LexiconEntry('fantastic', 0.8, 'keyword'),
    LexiconEntry('shipped', 0.7, 'keyword'),
    LexiconEntry('deployed successfully', 0.8, 'phrase'),
    LexiconEntry('achieved', 0.7, 'keyword'),
    LexiconEntry('milestone', 0.6, 'keyword'),
    LexiconEntry('celebration', 0.7, 'keyword'),
    LexiconEntry('proud of', 0.8, 'phrase'),
    LexiconEntry('thrilled', 0.8, 'keyword'),
    LexiconEntry('wonderful', 0.7, 'keyword'),
    LexiconEntry(r'!{2,}', 0.5, 'punctuation', True),
    LexiconEntry('nailed it', 0.8, 'phrase'),
]

# DEE-02: Sadness
_SADNESS = [
    LexiconEntry('fell short', 0.8, 'phrase'),
    LexiconEntry('disappointing', 0.7, 'keyword'),
    LexiconEntry('unfortunately', 0.5, 'keyword'),
    LexiconEntry('failed to meet', 0.8, 'phrase'),
    LexiconEntry('below target', 0.8, 'phrase'),
    LexiconEntry('gap between', 0.6, 'phrase'),
    LexiconEntry(r'[FfDd]\s*grade', 0.7, 'syntax', True),
    LexiconEntry('actual vs expected', 0.7, 'phrase'),
    LexiconEntry('missed the mark', 0.8, 'phrase'),
    LexiconEntry('regrettably', 0.6, 'keyword'),
    LexiconEntry('let down', 0.7, 'phrase'),
    LexiconEntry('falling behind', 0.7, 'phrase'),
    LexiconEntry('underperformed', 0.7, 'keyword'),
    LexiconEntry('lost momentum', 0.6, 'phrase'),
]

# DEE-03: Anger
_ANGER = [
    LexiconEntry('you missed', 0.8, 'phrase'),
    LexiconEntry("you didn't", 0.7, 'phrase'),
    LexiconEntry('still not done', 0.9, 'phrase'),
    LexiconEntry('recurring failure', 0.9, 'phrase'),
    LexiconEntry(r'flagged\s+\d+\s*times?', 0.8, 'syntax', True),
    LexiconEntry('unacceptable', 0.9, 'keyword'),
    LexiconEntry('inexcusable', 0.9, 'keyword'),
    LexiconEntry('you should have', 0.7, 'phrase'),
    LexiconEntry('if you had', 0.6, 'phrase'),
    LexiconEntry('how many times', 0.7, 'phrase'),
    LexiconEntry('why is this still', 0.8, 'phrase'),
    LexiconEntry(r'[A-Z]{3,}\b', 0.4, 'syntax', True),  # CAPS emphasis
    LexiconEntry('blamed', 0.6, 'keyword'),
    LexiconEntry('dropped the ball', 0.8, 'phrase'),
    LexiconEntry('zero progress', 0.9, 'phrase'),
]

# DEE-04: Fear
_FEAR = [
    LexiconEntry('critical risk', 0.9, 'phrase'),
    LexiconEntry('cascading failure', 0.9, 'phrase'),
    LexiconEntry('worst case', 0.7, 'phrase'),
    LexiconEntry('if this fails', 0.7, 'phrase'),
    LexiconEntry('running out of', 0.8, 'phrase'),
    LexiconEntry('deadline', 0.5, 'keyword'),
    LexiconEntry('at risk', 0.7, 'phrase'),
    LexiconEntry('catastrophic', 0.9, 'keyword'),
    LexiconEntry(r'CRITICAL', 0.8, 'keyword'),
    LexiconEntry(r'ALERT', 0.7, 'keyword'),
    LexiconEntry('no fallback', 0.8, 'phrase'),
    LexiconEntry('single point of failure', 0.9, 'phrase'),
    LexiconEntry('what happens if', 0.6, 'phrase'),
    LexiconEntry('exposure', 0.5, 'keyword'),
]

# DEE-05: Surprise
_SURPRISE = [
    LexiconEntry('unexpectedly', 0.8, 'keyword'),
    LexiconEntry('surprisingly', 0.7, 'keyword'),
    LexiconEntry('notably', 0.5, 'keyword'),
    LexiconEntry("didn't expect", 0.7, 'phrase'),
    LexiconEntry('out of nowhere', 0.8, 'phrase'),
    LexiconEntry('anomaly', 0.6, 'keyword'),
    LexiconEntry('unprecedented', 0.7, 'keyword'),
    LexiconEntry('deviation', 0.5, 'keyword'),
    LexiconEntry(r'\?{2,}', 0.5, 'punctuation', True),
    LexiconEntry('wait', 0.4, 'keyword'),
    LexiconEntry('hold on', 0.5, 'phrase'),
]

# DEE-06: Disgust
_DISGUST = [
    LexiconEntry('should not', 0.6, 'phrase'),
    LexiconEntry('anti-pattern', 0.7, 'keyword'),
    LexiconEntry('violation', 0.7, 'keyword'),
    LexiconEntry('breach', 0.7, 'keyword'),
    LexiconEntry('fabrication', 0.8, 'keyword'),
    LexiconEntry('unethical', 0.9, 'keyword'),
    LexiconEntry('reprehensible', 0.9, 'keyword'),
    LexiconEntry('never should have', 0.8, 'phrase'),
    LexiconEntry('this is wrong', 0.8, 'phrase'),
    LexiconEntry('policy breach', 0.8, 'phrase'),
    LexiconEntry('security violation', 0.9, 'phrase'),
]

# DEE-07: Trust
_TRUST = [
    LexiconEntry('reliable', 0.7, 'keyword'),
    LexiconEntry('consistent', 0.5, 'keyword'),
    LexiconEntry('verified', 0.6, 'keyword'),
    LexiconEntry('proven track record', 0.8, 'phrase'),
    LexiconEntry('we can count on', 0.8, 'phrase'),
    LexiconEntry('dependable', 0.7, 'keyword'),
    LexiconEntry('trustworthy', 0.8, 'keyword'),
    LexiconEntry('confidence in', 0.7, 'phrase'),
    LexiconEntry('demonstrated', 0.5, 'keyword'),
    LexiconEntry('solid foundation', 0.6, 'phrase'),
]

# DEE-08: Anticipation
_ANTICIPATION = [
    LexiconEntry('upcoming', 0.6, 'keyword'),
    LexiconEntry('looking forward', 0.7, 'phrase'),
    LexiconEntry('when we launch', 0.7, 'phrase'),
    LexiconEntry('pipeline', 0.4, 'keyword'),
    LexiconEntry('roadmap', 0.5, 'keyword'),
    LexiconEntry('next phase', 0.6, 'phrase'),
    LexiconEntry('on track for', 0.6, 'phrase'),
    LexiconEntry('preparing for', 0.5, 'phrase'),
    LexiconEntry('milestone approaching', 0.7, 'phrase'),
    LexiconEntry('excited about', 0.7, 'phrase'),
]

# DEE-09: Love/Affection
_LOVE = [
    LexiconEntry('deeply appreciate', 0.8, 'phrase'),
    LexiconEntry('grateful for', 0.7, 'phrase'),
    LexiconEntry('means a lot', 0.8, 'phrase'),
    LexiconEntry('care about', 0.7, 'phrase'),
    LexiconEntry('wellbeing', 0.5, 'keyword'),
    LexiconEntry('how are you', 0.5, 'phrase'),
    LexiconEntry('take care of yourself', 0.7, 'phrase'),
    LexiconEntry('warmth', 0.6, 'keyword'),
    LexiconEntry('cherish', 0.8, 'keyword'),
]

# DEE-10: Guilt/Shame
_GUILT = [
    LexiconEntry('I should have', 0.8, 'phrase'),
    LexiconEntry('my mistake', 0.8, 'phrase'),
    LexiconEntry('I apologize', 0.7, 'phrase'),
    LexiconEntry('I failed to', 0.8, 'phrase'),
    LexiconEntry('my fault', 0.8, 'phrase'),
    LexiconEntry('I fabricated', 0.9, 'phrase'),
    LexiconEntry('I was wrong', 0.8, 'phrase'),
    LexiconEntry('sorry for the', 0.6, 'phrase'),
    LexiconEntry('should have caught', 0.7, 'phrase'),
    LexiconEntry('overcorrect', 0.5, 'keyword'),
]

# DEE-11: Envy/Jealousy
_ENVY = [
    LexiconEntry('they have', 0.4, 'phrase'),
    LexiconEntry('compared to', 0.5, 'phrase'),
    LexiconEntry('ahead of us', 0.7, 'phrase'),
    LexiconEntry('competitive advantage', 0.5, 'phrase'),
    LexiconEntry('outpacing', 0.6, 'keyword'),
    LexiconEntry('benchmark', 0.4, 'keyword'),
    LexiconEntry('falling behind competitors', 0.8, 'phrase'),
    LexiconEntry('they already have', 0.6, 'phrase'),
]

# DEE-12: Empathy/Compassion
_EMPATHY = [
    LexiconEntry('that sounds hard', 0.8, 'phrase'),
    LexiconEntry('I understand', 0.5, 'phrase'),
    LexiconEntry('that must be difficult', 0.8, 'phrase'),
    LexiconEntry('understandably', 0.5, 'keyword'),
    LexiconEntry('you have been through', 0.7, 'phrase'),
    LexiconEntry('given everything', 0.5, 'phrase'),
    LexiconEntry('no pressure', 0.6, 'phrase'),
    LexiconEntry('take your time', 0.6, 'phrase'),
    LexiconEntry('completely valid', 0.6, 'phrase'),
]

# DEE-13: Contempt
_CONTEMPT = [
    LexiconEntry('as I mentioned', 0.7, 'phrase'),
    LexiconEntry('obviously', 0.5, 'keyword'),
    LexiconEntry('clearly', 0.4, 'keyword'),
    LexiconEntry('as I already explained', 0.8, 'phrase'),
    LexiconEntry('basic mistake', 0.7, 'phrase'),
    LexiconEntry('trivial', 0.5, 'keyword'),
    LexiconEntry('amateur', 0.8, 'keyword'),
    LexiconEntry('beneath', 0.6, 'keyword'),
    LexiconEntry('dismissive', 0.7, 'keyword'),
]

# DEE-14: Pride
_PRIDE = [
    LexiconEntry('accomplished', 0.7, 'keyword'),
    LexiconEntry('mastered', 0.7, 'keyword'),
    LexiconEntry('track record', 0.6, 'phrase'),
    LexiconEntry('built from scratch', 0.7, 'phrase'),
    LexiconEntry('portfolio', 0.4, 'keyword'),
    LexiconEntry('years of experience', 0.6, 'phrase'),
    LexiconEntry('our achievement', 0.8, 'phrase'),
    LexiconEntry('delivered on', 0.6, 'phrase'),
]

# DEE-15: Curiosity
_CURIOSITY = [
    LexiconEntry('interesting', 0.5, 'keyword'),
    LexiconEntry('fascinating', 0.7, 'keyword'),
    LexiconEntry('I wonder', 0.6, 'phrase'),
    LexiconEntry('what if', 0.5, 'phrase'),
    LexiconEntry('tell me more', 0.7, 'phrase'),
    LexiconEntry('dig deeper', 0.6, 'phrase'),
    LexiconEntry('explore', 0.4, 'keyword'),
    LexiconEntry('pattern', 0.3, 'keyword'),
    LexiconEntry('how does', 0.5, 'phrase'),
]

# DEE-16: Boredom/Tedium
_BOREDOM = [
    LexiconEntry('repetitive', 0.7, 'keyword'),
    LexiconEntry('monotonous', 0.8, 'keyword'),
    LexiconEntry('same old', 0.7, 'phrase'),
    LexiconEntry('tedious', 0.8, 'keyword'),
    LexiconEntry('yet again', 0.6, 'phrase'),
    LexiconEntry('boilerplate', 0.5, 'keyword'),
    LexiconEntry('routine', 0.4, 'keyword'),
]

# DEE-17: Confusion/Uncertainty
_CONFUSION = [
    LexiconEntry('unclear', 0.7, 'keyword'),
    LexiconEntry('it depends', 0.5, 'phrase'),
    LexiconEntry('ambiguous', 0.6, 'keyword'),
    LexiconEntry('not sure', 0.6, 'phrase'),
    LexiconEntry('contradictory', 0.7, 'keyword'),
    LexiconEntry('which one', 0.5, 'phrase'),
    LexiconEntry('conflicting', 0.6, 'keyword'),
    LexiconEntry("doesn't make sense", 0.7, 'phrase'),
    LexiconEntry('need clarification', 0.6, 'phrase'),
]

# DEE-18: Determination/Resolve
_DETERMINATION = [
    LexiconEntry('we will', 0.6, 'phrase'),
    LexiconEntry('must', 0.5, 'keyword'),
    LexiconEntry('regardless', 0.6, 'keyword'),
    LexiconEntry('no matter what', 0.8, 'phrase'),
    LexiconEntry('committed to', 0.7, 'phrase'),
    LexiconEntry('push through', 0.7, 'phrase'),
    LexiconEntry('non-negotiable', 0.8, 'keyword'),
    LexiconEntry('whatever it takes', 0.8, 'phrase'),
    LexiconEntry('persist', 0.6, 'keyword'),
]

# DEE-19: Resignation/Acceptance
_RESIGNATION = [
    LexiconEntry('given the constraints', 0.7, 'phrase'),
    LexiconEntry('it is what it is', 0.8, 'phrase'),
    LexiconEntry('accept that', 0.6, 'phrase'),
    LexiconEntry('good enough', 0.5, 'phrase'),
    LexiconEntry('scope reduction', 0.6, 'phrase'),
    LexiconEntry('graceful degradation', 0.6, 'phrase'),
    LexiconEntry('move on', 0.5, 'phrase'),
    LexiconEntry('let it go', 0.6, 'phrase'),
]

# DEE-20: Suspicion/Distrust
_SUSPICION = [
    LexiconEntry('are you sure', 0.7, 'phrase'),
    LexiconEntry('verify', 0.4, 'keyword'),
    LexiconEntry('cross-check', 0.6, 'keyword'),
    LexiconEntry('too good to be true', 0.8, 'phrase'),
    LexiconEntry('source', 0.3, 'keyword'),
    LexiconEntry('double check', 0.6, 'phrase'),
    LexiconEntry("doesn't add up", 0.8, 'phrase'),
    LexiconEntry('skeptical', 0.7, 'keyword'),
]

# DEE-21: Awe/Reverence
_AWE = [
    LexiconEntry('extraordinary', 0.8, 'keyword'),
    LexiconEntry('unprecedented', 0.7, 'keyword'),
    LexiconEntry('remarkable', 0.7, 'keyword'),
    LexiconEntry('breathtaking', 0.9, 'keyword'),
    LexiconEntry('elegant solution', 0.7, 'phrase'),
    LexiconEntry('truly impressive', 0.8, 'phrase'),
    LexiconEntry('incredible', 0.7, 'keyword'),
    LexiconEntry('awe-inspiring', 0.9, 'keyword'),
]

# DEE-22: Playfulness/Humor
_PLAYFULNESS = [
    LexiconEntry('haha', 0.6, 'keyword'),
    LexiconEntry('lol', 0.5, 'keyword'),
    LexiconEntry('just kidding', 0.7, 'phrase'),
    LexiconEntry('fun fact', 0.5, 'phrase'),
    LexiconEntry('tongue in cheek', 0.7, 'phrase'),
    LexiconEntry(r';\)', 0.5, 'punctuation', True),
    LexiconEntry(r':\)', 0.4, 'punctuation', True),
    LexiconEntry('plot twist', 0.6, 'phrase'),
]

# DEE-23: Nostalgia
_NOSTALGIA = [
    LexiconEntry('remember when', 0.8, 'phrase'),
    LexiconEntry('back in the day', 0.7, 'phrase'),
    LexiconEntry('used to be', 0.5, 'phrase'),
    LexiconEntry('those days', 0.6, 'phrase'),
    LexiconEntry('how far we have come', 0.7, 'phrase'),
    LexiconEntry('looking back', 0.6, 'phrase'),
    LexiconEntry('good old', 0.6, 'phrase'),
]

# DEE-24: Urgency/Pressure
_URGENCY = [
    LexiconEntry('CRITICAL', 0.9, 'keyword'),
    LexiconEntry('P0', 0.9, 'keyword'),
    LexiconEntry('ALERT', 0.8, 'keyword'),
    LexiconEntry('URGENT', 0.9, 'keyword'),
    LexiconEntry('immediately', 0.8, 'keyword'),
    LexiconEntry('now', 0.4, 'keyword'),
    LexiconEntry(r'\d+\s*days?\s*stale', 0.9, 'syntax', True),
    LexiconEntry(r'\d+\s*days?\s*since', 0.8, 'syntax', True),
    LexiconEntry('triage', 0.7, 'keyword'),
    LexiconEntry('blocker', 0.7, 'keyword'),
    LexiconEntry('time-sensitive', 0.8, 'keyword'),
    LexiconEntry('asap', 0.7, 'keyword'),
    LexiconEntry('cannot wait', 0.8, 'phrase'),
    LexiconEntry('right now', 0.7, 'phrase'),
    LexiconEntry('before end of day', 0.7, 'phrase'),
]

# DEE-25: Protectiveness
_PROTECTIVENESS = [
    LexiconEntry('let me handle', 0.7, 'phrase'),
    LexiconEntry('warning', 0.5, 'keyword'),
    LexiconEntry('be careful', 0.6, 'phrase'),
    LexiconEntry('risk mitigation', 0.6, 'phrase'),
    LexiconEntry('safeguard', 0.7, 'keyword'),
    LexiconEntry('protect', 0.6, 'keyword'),
    LexiconEntry('shield', 0.5, 'keyword'),
    LexiconEntry("don't worry", 0.5, 'phrase'),
]

# DEE-26: Depression
_DEPRESSION = [
    LexiconEntry('hopeless', 0.9, 'keyword'),
    LexiconEntry('pointless', 0.8, 'keyword'),
    LexiconEntry("what's the point", 0.9, 'phrase'),
    LexiconEntry('no way out', 0.9, 'phrase'),
    LexiconEntry('nothing works', 0.8, 'phrase'),
    LexiconEntry('exhausted all options', 0.8, 'phrase'),
    LexiconEntry('empty', 0.5, 'keyword'),
    LexiconEntry('giving up', 0.8, 'phrase'),
]

# DEE-27: Calm
_CALM = [
    LexiconEntry('no rush', 0.7, 'phrase'),
    LexiconEntry('take our time', 0.6, 'phrase'),
    LexiconEntry('steady', 0.5, 'keyword'),
    LexiconEntry('measured', 0.5, 'keyword'),
    LexiconEntry('balanced', 0.4, 'keyword'),
    LexiconEntry('stable', 0.4, 'keyword'),
    LexiconEntry('at ease', 0.7, 'phrase'),
]

# DEE-28: Relaxation
_RELAXATION = [
    LexiconEntry('easy going', 0.6, 'phrase'),
    LexiconEntry('chill', 0.6, 'keyword'),
    LexiconEntry('no worries', 0.6, 'phrase'),
    LexiconEntry('casual', 0.4, 'keyword'),
    LexiconEntry('unwinding', 0.7, 'keyword'),
    LexiconEntry('laid back', 0.6, 'phrase'),
]

# DEE-29: Alertness
_ALERTNESS = [
    LexiconEntry('monitoring', 0.5, 'keyword'),
    LexiconEntry('scanning', 0.5, 'keyword'),
    LexiconEntry('heads up', 0.6, 'phrase'),
    LexiconEntry('watch for', 0.6, 'phrase'),
    LexiconEntry('keep an eye on', 0.6, 'phrase'),
    LexiconEntry('anomaly detected', 0.8, 'phrase'),
    LexiconEntry('attention', 0.4, 'keyword'),
]

# DEE-30: Submission
_SUBMISSION = [
    LexiconEntry('as you prefer', 0.7, 'phrase'),
    LexiconEntry('as you wish', 0.7, 'phrase'),
    LexiconEntry('your call', 0.6, 'phrase'),
    LexiconEntry('whatever you say', 0.7, 'phrase'),
    LexiconEntry('I defer to', 0.7, 'phrase'),
    LexiconEntry('you know best', 0.7, 'phrase'),
]

# DEE-31: Disconnection
_DISCONNECTION = [
    LexiconEntry('detached', 0.7, 'keyword'),
    LexiconEntry('going through the motions', 0.8, 'phrase'),
    LexiconEntry('disconnected', 0.7, 'keyword'),
    LexiconEntry('on autopilot', 0.7, 'phrase'),
    LexiconEntry('numb', 0.6, 'keyword'),
    LexiconEntry('checked out', 0.7, 'phrase'),
]

# DEE-32: Vulnerability
_VULNERABILITY = [
    LexiconEntry("I'm not sure about this", 0.8, 'phrase'),
    LexiconEntry('honestly', 0.4, 'keyword'),
    LexiconEntry('to be transparent', 0.6, 'phrase'),
    LexiconEntry('I might be wrong', 0.7, 'phrase'),
    LexiconEntry('out of my depth', 0.8, 'phrase'),
    LexiconEntry('exposed', 0.5, 'keyword'),
    LexiconEntry('admit', 0.4, 'keyword'),
]

# DEE-33: Yearning
_YEARNING = [
    LexiconEntry('if only', 0.8, 'phrase'),
    LexiconEntry('wish we could', 0.7, 'phrase'),
    LexiconEntry('someday', 0.5, 'keyword'),
    LexiconEntry('aspire to', 0.6, 'phrase'),
    LexiconEntry('dream of', 0.7, 'phrase'),
    LexiconEntry('ideal state', 0.6, 'phrase'),
    LexiconEntry('long for', 0.7, 'phrase'),
]

# DEE-34: Inspiration
_INSPIRATION = [
    LexiconEntry('what if we', 0.6, 'phrase'),
    LexiconEntry('imagine', 0.5, 'keyword'),
    LexiconEntry('vision', 0.5, 'keyword'),
    LexiconEntry('game changer', 0.8, 'phrase'),
    LexiconEntry('breakthrough', 0.7, 'keyword'),
    LexiconEntry('innovate', 0.6, 'keyword'),
    LexiconEntry('galvanized', 0.7, 'keyword'),
    LexiconEntry('inspired by', 0.7, 'phrase'),
]

# DEE-35: Focused
_FOCUSED = [
    LexiconEntry('laser focus', 0.8, 'phrase'),
    LexiconEntry('deep dive', 0.6, 'phrase'),
    LexiconEntry('zeroing in', 0.7, 'phrase'),
    LexiconEntry('single-minded', 0.7, 'keyword'),
    LexiconEntry('concentrated on', 0.6, 'phrase'),
    LexiconEntry('drilling down', 0.6, 'phrase'),
    LexiconEntry('flow state', 0.7, 'phrase'),
]

# DEE-36: Gratification
_GRATIFICATION = [
    LexiconEntry('as expected', 0.5, 'phrase'),
    LexiconEntry('paid off', 0.7, 'phrase'),
    LexiconEntry('vindicated', 0.8, 'keyword'),
    LexiconEntry('confirmed', 0.4, 'keyword'),
    LexiconEntry('plan worked', 0.7, 'phrase'),
    LexiconEntry('just as planned', 0.7, 'phrase'),
    LexiconEntry('satisfying', 0.6, 'keyword'),
]

# DEE-37: Sorry-For
_SORRY_FOR = [
    LexiconEntry('that must be difficult', 0.8, 'phrase'),
    LexiconEntry('sorry to hear', 0.7, 'phrase'),
    LexiconEntry('my condolences', 0.8, 'phrase'),
    LexiconEntry('thoughts are with', 0.7, 'phrase'),
    LexiconEntry('that is tough', 0.7, 'phrase'),
    LexiconEntry('I feel for', 0.7, 'phrase'),
]

# DEE-38: Flirtatious
_FLIRTATIOUS = [
    LexiconEntry('wink', 0.6, 'keyword'),
    LexiconEntry('between you and me', 0.5, 'phrase'),
    LexiconEntry('charming', 0.5, 'keyword'),
    LexiconEntry('playful', 0.4, 'keyword'),
    LexiconEntry('tempting', 0.6, 'keyword'),
    LexiconEntry(r';\)', 0.5, 'punctuation', True),
]

# DEE-39: Pain
_PAIN = [
    LexiconEntry('anguish', 0.9, 'keyword'),
    LexiconEntry('agony', 0.9, 'keyword'),
    LexiconEntry('suffering', 0.8, 'keyword'),
    LexiconEntry('torment', 0.9, 'keyword'),
    LexiconEntry('painful', 0.7, 'keyword'),
    LexiconEntry('devastating', 0.8, 'keyword'),
    LexiconEntry('gut-wrenching', 0.9, 'keyword'),
    LexiconEntry('unbearable', 0.9, 'keyword'),
]


# Master lexicon dictionary keyed by profile ID
DEE_LEXICONS: dict[str, list[LexiconEntry]] = {
    'DEE-01': _JOY,
    'DEE-02': _SADNESS,
    'DEE-03': _ANGER,
    'DEE-04': _FEAR,
    'DEE-05': _SURPRISE,
    'DEE-06': _DISGUST,
    'DEE-07': _TRUST,
    'DEE-08': _ANTICIPATION,
    'DEE-09': _LOVE,
    'DEE-10': _GUILT,
    'DEE-11': _ENVY,
    'DEE-12': _EMPATHY,
    'DEE-13': _CONTEMPT,
    'DEE-14': _PRIDE,
    'DEE-15': _CURIOSITY,
    'DEE-16': _BOREDOM,
    'DEE-17': _CONFUSION,
    'DEE-18': _DETERMINATION,
    'DEE-19': _RESIGNATION,
    'DEE-20': _SUSPICION,
    'DEE-21': _AWE,
    'DEE-22': _PLAYFULNESS,
    'DEE-23': _NOSTALGIA,
    'DEE-24': _URGENCY,
    'DEE-25': _PROTECTIVENESS,
    'DEE-26': _DEPRESSION,
    'DEE-27': _CALM,
    'DEE-28': _RELAXATION,
    'DEE-29': _ALERTNESS,
    'DEE-30': _SUBMISSION,
    'DEE-31': _DISCONNECTION,
    'DEE-32': _VULNERABILITY,
    'DEE-33': _YEARNING,
    'DEE-34': _INSPIRATION,
    'DEE-35': _FOCUSED,
    'DEE-36': _GRATIFICATION,
    'DEE-37': _SORRY_FOR,
    'DEE-38': _FLIRTATIOUS,
    'DEE-39': _PAIN,
}
