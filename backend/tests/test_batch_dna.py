"""Tests for the Batch DNA Engine."""

import pytest

from marginalia.engines.batch_dna import (
    extract_fingerprint,
    score_batch_dna,
)

# ── Test Fixtures ────────────────────────────────────────────────────────────

# AI batch — 3 reviews from same prompt template
AI_BATCH = [
    ("ai_1", """
This paper presents an interesting contribution to the field. The proposed method shows promising results.
However, the methodology section could be clearer. Additionally, the experimental setup lacks detail.
Overall, this is a solid paper. I recommend acceptance with minor revisions.
"""),
    ("ai_2", """
This paper presents a novel approach to the problem. The proposed method achieves competitive results.
However, the related work section is incomplete. Additionally, the ablation study is limited.
Overall, this is a good paper. I recommend acceptance with minor revisions.
"""),
    ("ai_3", """
This paper presents a new technique for the task. The proposed method demonstrates strong performance.
However, the theoretical analysis is missing. Additionally, the comparison with baselines is unfair.
Overall, this is a decent paper. I recommend acceptance with minor revisions.
"""),
]

# Human batch — clearly different writing styles
HUMAN_BATCH = [
    ("h_1", """
Equation 5 in Section 3.2 has a sign error in the third term.
Figure 4 caption mentions 'best viewed in color' but the heatmap is grayscale only.
On page 7, the claim about O(n) complexity contradicts the implementation in Algorithm 2.
Specific issues: (a) hyperparameter sensitivity not addressed, (b) only 3 random seeds used.
"""),
    ("h_2", """
I'm skeptical of the results in Table 3 — the improvement over BERT-base is within noise.
Have you tried longer training? The 50-epoch limit seems arbitrary.
Also, Section 4.3 references "future work" twice but doesn't specify what.
The paper would benefit from a clearer ablation; right now Section 5 is a wall of numbers.
"""),
    ("h_3", """
Strong submission overall. The proof in Appendix A is elegant.
Two concerns: (1) the assumption in Theorem 2 about Lipschitz continuity is too strong,
(2) Figure 3 shows divergence at step 100k but the text claims convergence.
Could the authors clarify which experiments used the released codebase versus reimplementations?
"""),
]


# ── Fingerprint Extraction ──────────────────────────────────────────────────

class TestFingerprint:
    def test_extracts_basic_fields(self):
        fp = extract_fingerprint("test", "First sentence. Second one. Third here.")
        assert fp.review_id == "test"
        assert fp.sentence_count >= 3
        assert fp.word_count > 0

    def test_handles_empty_text(self):
        fp = extract_fingerprint("empty", "")
        assert fp.word_count == 1  # min 1 to avoid div by zero
        assert fp.feature_vector is not None

    def test_feature_vector_is_numeric(self):
        fp = extract_fingerprint("test", "Some sample text here. Another sentence.")
        assert fp.feature_vector is not None
        assert len(fp.feature_vector) > 0
        assert all(isinstance(float(v), float) for v in fp.feature_vector)

    def test_detects_common_openers(self):
        fp = extract_fingerprint(
            "test",
            "This paper is good. The authors did well. The proposed method works."
        )
        assert fp.common_opener_count >= 2

    def test_paragraph_count(self):
        fp = extract_fingerprint("test", "Para one.\n\nPara two.\n\nPara three.")
        assert fp.paragraph_count == 3


# ── Batch DNA Scoring ───────────────────────────────────────────────────────

class TestBatchDNAScoring:
    def test_single_review_unavailable(self):
        results = score_batch_dna([("solo", "Some text here.")])
        assert "solo" in results
        assert results["solo"].available is False

    def test_empty_batch(self):
        results = score_batch_dna([])
        assert results == {}

    def test_ai_batch_clusters_together(self):
        results = score_batch_dna(AI_BATCH)
        assert len(results) == 3
        # AI reviews should share a cluster
        cluster_ids = [results[rid].cluster_id for rid, _ in AI_BATCH]
        # At least 2 of the 3 should be in same cluster
        from collections import Counter
        most_common = Counter(cluster_ids).most_common(1)[0][1]
        assert most_common >= 2, f"AI batch did not cluster, IDs: {cluster_ids}"

    def test_human_batch_does_not_cluster_tightly(self):
        results = score_batch_dna(HUMAN_BATCH)
        assert len(results) == 3
        # Each result should have a score
        for rid, _ in HUMAN_BATCH:
            assert rid in results
            assert results[rid].available

    def test_scores_in_valid_range(self):
        results = score_batch_dna(AI_BATCH + HUMAN_BATCH)
        for r in results.values():
            if r.score is not None:
                assert 0 <= r.score <= 100

    def test_clustered_reviews_score_higher(self):
        ai_results = score_batch_dna(AI_BATCH)
        # At least one AI review should be flagged with a cluster size >= 2
        cluster_sizes = [r.cluster_size for r in ai_results.values() if r.cluster_size]
        max_size = max(cluster_sizes) if cluster_sizes else 1
        assert max_size >= 2, "AI batch should produce a cluster of size >= 2"
