"""Tests for the Specificity Engine."""

from marginalia.engines.specificity import (
    extract_anchors,
    score_specificity,
    split_sentences,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

AI_REVIEW = """
This paper presents an interesting contribution to the field of machine learning.
The methodology is well-described and the results are promising.
The authors have done a good job of explaining their approach.
The writing is clear and the paper is well-organized.
I recommend acceptance with minor revisions.
"""

HUMAN_REVIEW = """
The paper proposes a novel attention mechanism described in Section 3.2.
However, Equation 5 contains a derivation error — the normalization term
is missing from the denominator. Figure 4(b) shows the ablation results,
but Table 2 is missing confidence intervals for the baseline comparisons.
In Section 5.1, the authors claim 94% accuracy but the numbers in
Figure 6 show 91.2%, which is a discrepancy that needs addressing.
Algorithm 1 on page 8 also has an off-by-one error in the loop bounds.
"""


# ── Anchor Extraction ───────────────────────────────────────────────────────

class TestAnchorExtraction:
    def test_detects_equation_reference(self):
        anchors = extract_anchors("As shown in Equation 5, the loss function...")
        assert any(a.anchor_type == "equation" for a in anchors)

    def test_detects_figure_reference(self):
        anchors = extract_anchors("Figure 4(b) shows the ablation results.")
        assert any(a.anchor_type == "figure" for a in anchors)

    def test_detects_section_reference(self):
        anchors = extract_anchors("In Section 3.2, the authors describe...")
        assert any(a.anchor_type == "section" for a in anchors)

    def test_detects_table_reference(self):
        anchors = extract_anchors("Table 2 shows the comparison results.")
        assert any(a.anchor_type == "table" for a in anchors)

    def test_detects_algorithm_reference(self):
        anchors = extract_anchors("Algorithm 1 has an off-by-one error.")
        assert any(a.anchor_type == "algorithm" for a in anchors)

    def test_detects_theorem_reference(self):
        anchors = extract_anchors("Theorem 2 needs additional proof.")
        assert any(a.anchor_type == "theorem" for a in anchors)

    def test_detects_page_reference(self):
        anchors = extract_anchors("On page 5, the authors note...")
        assert any(a.anchor_type == "page" for a in anchors)

    def test_no_anchors_in_fluff(self):
        anchors = extract_anchors("This paper presents an interesting contribution.")
        assert len(anchors) == 0

    def test_handles_empty_text(self):
        assert extract_anchors("") == []

    def test_multiple_anchors_in_one_sentence(self):
        anchors = extract_anchors("Equation 3 in Section 5.1 contradicts Figure 7.")
        types = {a.anchor_type for a in anchors}
        assert "equation" in types
        assert "section" in types
        assert "figure" in types


# ── Sentence Splitting ──────────────────────────────────────────────────────

class TestSentenceSplitting:
    def test_splits_basic_sentences(self):
        text = "First sentence. Second sentence. Third one."
        assert len(split_sentences(text)) == 3

    def test_handles_questions(self):
        text = "Is this clear? It should be. Yes."
        assert len(split_sentences(text)) == 3

    def test_handles_empty(self):
        assert split_sentences("") == []
        assert split_sentences("   ") == []


# ── Score Behavior ───────────────────────────────────────────────────────────

class TestSpecificityScoring:
    def test_ai_review_gets_low_score(self):
        result = score_specificity(AI_REVIEW)
        assert result.score < 40, f"AI review should score < 40, got {result.score}"

    def test_human_review_gets_high_score(self):
        result = score_specificity(HUMAN_REVIEW)
        assert result.score > 60, f"Human review should score > 60, got {result.score}"

    def test_human_has_more_anchors_than_ai(self):
        ai = score_specificity(AI_REVIEW)
        human = score_specificity(HUMAN_REVIEW)
        assert human.total_anchors > ai.total_anchors

    def test_returns_sentence_breakdown(self):
        result = score_specificity(HUMAN_REVIEW)
        assert len(result.sentences) > 0

    def test_anchors_per_100_words_positive(self):
        result = score_specificity(HUMAN_REVIEW)
        assert result.anchors_per_100_words > 0

    def test_empty_review_does_not_crash(self):
        result = score_specificity("")
        assert 0 <= result.score <= 100
        assert result.total_anchors == 0

    def test_short_review_handled(self):
        result = score_specificity("This is good.")
        assert 0 <= result.score <= 100

    def test_score_in_valid_range(self):
        for text in [AI_REVIEW, HUMAN_REVIEW, "", "a", "Equation 3 is wrong."]:
            r = score_specificity(text)
            assert 0 <= r.score <= 100, f"Out of range for: {text[:30]}"

    def test_per_sentence_anchor_counts_match_total(self):
        result = score_specificity(HUMAN_REVIEW)
        per_sentence_total = sum(s.anchor_count for s in result.sentences)
        assert per_sentence_total == result.total_anchors
