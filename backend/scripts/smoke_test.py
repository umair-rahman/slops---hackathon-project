"""
Smoke test — verifies end-to-end pipeline works with real data.

Run: python scripts/smoke_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


async def main() -> None:
    print("=" * 60)
    print("MARGINALIA PHASE 2 SMOKE TEST")
    print("=" * 60)

    # ── Test 1: Specificity Engine ──────────────────────────────────────────
    print("\n[1/5] Specificity Engine")
    from marginalia.engines.specificity import score_specificity

    ai_review = (
        "This paper presents an interesting contribution. "
        "The methodology is well-described. The results are promising."
    )
    human_review = (
        "Equation 5 has a sign error in Section 3.2. "
        "Figure 4(b) shows the issue. Table 2 confirms it."
    )
    ai_spec = score_specificity(ai_review)
    human_spec = score_specificity(human_review)
    print(f"  AI    review: spec={ai_spec.score:.1f} anchors={ai_spec.total_anchors}")
    print(f"  Human review: spec={human_spec.score:.1f} anchors={human_spec.total_anchors}")
    assert ai_spec.score < human_spec.score, "Specificity ordering broken"
    print("  ✓ PASS")

    # ── Test 2: Embedding Service ───────────────────────────────────────────
    print("\n[2/5] Embedding Service (sentence-transformers)")
    from marginalia.ml.embeddings import embedder

    emb = embedder.encode_one("hello world")
    assert emb.shape == (384,), f"Wrong embedding dim: {emb.shape}"
    sim = embedder.cosine(emb, embedder.encode_one("hello world"))
    assert sim > 0.99, f"Identical text should have sim ~1, got {sim}"
    print(f"  ✓ Embedding dim: {emb.shape}")
    print(f"  ✓ Self-similarity: {sim:.4f}")
    print("  ✓ PASS")

    # ── Test 3: Asymmetry Engine ────────────────────────────────────────────
    print("\n[3/5] Asymmetry Engine")
    from marginalia.engines.asymmetry import score_asymmetry

    abstract = "We propose a new attention mechanism for transformers."
    body = {
        "introduction": "Attention is critical for sequence models.",
        "methodology": "We use sparse attention with local windows.",
        "results": "Our method outperforms baselines on GLUE.",
    }
    abstract_only_review = (
        "This paper proposes a new attention mechanism for transformers. "
        "The contribution is interesting."
    )
    asym = score_asymmetry(abstract_only_review, abstract, body, embedder)
    print(f"  asymmetry score: {asym.score} (sim_abs={asym.sim_abstract}, sim_body={asym.sim_body})")
    assert 0 <= asym.score <= 100, "Asymmetry out of range"
    print("  ✓ PASS")

    # ── Test 4: Batch DNA Engine ────────────────────────────────────────────
    print("\n[4/5] Batch DNA Engine")
    from marginalia.engines.batch_dna import score_batch_dna

    template = (
        "This paper presents {} contribution. "
        "The proposed method shows {} results. "
        "However, the experimental setup lacks detail. "
        "Overall, this is a solid paper."
    )
    ai_batch = [
        ("ai1", template.format("an interesting", "promising")),
        ("ai2", template.format("a novel", "competitive")),
        ("ai3", template.format("a new", "strong")),
    ]
    results = score_batch_dna(ai_batch)
    cluster_sizes = [r.cluster_size for r in results.values() if r.cluster_size]
    print(f"  AI batch cluster sizes: {cluster_sizes}")
    assert max(cluster_sizes) >= 2, "Failed to cluster AI batch"
    print("  ✓ PASS")

    # ── Test 5: Full Pipeline (Single Review, no paper) ─────────────────────
    print("\n[5/5] Full Pipeline (single review)")
    from marginalia.engines.pipeline import analyze_single_review

    score = await analyze_single_review(
        review_text=(
            "Equation 5 in Section 3.2 has a sign error. "
            "Figure 4(b) shows the ablation but Table 2 is missing CIs. "
            "Algorithm 1 has an off-by-one error."
        ),
    )
    print(f"  Ghost score: {score.overall} ({score.label})")
    print(f"  Specificity: {score.specificity.score}")
    print(f"  Anchors found: {score.specificity.total_anchors}")
    assert score.overall < 50, f"Human review should score < 50, got {score.overall}"
    print("  ✓ PASS")

    print("\n" + "=" * 60)
    print("✓ ALL SMOKE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
