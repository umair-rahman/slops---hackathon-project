"""
Detection Pipeline — Orchestrates all 3 engines for review analysis.
"""

from __future__ import annotations

import logging

from marginalia.data.arxiv import ArxivPaper, arxiv_client
from marginalia.engines.aggregator import GhostScore, compute_ghost_score
from marginalia.engines.asymmetry import score_asymmetry
from marginalia.engines.batch_dna import BatchDNAResult, score_batch_dna
from marginalia.engines.specificity import score_specificity
from marginalia.ml.embeddings import embedder

logger = logging.getLogger(__name__)


async def analyze_single_review(
    review_text: str,
    paper_arxiv_id: str | None = None,
) -> GhostScore:
    """
    Analyze a single review with available signals.

    - Always runs Specificity Engine
    - Runs Asymmetry Engine if paper_arxiv_id provided
    - Skips Batch DNA (needs batch context)
    """
    word_count = len(review_text.split())

    # Layer 1: Specificity (always available)
    spec_result = score_specificity(review_text)

    # Layer 2: Asymmetry (if paper available)
    paper: ArxivPaper | None = None
    if paper_arxiv_id:
        try:
            paper = await arxiv_client.fetch_paper(paper_arxiv_id)
        except Exception as e:
            logger.warning(f"Failed to fetch paper {paper_arxiv_id}: {e}")

    if paper:
        asym_result = score_asymmetry(
            review_text=review_text,
            abstract=paper.abstract,
            body_sections=paper.sections.body_dict(),
            embedder=embedder,
        )
    else:
        # No paper context — return zero-score result
        from marginalia.engines.asymmetry import AsymmetryResult
        asym_result = AsymmetryResult(
            score=0.0,
            sim_abstract=0.0,
            sim_body=0.0,
            asymmetry_ratio=0.0,
            hallucinated_sentences=[],
        )

    # Layer 3: Not available for single review
    batch_result: BatchDNAResult | None = None

    # Mark hallucinated sentences in specificity result (cross-engine)
    if asym_result.hallucinated_sentences:
        hall_set = set(asym_result.hallucinated_sentences)
        for sent in spec_result.sentences:
            if sent.text in hall_set:
                sent.is_hallucinated = True
                sent.hallucination_reason = "Content not grounded in paper text"

    return compute_ghost_score(
        specificity=spec_result,
        asymmetry=asym_result,
        batch_dna=batch_result,
        review_word_count=word_count,
    )


async def analyze_review_batch(
    reviews: list[tuple[str, str]],
    paper_arxiv_id: str | None = None,
) -> list[GhostScore]:
    """
    Analyze a batch of reviews together.

    Args:
        reviews: List of (review_id, review_text) tuples.
        paper_arxiv_id: Optional shared paper for asymmetry analysis.

    Returns:
        List of GhostScore in same order as input.
    """
    if not reviews:
        return []

    # Fetch paper once (shared across all reviews if applicable)
    paper: ArxivPaper | None = None
    if paper_arxiv_id:
        try:
            paper = await arxiv_client.fetch_paper(paper_arxiv_id)
        except Exception as e:
            logger.warning(f"Failed to fetch paper: {e}")

    # Run Batch DNA across the whole batch
    batch_results = score_batch_dna(reviews)

    final_scores: list[GhostScore] = []
    for review_id, review_text in reviews:
        spec_result = score_specificity(review_text)

        if paper:
            asym_result = score_asymmetry(
                review_text=review_text,
                abstract=paper.abstract,
                body_sections=paper.sections.body_dict(),
                embedder=embedder,
            )
        else:
            from marginalia.engines.asymmetry import AsymmetryResult
            asym_result = AsymmetryResult(
                score=0.0,
                sim_abstract=0.0,
                sim_body=0.0,
                asymmetry_ratio=0.0,
                hallucinated_sentences=[],
            )

        batch_result = batch_results.get(review_id)

        if asym_result.hallucinated_sentences:
            hall_set = set(asym_result.hallucinated_sentences)
            for sent in spec_result.sentences:
                if sent.text in hall_set:
                    sent.is_hallucinated = True
                    sent.hallucination_reason = "Content not grounded in paper text"

        word_count = len(review_text.split())
        score = compute_ghost_score(
            specificity=spec_result,
            asymmetry=asym_result,
            batch_dna=batch_result,
            review_word_count=word_count,
        )
        final_scores.append(score)

    return final_scores
