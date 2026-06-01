"""Single review analysis endpoint."""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, HTTPException

from marginalia.api.schemas import (
    AnalyzeReviewRequest,
    BatchAnalyzeRequest,
    GhostScoreResponse,
)
from marginalia.data.db import db
from marginalia.engines.pipeline import analyze_review_batch, analyze_single_review

logger = logging.getLogger(__name__)
router = APIRouter()


def _ghost_to_response(score) -> GhostScoreResponse:
    return GhostScoreResponse(
        overall=score.overall,
        label=score.label,
        confidence_low=score.confidence_low,
        confidence_high=score.confidence_high,
        specificity={  # type: ignore
            "score": score.specificity.score,
            "anchors_per_100_words": score.specificity.anchors_per_100_words,
            "total_anchors": score.specificity.total_anchors,
            "sentences": [
                {
                    "text": s.text,
                    "anchor_count": s.anchor_count,
                    "anchors": [
                        {"text": a.text, "anchor_type": a.anchor_type} for a in s.anchors
                    ],
                    "is_hallucinated": s.is_hallucinated,
                    "hallucination_reason": s.hallucination_reason,
                }
                for s in score.specificity.sentences
            ],
        },
        asymmetry={  # type: ignore
            "score": score.asymmetry.score,
            "sim_abstract": score.asymmetry.sim_abstract,
            "sim_body": score.asymmetry.sim_body,
            "asymmetry_ratio": score.asymmetry.asymmetry_ratio,
            "hallucinated_sentences": score.asymmetry.hallucinated_sentences,
        },
        batch_dna={  # type: ignore
            "score": score.batch_dna.score,
            "cluster_id": score.batch_dna.cluster_id,
            "cluster_size": score.batch_dna.cluster_size,
            "available": score.batch_dna.available,
            "reason": score.batch_dna.reason,
        },
        explanation=score.explanation,
    )


def _hash_review(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@router.post("/analyze/review", response_model=GhostScoreResponse)
async def analyze_review(req: AnalyzeReviewRequest) -> GhostScoreResponse:
    """
    Analyze a single peer review for AI-generation signals.
    Persists result to Postgres asynchronously (best-effort).
    """
    try:
        score = await analyze_single_review(
            review_text=req.review_text,
            paper_arxiv_id=req.paper_arxiv_id,
        )
        response = _ghost_to_response(score)

        # Persist (best effort — don't fail request on DB error)
        try:
            text_hash = _hash_review(req.review_text)
            await db.insert_analysis(
                review_text_hash=text_hash,
                paper_arxiv_id=req.paper_arxiv_id,
                ghost_data=response.model_dump(),
                word_count=len(req.review_text.split()),
            )
        except Exception as e:
            logger.warning(f"Persistence skipped: {e}")

        return response
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {e}")


@router.post("/analyze/batch", response_model=list[GhostScoreResponse])
async def analyze_batch(req: BatchAnalyzeRequest) -> list[GhostScoreResponse]:
    """Analyze a batch of reviews together. Enables Batch DNA clustering."""
    try:
        review_pairs = [
            (r.get("review_id", f"r{i}"), r["review_text"])
            for i, r in enumerate(req.reviews)
            if "review_text" in r and len(r["review_text"]) >= 20
        ]
        if not review_pairs:
            raise HTTPException(status_code=400, detail="No valid reviews provided")

        scores = await analyze_review_batch(
            reviews=review_pairs,
            paper_arxiv_id=req.paper_arxiv_id,
        )
        return [_ghost_to_response(s) for s in scores]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch analysis error: {e}")
