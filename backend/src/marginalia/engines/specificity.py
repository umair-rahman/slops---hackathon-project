"""
Specificity Engine — Layer 1 of Ghost Score.

Detects AI-generated reviews by measuring how many specific paper
elements (equations, figures, sections, tables) the reviewer references.

Real reviewers cite specifics. AI reviewers write generic fluff.
"""

from __future__ import annotations

import math
import re
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
    Score a review's specificity based on academic anchor density.

    Returns a 0-100 score where higher = more specific = more human-like.
    """
    if not review_text or not review_text.strip():
        return SpecificityResult(
            score=0.0, anchors_per_100_words=0.0, total_anchors=0, sentences=[]
        )

    sentences = split_sentences(review_text)
    word_count = len([w for w in review_text.split() if w])

    sentence_scores: list[SentenceScore] = []
    total_anchors = 0

    for sent in sentences:
        anchors = extract_anchors(sent)
        total_anchors += len(anchors)
        sentence_scores.append(
            SentenceScore(
                text=sent,
                anchor_count=len(anchors),
                anchors=anchors,
            )
        )

    anchors_per_100 = (total_anchors / max(word_count, 1)) * 100
    score = anchors_to_score(anchors_per_100)

    return SpecificityResult(
        score=score,
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
    """
    Map anchor density to 0-100 specificity score.

    0 anchors/100w  → ~5  (very AI-like)
    1 anchor/100w   → ~25
    2.5 anchors     → ~50
    4+ anchors      → ~80
    6+ anchors      → ~95 (very human-like)
    """
    x0, k = 2.5, 1.0
    raw = 1.0 / (1.0 + math.exp(-k * (anchors_per_100 - x0)))
    return round(raw * 100, 1)
