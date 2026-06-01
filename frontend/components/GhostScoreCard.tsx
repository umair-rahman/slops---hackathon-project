"use client";

import { getScoreColor, getScoreLabel } from "@/lib/types";

interface Props {
  score: number;
  label: string;
  confidenceLow: number;
  confidenceHigh: number;
}

export function GhostScoreCard({ score, label, confidenceLow, confidenceHigh }: Props) {
  const color = getScoreColor(score);

  return (
    <div className="card-gradient-border rounded-2xl p-10 text-center animate-fade-up relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${color}30 0%, transparent 60%)`,
        }}
      />
      <span className="margin-tag relative">ghost score</span>
      <div className="relative mt-4">
        <div
          className="font-serif text-7xl sm:text-8xl md:text-9xl font-light score-counter leading-none animate-fade-up delay-100"
          style={{
            color,
            textShadow: `0 0 60px ${color}40`,
          }}
        >
          {score}
        </div>
        <div className="text-sm text-[#737373] mt-2 font-mono">/ 100</div>
      </div>
      <div className="text-lg sm:text-xl font-serif italic mt-6 animate-fade-up delay-200">
        {label || getScoreLabel(score)}
      </div>
      <div className="text-xs text-[#737373] mt-3 font-mono animate-fade-up delay-300">
        confidence interval: {confidenceLow} – {confidenceHigh}
      </div>
    </div>
  );
}
