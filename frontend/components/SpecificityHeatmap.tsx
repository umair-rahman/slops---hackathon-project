"use client";

import type { SentenceResult } from "@/lib/types";

interface Props {
  sentences: SentenceResult[];
}

export function SpecificityHeatmap({ sentences }: Props) {
  if (!sentences || sentences.length === 0) {
    return (
      <div className="card-gradient-border rounded-xl p-7 animate-fade-up delay-200">
        <h3 className="font-serif text-xl mb-3">specificity heatmap</h3>
        <p className="text-[#737373] text-sm">No sentences to display.</p>
      </div>
    );
  }

  return (
    <div className="card-gradient-border rounded-xl p-7 animate-fade-up delay-200">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-serif text-xl">specificity heatmap</h3>
        <span className="chip">per-sentence</span>
      </div>
      <div className="font-serif text-base md:text-lg leading-loose">
        {sentences.map((sent, i) => (
          <span
            key={i}
            title={
              sent.anchors.length > 0
                ? `anchors: ${sent.anchors.map((a) => a.text).join(", ")}`
                : "no anchors — generic content"
            }
            className={`heatmap-sentence ${
              sent.is_hallucinated
                ? "heatmap-hallucinated"
                : sent.anchor_count >= 2
                ? "heatmap-strong"
                : sent.anchor_count === 1
                ? "heatmap-light"
                : "heatmap-fluff"
            }`}
          >
            {sent.text}
            {sent.is_hallucinated && (
              <span className="ml-1 text-red-400 text-sm">⚠</span>
            )}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap gap-4 mt-6 pt-6 border-t border-white/5 text-xs text-[#737373]">
        <LegendItem color="rgba(34,197,94,0.4)" label="anchored (2+)" />
        <LegendItem color="rgba(250,204,21,0.4)" label="light anchor (1)" />
        <LegendItem color="rgba(239,68,68,0.3)" label="generic fluff" />
        <LegendItem color="rgba(239,68,68,0.6)" label="⚠ hallucinated" />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
