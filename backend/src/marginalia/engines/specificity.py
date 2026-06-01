"""
Specificity Engine — Layer 1 of Ghost Score.

Detects AI-generated reviews using multiple signals:
1. Academic anchor density (equations, figures, sections)
2. Generic AI phrase detection (filler words common in AI reviews)
3. Specific detail words (numbers, percentages, technical terms)
4. Sentence variety (AI tends to have uniform sentence lengths)
5. Hedging and uncertainty markers (humans use these more)

Real reviewers cite specifics AND show varied writing patterns.
AI reviewers use generic praise phrases AND uniform structure.
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field


# ── Anchor Patterns ──────────────────────────────────────────────────────────

ANCHOR_PATTERNS: dict[str, str] = {
    "equation": r"\b(?:eq(?:uation)?s?\.?|formula)\s*[\(\[]?\d+(?:\.\d+)?[\)\]]?",
    "figure": r"\b(?:fig(?:ure)?s?\.?)\s*\d+[a-z]?(?:\s*[\(\[]\w[\)\]])?",
    "table": r"\b(?:table)\s*\d+[a-z]?",
    "section": r"\b(?:sec(?:tion)?s?\.?|§)\s*\d+(?:\.\d+)*",
    "theorem": r"\b(?:theorem|lemma|proposition|corollary|definition)\s*\d+",
    "algorithm": r"\b(?:algorithm|alg\.?)\s*\d+",
    "appendix": r"\b(?:appendix)\s*[a-z]\b",
    "line": r"\b(?:line|lines)\s*\d+(?:\s*[-–]\s*\d+)?",
    "page": r"\b(?:page|p\.)\s*\d+\b",
}

COMPILED_PATTERNS = {
    anchor_type: re.compile(pattern, re.IGNORECASE)
    for anchor_type, pattern in ANCHOR_PATTERNS.items()
}


# Generic AI praise/filler phrases
AI_FILLER_PHRASES = [
    "interesting contribution", "promising results", "well-described",
    "well-organized", "well-written", "good job", "minor revisions",
    "novel approach", "competitive results", "strong results",
    "well-motivated", "clearly presented", "thorough evaluation",
    "comprehensive analysis", "important problem", "valuable insight",
    "I recommend acceptance", "recommend acceptance", "solid paper",
    "good paper", "decent paper", "this work", "this paper",
    "the proposed method", "the authors", "well done",
    "clearly written", "easy to follow", "make sense",
    "in summary", "overall", "in conclusion",
]

# Specific human reviewer indicators
HUMAN_INDICATORS = [
    "however", "but", "actually", "in fact", "specifically",
    "for example", "for instance", "i.e.", "e.g.",
    "i'm not sure", "unclear", "confused", "wrong", "incorrect",
    "missing", "should be", "could be", "would benefit",
    "i wonder", "i suspect", "in my opinion", "i think",
    "minor", "major", "critical", "concern", "issue",
    "fix", "typo", "error", "bug", "flaw",
    "%", "percent", "x faster", "x slower",
]


@dataclass
class AnchorMatch:
    text: str
    anchor_type: str


@dataclass
class SentenceScore:
    text: str
    anchor_count: int
    anchors: list[AnchorMatch] = field(default_factory=list)
    is_hallucinated: bool = False
    hallucination_reason: str | None = None


@dataclass
class SpecificityResult:
    score: float
    anchors_per_100_words: float
    total_anchors: int
    sentences: list[SentenceScore]


def score_specificity(review_text: str) -> SpecificityResult:
    """
    Score a review's specificity using multiple signals.

    Returns a 0-100 score where higher = more specific = more human-like.
    """
    if not review_text or not review_text.strip():
        return SpecificityResult(
            score=0.0, anchors_per_100_words=0.0, total_anchors=0, sentences=[]
        )

    sentences = split_sentences(review_text)
    word_count = len([w for w in review_text.split() if w])

    # ── Signal 1: Anchor density ──────────────────────────────────────────
    sentence_scores: list[SentenceScore] = []
    total_anchors = 0

    for sent in sentences:
        anchors = extract_anchors(sent)
        total_anchors += len(anchors)
        sentence_scores.append(
            SentenceScore(text=sent, anchor_count=len(anchors), anchors=anchors)
        )

    anchors_per_100 = (total_anchors / max(word_count, 1)) * 100
    anchor_signal = anchors_to_score(anchors_per_100)

    # ── Signal 2: AI filler phrase penalty ────────────────────────────────
    text_lower = review_text.lower()
    filler_count = sum(1 for phrase in AI_FILLER_PHRASES if phrase in text_lower)
    # Cap penalty at 30, scale by filler count
    filler_penalty = min(filler_count * 8, 30)

    # ── Signal 3: Human indicator bonus ──────────────────────────────────
    human_count = sum(1 for word in HUMAN_INDICATORS if word in text_lower)
    # Bonus: up to +30
    human_bonus = min(human_count * 4, 30)

    # ── Signal 4: Sentence length variety (humans vary, AI doesn't) ──────
    if len(sentences) >= 3:
        lengths = [len(s.split()) for s in sentences]
        try:
            length_std = statistics.stdev(lengths)
            mean_len = statistics.mean(lengths)
            # Coefficient of variation: humans usually > 0.4, AI usually < 0.3
            cv = length_std / max(mean_len, 1)
            variety_bonus = min(cv * 30, 15)
        except Exception:
            variety_bonus = 0.0
    else:
        variety_bonus = 0.0

    # ── Signal 5: Specific numbers / percentages ─────────────────────────
    number_matches = re.findall(r'\b\d+(?:\.\d+)?%?\b', review_text)
    has_specifics = len(number_matches) > 0
    number_bonus = min(len(number_matches) * 2, 15) if has_specifics else 0

    # ── Signal 6: Short generic review penalty ───────────────────────────
    if word_count < 20:
        short_penalty = 10  # very short reviews are suspicious
    else:
        short_penalty = 0

    # ── Aggregate ────────────────────────────────────────────────────────
    score = anchor_signal - filler_penalty + human_bonus + variety_bonus + number_bonus - short_penalty
    score = max(0.0, min(100.0, score))

    return SpecificityResult(
        score=round(score, 1),
        anchors_per_100_words=round(anchors_per_100, 2),
        total_anchors=total_anchors,
        sentences=sentence_scores,
    )


def extract_anchors(text: str) -> list[AnchorMatch]:
    """Extract all academic anchors from a text snippet."""
    anchors: list[AnchorMatch] = []
    for anchor_type, pattern in COMPILED_PATTERNS.items():
        for match in pattern.finditer(text):
            anchors.append(AnchorMatch(text=match.group(), anchor_type=anchor_type))
    return anchors


# Backward compatibility alias for tests
_extract_anchors = extract_anchors


def split_sentences(text: str) -> list[str]:
    """Sentence splitter using regex (works without spaCy)."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def anchors_to_score(anchors_per_100: float) -> float:
    """Map anchor density to base score (will be adjusted by other signals)."""
    x0, k = 2.5, 1.0
    raw = 1.0 / (1.0 + math.exp(-k * (anchors_per_100 - x0)))
    return round(raw * 100, 1)
