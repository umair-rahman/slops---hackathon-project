"use client";

import { useState } from "react";
import Link from "next/link";
import { scanConference } from "@/lib/api";
import type { ConferenceScanResult, ScanProgressEvent } from "@/lib/types";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Nav } from "@/components/Nav";
import { ScoreHistogram } from "@/components/ScoreHistogram";

const POPULAR_VENUES = [
  { label: "ICLR 2024", id: "ICLR.cc/2024/Conference", reviews: "~7000" },
  { label: "ICLR 2025", id: "ICLR.cc/2025/Conference", reviews: "~7500" },
  { label: "NeurIPS 2024", id: "NeurIPS.cc/2024/Conference", reviews: "~6000" },
];

export default function ConferencePage() {
  const [venueId, setVenueId] = useState("");
  const [progress, setProgress] = useState<ScanProgressEvent | null>(null);
  const [result, setResult] = useState<ConferenceScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleScan(id?: string) {
    const target = id ?? venueId;
    if (!target.trim()) return;

    setScanning(true);
    setError(null);
    setResult(null);
    setProgress(null);

    scanConference(
      target,
      50,
      (event) => {
        setProgress(event);
        if (event.type === "complete" && event.data) {
          setResult(event.data);
          setScanning(false);
        }
        if (event.type === "error") {
          setError(event.error ?? "Unknown error");
          setScanning(false);
        }
      },
      (err) => {
        setError(err.message);
        setScanning(false);
      }
    );
  }

  return (
    <>
      <AnimatedBackground />
      <Nav />

      <main className="relative pt-24 pb-20 px-6 sm:px-8 min-h-screen">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="mb-12 animate-fade-up">
            <span className="margin-tag inline-block mb-4">venue health scan</span>
            <h1 className="font-serif text-4xl md:text-5xl font-light tracking-tight mb-3">
              Scan an entire <span className="italic text-[#facc15]/90">conference</span>.
            </h1>
            <p className="text-[#a3a3a3]">
              Pull every public review from a venue. Run all 3 detection layers. Surface suspect reviewers.
            </p>
          </div>

          {/* Input */}
          <div className="card-gradient-border rounded-xl p-2 flex flex-col sm:flex-row gap-2 mb-6 animate-fade-up delay-100">
            <input
              type="text"
              value={venueId}
              onChange={(e) => setVenueId(e.target.value)}
              placeholder="e.g. ICLR.cc/2024/Conference"
              className="input-glow flex-1 bg-transparent border-0 px-4 py-3 text-sm font-mono placeholder:text-white/20 focus:outline-none"
            />
            <button
              onClick={() => handleScan()}
              disabled={scanning || !venueId.trim()}
              className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:transform-none"
            >
              {scanning ? "scanning..." : (
                <>scan <span>→</span></>
              )}
            </button>
          </div>

          {/* Popular venues */}
          <div className="mb-12 animate-fade-up delay-200">
            <div className="text-xs text-[#737373] uppercase tracking-wider mb-3">
              popular venues
            </div>
            <div className="flex flex-wrap gap-2">
              {POPULAR_VENUES.map((v) => (
                <button
                  key={v.id}
                  onClick={() => {
                    setVenueId(v.id);
                    handleScan(v.id);
                  }}
                  disabled={scanning}
                  className="group flex items-center gap-2 px-4 py-2 border border-white/10 rounded-lg hover:border-[#facc15]/40 hover:bg-[#facc15]/5 transition-all disabled:opacity-40"
                >
                  <span className="text-sm font-medium">{v.label}</span>
                  <span className="text-xs text-[#737373] font-mono">{v.reviews}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Progress */}
          {scanning && progress && (
            <div className="card-gradient-border rounded-xl p-7 mb-8 animate-fade-up">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="dot-pulse" />
                  <span className="font-mono text-xs uppercase tracking-wider text-[#facc15]">
                    streaming live
                  </span>
                </div>
                <span className="font-mono text-2xl text-[#facc15]">{progress.percent}%</span>
              </div>
              <div className="text-sm text-[#a3a3a3] mb-4 font-serif italic">
                {progress.message}
              </div>
              <div className="relative h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 bg-[#facc15] rounded-full transition-all duration-500"
                  style={{
                    width: `${progress.percent ?? 0}%`,
                    boxShadow: "0 0 12px rgba(250, 204, 21, 0.6)",
                  }}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-4 border border-red-500/30 bg-red-500/[0.05] rounded-lg text-sm text-red-400 mb-8 animate-fade-up">
              <span className="font-mono text-xs uppercase tracking-wider">error</span>
              <p className="mt-1">{error}</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-6 animate-fade-up">
              {/* Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <BigStat label="reviews scanned" value={result.total_reviews.toLocaleString()} color="#fafaf9" />
                <BigStat
                  label="ghost-flagged"
                  value={`${result.flagged_percent.toFixed(1)}%`}
                  color="#ef4444"
                  highlight
                />
                <BigStat
                  label="suspect reviewers"
                  value={result.top_suspect_reviewers.length.toString()}
                  color="#ea580c"
                />
                <BigStat
                  label="collusion pairs"
                  value={(result.collusion_count ?? 0).toString()}
                  color={result.collusion_count ? "#ef4444" : "#737373"}
                />
              </div>

              {/* Histogram */}
              {result.score_distribution && result.score_distribution.length > 0 && (
                <ScoreHistogram distribution={result.score_distribution} />
              )}

              {/* Top suspects */}
              {result.top_suspect_reviewers.length > 0 && (
                <div className="card-gradient-border rounded-xl p-7">
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="font-serif text-xl">top suspect reviewers</h3>
                    <span className="chip">sorted by ghost score</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm min-w-[500px]">
                      <thead>
                        <tr className="text-[#737373] text-xs uppercase tracking-wider border-b border-white/5">
                          <th className="text-left py-3 font-mono">reviewer</th>
                          <th className="text-right py-3 font-mono">reviews</th>
                          <th className="text-right py-3 font-mono">avg score</th>
                          <th className="text-right py-3 font-mono">dna cluster</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.top_suspect_reviewers.map((r) => (
                          <tr
                            key={r.reviewer_id}
                            className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                          >
                            <td className="py-3">
                              <Link
                                href={`/reviewer/${encodeURIComponent(r.reviewer_id)}`}
                                className="hover:text-[#facc15] transition-colors font-mono text-sm break-all"
                              >
                                {r.reviewer_id}
                              </Link>
                            </td>
                            <td className="text-right py-3 text-[#a3a3a3]">{r.total_reviews}</td>
                            <td className="text-right py-3 font-mono text-base">
                              {r.avg_ghost_score.toFixed(0)}
                            </td>
                            <td className="text-right py-3">
                              {r.has_dna_cluster ? (
                                <span className="text-red-400 text-xs">● yes</span>
                              ) : (
                                <span className="text-[#737373] text-xs">○ no</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Empty state */}
              {result.total_reviews === 0 && (
                <div className="card-gradient-border rounded-xl p-12 text-center">
                  <div className="font-serif italic text-2xl mb-2">No reviews found.</div>
                  <p className="text-[#a3a3a3] text-sm">
                    {result.message ?? "Check the venue ID. Try a popular venue from the chips above."}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </>
  );
}

function BigStat({
  label,
  value,
  color,
  highlight = false,
}: {
  label: string;
  value: string;
  color: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`card-gradient-border rounded-xl p-7 text-center relative overflow-hidden ${
        highlight ? "ring-1 ring-red-500/20" : ""
      }`}
    >
      {highlight && (
        <div
          className="absolute inset-0 opacity-30 pointer-events-none"
          style={{
            background: `radial-gradient(circle at 50% 50%, ${color}30 0%, transparent 70%)`,
          }}
        />
      )}
      <div className="relative">
        <div className="font-serif text-5xl md:text-6xl font-light score-counter mb-2" style={{ color }}>
          {value}
        </div>
        <div className="text-xs text-[#737373] uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}
