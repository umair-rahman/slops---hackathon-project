"use client";

import { useMemo } from "react";
import { getScoreColor } from "@/lib/types";
import type { ReviewerProfileReview } from "@/lib/types";

interface Props {
  reviews: ReviewerProfileReview[];
  driftDetected: boolean;
  driftStrength: number;
  driftPoint?: number | null;
}

export function DriftTimeline({ reviews, driftDetected, driftStrength, driftPoint }: Props) {
  // Sort by timestamp ascending for timeline
  const sorted = useMemo(
    () => [...reviews].sort((a, b) => a.timestamp - b.timestamp),
    [reviews]
  );

  if (sorted.length === 0) {
    return (
      <div className="card-gradient-border rounded-xl p-7">
        <h3 className="font-serif text-xl mb-2">style drift timeline</h3>
        <p className="text-[#737373] text-sm">No reviews to display.</p>
      </div>
    );
  }

  const maxScore = 100;
  const svgWidth = 600;
  const svgHeight = 160;
  const padX = 40;
  const padY = 20;
  const plotW = svgWidth - padX * 2;
  const plotH = svgHeight - padY * 2;

  // Map reviews to SVG coordinates
  const points = sorted.map((r, i) => ({
    x: padX + (i / Math.max(sorted.length - 1, 1)) * plotW,
    y: padY + plotH - (r.ghost_score / maxScore) * plotH,
    score: r.ghost_score,
    title: r.paper_title,
    date: new Date(r.timestamp).toISOString().slice(0, 10),
    review: r,
  }));

  // Polyline path
  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");

  // Find drift point index
  const driftIdx = driftPoint
    ? sorted.findIndex((r) => r.timestamp >= driftPoint)
    : -1;

  const driftX =
    driftIdx >= 0
      ? padX + (driftIdx / Math.max(sorted.length - 1, 1)) * plotW
      : null;

  return (
    <div className="card-gradient-border rounded-xl p-7">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-xl">style drift timeline</h3>
        <div className="flex items-center gap-2">
          {driftDetected ? (
            <span className="chip text-red-400 border-red-500/30 bg-red-500/10">
              drift detected · strength {driftStrength}
            </span>
          ) : (
            <span className="chip text-green-400 border-green-500/30 bg-green-500/10">
              stable
            </span>
          )}
        </div>
      </div>

      <div className="w-full overflow-hidden rounded-lg bg-white/[0.01]">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          width="100%"
          height={svgHeight}
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((v) => {
            const y = padY + plotH - (v / 100) * plotH;
            return (
              <g key={v}>
                <line
                  x1={padX}
                  y1={y}
                  x2={svgWidth - padX}
                  y2={y}
                  stroke="rgba(250,250,249,0.05)"
                  strokeWidth="1"
                />
                <text
                  x={padX - 6}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="9"
                  fill="#737373"
                  fontFamily="JetBrains Mono"
                >
                  {v}
                </text>
              </g>
            );
          })}

          {/* Drift line */}
          {driftX !== null && (
            <g>
              <line
                x1={driftX}
                y1={padY}
                x2={driftX}
                y2={padY + plotH}
                stroke="rgba(239,68,68,0.6)"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
              <text
                x={driftX + 4}
                y={padY + 12}
                fontSize="9"
                fill="rgba(239,68,68,0.8)"
                fontFamily="JetBrains Mono"
              >
                drift
              </text>
            </g>
          )}

          {/* Line */}
          <polyline
            points={polyline}
            fill="none"
            stroke="rgba(250,204,21,0.5)"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />

          {/* Points */}
          {points.map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y}
                r={5}
                fill={getScoreColor(p.score)}
                stroke="rgba(0,0,0,0.4)"
                strokeWidth="1"
              >
                <title>{`${p.date}: ${p.title} · ghost ${p.score}`}</title>
              </circle>
            </g>
          ))}
        </svg>
      </div>

      <div className="flex justify-between mt-2 text-[10px] text-[#737373] font-mono px-2">
        <span>{sorted[0] ? new Date(sorted[0].timestamp).toISOString().slice(0, 7) : ""}</span>
        <span>ghost score over time</span>
        <span>
          {sorted[sorted.length - 1]
            ? new Date(sorted[sorted.length - 1].timestamp).toISOString().slice(0, 7)
            : ""}
        </span>
      </div>
    </div>
  );
}
