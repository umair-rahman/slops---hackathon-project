"use client";

import { getScoreColor } from "@/lib/types";
import type { GhostScore } from "@/lib/types";

interface Props {
  result: GhostScore;
}

export function LayerBreakdown({ result }: Props) {
  const layers = [
    {
      label: "Specificity Index",
      score: result.specificity.score,
      note: `${result.specificity.total_anchors} anchors · ${result.specificity.anchors_per_100_words}/100w`,
      help: "Higher = more anchors = more human",
    },
    {
      label: "Asymmetry Score",
      score: result.asymmetry.score,
      note:
        result.asymmetry.score === 0
          ? "needs arXiv ID"
          : `ratio: ${result.asymmetry.asymmetry_ratio.toFixed(2)}`,
      help: "Higher = more abstract-derived = more AI-like",
    },
    {
      label: "Batch DNA",
      score: result.batch_dna.score ?? 0,
      note: result.batch_dna.available
        ? `cluster size: ${result.batch_dna.cluster_size}`
        : "needs batch context",
      help: "Higher = clustered with batch = AI batch signal",
    },
  ];

  return (
    <div className="card-gradient-border rounded-xl p-7 animate-fade-up delay-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-serif text-xl">layer breakdown</h3>
        <span className="chip">3 signals</span>
      </div>
      <div className="space-y-5">
        {layers.map((layer, i) => (
          <div
            key={layer.label}
            className="animate-fade-up"
            style={{ animationDelay: `${i * 80}ms` }}
            title={layer.help}
          >
            <div className="flex justify-between text-sm mb-2">
              <span className="font-medium">{layer.label}</span>
              <span className="text-[#737373] font-mono text-xs">{layer.note}</span>
            </div>
            <div className="relative h-2 bg-white/[0.05] rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000"
                style={{
                  width: `${layer.score}%`,
                  backgroundColor: getScoreColor(layer.score),
                  boxShadow: `0 0 16px ${getScoreColor(layer.score)}80`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
