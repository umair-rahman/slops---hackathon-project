"""Tests for the Style Drift Engine."""

from marginalia.engines.style_drift import detect_style_drift


# Real-style early reviews with anchors and varied structure
EARLY_HUMAN = [
    "Equation 5 in Section 3.2 has an issue with normalization. Figure 4(b) is unclear.",
    "I disagree with the claim on page 7. The proof in Appendix A skips a step.",
    "Strong contribution overall. However Theorem 2 needs the Lipschitz assumption.",
    "Algorithm 1 line 5 has an off-by-one bug. The benchmark in Table 3 is dated.",
]

# AI-style late reviews — generic and templated
LATE_AI = [
    "This paper presents an interesting contribution. The methodology is well-described. The results are promising. I recommend acceptance.",
    "This paper presents a novel approach. The methodology is clear. The results are competitive. I recommend acceptance with minor revisions.",
    "This paper presents a new technique. The methodology is sound. The results are strong. I recommend acceptance.",
    "This paper presents an important contribution. The methodology is rigorous. The results are convincing. I recommend acceptance.",
]


def test_drift_detected_when_style_changes():
    reviews = []
    for i, t in enumerate(EARLY_HUMAN):
        reviews.append((f"r{i}", t, 1700000000 + i * 100))
    for i, t in enumerate(LATE_AI):
        reviews.append((f"r{4+i}", t, 1700000000 + (4 + i) * 100))

    result = detect_style_drift(reviews)
    assert result.drift_detected
    assert result.drift_index is not None
    assert result.drift_strength > 0.05


def test_no_drift_when_consistent_style():
    # All consistent AI-style reviews
    reviews = []
    for i, t in enumerate(LATE_AI * 2):
        reviews.append((f"r{i}", t, 1700000000 + i * 100))
    result = detect_style_drift(reviews)
    # Should not detect drift (already homogeneous)
    assert result.drift_strength < 0.3


def test_too_few_reviews_returns_no_drift():
    reviews = [("r1", "Test review.", 100), ("r2", "Another one.", 200)]
    result = detect_style_drift(reviews)
    assert not result.drift_detected
    assert result.drift_index is None


def test_empty_input():
    result = detect_style_drift([])
    assert not result.drift_detected
