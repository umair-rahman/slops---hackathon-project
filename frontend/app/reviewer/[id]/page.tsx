"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";

import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Nav } from "@/components/Nav";
import { ClusterMap } from "@/components/ClusterMap";
import { DriftTimeline } from "@/components/DriftTimeline";
import { getReviewerProfile } from "@/lib/api";
import type { ReviewerProfile } from "@/lib/types";
import { getScoreColor } from "@/lib/types";

interface Props {
  params: Promise<{ id: string }>;
}

export default function ReviewerDetailPage({ params }: Props) {
  const { id } = use(params);
  const reviewerId = decodeURIComponent(id);

  const [profile, setProfile] = useState<ReviewerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getReviewerProfile(reviewerId)
      .then((p) => {
        if (!cancelled) {
          setProfile(p);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load profile");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [reviewerId]);

  const clusterNodes =
    profile?.reviews.map((r) => ({
      id: r.review_id,
      cluster: r.cluster_id ?? -1,
      ghost_score: r.ghost_score,
      size: r.cluster_size ?? 1,
    })) ?? [];

  return (
    <>
      <AnimatedBackground />
      <Nav />

      <main className="relative pt-24 pb-20 px-6 sm:px-8 min-h-screen">
        <div className="max-w-5xl mx-auto">
          <Link
            href="/conference"
            className="text-sm text-[#737373] hover:text-[#facc15] transition-colors inline-block mb-6"
          >
            ← back to scan
          </Link>

          <div className="mb-8 animate-fade-up">
            <span className="margin-tag inline-block mb-4">reviewer profile</span>
            <h1 className="font-serif text-3xl md:text-4xl font-light tracking-tight mb-2 break-all">
              <span className="font-mono text-2xl text-[#facc15]/90">{reviewerId}</span>
            </h1>
          </div>

          {loading && (
            <div className="card-gradient-border rounded-xl p-12 text-center">
              <div className="font-mono text-sm text-[#737373] mb-3">loading...</div>
              <div className="shimmer h-6 w-1/2 mx-auto rounded" />
            </div>
          )}

          {error && (
            <div className="p-6 border border-red-500/30 bg-red-500/[0.05] rounded-lg animate-fade-up">
              <div className="font-mono text-xs uppercase tracking-wider text-red-400 mb-2">
                error
              </div>
              <p className="text-sm text-red-300">{error}</p>
              <p className="text-xs text-[#737373] mt-3">
                Reviewer profiles require cached venue data. Run a venue scan first from the{" "}
                <Link href="/conference" className="underline hover:text-[#facc15]">
                  conference page
                </Link>
                .
              </p>
            </div>
          )}

          {profile && (
            <div className="space-y-6 animate-fade-up">
              {/* Stats grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Stat label="total reviews" value={profile.total_reviews.toString()} color="#fafaf9" />
                <Stat
                  label="avg ghost score"
                  value={profile.avg_ghost_score.toFixed(1)}
                  color={getScoreColor(profile.avg_ghost_score)}
                />
                <Stat
                  label="cluster count"
                  value={profile.cluster_count.toString()}
                  color="#ea580c"
                />
                <Stat
                  label="style drift"
                  value={profile.drift_detected ? "DETECTED" : "stable"}
                  color={profile.drift_detected ? "#ef4444" : "#22c55e"}
                />
              </div>

              {/* Time-on-task warning */}
              {profile.burst_detected && (
                <div className="card-gradient-border rounded-xl p-6 ring-1 ring-orange-500/20">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-orange-400 text-xl">⏱</span>
                    <h3 className="font-serif text-lg">implausible submission timing</h3>
                    <span className="chip text-orange-400 border-orange-500/30 bg-orange-500/10">
                      burst detected
                    </span>
                  </div>
                  <p className="text-sm text-[#a3a3a3]">
                    {profile.implausible_count} review(s) submitted in an implausibly short window
                    {profile.burst_window_seconds
                      ? ` (${profile.burst_window_seconds.toFixed(0)}s)`
                      : ""}
                    . Minimum realistic time to read + write a review is ~20 minutes.
                  </p>
                </div>
              )}

              {/* Drift indicator */}
              {profile.drift_detected && (
                <div className="card-gradient-border rounded-xl p-7 ring-1 ring-red-500/20">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">⚠</span>
                    <h3 className="font-serif text-xl">style drift detected</h3>
                    <span className="chip">strength: {profile.drift_strength}</span>
                  </div>
                  <p className="text-sm text-[#a3a3a3]">
                    This reviewer&apos;s writing style shifted significantly across their review
                    history. Possible indicators: switched to AI-assisted reviewing or changed
                    review approach mid-career.
                  </p>
                </div>
              )}

              {/* Cluster map */}
              {clusterNodes.length > 0 && <ClusterMap nodes={clusterNodes} height={320} />}

              {/* Drift timeline */}
              {profile.reviews.length >= 2 && (
                <DriftTimeline
                  reviews={profile.reviews}
                  driftDetected={profile.drift_detected}
                  driftStrength={profile.drift_strength}
                  driftPoint={profile.drift_point}
                />
              )}

              {/* Reviews timeline */}
              <div className="card-gradient-border rounded-xl p-7">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-serif text-xl">review timeline</h3>
                  <span className="chip">{profile.reviews.length} reviews</span>
                </div>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {profile.reviews.map((r) => (
                    <div
                      key={r.review_id}
                      className="border border-white/5 rounded-lg p-4 hover:border-white/10 transition-colors"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-serif text-sm md:text-base mb-1 break-words">
                            {r.paper_title}
                          </div>
                          <div className="text-xs text-[#737373] font-mono">
                            {r.venue_id} · {new Date(r.timestamp).toISOString().slice(0, 10)}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {r.cluster_size && r.cluster_size >= 2 && (
                            <span className="text-xs text-red-400 font-mono">
                              cluster ×{r.cluster_size}
                            </span>
                          )}
                          <div
                            className="font-mono text-2xl"
                            style={{ color: getScoreColor(r.ghost_score) }}
                          >
                            {r.ghost_score}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-3 text-xs text-[#737373] mt-2">
                        <span>spec: {r.specificity_score.toFixed(0)}</span>
                        <span>anchors: {r.anchor_count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="card-gradient-border rounded-xl p-5 text-center">
      <div className="font-serif text-3xl font-light score-counter mb-1" style={{ color }}>
        {value}
      </div>
      <div className="text-xs text-[#737373] uppercase tracking-wider">{label}</div>
    </div>
  );
}
