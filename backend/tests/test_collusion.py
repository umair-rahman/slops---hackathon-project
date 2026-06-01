"""Tests for Cross-Reviewer Collusion Detection."""

from marginalia.engines.collusion import detect_collusion, detect_collusion_batch


# ── Fixtures ─────────────────────────────────────────────────────────────────

TEMPLATE = (
    "This paper presents {} contribution. The proposed method shows {} results. "
    "However, the experimental setup lacks detail. "
    "Overall, this is a solid paper. I recommend acceptance with minor revisions."
)

# Three reviewers using same AI template on same paper
COLLUDING_REVIEWS = [
    ("reviewer_A", TEMPLATE.format("an interesting", "promising")),
    ("reviewer_B", TEMPLATE.format("a novel", "competitive")),
    ("reviewer_C", TEMPLATE.format("a new", "strong")),
]

# Three reviewers with genuinely different styles
INDEPENDENT_REVIEWS = [
    ("reviewer_X", "Equation 5 in Section 3.2 has a sign error. Figure 4(b) is unclear. "
                   "The proof in Appendix A skips a step. I disagree with the claim on page 7."),
    ("reviewer_Y", "Strong contribution overall. However Theorem 2 needs the Lipschitz assumption. "
                   "Algorithm 1 line 5 has an off-by-one bug. The benchmark in Table 3 is dated."),
    ("reviewer_Z", "I'm skeptical of the results in Table 3. The improvement over BERT-base is within noise. "
                   "Section 4.3 references future work twice but doesn't specify what."),
]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCollusionDetection:
    def test_detects_colluding_reviewers(self):
        result = detect_collusion("paper_001", COLLUDING_REVIEWS)
        assert result.collusion_detected
        assert len(result.flagged_pairs) >= 1
        assert result.max_similarity > 0.7

    def test_no_collusion_for_independent_reviewers(self):
        result = detect_collusion("paper_002", INDEPENDENT_REVIEWS)
        # Independent reviewers should have low similarity
        assert result.max_similarity < 0.95

    def test_single_reviewer_no_collusion(self):
        result = detect_collusion("paper_003", [("reviewer_A", "Some review text here.")])
        assert not result.collusion_detected
        assert len(result.flagged_pairs) == 0

    def test_empty_reviews(self):
        result = detect_collusion("paper_004", [])
        assert not result.collusion_detected
        assert result.total_reviewers == 0

    def test_collusion_score_range(self):
        result = detect_collusion("paper_005", COLLUDING_REVIEWS)
        assert 0 <= result.collusion_score <= 100

    def test_flagged_pair_contains_reviewer_ids(self):
        result = detect_collusion("paper_001", COLLUDING_REVIEWS)
        if result.flagged_pairs:
            pair = result.flagged_pairs[0]
            reviewer_ids = {r[0] for r in COLLUDING_REVIEWS}
            assert pair.reviewer_a in reviewer_ids
            assert pair.reviewer_b in reviewer_ids

    def test_batch_collusion(self):
        papers = {
            "paper_A": COLLUDING_REVIEWS,
            "paper_B": INDEPENDENT_REVIEWS,
        }
        results = detect_collusion_batch(papers)
        assert "paper_A" in results
        assert "paper_B" in results
        # Paper A should have higher collusion score
        assert results["paper_A"].collusion_score >= results["paper_B"].collusion_score

    def test_custom_threshold(self):
        # Very strict threshold — should flag fewer pairs
        strict = detect_collusion("paper_001", COLLUDING_REVIEWS, similarity_threshold=0.99)
        lenient = detect_collusion("paper_001", COLLUDING_REVIEWS, similarity_threshold=0.50)
        assert len(strict.flagged_pairs) <= len(lenient.flagged_pairs)
