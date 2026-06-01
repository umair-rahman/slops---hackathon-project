"""Pydantic schemas for API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────────────────

class AnalyzeReviewRequest(BaseModel):
    review_text: str = Field(..., min_length=20, description="Full peer review text")
    paper_arxiv_id: str | None = Field(None, description="arXiv ID e.g. '1706.03762'")
    paper_url: str | None = Field(None, description="arXiv or OpenReview paper URL")
    reviewer_id: str | None = Field(None, description="Reviewer ID for batch context")


class BatchAnalyzeRequest(BaseModel):
    reviews: list[dict] = Field(..., description="List of {review_id, review_text}")
    paper_arxiv_id: str | None = Field(None, description="Shared paper arXiv ID")


class ScanConferenceRequest(BaseModel):
    venue_id: str = Field(..., description="OpenReview venue ID e.g. 'ICLR.cc/2024/Conference'")
    max_papers: int = Field(50, ge=1, le=2000, description="Max papers to scan")


# ── Sub-result Models ────────────────────────────────────────────────────────

class AnchorDetail(BaseModel):
    text: str
    anchor_type: str


class SentenceResult(BaseModel):
    text: str
    anchor_count: int
    anchors: list[AnchorDetail]
    is_hallucinated: bool
    hallucination_reason: str | None = None


class SpecificityResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    anchors_per_100_words: float
    total_anchors: int
    sentences: list[SentenceResult]


class AsymmetryResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    sim_abstract: float
    sim_body: float
    asymmetry_ratio: float
    hallucinated_sentences: list[str] = []


class BatchDNAResult(BaseModel):
    score: float | None = Field(None, ge=0, le=100)
    cluster_id: int | None = None
    cluster_size: int | None = None
    available: bool = False
    reason: str | None = None


# ── Main Response Models ─────────────────────────────────────────────────────

class GhostScoreResponse(BaseModel):
    overall: float = Field(..., ge=0, le=100, description="Ghost probability 0-100")
    label: str
    confidence_low: float
    confidence_high: float
    specificity: SpecificityResult
    asymmetry: AsymmetryResult
    batch_dna: BatchDNAResult
    explanation: str


class ReviewerSummary(BaseModel):
    reviewer_id: str
    total_reviews: int
    avg_ghost_score: float
    has_dna_cluster: bool
    drift_detected: bool


class ConferenceScanResult(BaseModel):
    venue_id: str
    total_papers: int
    total_reviews: int
    flagged_count: int
    flagged_percent: float
    top_suspect_reviewers: list[ReviewerSummary]
    score_distribution: list[int]
    avg_score: float = 0.0


class ReviewerProfileResult(BaseModel):
    reviewer_id: str
    total_reviews: int
    avg_ghost_score: float
    drift_detected: bool
    drift_point: str | None = None
    cluster_count: int = 0
    reviews: list[dict] = []
