"""
Batch DNA Engine — Layer 3 of Ghost Score.

Detects AI-generated review batches by extracting structural fingerprints
from each review and clustering. Tight clusters indicate same prompt
applied across multiple papers.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

import numpy as np

from marginalia.engines.specificity import split_sentences


# Common transition/discourse markers (frequency varies between human and AI)
TRANSITION_WORDS = [
    "however", "moreover", "furthermore", "additionally", "specifically",
    "particularly", "notably", "importantly", "interestingly", "surprisingly",
    "overall", "finally", "firstly", "secondly", "lastly", "indeed",
    "nevertheless", "nonetheless", "consequently", "thus", "therefore",
    "hence", "accordingly", "subsequently", "alternatively", "conversely",
    "meanwhile", "subsequently", "indeed", "namely", "essentially",
    "fundamentally", "ultimately", "primarily", "presumably", "arguably",
]

# Common review opening phrases (AI uses these heavily)
COMMON_OPENERS = [
    "the paper", "this paper", "this work", "the authors",
    "in this paper", "the proposed", "the study", "the research",
    "the manuscript", "the submission",
]


@dataclass
class ReviewFingerprint:
    review_id: str
    paragraph_count: int
    sentence_count: int
    word_count: int
    avg_sentence_length: float
    sentence_length_std: float
    opener_pattern: str  # first 3 words of first sentence (lowercased)
    transition_density: float  # transitions per 100 words
    punctuation_density: dict[str, float]  # density per 100 chars
    common_opener_count: int  # how many sentences start with common openers
    sentiment_trajectory: list[int]  # +1/0/-1 per sentence (simple polarity)
    feature_vector: np.ndarray = None  # type: ignore


@dataclass
class BatchDNAResult:
    score: float | None
    cluster_id: int | None
    cluster_size: int | None
    available: bool
    reason: str | None = None


def extract_fingerprint(review_id: str, review_text: str) -> ReviewFingerprint:
    """Extract a structural fingerprint vector from a review."""
    text = review_text or ""

    # Paragraph & sentence counts
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    paragraph_count = len(paragraphs) or 1

    sentences = split_sentences(text)
    sentence_count = len(sentences) or 1

    word_count = len([w for w in text.split() if w])
    word_count = max(word_count, 1)

    # Sentence length stats
    sentence_lengths = [len(s.split()) for s in sentences]
    if len(sentence_lengths) >= 2:
        avg_sentence_length = statistics.mean(sentence_lengths)
        sentence_length_std = statistics.stdev(sentence_lengths)
    elif len(sentence_lengths) == 1:
        avg_sentence_length = float(sentence_lengths[0])
        sentence_length_std = 0.0
    else:
        avg_sentence_length = 0.0
        sentence_length_std = 0.0

    # Opener pattern — first 3 words of first sentence
    if sentences:
        first_words = sentences[0].lower().split()[:3]
        opener_pattern = " ".join(first_words)
    else:
        opener_pattern = ""

    # Common opener count
    common_opener_count = 0
    for sent in sentences:
        sent_lower = sent.lower().strip()
        for opener in COMMON_OPENERS:
            if sent_lower.startswith(opener):
                common_opener_count += 1
                break

    # Transition word density
    text_lower = text.lower()
    transition_count = 0
    for trans in TRANSITION_WORDS:
        transition_count += len(re.findall(r"\b" + re.escape(trans) + r"\b", text_lower))
    transition_density = (transition_count / word_count) * 100

    # Punctuation density
    char_count = max(len(text), 1)
    punct_density = {
        "comma": text.count(",") / char_count * 100,
        "semicolon": text.count(";") / char_count * 100,
        "colon": text.count(":") / char_count * 100,
        "em_dash": (text.count("—") + text.count("--")) / char_count * 100,
        "parens": (text.count("(") + text.count(")")) / char_count * 100,
        "question": text.count("?") / char_count * 100,
    }

    # Simple sentiment trajectory (very rough: positive/negative word ratio per sentence)
    positive_words = {"good", "great", "excellent", "strong", "novel", "interesting",
                      "promising", "well", "clear", "thorough", "rigorous", "elegant"}
    negative_words = {"weak", "limited", "unclear", "lacking", "missing", "flawed",
                      "insufficient", "poor", "incorrect", "wrong", "misleading"}

    trajectory: list[int] = []
    for sent in sentences:
        words_in_sent = set(sent.lower().split())
        pos = len(words_in_sent & positive_words)
        neg = len(words_in_sent & negative_words)
        if pos > neg:
            trajectory.append(1)
        elif neg > pos:
            trajectory.append(-1)
        else:
            trajectory.append(0)

    fp = ReviewFingerprint(
        review_id=review_id,
        paragraph_count=paragraph_count,
        sentence_count=sentence_count,
        word_count=word_count,
        avg_sentence_length=round(avg_sentence_length, 2),
        sentence_length_std=round(sentence_length_std, 2),
        opener_pattern=opener_pattern,
        transition_density=round(transition_density, 3),
        punctuation_density=punct_density,
        common_opener_count=common_opener_count,
        sentiment_trajectory=trajectory,
    )
    fp.feature_vector = _to_feature_vector(fp)
    return fp


def _to_feature_vector(fp: ReviewFingerprint) -> np.ndarray:
    """Convert fingerprint to numerical feature vector for clustering."""
    # Normalize against typical review (300 words)
    features: list[float] = [
        fp.paragraph_count / 5.0,
        fp.sentence_count / 20.0,
        fp.word_count / 300.0,
        fp.avg_sentence_length / 25.0,
        fp.sentence_length_std / 15.0,
        fp.transition_density,
        fp.common_opener_count / max(fp.sentence_count, 1),
        fp.punctuation_density["comma"],
        fp.punctuation_density["semicolon"],
        fp.punctuation_density["colon"],
        fp.punctuation_density["em_dash"],
        fp.punctuation_density["parens"],
        fp.punctuation_density["question"],
    ]

    # Sentiment trajectory summary
    if fp.sentiment_trajectory:
        traj = fp.sentiment_trajectory
        features.extend([
            sum(1 for x in traj if x > 0) / len(traj),
            sum(1 for x in traj if x < 0) / len(traj),
            sum(1 for x in traj if x == 0) / len(traj),
        ])
    else:
        features.extend([0.0, 0.0, 1.0])

    return np.array(features, dtype=np.float32)


def score_batch_dna(
    reviews: list[tuple[str, str]],
    similarity_threshold: float = 0.92,
) -> dict[str, BatchDNAResult]:
    """
    Cluster a batch of reviews by structural similarity.

    Args:
        reviews: List of (review_id, review_text) tuples.
        similarity_threshold: Cosine similarity threshold above which two
                              reviews are considered structurally similar.

    Returns:
        Dict mapping review_id → BatchDNAResult.
    """
    if len(reviews) < 2:
        return {
            rid: BatchDNAResult(
                score=None,
                cluster_id=None,
                cluster_size=None,
                available=False,
                reason="Need at least 2 reviews for batch DNA analysis",
            )
            for rid, _ in reviews
        }

    # Extract fingerprints
    fingerprints = [extract_fingerprint(rid, text) for rid, text in reviews]
    feature_matrix = np.array([fp.feature_vector for fp in fingerprints])

    # Normalize feature vectors (L2 norm) for cosine-style comparison
    norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = feature_matrix / norms

    # Pairwise similarity matrix
    sim_matrix = np.dot(normalized, normalized.T)

    # Identify clusters via greedy agglomeration
    n = len(fingerprints)
    cluster_assignments = list(range(n))  # each starts in own cluster

    for i in range(n):
        for j in range(i + 1, n):
            # Also require similar opener pattern as additional filter
            same_opener = (
                fingerprints[i].opener_pattern == fingerprints[j].opener_pattern
                and fingerprints[i].opener_pattern != ""
            )
            structural_match = sim_matrix[i, j] >= similarity_threshold

            if structural_match or (same_opener and sim_matrix[i, j] >= 0.85):
                # Merge clusters
                root_i = _find(cluster_assignments, i)
                root_j = _find(cluster_assignments, j)
                if root_i != root_j:
                    cluster_assignments[root_j] = root_i

    # Compress to canonical cluster IDs
    canonical: dict[int, int] = {}
    next_id = 0
    final_clusters: list[int] = []
    for i in range(n):
        root = _find(cluster_assignments, i)
        if root not in canonical:
            canonical[root] = next_id
            next_id += 1
        final_clusters.append(canonical[root])

    # Compute cluster sizes
    cluster_sizes: dict[int, int] = {}
    for cid in final_clusters:
        cluster_sizes[cid] = cluster_sizes.get(cid, 0) + 1

    # Build results
    results: dict[str, BatchDNAResult] = {}
    for fp, cid in zip(fingerprints, final_clusters):
        size = cluster_sizes[cid]
        if size >= 2:
            # In a batch cluster — high ghost score
            cluster_strength = min(size / 5.0, 1.0)  # cap at 5
            score = round(60.0 + cluster_strength * 35.0, 1)  # 60-95
        else:
            # Solo — low ghost score
            score = 15.0

        results[fp.review_id] = BatchDNAResult(
            score=score,
            cluster_id=cid,
            cluster_size=size,
            available=True,
            reason=None,
        )

    return results


def _find(parent: list[int], i: int) -> int:
    """Union-find: find root of cluster."""
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
