"""
Asymmetry Engine — Layer 2 of Ghost Score.

Detects AI-generated reviews by measuring whether the reviewer's content
is grounded in the paper's body or only in its abstract.

AI reviewers are typically fed only the abstract → review reflects abstract content.
Real reviewers read the full paper → review references body-specific content.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from marginalia.engines.specificity import split_sentences
from marginalia.ml.embeddings import EmbeddingService


@dataclass
class AsymmetryResult:
    score: float
    sim_abstract: float
    sim_body: float
    asymmetry_ratio: float
    hallucinated_sentences: list[str] = field(default_factory=list)


def score_asymmetry(
    review_text: str,
    abstract: str,
    body_sections: dict[str, str],
    embedder: EmbeddingService,
    hallucination_threshold: float = 0.30,
) -> AsymmetryResult:
    """
    Score a review's asymmetry between abstract-grounding and body-grounding.

    Args:
        review_text: Full peer review text.
        abstract: Paper abstract text.
        body_sections: Dict of section_name → section_text (introduction, methodology, etc.)
        embedder: EmbeddingService instance.
        hallucination_threshold: Cosine threshold below which a sentence is flagged
                                  as ungrounded (potentially hallucinated).

    Returns:
        AsymmetryResult with scores and hallucination flags.
    """
    if not review_text.strip():
        return AsymmetryResult(
            score=0.0,
            sim_abstract=0.0,
            sim_body=0.0,
            asymmetry_ratio=0.0,
            hallucinated_sentences=[],
        )

    # No paper context — return neutral score
    has_abstract = bool(abstract and abstract.strip())
    valid_sections = [s for s in body_sections.values() if s and s.strip()]
    has_body = bool(valid_sections)

    if not has_abstract and not has_body:
        return AsymmetryResult(
            score=0.0,
            sim_abstract=0.0,
            sim_body=0.0,
            asymmetry_ratio=0.0,
            hallucinated_sentences=[],
        )

    # Embed review
    review_emb = embedder.encode_one(review_text)

    # Embed abstract
    if has_abstract:
        abstract_emb = embedder.encode_one(abstract)
        sim_abstract = embedder.cosine(review_emb, abstract_emb)
    else:
        sim_abstract = 0.0

    # Embed body sections individually, take max similarity
    sim_body = 0.0
    if has_body:
        body_embs = embedder.encode(valid_sections)
        body_sims = embedder.cosine_matrix(review_emb.reshape(1, -1), body_embs)[0]
        sim_body = float(np.max(body_sims))

    # Asymmetry ratio: how much does review depend on abstract vs body?
    denom = sim_abstract + sim_body
    if denom > 0:
        asymmetry_ratio = sim_abstract / denom
    else:
        asymmetry_ratio = 0.5  # neutral

    # Hallucination check: per-sentence grounding against full paper text
    hallucinated: list[str] = []
    if has_abstract or has_body:
        full_paper_chunks = []
        if has_abstract:
            full_paper_chunks.append(abstract)
        full_paper_chunks.extend(valid_sections)

        sentences = split_sentences(review_text)
        # Skip very short sentences (single words, punctuation)
        meaningful_sentences = [s for s in sentences if len(s.split()) >= 4]

        if meaningful_sentences:
            sentence_embs = embedder.encode(meaningful_sentences)
            paper_embs = embedder.encode(full_paper_chunks)
            sim_matrix = embedder.cosine_matrix(sentence_embs, paper_embs)

            # For each sentence, max similarity across all paper chunks
            for i, sent in enumerate(meaningful_sentences):
                max_sim = float(np.max(sim_matrix[i]))
                if max_sim < hallucination_threshold:
                    hallucinated.append(sent)

    score = asymmetry_to_score(asymmetry_ratio, has_body)

    return AsymmetryResult(
        score=score,
        sim_abstract=round(sim_abstract, 3),
        sim_body=round(sim_body, 3),
        asymmetry_ratio=round(asymmetry_ratio, 3),
        hallucinated_sentences=hallucinated,
    )


def asymmetry_to_score(ratio: float, has_body: bool) -> float:
    """
    Map asymmetry ratio to 0-100 ghost score.

    ratio ~0.5 (balanced)        → score ~20  (human)
    ratio ~0.7  (lean abstract)  → score ~50
    ratio ~0.85+ (abstract-heavy)→ score ~90  (AI)

    If only abstract is available (no body), we cannot compute true asymmetry,
    so return a neutral score with a small penalty.
    """
    if not has_body:
        # No body sections — can't reliably detect asymmetry
        return 30.0

    x0, k = 0.65, 12.0
    raw = 1.0 / (1.0 + math.exp(-k * (ratio - x0)))
    return round(raw * 100, 1)
