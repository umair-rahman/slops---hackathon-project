"""
Public API v1 — versioned, rate-limited, documented endpoints.

These are the stable public-facing endpoints for external integrations.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from marginalia.api.routes.analyze import _ghost_to_response
from marginalia.api.schemas import GhostScoreResponse
from marginalia.engines.collusion import detect_collusion
from marginalia.engines.pipeline import analyze_single_review
from marginalia.engines.time_on_task import estimate_time_on_task

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ────────────────────────────────────────────────

class V1AnalyzeRequest(BaseModel):
    review_text: str = Field(
        ...,
        min_length=20,
        max_length=10000,
        description="Full peer review text (20-10000 chars)",
    )
    paper_arxiv_id: str | None = Field(
        None,
        description="arXiv paper ID for asymmetry analysis (e.g. '1706.03762')",
    )


class CollusionReviewInput(BaseModel):
    reviewer_id: str = Field(..., description="Reviewer identifier")
    review_text: str = Field(..., min_length=20, description="Review text")


class V1CollusionRequest(BaseModel):
    paper_id: str = Field(..., description="Paper identifier")
    reviews: list[CollusionReviewInput] = Field(
        ..., min_length=2, description="At least 2 reviews for the same paper"
    )
    similarity_threshold: float = Field(
        0.80, ge=0.5, le=1.0, description="Similarity threshold (0.5-1.0)"
    )


class CollusionPairOut(BaseModel):
    reviewer_a: str
    reviewer_b: str
    similarity: float
    shared_opener: bool


class V1CollusionResponse(BaseModel):
    paper_id: str
    total_reviewers: int
    flagged_pairs: list[CollusionPairOut]
    max_similarity: float
    collusion_detected: bool
    collusion_score: float


class TimingInput(BaseModel):
    review_id: str
    review_text: str
    timestamp_ms: int = Field(..., description="Unix timestamp in milliseconds")


class V1TimeOnTaskRequest(BaseModel):
    reviewer_id: str
    reviews: list[TimingInput] = Field(..., min_length=1)


class ReviewTimingOut(BaseModel):
    review_id: str
    review_word_count: int
    timestamp_ms: int
    min_realistic_seconds: float
    implausible: bool
    reason: str | None = None


class V1TimeOnTaskResponse(BaseModel):
    reviewer_id: str
    total_reviews: int
    implausible_count: int
    burst_detected: bool
    burst_window_seconds: float | None
    reviews_in_burst: int
    time_on_task_score: float
    implausible_reviews: list[ReviewTimingOut]


class V1HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    endpoints: list[str]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/health", response_model=V1HealthResponse, summary="API health check")
async def v1_health() -> V1HealthResponse:
    """Check API health and list available v1 endpoints."""
    return V1HealthResponse(
        status="ok",
        version="1.0.0",
        service="marginalia",
        endpoints=[
            "GET  /api/v1/health",
            "POST /api/v1/analyze",
            "POST /api/v1/collusion",
            "POST /api/v1/time-on-task",
        ],
    )


@router.post(
    "/analyze",
    response_model=GhostScoreResponse,
    summary="Analyze a peer review for AI-generation signals",
    description="""
Analyze a single peer review and return a Ghost Score (0-100).

**Ghost Score interpretation:**
- 0-25: Likely human
- 25-50: Uncertain, lean human
- 50-70: Uncertain, lean AI
- 70-85: Likely AI-generated
- 85-100: Almost certainly AI-generated

**Layers:**
- Specificity Index: anchor density (equations, figures, sections)
- Asymmetry Score: abstract vs body grounding (requires paper_arxiv_id)
- Batch DNA: structural fingerprint clustering (requires batch context)

**Rate limit:** 20 requests per minute per IP.
""",
)
async def v1_analyze(req: V1AnalyzeRequest) -> GhostScoreResponse:
    """Public v1 analyze endpoint."""
    try:
        score = await analyze_single_review(
            review_text=req.review_text,
            paper_arxiv_id=req.paper_arxiv_id,
        )
        return _ghost_to_response(score)
    except Exception as e:
        logger.exception(f"v1 analyze failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {e}")


@router.post(
    "/collusion",
    response_model=V1CollusionResponse,
    summary="Detect cross-reviewer collusion on a single paper",
    description="""
Detect whether multiple reviewers of the same paper used the same AI prompt.

Computes pairwise structural similarity between all review pairs.
Pairs with similarity above the threshold are flagged as potential collusion.

**Collusion score interpretation:**
- 0: No collusion detected
- 50-70: Moderate similarity, possible shared template
- 70-100: High similarity, likely same AI prompt

**Rate limit:** 20 requests per minute per IP.
""",
)
async def v1_collusion(req: V1CollusionRequest) -> V1CollusionResponse:
    """Detect cross-reviewer collusion on a paper."""
    try:
        reviews = [(r.reviewer_id, r.review_text) for r in req.reviews]
        result = detect_collusion(req.paper_id, reviews, req.similarity_threshold)

        return V1CollusionResponse(
            paper_id=result.paper_id,
            total_reviewers=result.total_reviewers,
            flagged_pairs=[
                CollusionPairOut(
                    reviewer_a=p.reviewer_a,
                    reviewer_b=p.reviewer_b,
                    similarity=p.similarity,
                    shared_opener=p.shared_opener,
                )
                for p in result.flagged_pairs
            ],
            max_similarity=result.max_similarity,
            collusion_detected=result.collusion_detected,
            collusion_score=result.collusion_score,
        )
    except Exception as e:
        logger.exception(f"v1 collusion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Collusion detection error: {e}")


@router.post(
    "/time-on-task",
    response_model=V1TimeOnTaskResponse,
    summary="Estimate whether a reviewer's submission timing is plausible",
    description="""
Analyze a reviewer's submission timestamps against review lengths to detect
implausible patterns (e.g., 5 long reviews submitted in 10 minutes).

**Time-on-task score:**
- 0: All timings plausible
- 50+: Burst detected or implausible timings
- 100: Extreme implausibility

**Rate limit:** 20 requests per minute per IP.
""",
)
async def v1_time_on_task(req: V1TimeOnTaskRequest) -> V1TimeOnTaskResponse:
    """Estimate time-on-task plausibility for a reviewer."""
    try:
        reviews = [
            (r.review_id, r.review_text, r.timestamp_ms) for r in req.reviews
        ]
        result = estimate_time_on_task(req.reviewer_id, reviews)

        return V1TimeOnTaskResponse(
            reviewer_id=result.reviewer_id,
            total_reviews=result.total_reviews,
            implausible_count=result.implausible_count,
            burst_detected=result.burst_detected,
            burst_window_seconds=result.burst_window_seconds,
            reviews_in_burst=result.reviews_in_burst,
            time_on_task_score=result.time_on_task_score,
            implausible_reviews=[
                ReviewTimingOut(
                    review_id=rt.review_id,
                    review_word_count=rt.review_word_count,
                    timestamp_ms=rt.timestamp_ms,
                    min_realistic_seconds=rt.min_realistic_seconds,
                    implausible=rt.implausible,
                    reason=rt.reason,
                )
                for rt in result.implausible_reviews
            ],
        )
    except Exception as e:
        logger.exception(f"v1 time-on-task failed: {e}")
        raise HTTPException(status_code=500, detail=f"Time-on-task error: {e}")
