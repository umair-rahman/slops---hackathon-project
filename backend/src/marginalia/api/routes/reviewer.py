"""Reviewer profile and DNA analysis endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from marginalia.data.openreview import openreview_client
from marginalia.engines.batch_dna import score_batch_dna
from marginalia.engines.specificity import score_specificity
from marginalia.engines.style_drift import detect_style_drift
from marginalia.engines.time_on_task import estimate_time_on_task

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/reviewer/{reviewer_id:path}")
async def get_reviewer_profile(reviewer_id: str) -> dict:
    """
    Get a reviewer profile with:
    - Per-review ghost scores (Specificity + Batch DNA, no paper)
    - Style drift detection over time
    - Cluster membership across all reviews
    """
    try:
        reviews = await openreview_client.get_reviewer_reviews(reviewer_id)
        if not reviews:
            raise HTTPException(
                status_code=404,
                detail=f"No reviews found for {reviewer_id}",
            )

        # Score each review's specificity
        review_scores = []
        for r in reviews:
            spec = score_specificity(r.review_text)
            review_scores.append({
                "review_id": r.review_id,
                "review_text": r.review_text,
                "paper_id": r.paper_id,
                "paper_title": r.paper_title,
                "venue_id": r.venue_id,
                "timestamp": r.timestamp,
                "specificity_score": spec.score,
                "anchor_count": spec.total_anchors,
            })

        # Batch DNA across reviewer's full history
        batch_pairs = [(r.review_id, r.review_text) for r in reviews]
        dna_results = score_batch_dna(batch_pairs) if len(batch_pairs) >= 2 else {}

        # Aggregate ghost score per review
        for rs in review_scores:
            spec_ghost = 100.0 - rs["specificity_score"]
            dna = dna_results.get(rs["review_id"])
            if dna and dna.available and dna.score is not None:
                ghost = 0.6 * spec_ghost + 0.4 * dna.score
                rs["cluster_id"] = dna.cluster_id
                rs["cluster_size"] = dna.cluster_size
            else:
                ghost = spec_ghost
                rs["cluster_id"] = None
                rs["cluster_size"] = None
            rs["ghost_score"] = round(max(0.0, min(100.0, ghost)), 1)

        # Style drift detection
        drift = detect_style_drift([
            (r.review_id, r.review_text, r.timestamp) for r in reviews
        ])

        # Time-on-task estimation
        tot = estimate_time_on_task(
            reviewer_id,
            [(r.review_id, r.review_text, r.timestamp) for r in reviews],
        )

        avg_score = (
            sum(r["ghost_score"] for r in review_scores) / len(review_scores)
            if review_scores else 0.0
        )

        cluster_ids = {r["cluster_id"] for r in review_scores if r.get("cluster_id") is not None}

        # Sort reviews by time descending
        review_scores.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "reviewer_id": reviewer_id,
            "total_reviews": len(reviews),
            "avg_ghost_score": round(avg_score, 1),
            "drift_detected": drift.drift_detected,
            "drift_strength": drift.drift_strength,
            "drift_point": (
                review_scores[len(review_scores) - drift.drift_index - 1]["timestamp"]
                if drift.drift_index is not None and drift.drift_index < len(review_scores)
                else None
            ),
            "cluster_count": len(cluster_ids),
            "time_on_task_score": tot.time_on_task_score,
            "burst_detected": tot.burst_detected,
            "burst_window_seconds": tot.burst_window_seconds,
            "implausible_count": tot.implausible_count,
            "reviews": review_scores,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Reviewer profile failed: {e}")
        raise HTTPException(status_code=500, detail=f"Profile error: {e}")
