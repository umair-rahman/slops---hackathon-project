"""
Aggregator — Combines all engine scores into final Ghost Score.

Weights:
  Specificity  40%  (inverted: high specificity → low ghost contribution)
  Asymmetry    35%
  Batch DNA    25%  (when available, redistributed otherwise)
"""

from __future__ import annotations

from dataclasses import dataclass

from marginalia.engines.asymmetry import AsymmetryResult
from marginalia.engines.batch_dna import BatchDNAResult
from marginalia.engines.specificity import SpecificityResult


@dataclass
class GhostScore:
    overall: float
    label: str
    confidence_low: float
    confidence_high: float
    specificity: SpecificityResult
    asymmetry: AsymmetryResult
    batch_dna: BatchDNAResult
    explanation: str


# Weights
W_SPECIFICITY = 0.40
W_ASYMMETRY = 0.35
W_BATCH_DNA = 0.25


def compute_ghost_score(
    specificity: SpecificityResult,
    asymmetry: AsymmetryResult,
    batch_dna: BatchDNAResult | None = None,
    review_word_count: int = 300,
) -> GhostScore:
    """
    Combine engine scores into a single Ghost Score (0-100).

    High = AI-generated. Low = human-written.
    """
    # Invert specificity: 100 - specificity_score = ghost contribution
    spec_ghost = 100.0 - specificity.score

    # Asymmetry score directly contributes (high = AI)
    asym_ghost = asymmetry.score

    # Decide whether to use Batch DNA
    use_batch = batch_dna is not None and batch_dna.available and batch_dna.score is not None
    asym_available = asymmetry.score > 0.0  # asymmetry returns 0.0 when no paper context

    # Weight redistribution based on what's available
    if use_batch and asym_available:
        overall = (
            W_SPECIFICITY * spec_ghost
            + W_ASYMMETRY * asym_ghost
            + W_BATCH_DNA * batch_dna.score  # type: ignore
        )
    elif use_batch and not asym_available:
        # No paper context — distribute asymmetry weight to spec + batch
        w_spec = W_SPECIFICITY + W_ASYMMETRY * 0.6
        w_batch = W_BATCH_DNA + W_ASYMMETRY * 0.4
        total = w_spec + w_batch
        overall = (w_spec * spec_ghost + w_batch * batch_dna.score) / total  # type: ignore
    elif asym_available:
        # No batch context — redistribute batch weight
        w_spec = W_SPECIFICITY + W_BATCH_DNA * 0.5
        w_asym = W_ASYMMETRY + W_BATCH_DNA * 0.5
        total = w_spec + w_asym
        overall = (w_spec * spec_ghost + w_asym * asym_ghost) / total
    else:
        # Only specificity — full weight on it
        overall = spec_ghost

    overall = round(min(max(overall, 0.0), 100.0), 1)

    # Confidence interval — wider for short reviews
    ci_half = _confidence_half_width(review_word_count)
    ci_low = round(max(overall - ci_half, 0.0), 1)
    ci_high = round(min(overall + ci_half, 100.0), 1)

    label = _score_to_label(overall)
    explanation = _build_explanation(
        overall, spec_ghost, asym_ghost, batch_dna, asym_available, use_batch
    )

    final_batch = batch_dna or BatchDNAResult(
        score=None,
        cluster_id=None,
        cluster_size=None,
        available=False,
        reason="No batch context provided",
    )

    return GhostScore(
        overall=overall,
        label=label,
        confidence_low=ci_low,
        confidence_high=ci_high,
        specificity=specificity,
        asymmetry=asymmetry,
        batch_dna=final_batch,
        explanation=explanation,
    )


def _score_to_label(score: float) -> str:
    if score < 25:
        return "likely human"
    elif score < 50:
        return "uncertain — lean human"
    elif score < 70:
        return "uncertain — lean AI"
    elif score < 85:
        return "likely AI-generated"
    else:
        return "almost certainly AI-generated"


def _confidence_half_width(word_count: int) -> float:
    """Shorter reviews → wider confidence interval."""
    if word_count < 100:
        return 20.0
    elif word_count < 200:
        return 12.0
    elif word_count < 400:
        return 8.0
    else:
        return 5.0


def _build_explanation(
    overall: float,
    spec_ghost: float,
    asym_ghost: float,
    batch_dna: BatchDNAResult | None,
    asym_available: bool,
    use_batch: bool,
) -> str:
    parts = []

    if spec_ghost > 70:
        parts.append("the review contains almost no specific references to paper elements")
    elif spec_ghost > 50:
        parts.append("the review uses few specific references")
    elif spec_ghost < 30:
        parts.append("the review cites specific equations, figures, or sections")

    if asym_available:
        if asym_ghost > 70:
            parts.append("content appears heavily abstract-derived rather than body-grounded")
        elif asym_ghost < 30:
            parts.append("content is well-grounded in the paper body")

    if use_batch and batch_dna is not None:
        if batch_dna.cluster_size and batch_dna.cluster_size >= 2:
            parts.append(
                f"this review shares structural DNA with {batch_dna.cluster_size - 1} "
                f"other review(s) in the batch"
            )

    if not parts:
        return f"Ghost score {overall}/100 — mixed signals across detection layers."

    return f"Ghost score {overall}/100 — " + "; ".join(parts) + "."
