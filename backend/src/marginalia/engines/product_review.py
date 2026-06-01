"""
Cross-Track Extension — Track G: Marketplace Product Reviews.

Adapts Marginalia's detection signals for product review slop.
Same core insight: AI product reviews are generic, lack specifics,
and cluster structurally when generated from the same prompt.

Key differences from academic reviews:
- Anchors: product specs (model numbers, dimensions, features) instead of equations/figures
- Asymmetry: review vs product description instead of review vs paper
- Batch DNA: same clustering approach works identically
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


# Product-specific anchor patterns
PRODUCT_ANCHOR_PATTERNS: dict[str, str] = {
    "model_number": r"\b[A-Z]{1,4}[-\s]?\d{3,8}[A-Z]?\b",
    "dimension": r"\b\d+(?:\.\d+)?\s*(?:inch(?:es)?|cm|mm|ft|\")\b",
    "weight": r"\b\d+(?:\.\d+)?\s*(?:lbs?|kg|oz|grams?)\b",
    "battery": r"\b\d+\s*(?:mAh|hours?|days?)\s*(?:battery|life|charge)?\b",
    "price": r"\$\d+(?:\.\d{2})?",
    "rating": r"\b[1-5]\s*(?:star|\/5|out of 5)\b",
    "specific_feature": r"\b(?:bluetooth|wifi|usb-?c|hdmi|4k|1080p|waterproof|ip\d+)\b",
    "duration": r"\b(?:after|within|for)\s+\d+\s+(?:days?|weeks?|months?|years?)\b",
    "comparison": r"\b(?:better|worse|same|similar)\s+(?:than|to)\s+\w+",
}

COMPILED_PRODUCT_PATTERNS = {
    k: re.compile(v, re.IGNORECASE)
    for k, v in PRODUCT_ANCHOR_PATTERNS.items()
}

# Generic AI product review phrases
AI_PRODUCT_PHRASES = [
    "great product", "highly recommend", "works as expected",
    "good quality", "fast shipping", "easy to use",
    "worth the price", "very satisfied", "would recommend",
    "five stars", "excellent product", "love this product",
    "amazing product", "perfect product", "best purchase",
]


@dataclass
class ProductAnchor:
    text: str
    anchor_type: str


@dataclass
class ProductReviewScore:
    ghost_score: float
    specificity_score: float
    generic_phrase_count: int
    product_anchors: list[ProductAnchor]
    spec_mismatch: bool
    spec_mismatch_reason: str | None
    label: str
    explanation: str


def score_product_review(
    review_text: str,
    product_specs: dict[str, str] | None = None,
) -> ProductReviewScore:
    """
    Score a product review for AI-generation signals.

    Args:
        review_text: The product review text.
        product_specs: Optional dict of product specifications
                      (e.g., {"battery": "5000mAh", "weight": "200g"}).
                      Used for spec-claim mismatch detection.

    Returns:
        ProductReviewScore with ghost score and explanation.
    """
    if not review_text or not review_text.strip():
        return ProductReviewScore(
            ghost_score=50.0,
            specificity_score=50.0,
            generic_phrase_count=0,
            product_anchors=[],
            spec_mismatch=False,
            spec_mismatch_reason=None,
            label="uncertain",
            explanation="Empty review.",
        )

    word_count = max(len(review_text.split()), 1)

    # Extract product anchors
    anchors: list[ProductAnchor] = []
    for anchor_type, pattern in COMPILED_PRODUCT_PATTERNS.items():
        for match in pattern.finditer(review_text):
            anchors.append(ProductAnchor(text=match.group(), anchor_type=anchor_type))

    anchor_density = (len(anchors) / word_count) * 100

    # Count generic AI phrases
    review_lower = review_text.lower()
    generic_count = sum(
        1 for phrase in AI_PRODUCT_PHRASES if phrase in review_lower
    )
    generic_density = (generic_count / word_count) * 100

    # Specificity score (higher = more specific = more human)
    specificity = _anchor_density_to_score(anchor_density)

    # Generic penalty
    generic_penalty = min(generic_density * 20, 40)

    # Spec-claim mismatch detection
    spec_mismatch = False
    spec_mismatch_reason = None

    if product_specs:
        spec_mismatch, spec_mismatch_reason = _check_spec_mismatch(
            review_text, product_specs
        )

    # Ghost score
    spec_ghost = 100.0 - specificity + generic_penalty
    if spec_mismatch:
        spec_ghost = min(spec_ghost + 30, 100)

    ghost_score = round(min(max(spec_ghost, 0.0), 100.0), 1)

    label = _score_to_label(ghost_score)
    explanation = _build_explanation(
        ghost_score, specificity, generic_count, spec_mismatch, spec_mismatch_reason
    )

    return ProductReviewScore(
        ghost_score=ghost_score,
        specificity_score=round(specificity, 1),
        generic_phrase_count=generic_count,
        product_anchors=anchors,
        spec_mismatch=spec_mismatch,
        spec_mismatch_reason=spec_mismatch_reason,
        label=label,
        explanation=explanation,
    )


def _check_spec_mismatch(
    review_text: str, product_specs: dict[str, str]
) -> tuple[bool, str | None]:
    """
    Check if review claims contradict product specifications.

    Example: review says "battery lasts 20 hours" but product is wired.
    """
    review_lower = review_text.lower()

    # Check for battery claims on non-battery products
    if "battery" not in product_specs and "wired" not in product_specs:
        pass  # Can't determine
    elif "wired" in product_specs.get("connectivity", "").lower():
        battery_claim = re.search(
            r"\d+\s*(?:hour|day|mah|charge)", review_lower
        )
        if battery_claim:
            return True, f"Review mentions battery life but product is wired"

    # Check for wireless claims on wired products
    if "wired" in product_specs.get("connectivity", "").lower():
        wireless_claim = re.search(r"\b(?:wireless|bluetooth|wifi)\b", review_lower)
        if wireless_claim:
            return True, "Review mentions wireless features but product is wired"

    # Check for dimension mismatches
    spec_weight = product_specs.get("weight", "")
    if spec_weight:
        weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lbs?|kg)", review_lower)
        if weight_match:
            review_weight = float(weight_match.group(1))
            spec_match = re.search(r"(\d+(?:\.\d+)?)", spec_weight)
            if spec_match:
                spec_weight_val = float(spec_match.group(1))
                if abs(review_weight - spec_weight_val) / max(spec_weight_val, 1) > 0.5:
                    return True, f"Review claims weight {review_weight} but spec says {spec_weight_val}"

    return False, None


def _anchor_density_to_score(density: float) -> float:
    """Map product anchor density to specificity score."""
    x0, k = 1.5, 1.2
    raw = 1.0 / (1.0 + math.exp(-k * (density - x0)))
    return round(raw * 100, 1)


def _score_to_label(score: float) -> str:
    if score < 30:
        return "likely genuine"
    elif score < 55:
        return "uncertain"
    elif score < 75:
        return "likely AI-generated"
    else:
        return "almost certainly AI-generated"


def _build_explanation(
    score: float,
    specificity: float,
    generic_count: int,
    spec_mismatch: bool,
    mismatch_reason: str | None,
) -> str:
    parts = []
    if specificity < 30:
        parts.append("review contains no specific product details")
    if generic_count >= 2:
        parts.append(f"contains {generic_count} generic AI phrases")
    if spec_mismatch and mismatch_reason:
        parts.append(f"spec mismatch: {mismatch_reason}")

    if not parts:
        return f"Ghost score {score}/100 — mixed signals."
    return f"Ghost score {score}/100 — " + "; ".join(parts) + "."
