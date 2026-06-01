"use client";

interface Props {
  sentences: string[];
  compact?: boolean;
}

export function HallucinationBadge({ sentences, compact = false }: Props) {
  if (!sentences || sentences.length === 0) return null;

  if (compact) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-red-500/15 border border-red-500/30 text-red-400"
        title={`${sentences.length} hallucinated sentence(s) detected`}
      >
        ⚠ {sentences.length} hallucinated
      </span>
    );
  }

  return (
    <div className="card-gradient-border rounded-xl p-6 ring-1 ring-red-500/20">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-red-400 text-lg">⚠</span>
        <h3 className="font-serif text-lg">hallucinations detected</h3>
        <span className="chip text-red-400 border-red-500/30 bg-red-500/10">
          {sentences.length}
        </span>
      </div>
      <p className="text-xs text-[#737373] mb-4">
        These review sentences reference content not found in the paper. The reviewer may have
        invented details or used an AI that hallucinated paper content.
      </p>
      <div className="space-y-2">
        {sentences.map((s, i) => (
          <div
            key={i}
            className="text-sm font-serif italic text-red-300/80 bg-red-500/[0.05] border border-red-500/10 rounded px-3 py-2"
          >
            &ldquo;{s}&rdquo;
          </div>
        ))}
      </div>
    </div>
  );
}
