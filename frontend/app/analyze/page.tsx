"use client";

import { useState } from "react";
import { analyzeReview } from "@/lib/api";
import type { GhostScore } from "@/lib/types";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Nav } from "@/components/Nav";
import { GhostScoreCard } from "@/components/GhostScoreCard";
import { LayerBreakdown } from "@/components/LayerBreakdown";
import { SpecificityHeatmap } from "@/components/SpecificityHeatmap";
import { HallucinationBadge } from "@/components/HallucinationBadge";
import { ShareCard } from "@/components/ShareCard";

export default function AnalyzePage() {
  const [reviewText, setReviewText] = useState("");
  const [arxivId, setArxivId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GhostScore | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewText.trim() || reviewText.length < 20) {
      setError("Review must be at least 20 characters");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const score = await analyzeReview({
        review_text: reviewText,
        paper_arxiv_id: arxivId.trim() || undefined,
      });
      setResult(score);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  function loadDemo(type: "ai" | "human") {
    if (type === "ai") {
      setReviewText(
        "This paper presents an interesting contribution to the field of machine learning. The methodology is well-described and the results are promising. The authors have done a good job of explaining their approach. The writing is clear and the paper is well-organized. I recommend acceptance with minor revisions."
      );
    } else {
      setReviewText(
        "The paper proposes a novel attention mechanism described in Section 3.2. However, Equation 5 contains a derivation error — the normalization term is missing from the denominator. Figure 4(b) shows the ablation results, but Table 2 is missing confidence intervals for the baseline comparisons. In Section 5.1, the authors claim 94% accuracy but the numbers in Figure 6 show 91.2%. Algorithm 1 on page 8 has an off-by-one error in the loop bounds."
      );
    }
    setArxivId("");
  }

  return (
    <>
      <AnimatedBackground />
      <Nav />

      <main className="relative pt-24 pb-20 px-6 sm:px-8 min-h-screen">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="mb-12 animate-fade-up">
            <span className="margin-tag inline-block mb-4">layer 1 + 2 analysis</span>
            <h1 className="font-serif text-4xl md:text-5xl font-light tracking-tight mb-3">
              Analyze a single <span className="italic text-[#facc15]/90">peer review</span>.
            </h1>
            <p className="text-[#a3a3a3]">
              Paste any review. Optionally provide the paper&apos;s arXiv ID for asymmetry analysis.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6 animate-fade-up delay-100">
            <div>
              <div className="flex flex-wrap justify-between items-center mb-3 gap-2">
                <label className="text-sm text-[#a3a3a3]">
                  review text <span className="text-[#facc15]">*</span>
                </label>
                <div className="flex gap-3 text-xs">
                  <button
                    type="button"
                    onClick={() => loadDemo("ai")}
                    className="text-red-400/80 hover:text-red-400 transition-colors font-mono"
                  >
                    load AI demo →
                  </button>
                  <button
                    type="button"
                    onClick={() => loadDemo("human")}
                    className="text-green-400/80 hover:text-green-400 transition-colors font-mono"
                  >
                    load human demo →
                  </button>
                </div>
              </div>
              <div className="relative">
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  placeholder="Paste the full peer review text here (min 20 characters)..."
                  rows={11}
                  className="input-glow w-full bg-white/[0.02] border border-white/10 rounded-lg px-5 py-4 text-sm font-serif resize-none placeholder:text-white/20 transition-all"
                  required
                  minLength={20}
                />
                <div className="absolute bottom-3 right-4 text-xs text-[#737373] font-mono">
                  {reviewText.split(/\s+/).filter(Boolean).length} words
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm text-[#a3a3a3] mb-3">
                arXiv ID{" "}
                <span className="text-white/30 text-xs">
                  (optional · enables asymmetry + hallucination detection)
                </span>
              </label>
              <input
                type="text"
                value={arxivId}
                onChange={(e) => setArxivId(e.target.value)}
                placeholder="e.g. 1706.03762 or https://arxiv.org/abs/1706.03762"
                className="input-glow w-full bg-white/[0.02] border border-white/10 rounded-lg px-5 py-4 text-sm font-mono placeholder:text-white/20 transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !reviewText.trim()}
              className="btn-primary w-full justify-center disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:transform-none"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-[#0a0a0a] border-t-transparent rounded-full animate-spin" />
                  analyzing across 3 layers...
                </span>
              ) : (
                <>
                  analyze review
                  <span>→</span>
                </>
              )}
            </button>
          </form>

          {/* Error */}
          {error && (
            <div className="mt-8 p-4 border border-red-500/30 bg-red-500/[0.05] rounded-lg text-sm text-red-400 animate-fade-up">
              <span className="font-mono text-xs uppercase tracking-wider">error</span>
              <p className="mt-1">{error}</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="mt-16 space-y-8">
              <GhostScoreCard
                score={result.overall}
                label={result.label}
                confidenceLow={result.confidence_low}
                confidenceHigh={result.confidence_high}
              />
              <LayerBreakdown result={result} />
              <SpecificityHeatmap sentences={result.specificity.sentences} />

              {result.asymmetry.hallucinated_sentences.length > 0 && (
                <HallucinationBadge sentences={result.asymmetry.hallucinated_sentences} />
              )}

              <div className="card-gradient-border rounded-xl p-7 animate-fade-up delay-300">
                <span className="margin-tag inline-block mb-3">explanation</span>
                <p className="font-serif text-lg leading-relaxed">{result.explanation}</p>
              </div>

              <ShareCard
                score={result.overall}
                label={result.label}
                paperTitle={arxivId ? `arXiv:${arxivId}` : undefined}
              />
            </div>
          )}
        </div>
      </main>
    </>
  );
}
