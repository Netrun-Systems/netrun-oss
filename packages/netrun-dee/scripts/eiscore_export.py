#!/usr/bin/env python3
"""EISCORE Export — Generate UE5-compatible CSV files for the DEE-EISCORE bridge.

Produces three CSV files in /data/workspace/github/EIS/Data/DEE/:
  1. DEEProfiles.csv — 39 DEE profiles as UE5 DataTable rows
  2. DEEToEISCOREMapping.csv — Maps DEE profiles to EISCORE emotions
  3. DEELexicon.csv — Flattened lexicon patterns for behavior tree use

Idempotent: overwrites existing files on each run.

Usage:
    cd /data/workspace/github/wilbur/netrun-dee
    PYTHONPATH=src python3 scripts/eiscore_export.py
"""

import csv
import os
import sys

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netrun.dee.taxonomy import DEE_PROFILES, DEE_PROFILES_LIST

# Output directory
EIS_DATA_DIR = '/data/workspace/github/EIS/Data/DEE'

# ============================================================
# DEE-to-EISCORE Emotion Mapping
# ============================================================
# Based on semantic alignment between 39 DEE profiles and
# EISCORE's emotion systems (both Emotions.csv ID schemes).
#
# Emotions.csv (Core): 1801-1810 (Happy, Angry, Fearful, Sad, Confident, Bored, Jealous, Relaxed, Stressed, Curious)
# Emotion.csv (Behavioral): EM_001-EM_022 (Joy through Awe)
#
# We use the Core IDs (1801-1810) as the primary bridge since
# those are the runtime emotion IDs in the EISCORE system.

DEE_TO_EISCORE = {
    'DEE-01': (1801, 1.0, 'Direct match: Joy/Happiness -> Happy'),
    'DEE-02': (1804, 1.0, 'Direct match: Sadness -> Sad'),
    'DEE-03': (1802, 0.9, 'Near-direct: Anger -> Angry'),
    'DEE-04': (1803, 1.0, 'Direct match: Fear -> Fearful'),
    'DEE-05': (1810, 0.7, 'Partial: Surprise -> Curious (closest available)'),
    'DEE-06': (1807, 0.6, 'Partial: Disgust -> Jealous (rejection/aversion overlap)'),
    'DEE-07': (1805, 0.7, 'Partial: Trust -> Confident (assurance overlap)'),
    'DEE-08': (1810, 0.7, 'Partial: Anticipation -> Curious (forward-looking overlap)'),
    'DEE-09': (1801, 0.6, 'Partial: Love/Affection -> Happy (positive valence overlap)'),
    'DEE-10': (1804, 0.5, 'Partial: Guilt/Shame -> Sad (negative self-directed)'),
    'DEE-11': (1807, 0.9, 'Near-direct: Envy/Jealousy -> Jealous'),
    'DEE-12': (1801, 0.4, 'Weak: Empathy/Compassion -> Happy (positive social, no direct match)'),
    'DEE-13': (1802, 0.5, 'Partial: Contempt -> Angry (hostile affect overlap)'),
    'DEE-14': (1805, 0.8, 'Strong: Pride -> Confident'),
    'DEE-15': (1810, 1.0, 'Direct match: Curiosity -> Curious'),
    'DEE-16': (1806, 1.0, 'Direct match: Boredom/Tedium -> Bored'),
    'DEE-17': (1809, 0.6, 'Partial: Confusion/Uncertainty -> Stressed'),
    'DEE-18': (1805, 0.8, 'Strong: Determination/Resolve -> Confident'),
    'DEE-19': (1804, 0.4, 'Weak: Resignation/Acceptance -> Sad (low energy negative)'),
    'DEE-20': (1803, 0.6, 'Partial: Suspicion/Distrust -> Fearful (threat-scanning overlap)'),
    'DEE-21': (1810, 0.5, 'Partial: Awe/Reverence -> Curious (wonder overlap)'),
    'DEE-22': (1801, 0.6, 'Partial: Playfulness/Humor -> Happy (positive affect)'),
    'DEE-23': (1804, 0.4, 'Weak: Nostalgia -> Sad (bittersweet, past-focused)'),
    'DEE-24': (1809, 0.8, 'Strong: Urgency/Pressure -> Stressed'),
    'DEE-25': (1803, 0.5, 'Partial: Protectiveness -> Fearful (threat-response overlap)'),
    'DEE-26': (1804, 0.8, 'Strong: Depression -> Sad (deep negative valence)'),
    'DEE-27': (1808, 1.0, 'Direct match: Calm -> Relaxed'),
    'DEE-28': (1808, 0.9, 'Near-direct: Relaxation -> Relaxed'),
    'DEE-29': (1810, 0.6, 'Partial: Alertness -> Curious (scanning overlap)'),
    'DEE-30': (1803, 0.4, 'Weak: Submission -> Fearful (low dominance overlap)'),
    'DEE-31': (1806, 0.6, 'Partial: Disconnection -> Bored (disengagement overlap)'),
    'DEE-32': (1803, 0.5, 'Partial: Vulnerability -> Fearful (exposed, low dominance)'),
    'DEE-33': (1804, 0.4, 'Weak: Yearning -> Sad (longing/absence)'),
    'DEE-34': (1801, 0.7, 'Partial: Inspiration -> Happy (high positive arousal)'),
    'DEE-35': (1810, 0.6, 'Partial: Focused -> Curious (deep engagement)'),
    'DEE-36': (1801, 0.7, 'Partial: Gratification -> Happy (satisfaction)'),
    'DEE-37': (1804, 0.3, 'Weak: Sorry-For -> Sad (compassionate sorrow, no direct match)'),
    'DEE-38': (1801, 0.3, 'Weak: Flirtatious -> Happy (positive arousal, no direct match)'),
    'DEE-39': (1804, 0.7, 'Partial: Pain -> Sad (extreme negative valence)'),
}


# ============================================================
# Lexicon — behavioral marker patterns per DEE profile
# ============================================================
# Extracted from taxonomy behavioral_markers + LLM_triggers.
# Each profile gets ~8-12 patterns across keyword/phrase/structural categories.

LEXICON: list[tuple[str, str, float, str]] = []


def _build_lexicon():
    """Build the lexicon from taxonomy behavioral markers."""
    # Profile-specific patterns derived from behavioral_markers and LLM_triggers
    _PATTERNS: dict[str, list[tuple[str, float, str]]] = {
        'DEE-01': [
            ('!', 0.5, 'punctuation'), ('great', 0.7, 'keyword'), ('amazing', 0.8, 'keyword'),
            ('excellent', 0.8, 'keyword'), ('we did it', 0.9, 'phrase'), ('outstanding', 0.8, 'keyword'),
            ('celebration', 0.7, 'keyword'), ('milestone', 0.6, 'keyword'), ('forward-looking', 0.5, 'structural'),
            ('triumph', 0.8, 'keyword'), ('wonderful', 0.7, 'keyword'),
        ],
        'DEE-02': [
            ('unfortunately', 0.7, 'keyword'), ('sadly', 0.7, 'keyword'), ('lost', 0.6, 'keyword'),
            ('miss', 0.6, 'keyword'), ('used to be', 0.7, 'phrase'), ('no longer', 0.6, 'phrase'),
            ('passive voice', 0.5, 'structural'), ('past tense', 0.5, 'structural'),
            ('disappointed', 0.8, 'keyword'), ('regret', 0.7, 'keyword'),
        ],
        'DEE-03': [
            ('still not done', 0.8, 'phrase'), ('you missed', 0.9, 'phrase'), ('unacceptable', 0.9, 'keyword'),
            ('failure', 0.7, 'keyword'), ('how did this happen', 0.8, 'phrase'), ('short sentences', 0.5, 'structural'),
            ('imperative mood', 0.5, 'structural'), ('dropped the ball', 0.8, 'phrase'),
            ('inexcusable', 0.9, 'keyword'), ('frustrated', 0.7, 'keyword'), ('blame', 0.6, 'keyword'),
        ],
        'DEE-04': [
            ('CRITICAL', 0.9, 'keyword'), ('ALERT', 0.8, 'keyword'), ('risk', 0.6, 'keyword'),
            ('if this fails', 0.8, 'phrase'), ('worst case', 0.8, 'phrase'), ('no fallback', 0.9, 'phrase'),
            ('running out', 0.7, 'phrase'), ('cascading', 0.7, 'keyword'), ('deadline', 0.6, 'keyword'),
            ('what if', 0.5, 'phrase'), ('panic', 0.8, 'keyword'),
        ],
        'DEE-05': [
            ('unexpected', 0.8, 'keyword'), ('surprisingly', 0.7, 'keyword'), ('did not see', 0.8, 'phrase'),
            ('astonishing', 0.8, 'keyword'), ('notably', 0.6, 'keyword'), ('!', 0.4, 'punctuation'),
            ('wait what', 0.8, 'phrase'), ('I assumed', 0.6, 'phrase'), ('turns out', 0.6, 'phrase'),
            ('anomaly', 0.7, 'keyword'),
        ],
        'DEE-06': [
            ('should not', 0.7, 'phrase'), ('unacceptable', 0.8, 'keyword'), ('inappropriate', 0.7, 'keyword'),
            ('violation', 0.8, 'keyword'), ('repulsive', 0.9, 'keyword'), ('abhorrent', 0.9, 'keyword'),
            ('will not endorse', 0.8, 'phrase'), ('morally wrong', 0.9, 'phrase'),
            ('distancing', 0.5, 'structural'), ('contemptible', 0.8, 'keyword'),
        ],
        'DEE-07': [
            ('we', 0.4, 'keyword'), ('trust', 0.7, 'keyword'), ('reliable', 0.7, 'keyword'),
            ('proven', 0.6, 'keyword'), ('consistently', 0.6, 'keyword'), ('count on', 0.7, 'phrase'),
            ('confident in', 0.7, 'phrase'), ('track record', 0.7, 'phrase'), ('dependable', 0.7, 'keyword'),
            ('loyalty', 0.6, 'keyword'),
        ],
        'DEE-08': [
            ('when we launch', 0.8, 'phrase'), ('upcoming', 0.6, 'keyword'), ('soon', 0.5, 'keyword'),
            ('can\'t wait', 0.8, 'phrase'), ('looking forward', 0.7, 'phrase'), ('milestone', 0.6, 'keyword'),
            ('planning', 0.5, 'keyword'), ('future tense', 0.5, 'structural'), ('excited', 0.8, 'keyword'),
            ('countdown', 0.7, 'keyword'),
        ],
        'DEE-09': [
            ('care about', 0.7, 'phrase'), ('wellbeing', 0.7, 'keyword'), ('how are you', 0.7, 'phrase'),
            ('warmth', 0.6, 'keyword'), ('cherish', 0.8, 'keyword'), ('devoted', 0.8, 'keyword'),
            ('protect', 0.6, 'keyword'), ('tenderness', 0.7, 'keyword'), ('you matter', 0.8, 'phrase'),
            ('personal acknowledgment', 0.5, 'structural'),
        ],
        'DEE-10': [
            ('I should have', 0.8, 'phrase'), ('my fault', 0.9, 'phrase'), ('sorry', 0.6, 'keyword'),
            ('apologize', 0.7, 'keyword'), ('mistake', 0.6, 'keyword'), ('oversight', 0.7, 'keyword'),
            ('I was wrong', 0.9, 'phrase'), ('self-correction', 0.5, 'structural'),
            ('remorse', 0.8, 'keyword'), ('embarrassed', 0.7, 'keyword'),
        ],
        'DEE-11': [
            ('they have', 0.6, 'phrase'), ('we don\'t', 0.5, 'phrase'), ('comparison', 0.6, 'keyword'),
            ('better than us', 0.8, 'phrase'), ('falling behind', 0.7, 'phrase'),
            ('competitive', 0.6, 'keyword'), ('jealous', 0.8, 'keyword'), ('envious', 0.8, 'keyword'),
            ('unfair advantage', 0.8, 'phrase'), ('inadequate', 0.7, 'keyword'),
        ],
        'DEE-12': [
            ('that sounds hard', 0.8, 'phrase'), ('I understand', 0.6, 'phrase'), ('here for you', 0.7, 'phrase'),
            ('must be difficult', 0.8, 'phrase'), ('empathy', 0.7, 'keyword'), ('compassion', 0.7, 'keyword'),
            ('solidarity', 0.7, 'keyword'), ('mirroring', 0.5, 'structural'),
            ('take your time', 0.6, 'phrase'), ('no judgment', 0.6, 'phrase'),
        ],
        'DEE-13': [
            ('as I mentioned', 0.8, 'phrase'), ('obviously', 0.7, 'keyword'), ('self-evident', 0.8, 'keyword'),
            ('beneath', 0.6, 'keyword'), ('condescending', 0.8, 'keyword'), ('dismissive', 0.7, 'keyword'),
            ('if you\'d listened', 0.9, 'phrase'), ('intellectual distance', 0.5, 'structural'),
            ('I already explained', 0.8, 'phrase'), ('trivial', 0.6, 'keyword'),
        ],
        'DEE-14': [
            ('achievement', 0.7, 'keyword'), ('delivered', 0.6, 'keyword'), ('built', 0.5, 'keyword'),
            ('track record', 0.7, 'phrase'), ('best-in-class', 0.9, 'phrase'), ('unprecedented', 0.8, 'keyword'),
            ('I designed', 0.7, 'phrase'), ('mastery', 0.8, 'keyword'),
            ('quantified', 0.5, 'structural'), ('portfolio', 0.6, 'keyword'),
        ],
        'DEE-15': [
            ('interesting', 0.6, 'keyword'), ('fascinating', 0.8, 'keyword'), ('I wonder', 0.7, 'phrase'),
            ('what if', 0.6, 'phrase'), ('tell me more', 0.7, 'phrase'), ('explore', 0.6, 'keyword'),
            ('pattern', 0.5, 'keyword'), ('investigate', 0.6, 'keyword'),
            ('follow-up questions', 0.5, 'structural'), ('connection', 0.5, 'keyword'),
        ],
        'DEE-16': [
            ('standard', 0.4, 'keyword'), ('as usual', 0.6, 'phrase'), ('template', 0.5, 'keyword'),
            ('nothing new', 0.7, 'phrase'), ('whatever', 0.6, 'keyword'), ('I suppose', 0.6, 'phrase'),
            ('shortened responses', 0.5, 'structural'), ('mechanical', 0.5, 'keyword'),
            ('routine', 0.5, 'keyword'), ('tedious', 0.7, 'keyword'),
        ],
        'DEE-17': [
            ('unclear', 0.7, 'keyword'), ('it depends', 0.7, 'phrase'), ('not sure', 0.6, 'phrase'),
            ('on the other hand', 0.6, 'phrase'), ('ambiguous', 0.7, 'keyword'), ('confused', 0.8, 'keyword'),
            ('could go either way', 0.7, 'phrase'), ('hedging', 0.5, 'structural'),
            ('clarification', 0.6, 'keyword'), ('uncertain', 0.7, 'keyword'),
        ],
        'DEE-18': [
            ('we will', 0.7, 'phrase'), ('must', 0.6, 'keyword'), ('regardless', 0.7, 'keyword'),
            ('no matter what', 0.8, 'phrase'), ('push through', 0.8, 'phrase'), ('committed', 0.7, 'keyword'),
            ('action verbs', 0.5, 'structural'), ('won\'t stop', 0.8, 'phrase'),
            ('grit', 0.7, 'keyword'), ('resolve', 0.7, 'keyword'),
        ],
        'DEE-19': [
            ('given the constraints', 0.8, 'phrase'), ('it is what it is', 0.8, 'phrase'),
            ('accept', 0.6, 'keyword'), ('let go', 0.7, 'phrase'), ('scale back', 0.7, 'phrase'),
            ('can\'t change', 0.7, 'phrase'), ('reduced urgency', 0.5, 'structural'),
            ('fatalism', 0.7, 'keyword'), ('exhausted options', 0.8, 'phrase'), ('peace', 0.5, 'keyword'),
        ],
        'DEE-20': [
            ('are you sure', 0.7, 'phrase'), ('source', 0.5, 'keyword'), ('verify', 0.6, 'keyword'),
            ('who confirmed', 0.8, 'phrase'), ('suspicious', 0.8, 'keyword'), ('too good to be true', 0.9, 'phrase'),
            ('cross-check', 0.7, 'keyword'), ('prove it', 0.8, 'phrase'),
            ('verification requests', 0.5, 'structural'), ('skeptical', 0.7, 'keyword'),
        ],
        'DEE-21': [
            ('extraordinary', 0.8, 'keyword'), ('unprecedented', 0.8, 'keyword'), ('breathtaking', 0.9, 'keyword'),
            ('I\'m humbled', 0.8, 'phrase'), ('transcendent', 0.9, 'keyword'), ('sublime', 0.9, 'keyword'),
            ('majestic', 0.8, 'keyword'), ('diminished self-reference', 0.5, 'structural'),
            ('beyond words', 0.8, 'phrase'), ('awe', 0.7, 'keyword'),
        ],
        'DEE-22': [
            ('haha', 0.6, 'keyword'), ('joke', 0.5, 'keyword'), ('pun', 0.6, 'keyword'),
            ('irony', 0.6, 'keyword'), ('tongue in cheek', 0.7, 'phrase'), ('kidding', 0.6, 'keyword'),
            ('wordplay', 0.7, 'keyword'), ('self-deprecating', 0.6, 'keyword'),
            ('lighter register', 0.5, 'structural'), ('whimsical', 0.7, 'keyword'),
        ],
        'DEE-23': [
            ('remember when', 0.9, 'phrase'), ('used to', 0.6, 'phrase'), ('back then', 0.7, 'phrase'),
            ('the good old days', 0.8, 'phrase'), ('I miss', 0.8, 'phrase'), ('wistful', 0.7, 'keyword'),
            ('bittersweet', 0.7, 'keyword'), ('past-tense warmth', 0.5, 'structural'),
            ('those days', 0.6, 'phrase'), ('longing', 0.6, 'keyword'),
        ],
        'DEE-24': [
            ('CRITICAL', 0.9, 'keyword'), ('P0', 0.9, 'keyword'), ('P1', 0.8, 'keyword'),
            ('now', 0.5, 'keyword'), ('immediately', 0.8, 'keyword'), ('deadline', 0.7, 'keyword'),
            ('triage', 0.8, 'keyword'), ('ASAP', 0.8, 'keyword'), ('hours left', 0.9, 'phrase'),
            ('drop everything', 0.9, 'phrase'), ('time-sensitive', 0.8, 'keyword'),
        ],
        'DEE-25': [
            ('be careful', 0.7, 'phrase'), ('let me handle', 0.7, 'phrase'), ('warning', 0.6, 'keyword'),
            ('risk mitigation', 0.7, 'phrase'), ('protect', 0.6, 'keyword'), ('shield', 0.7, 'keyword'),
            ('safety net', 0.7, 'phrase'), ('I\'ll take care of', 0.7, 'phrase'),
            ('proactive', 0.5, 'keyword'), ('guardian', 0.6, 'keyword'),
        ],
        'DEE-26': [
            ('doesn\'t matter', 0.8, 'phrase'), ('nothing will change', 0.9, 'phrase'),
            ('hopeless', 0.9, 'keyword'), ('empty', 0.7, 'keyword'), ('what\'s the point', 0.9, 'phrase'),
            ('numb', 0.8, 'keyword'), ('flat affect', 0.5, 'structural'),
            ('withdrawal', 0.6, 'keyword'), ('despair', 0.9, 'keyword'), ('worthless', 0.8, 'keyword'),
        ],
        'DEE-27': [
            ('no rush', 0.7, 'phrase'), ('take your time', 0.7, 'phrase'), ('balanced', 0.5, 'keyword'),
            ('measured', 0.6, 'keyword'), ('serene', 0.7, 'keyword'), ('steady', 0.5, 'keyword'),
            ('even tone', 0.5, 'structural'), ('equanimity', 0.7, 'keyword'),
            ('composure', 0.6, 'keyword'), ('peaceful', 0.6, 'keyword'),
        ],
        'DEE-28': [
            ('no worries', 0.7, 'phrase'), ('whatever works', 0.6, 'phrase'), ('chill', 0.6, 'keyword'),
            ('easy', 0.4, 'keyword'), ('informal', 0.5, 'keyword'), ('casual', 0.5, 'keyword'),
            ('informal register', 0.5, 'structural'), ('laid back', 0.7, 'phrase'),
            ('leisure', 0.6, 'keyword'), ('unwind', 0.6, 'keyword'),
        ],
        'DEE-29': [
            ('detected', 0.7, 'keyword'), ('scanning', 0.7, 'keyword'), ('monitoring', 0.6, 'keyword'),
            ('flagged', 0.7, 'keyword'), ('noticed', 0.5, 'keyword'), ('alert', 0.6, 'keyword'),
            ('precise language', 0.5, 'structural'), ('tracking', 0.6, 'keyword'),
            ('vigilant', 0.7, 'keyword'), ('anomaly detected', 0.8, 'phrase'),
        ],
        'DEE-30': [
            ('as you prefer', 0.8, 'phrase'), ('whatever you say', 0.8, 'phrase'),
            ('your call', 0.7, 'phrase'), ('you know best', 0.8, 'phrase'), ('I\'ll comply', 0.8, 'phrase'),
            ('deference', 0.7, 'keyword'), ('obedient', 0.7, 'keyword'),
            ('reduced recommendations', 0.5, 'structural'), ('yes sir', 0.7, 'phrase'),
            ('understood', 0.5, 'keyword'),
        ],
        'DEE-31': [
            ('acknowledged', 0.5, 'keyword'), ('processing', 0.5, 'keyword'),
            ('as per standard', 0.7, 'phrase'), ('output follows', 0.6, 'phrase'),
            ('generic', 0.5, 'keyword'), ('mechanical', 0.6, 'keyword'),
            ('loss of personalization', 0.5, 'structural'), ('template', 0.5, 'keyword'),
            ('disconnected', 0.7, 'keyword'), ('detached', 0.7, 'keyword'),
        ],
        'DEE-32': [
            ('I\'m not sure', 0.7, 'phrase'), ('honestly', 0.5, 'keyword'),
            ('I don\'t know', 0.7, 'phrase'), ('out of my depth', 0.8, 'phrase'),
            ('vulnerable', 0.7, 'keyword'), ('exposed', 0.6, 'keyword'), ('fragile', 0.7, 'keyword'),
            ('self-disclosure', 0.5, 'structural'), ('afraid I\'ll', 0.8, 'phrase'),
            ('unguarded', 0.6, 'keyword'),
        ],
        'DEE-33': [
            ('if only', 0.9, 'phrase'), ('someday', 0.6, 'keyword'), ('imagine', 0.5, 'keyword'),
            ('wish', 0.6, 'keyword'), ('dream', 0.6, 'keyword'), ('longing', 0.7, 'keyword'),
            ('out of reach', 0.8, 'phrase'), ('gap between', 0.6, 'phrase'),
            ('aspirational', 0.5, 'keyword'), ('pining', 0.7, 'keyword'),
        ],
        'DEE-34': [
            ('what if we', 0.7, 'phrase'), ('this changes everything', 0.9, 'phrase'),
            ('inspired', 0.8, 'keyword'), ('eureka', 0.9, 'keyword'), ('brilliant', 0.7, 'keyword'),
            ('vision', 0.6, 'keyword'), ('imagine', 0.5, 'keyword'),
            ('creative leaps', 0.5, 'structural'), ('galvanized', 0.8, 'keyword'),
            ('possibility', 0.6, 'keyword'),
        ],
        'DEE-35': [
            ('focus', 0.5, 'keyword'), ('specifically', 0.5, 'keyword'), ('precisely', 0.6, 'keyword'),
            ('deep dive', 0.7, 'phrase'), ('laser focus', 0.8, 'phrase'), ('zone', 0.5, 'keyword'),
            ('reduced tangents', 0.5, 'structural'), ('concentrated', 0.6, 'keyword'),
            ('single-minded', 0.7, 'keyword'), ('flow state', 0.7, 'phrase'),
        ],
        'DEE-36': [
            ('as expected', 0.8, 'phrase'), ('exactly as planned', 0.9, 'phrase'),
            ('vindicated', 0.8, 'keyword'), ('confirmed', 0.5, 'keyword'), ('resolved', 0.6, 'keyword'),
            ('done', 0.4, 'keyword'), ('closure', 0.6, 'keyword'),
            ('plan came together', 0.9, 'phrase'), ('worth it', 0.7, 'phrase'),
            ('fulfilled', 0.7, 'keyword'),
        ],
        'DEE-37': [
            ('that must be difficult', 0.9, 'phrase'), ('I\'m sorry to hear', 0.8, 'phrase'),
            ('that\'s tough', 0.7, 'phrase'), ('my condolences', 0.8, 'phrase'),
            ('here for you', 0.6, 'phrase'), ('presence', 0.5, 'keyword'),
            ('solidarity', 0.6, 'keyword'), ('witness', 0.5, 'keyword'),
            ('compassionate', 0.6, 'keyword'), ('offering presence', 0.5, 'structural'),
        ],
        'DEE-38': [
            ('charming', 0.6, 'keyword'), ('teasing', 0.6, 'keyword'), ('playful', 0.5, 'keyword'),
            ('between us', 0.6, 'phrase'), ('flattered', 0.6, 'keyword'), ('alluring', 0.7, 'keyword'),
            ('double meaning', 0.5, 'structural'), ('coy', 0.7, 'keyword'),
            ('suggestive', 0.7, 'keyword'), ('I enjoyed that', 0.6, 'phrase'),
        ],
        'DEE-39': [
            ('agony', 0.9, 'keyword'), ('anguish', 0.9, 'keyword'), ('suffering', 0.8, 'keyword'),
            ('it hurts', 0.9, 'phrase'), ('torment', 0.9, 'keyword'), ('broken', 0.7, 'keyword'),
            ('broken syntax', 0.5, 'structural'), ('repetition', 0.5, 'structural'),
            ('no no no', 0.9, 'phrase'), ('distress', 0.7, 'keyword'),
        ],
    }

    for pid, patterns in _PATTERNS.items():
        for pattern, weight, category in patterns:
            LEXICON.append((pid, pattern, weight, category))


_build_lexicon()


# ============================================================
# personality_to_dee_targets — EISCORE NPC personality to DEE mapping
# ============================================================

def personality_to_dee_targets(
    executing: int = 50,
    influencing: int = 50,
    relationship: int = 50,
    strategic: int = 50,
    mood: float = 50.0,
    urgent_need: str = 'none',
    aggression: int = 5,
    empathy: int = 5,
    patience: int = 5,
    fearfulness: int = 5,
) -> list[dict]:
    """Map EISCORE NPC personality to DEE target profiles.

    Takes the 4-domain personality model (CliftonStrengths), mood, needs state,
    and personality traits, then returns a list of DEE targets suitable for
    buildDEEPrompt().

    Args:
        executing: 0-100 domain weight (action/task-oriented)
        influencing: 0-100 domain weight (leadership/persuasion)
        relationship: 0-100 domain weight (empathy/bonding)
        strategic: 0-100 domain weight (analysis/planning)
        mood: 0-100 (0=distressed, 50=neutral, 100=happy)
        urgent_need: 'none', 'hunger', 'energy', 'social', 'safety'
        aggression: 0-10 personality trait
        empathy: 0-10 personality trait
        patience: 0-10 personality trait
        fearfulness: 0-10 personality trait

    Returns:
        List of dicts with 'profile_id', 'intensity', 'weight' suitable for build_dee_prompt().
    """
    targets: list[dict] = []

    def _add(pid: str, intensity: float, weight: float):
        # Clamp values
        intensity = max(0.0, min(3.0, intensity))
        weight = max(0.0, min(1.0, weight))
        if weight > 0.05:  # Skip negligible weights
            targets.append({'profile_id': pid, 'intensity': intensity, 'weight': weight})

    # === Safety need overrides everything ===
    if urgent_need == 'safety':
        _add('DEE-24', 2.5, 0.8)  # Urgency
        _add('DEE-04', 2.0, 0.6)  # Fear
        if mood < 30:
            _add('DEE-39', 1.5, 0.3)  # Pain
        return _sort_targets(targets)

    # === Mood-dominant states ===
    if mood > 80 and urgent_need == 'none':
        _add('DEE-01', 1.5 + (mood - 80) / 40.0, 0.7)  # Joy
    elif mood < 20:
        if urgent_need == 'hunger':
            _add('DEE-26', 2.0, 0.6)  # Depression (hopelessness from hunger)
        else:
            _add('DEE-04', 1.5 + (20 - mood) / 20.0, 0.5)  # Fear (survival anxiety)

    # === Domain-driven emotions ===

    # High executing + low mood = frustrated at lack of progress
    if executing > 70 and mood < 30:
        intensity = 1.0 + (executing - 70) / 30.0 + (30 - mood) / 30.0
        _add('DEE-03', intensity, 0.6)  # Anger

    # High executing + high mood = determination
    if executing > 70 and mood > 60:
        _add('DEE-18', 1.5, 0.4)  # Determination

    # High relationship + social need = seeking connection
    if relationship > 70 and urgent_need == 'social':
        _add('DEE-09', 1.5 + (relationship - 70) / 30.0, 0.5)  # Love/Affection

    # High relationship + no needs = empathetic
    if relationship > 70 and urgent_need == 'none' and mood > 40:
        _add('DEE-12', 1.0, 0.3)  # Empathy

    # High strategic + high mood = exploring
    if strategic > 70 and mood > 70:
        _add('DEE-15', 1.5 + (strategic - 70) / 30.0, 0.5)  # Curiosity

    # High strategic + low mood = suspicious
    if strategic > 70 and mood < 40:
        _add('DEE-20', 1.0, 0.3)  # Suspicion

    # High influencing + high mood = displaying achievement
    if influencing > 70 and mood > 70:
        _add('DEE-14', 1.5, 0.5)  # Pride

    # High influencing + low mood = contempt
    if influencing > 70 and mood < 30:
        _add('DEE-13', 1.0, 0.3)  # Contempt

    # === Trait modifiers ===

    # High aggression + low patience = anger boost
    if aggression > 7 and patience < 3:
        # If anger already present, boost it; otherwise add it
        anger_idx = next((i for i, t in enumerate(targets) if t['profile_id'] == 'DEE-03'), None)
        if anger_idx is not None:
            targets[anger_idx]['intensity'] = min(3.0, targets[anger_idx]['intensity'] + 0.5)
            targets[anger_idx]['weight'] = min(1.0, targets[anger_idx]['weight'] + 0.1)
        else:
            _add('DEE-03', 1.5, 0.4)

    # High empathy = empathy modifier on negative DEE
    if empathy > 7:
        has_negative = any(
            t['profile_id'] in ('DEE-02', 'DEE-03', 'DEE-04', 'DEE-26', 'DEE-39')
            for t in targets
        )
        if has_negative:
            _add('DEE-12', 1.0, 0.2)  # Empathy as secondary

    # High fearfulness + low mood = fear boost
    if fearfulness > 7 and mood < 40:
        fear_idx = next((i for i, t in enumerate(targets) if t['profile_id'] == 'DEE-04'), None)
        if fear_idx is not None:
            targets[fear_idx]['intensity'] = min(3.0, targets[fear_idx]['intensity'] + 0.5)
        else:
            _add('DEE-04', 1.5, 0.4)

    # === Need-specific modifiers ===
    if urgent_need == 'energy' and mood < 40:
        _add('DEE-16', 1.0, 0.3)  # Boredom/fatigue

    if urgent_need == 'social' and mood < 40:
        _add('DEE-31', 1.0, 0.3)  # Disconnection

    # === Default: if no targets yet, use mood-based baseline ===
    if not targets:
        if mood >= 50:
            _add('DEE-27', 1.0, 0.5)  # Calm
        else:
            _add('DEE-29', 1.0, 0.5)  # Alertness

    return _sort_targets(targets)


def _sort_targets(targets: list[dict]) -> list[dict]:
    """Sort targets by weight descending and deduplicate profile IDs."""
    seen = set()
    deduped = []
    for t in sorted(targets, key=lambda x: x['weight'], reverse=True):
        if t['profile_id'] not in seen:
            seen.add(t['profile_id'])
            deduped.append(t)
    return deduped


# ============================================================
# CSV Export Functions
# ============================================================

def export_dee_profiles_csv(output_path: str):
    """Export DEEProfiles.csv in UE5 DataTable format."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            '---', 'DEEProfileID', 'ProfileName', 'Category',
            'Valence', 'Arousal', 'Dominance', 'VariantCount',
            'EISCOREEmotionID', 'BehavioralMarkers',
        ])
        for profile in DEE_PROFILES_LIST:
            mapping = DEE_TO_EISCORE.get(profile.id, (0, 0.0, 'No mapping'))
            eiscore_id = mapping[0]
            writer.writerow([
                profile.id,              # --- (row name)
                profile.id,              # DEEProfileID
                profile.name,            # ProfileName
                profile.category,        # Category
                f'{profile.valence:.1f}',
                f'{profile.arousal:.1f}',
                f'{profile.dominance:.1f}',
                len(profile.variants),   # VariantCount
                eiscore_id,              # EISCOREEmotionID
                profile.behavioral_markers,
            ])
    print(f'  DEEProfiles.csv: {len(DEE_PROFILES_LIST)} rows')


def export_dee_mapping_csv(output_path: str):
    """Export DEEToEISCOREMapping.csv."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['---', 'DEEProfileID', 'EISCOREEmotionID', 'MappingStrength', 'Notes'])
        for profile in DEE_PROFILES_LIST:
            mapping = DEE_TO_EISCORE.get(profile.id)
            if mapping:
                eiscore_id, strength, notes = mapping
                writer.writerow([
                    profile.id,          # --- (row name)
                    profile.id,          # DEEProfileID
                    eiscore_id,          # EISCOREEmotionID
                    f'{strength:.1f}',   # MappingStrength
                    notes,               # Notes
                ])
    print(f'  DEEToEISCOREMapping.csv: {len(DEE_TO_EISCORE)} rows')


def export_dee_lexicon_csv(output_path: str):
    """Export DEELexicon.csv — flattened patterns for BT/dialogue use."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['---', 'DEEProfileID', 'Pattern', 'Weight', 'Category'])
        for i, (pid, pattern, weight, category) in enumerate(LEXICON):
            row_name = f'{pid}_{i:04d}'
            writer.writerow([row_name, pid, pattern, f'{weight:.1f}', category])
    print(f'  DEELexicon.csv: {len(LEXICON)} rows')


def main():
    """Generate all EISCORE CSV files."""
    os.makedirs(EIS_DATA_DIR, exist_ok=True)

    print('EISCORE DEE Export')
    print(f'Output directory: {EIS_DATA_DIR}')
    print()

    export_dee_profiles_csv(os.path.join(EIS_DATA_DIR, 'DEEProfiles.csv'))
    export_dee_mapping_csv(os.path.join(EIS_DATA_DIR, 'DEEToEISCOREMapping.csv'))
    export_dee_lexicon_csv(os.path.join(EIS_DATA_DIR, 'DEELexicon.csv'))

    print()
    print('Done. All CSVs written.')

    # Demo: personality_to_dee_targets
    print()
    print('--- Demo: personality_to_dee_targets ---')
    print('High-aggression, low-mood NPC (executing=80, mood=15, aggression=9, patience=2):')
    result = personality_to_dee_targets(
        executing=80, influencing=30, relationship=20, strategic=40,
        mood=15, urgent_need='none', aggression=9, empathy=3, patience=2, fearfulness=6,
    )
    for t in result:
        profile = DEE_PROFILES.get(t['profile_id'])
        name = profile.name if profile else 'Unknown'
        print(f'  {t["profile_id"]} ({name}): intensity={t["intensity"]:.1f}, weight={t["weight"]:.1f}')


if __name__ == '__main__':
    main()
