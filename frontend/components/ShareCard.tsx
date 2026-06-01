"use client";

import { useState } from "react";
import { getScoreColor, getScoreLabel } from "@/lib/types";

interface Props {
  score: number;
  label: string;
  paperTitle?: string;
  reviewerId?: string;
}

/**
 * Shareable score card — generates a copyable text summary
 * and a shareable URL for the current analysis.
 *
 * Note: True PNG export requires a canvas/html2canvas approach.
 * For hackathon, we provide a text card + copy-to-clipboard.
 */
export function ShareCard({ score, label, paperTitle, reviewerId }: Props) {
  const [copied, setCopied] = useState(false);

  const color = getScoreColor(score);

  const shareText = [
    `Marginalia Ghost Score: ${score}/100`,
    `Verdict: ${label}`,
    paperTitle ? `Paper: ${paperTitle}` : null,
    reviewerId ? `Reviewer: ${reviewerId}` : null,
    ``,
    `Analyzed by Marginalia — AI peer review detection`,
    `https://marginalia.vercel.app/analyze`,
  ]
    .filter(Boolean)
    .join("\n");

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for browsers without clipboard API
      const el = document.createElement("textarea");
      el.value = shareText;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  function handleTwitterShare() {
    const tweet = encodeURIComponent(
      `Ghost Score: ${score}/100 — "${label}"\n\nAnalyzed by @marginalia_ai\nhttps://marginalia.vercel.app/analyze`
    );
    window.open(`https://twitter.com/intent/tweet?text=${tweet}`, "_blank");
  }

  return (
    <div className="card-gradient-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg">share this result</h3>
        <span className="chip">shareable card</span>
      </div>

      {/* Preview card */}
      <div
        className="rounded-lg p-5 mb-4 border"
        style={{
          background: `linear-gradient(135deg, #0a0a0a 0%, rgba(${
            score > 65 ? "239,68,68" : score > 40 ? "234,88,12" : "34,197,94"
          },0.08) 100%)`,
          borderColor: `${color}30`,
        }}
      >
        <div className="text-xs text-[#737373] font-mono mb-2 uppercase tracking-wider">
          marginalia · ghost score
        </div>
        <div className="flex items-baseline gap-3 mb-2">
          <span
            className="font-serif text-5xl font-light"
            style={{ color, textShadow: `0 0 30px ${color}40` }}
          >
            {score}
          </span>
          <span className="text-[#737373] font-mono text-sm">/ 100</span>
        </div>
        <div className="font-serif italic text-base">{label}</div>
        {paperTitle && (
          <div className="text-xs text-[#737373] mt-2 truncate">{paperTitle}</div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-4 py-2 border border-white/10 rounded-lg text-sm hover:border-[#facc15]/40 hover:bg-[#facc15]/5 transition-all"
        >
          {copied ? (
            <>
              <span className="text-green-400">✓</span>
              <span className="text-green-400">copied</span>
            </>
          ) : (
            <>
              <span>📋</span>
              <span>copy text</span>
            </>
          )}
        </button>

        <button
          onClick={handleTwitterShare}
          className="flex items-center gap-2 px-4 py-2 border border-white/10 rounded-lg text-sm hover:border-blue-400/40 hover:bg-blue-400/5 transition-all"
        >
          <span>𝕏</span>
          <span>share on X</span>
        </button>
      </div>
    </div>
  );
}
