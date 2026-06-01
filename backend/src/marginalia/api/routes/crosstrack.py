"""
Cross-Track Extension — Track G: Marketplace Product Reviews.

Exposes the product review detection engine via API.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from marginalia.engines.product_review import score_product_review

logger = logging.getLogger(__name__)
router = APIRouter()


class ProductReviewRequest(BaseModel):
    review_text: str = Field(..., min_length=10, max_length=5000)
    product_specs: dict[str, str] | None = Field(
        None,
        description="Optional product specs for mismatch detection",
        examples=[{"connectivity": "wired", "weight": "200g", "battery": "none"}],
    )


class ProductAnchorOut(BaseModel):
    text: str
    anchor_type: str


class ProductReviewResponse(BaseModel):
    ghost_score: float
    specificity_score: float
    generic_phrase_count: int
    product_anchors: list[ProductAnchorOut]
    spec_mismatch: bool
    spec_mismatch_reason: str | None
    label: str
    explanation: str


@router.post(
    "/analyze/product-review",
    response_model=ProductReviewResponse,
    summary="Analyze a marketplace product review (Track G cross-track)",
    tags=["cross-track"],
)
async def analyze_product_review(req: ProductReviewRequest) -> ProductReviewResponse:
    """
    Detect AI-generated product reviews using the same detection engine
    adapted for marketplace content (Amazon, Trustpilot, etc.).

    **Signals:**
    - Product anchor density (model numbers, dimensions, features)
    - Generic AI phrase detection
    - Spec-claim mismatch (review claims features the product doesn't have)
    """
    try:
        result = score_product_review(req.review_text, req.product_specs)
        return ProductReviewResponse(
            ghost_score=result.ghost_score,
            specificity_score=result.specificity_score,
            generic_phrase_count=result.generic_phrase_count,
            product_anchors=[
                ProductAnchorOut(text=a.text, anchor_type=a.anchor_type)
                for a in result.product_anchors
            ],
            spec_mismatch=result.spec_mismatch,
            spec_mismatch_reason=result.spec_mismatch_reason,
            label=result.label,
            explanation=result.explanation,
        )
    except Exception as e:
        logger.exception(f"Product review analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {e}")
