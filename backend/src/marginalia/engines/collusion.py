"""
Cross-Reviewer Collusion Detection.

Detects when multiple reviewers of the SAME paper used the same AI prompt.
Signal: pairwise structural similarity between reviews on the same paper > threshold.

This is distinct from Batch DNA (which detects one reviewer's AI batch across papers).
Collusion detects multiple reviewers coordinating (or independently using same AI) on one paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from marginalia.engines.batch_dna import extract_fingerprint


@dataclass
class CollusionPair:
    reviewer_a: str
    reviewer_b: str
    similarity: float
    shared_opener: bool


@dataclass
class CollusionResult:
    paper_id: str
    total_reviewers: int
    flagged_pairs: list[CollusionPair]
    max_similarity: float
    collusion_detected: bool
    collusion_score: float  # 0-100


def detect_collusion(
    paper_id: str,
    reviews: list[tuple[str, str]],  # (reviewer_id, review_text)
    similarity_threshold: float = 0.80,
) -> CollusionResult:
    """
    Detect structural collusion between reviewers of the same paper.

    Args:
        paper_id: The paper being reviewed.
        reviews: List of (reviewer_id, review_text) for all reviewers of this paper.
        similarity_threshold: Cosine similarity above which two reviews are flagged.

    Returns:
        CollusionResult with flagged pairs and overall collusion score.
    """
    n = len(reviews)

    if n < 2:
        return CollusionResult(
            paper_id=paper_id,
            total_reviewers=n,
            flagged_pairs=[],
            max_similarity=0.0,
            collusion_detected=False,
            collusion_score=0.0,
        )

    # Extract fingerprints
    fingerprints = [extract_fingerprint(rid, text) for rid, text in reviews]
    feature_matrix = np.array([fp.feature_vector for fp in fingerprints])

    # L2 normalize
    norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = feature_matrix / norms

    # Pairwise similarity
    sim_matrix = np.dot(normalized, normalized.T)

    flagged_pairs: list[CollusionPair] = []
    max_sim = 0.0

    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            max_sim = max(max_sim, sim)

            shared_opener = (
                fingerprints[i].opener_pattern == fingerprints[j].opener_pattern
                and fingerprints[i].opener_pattern != ""
            )

            # Flag if structurally similar OR same opener with moderate similarity
            if sim >= similarity_threshold or (shared_opener and sim >= 0.70):
                flagged_pairs.append(
                    CollusionPair(
                        reviewer_a=reviews[i][0],
                        reviewer_b=reviews[j][0],
                        similarity=round(sim, 3),
                        shared_opener=shared_opener,
                    )
                )

    collusion_detected = len(flagged_pairs) > 0

    # Collusion score: 0-100 based on max similarity and number of flagged pairs
    if flagged_pairs:
        pair_factor = min(len(flagged_pairs) / max(n * (n - 1) / 2, 1), 1.0)
        collusion_score = round(
            (max_sim * 0.7 + pair_factor * 0.3) * 100, 1
        )
    else:
        collusion_score = 0.0

    return CollusionResult(
        paper_id=paper_id,
        total_reviewers=n,
        flagged_pairs=flagged_pairs,
        max_similarity=round(max_sim, 3),
        collusion_detected=collusion_detected,
        collusion_score=collusion_score,
    )


def detect_collusion_batch(
    papers: dict[str, list[tuple[str, str]]],
    similarity_threshold: float = 0.80,
) -> dict[str, CollusionResult]:
    """
    Detect collusion across multiple papers.

    Args:
        papers: Dict of paper_id → list of (reviewer_id, review_text).
        similarity_threshold: Similarity threshold for flagging.

    Returns:
        Dict of paper_id → CollusionResult.
    """
    return {
        paper_id: detect_collusion(paper_id, reviews, similarity_threshold)
        for paper_id, reviews in papers.items()
        if len(reviews) >= 2
    }
