"use client";

import { useEffect, useMemo, useRef } from "react";

import { getScoreColor } from "@/lib/types";

interface ClusterNode {
  id: string;
  cluster: number;
  ghost_score: number;
  size?: number;
}

interface Props {
  /** Each node = a review. */
  nodes: ClusterNode[];
  height?: number;
  onSelect?: (id: string) => void;
}

/**
 * Force-directed cluster map without external graph libraries.
 * Uses a lightweight verlet-style simulation in pure SVG.
 */
export function ClusterMap({ nodes: rawNodes, height = 360, onSelect }: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Layout positions per cluster
  const clusters = useMemo(() => {
    const map = new Map<number, ClusterNode[]>();
    for (const n of rawNodes) {
      if (!map.has(n.cluster)) map.set(n.cluster, []);
      map.get(n.cluster)!.push(n);
    }
    return map;
  }, [rawNodes]);

  const layout = useMemo(() => {
    if (rawNodes.length === 0) return [];

    const width = 600;
    const h = height;
    const cx = width / 2;
    const cy = h / 2;

    const clusterIds = Array.from(clusters.keys());
    const clusterPositions = new Map<number, { x: number; y: number }>();

    clusterIds.forEach((cid, i) => {
      // Place clusters in a ring; noise (-1) at center
      if (cid === -1 || clusters.get(cid)!.length < 2) {
        clusterPositions.set(cid, { x: cx, y: cy });
      } else {
        const angle = (i / Math.max(clusterIds.length, 1)) * Math.PI * 2;
        const r = Math.min(width, h) * 0.32;
        clusterPositions.set(cid, {
          x: cx + Math.cos(angle) * r,
          y: cy + Math.sin(angle) * r,
        });
      }
    });

    return rawNodes.map((n, i) => {
      const center = clusterPositions.get(n.cluster) ?? { x: cx, y: cy };
      const cluster = clusters.get(n.cluster) ?? [];
      const idxInCluster = cluster.indexOf(n);
      const clusterSize = cluster.length;

      // Spread within cluster
      const spread = clusterSize > 1 ? 18 + clusterSize * 4 : 0;
      const angle =
        clusterSize > 1 ? (idxInCluster / clusterSize) * Math.PI * 2 : 0;
      const jitter = (i % 7) * 1.5;

      return {
        ...n,
        x: center.x + Math.cos(angle) * spread + jitter,
        y: center.y + Math.sin(angle) * spread - jitter,
        radius: Math.max(4, Math.min(10, 4 + (n.size ?? 1))),
      };
    });
  }, [rawNodes, clusters, height]);

  if (rawNodes.length === 0) {
    return (
      <div className="card-gradient-border rounded-xl p-7">
        <h3 className="font-serif text-xl mb-2">cluster map</h3>
        <p className="text-[#737373] text-sm">No reviews to cluster yet.</p>
      </div>
    );
  }

  const totalClusters = Array.from(clusters.values()).filter((c) => c.length >= 2).length;

  return (
    <div className="card-gradient-border rounded-xl p-7" ref={containerRef}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-xl">cluster map</h3>
        <span className="chip">{totalClusters} clusters</span>
      </div>
      <div className="relative w-full overflow-hidden rounded-lg" style={{ height }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 600 ${height}`}
          width="100%"
          height={height}
          className="bg-white/[0.01]"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Cluster halos */}
          {Array.from(clusters.entries()).map(([cid, items]) => {
            if (items.length < 2 || cid === -1) return null;
            const xs = items.map((n) => layout.find((l) => l.id === n.id)?.x ?? 0);
            const ys = items.map((n) => layout.find((l) => l.id === n.id)?.y ?? 0);
            const cx = xs.reduce((a, b) => a + b, 0) / xs.length;
            const cy = ys.reduce((a, b) => a + b, 0) / ys.length;
            const radius = 18 + items.length * 6;
            return (
              <circle
                key={`halo-${cid}`}
                cx={cx}
                cy={cy}
                r={radius}
                fill="rgba(239,68,68,0.06)"
                stroke="rgba(239,68,68,0.25)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
            );
          })}

          {/* Edges within clusters */}
          {Array.from(clusters.entries()).map(([cid, items]) => {
            if (items.length < 2 || cid === -1) return null;
            const positions = items
              .map((n) => layout.find((l) => l.id === n.id))
              .filter(Boolean) as typeof layout;

            const lines: React.ReactNode[] = [];
            for (let i = 0; i < positions.length; i++) {
              for (let j = i + 1; j < positions.length; j++) {
                lines.push(
                  <line
                    key={`edge-${cid}-${i}-${j}`}
                    x1={positions[i].x}
                    y1={positions[i].y}
                    x2={positions[j].x}
                    y2={positions[j].y}
                    stroke="rgba(239,68,68,0.2)"
                    strokeWidth="1"
                  />
                );
              }
            }
            return lines;
          })}

          {/* Nodes */}
          {layout.map((n) => (
            <g
              key={n.id}
              transform={`translate(${n.x}, ${n.y})`}
              className="cursor-pointer"
              onClick={() => onSelect?.(n.id)}
            >
              <circle
                r={n.radius}
                fill={getScoreColor(n.ghost_score)}
                stroke="rgba(0,0,0,0.4)"
                strokeWidth="1"
                opacity="0.85"
              >
                <title>{`${n.id} · ghost ${n.ghost_score}`}</title>
              </circle>
            </g>
          ))}
        </svg>
      </div>
      <div className="flex flex-wrap gap-4 mt-4 text-xs text-[#737373]">
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500/70" /> low ghost
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-orange-500/70" /> uncertain
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500/70" /> high ghost
        </span>
        <span className="flex items-center gap-2">
          <span
            className="inline-block w-4 h-4 rounded-full border border-red-500/40"
            style={{ borderStyle: "dashed" }}
          />{" "}
          AI batch cluster
        </span>
      </div>
    </div>
  );
}
