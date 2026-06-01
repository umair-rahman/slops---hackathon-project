"""
Style Drift Engine — Layer 4 (advanced).

Detects when a reviewer's writing style shifts over time —
e.g. when they start using AI mid-career.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from marginalia.engines.batch_dna import extract_fingerprint


@dataclass
class DriftResult:
    drift_detected: bool
    drift_index: int | None  # index in time-ordered list where drift starts
    drift_strength: float    # 0-1
    early_avg_distance: float
    late_avg_distance: float


def detect_style_drift(reviews: list[tuple[str, str, int]]) -> DriftResult:
    """
    Detect a style shift in a reviewer's time-ordered review history.

    Args:
        reviews: List of (review_id, review_text, timestamp_ms), time-ordered.
        Must have at least 4 reviews to detect drift reliably.
    """
    if len(reviews) < 4:
        return DriftResult(
            drift_detected=False,
            drift_index=None,
            drift_strength=0.0,
            early_avg_distance=0.0,
            late_avg_distance=0.0,
        )

    # Sort by timestamp
    sorted_reviews = sorted(reviews, key=lambda r: r[2])

    fingerprints = [extract_fingerprint(rid, txt) for rid, txt, _ in sorted_reviews]
    feature_matrix = np.array([fp.feature_vector for fp in fingerprints])
    norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = feature_matrix / norms

    n = len(normalized)
    best_drift_index = None
    best_drift_strength = 0.0
    best_early_avg = 0.0
    best_late_avg = 0.0

    # Try splitting at each interior point (need >=2 in each half)
    for split in range(2, n - 1):
        early = normalized[:split]
        late = normalized[split:]

        # Avg pairwise sim within each half
        early_sim = _avg_pairwise_sim(early)
        late_sim = _avg_pairwise_sim(late)

        # Cross-half avg sim (low = drift)
        cross_sim = float(np.mean(np.dot(early, late.T)))

        # Drift strength: high within-half, low cross-half
        drift_strength = max(0.0, (early_sim + late_sim) / 2 - cross_sim)

        if drift_strength > best_drift_strength:
            best_drift_strength = drift_strength
            best_drift_index = split
            best_early_avg = early_sim
            best_late_avg = late_sim

    drift_detected = best_drift_strength > 0.05

    return DriftResult(
        drift_detected=drift_detected,
        drift_index=best_drift_index if drift_detected else None,
        drift_strength=round(best_drift_strength, 3),
        early_avg_distance=round(best_early_avg, 3),
        late_avg_distance=round(best_late_avg, 3),
    )


def _avg_pairwise_sim(matrix: np.ndarray) -> float:
    """Average pairwise cosine similarity within a set of L2-normalized vectors."""
    n = matrix.shape[0]
    if n < 2:
        return 1.0
    sim = np.dot(matrix, matrix.T)
    # Sum upper triangle (excluding diagonal)
    upper = sim[np.triu_indices(n, k=1)]
    return float(np.mean(upper)) if upper.size else 1.0
