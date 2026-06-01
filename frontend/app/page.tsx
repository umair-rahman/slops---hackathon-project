import Link from "next/link";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Nav } from "@/components/Nav";

export default function HomePage() {
  return (
    <>
      <AnimatedBackground />
      <Nav />

      <main className="relative pt-16">
        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="relative min-h-[92vh] flex items-center px-6 sm:px-8 py-20">
          <div className="relative w-full max-w-7xl mx-auto grid lg:grid-cols-12 gap-10 items-center">
            <div className="lg:col-span-7 text-center lg:text-left">
              {/* Margin annotation tag */}
              <div className="animate-fade-up flex items-center justify-center lg:justify-start gap-2 mb-8">
                <span className="dot-pulse" />
                <span className="margin-tag">peer review crisis · 2025</span>
              </div>

              {/* Main heading */}
              <h1 className="animate-fade-up delay-100 font-serif text-5xl sm:text-6xl md:text-7xl lg:text-[5.5rem] font-light tracking-tight leading-[1.05] mb-8">
                Find what&apos;s{" "}
                <span className="highlight-mark italic font-normal">missing</span>
                <br />
                in AI peer reviews.
              </h1>

              {/* Subhead */}
              <p className="animate-fade-up delay-200 text-[#a3a3a3] text-lg md:text-xl max-w-2xl mx-auto lg:mx-0 mb-10 leading-relaxed">
                Three layers of forensic detection.{" "}
                <span className="text-white">Specificity</span>,{" "}
                <span className="text-white">grounding</span>, and{" "}
                <span className="text-white">batch DNA</span>.
                No LLM-as-judge. No keyword tricks. Just signal.
              </p>

              {/* CTAs */}
              <div className="animate-fade-up delay-300 flex flex-col sm:flex-row gap-4 justify-center lg:justify-start items-center">
                <Link href="/analyze" className="btn-primary group">
                  analyze a review
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </Link>
                <Link href="/conference" className="btn-secondary group">
                  scan a venue
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </Link>
              </div>

              {/* Live indicator */}
              <div className="animate-fade-up delay-500 mt-10 inline-flex items-center gap-2 text-xs text-[#737373]">
                <span className="dot-pulse" />
                <span className="font-mono">live · streaming from openreview</span>
              </div>
            </div>

            {/* Right column reserved for globe — canvas lives in <AnimatedBackground/>.
                We keep this empty div so layout reserves room and the globe sits next
                to (not under) the hero copy on large screens. */}
            <div className="lg:col-span-5 hidden lg:block" aria-hidden />
          </div>

          {/* Decorative scribbles in margins */}
          <DecorativeScribbles />
        </section>

        {/* ── Stats Banner ─────────────────────────────────────────────── */}
        <section className="relative border-y border-white/5 backdrop-blur-sm bg-white/[0.01]">
          <div className="max-w-6xl mx-auto px-6 sm:px-8 py-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <Stat number="22%" label="of CS papers show AI-content signs" />
              <Stat number="1500+" label="reviews per major AI conference" />
              <Stat number="3" label="independent detection layers" />
              <Stat number="0" label="LLM-as-judge dependency" />
            </div>
          </div>
        </section>

        {/* ── How It Works ─────────────────────────────────────────────── */}
        <section className="relative py-32 px-6 sm:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-20">
              <span className="margin-tag inline-block mb-4">methodology</span>
              <h2 className="font-serif text-4xl md:text-5xl font-light mb-4">
                Three signals.<br />
                <span className="italic text-[#facc15]/90">One ghost score.</span>
              </h2>
              <p className="text-[#737373] max-w-xl mx-auto">
                We don&apos;t ask another LLM if a review is AI. We measure what AI reviewers structurally cannot fake.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <FeatureCard
                index="01"
                title="Specificity Index"
                tag="anchor density"
                description="Real reviewers cite Equation 3.2, Figure 4(b), Section 5.1. AI reviewers write 'interesting contribution' and 'methodology is well-described.' We count anchors per 100 words."
                example={[
                  { text: "Equation 5 has a derivation gap on page 4.", type: "anchor" },
                  { text: "The paper presents an interesting contribution.", type: "fluff" },
                ]}
              />
              <FeatureCard
                index="02"
                title="Asymmetry Score"
                tag="content grounding"
                description="AI reviewers fed only the abstract produce reviews mirroring abstract content. We embed the review against paper sections and measure which it grounds in. Body-grounding is hard to fake."
                example={[
                  { text: "Embeds review vs abstract.", type: "anchor" },
                  { text: "Embeds review vs body sections.", type: "anchor" },
                  { text: "ratio > 0.85 → AI fingerprint", type: "fluff" },
                ]}
              />
              <FeatureCard
                index="03"
                title="Batch DNA"
                tag="reviewer fingerprint"
                description="A reviewer with 8 papers feeds the same prompt 8 times. Output reviews share structural DNA — paragraph count, sentence openers, punctuation rhythm. We cluster via HDBSCAN."
                example={[
                  { text: "Reviewer ~Anon_8392 · 8 reviews", type: "anchor" },
                  { text: "7 reviews form tight cluster", type: "fluff" },
                  { text: "→ AI batch detected", type: "anchor" },
                ]}
              />
            </div>
          </div>
        </section>

        {/* ── Demo Preview ─────────────────────────────────────────────── */}
        <section className="relative py-32 px-6 sm:px-8 overflow-hidden">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <span className="margin-tag inline-block mb-4">live demo</span>
              <h2 className="font-serif text-4xl md:text-5xl font-light mb-4">
                See it work in <span className="italic text-[#facc15]/90">real-time</span>.
              </h2>
            </div>

            <div className="card-gradient-border rounded-xl p-8 md:p-12 relative overflow-hidden">
              {/* Mock heatmap preview */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <span className="chip">specificity heatmap</span>
                  <span className="text-xs text-[#737373] font-mono">demo · review #4471</span>
                </div>
                <div className="font-serif text-base md:text-lg leading-relaxed">
                  <span className="heatmap-sentence heatmap-fluff">
                    The paper presents an interesting contribution to the field.
                  </span>{" "}
                  <span className="heatmap-sentence heatmap-strong">
                    However, Equation 5 contains a derivation error in Section 3.2.
                  </span>{" "}
                  <span className="heatmap-sentence heatmap-light">
                    Figure 4(b) shows promising results.
                  </span>{" "}
                  <span className="heatmap-sentence heatmap-fluff">
                    The methodology is well-described overall.
                  </span>{" "}
                  <span className="heatmap-sentence heatmap-hallucinated" title="Paper has 3 figures">
                    I appreciated the clarity of Figure 7.
                  </span>
                </div>
              </div>

              {/* Score readout */}
              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-white/5">
                <ScoreReadout label="ghost score" value="73" color="#ef4444" />
                <ScoreReadout label="confidence" value="64–82" color="#a3a3a3" mono />
                <ScoreReadout label="hallucinations" value="1" color="#ea580c" />
              </div>

              <div className="mt-8 text-center">
                <Link href="/analyze" className="btn-primary">
                  try it on your review
                  <span>→</span>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ── Bake-Off Results ─────────────────────────────────────────── */}
        <section className="relative py-24 px-6 sm:px-8 border-t border-white/5">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <span className="margin-tag inline-block mb-4">bake-off results</span>
              <h2 className="font-serif text-3xl md:text-4xl font-light mb-3">
                Tested on <span className="italic text-[#facc15]/90">100 labeled reviews</span>.
              </h2>
              <p className="text-[#737373] text-sm">50 real OpenReview reviews + 50 AI-generated across 5 prompt types</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Precision", value: "87.0%", color: "#22c55e" },
                { label: "Recall", value: "80.0%", color: "#22c55e" },
                { label: "F1 Score", value: "83.3%", color: "#facc15" },
                { label: "Accuracy", value: "84.0%", color: "#22c55e" },
              ].map((m) => (
                <div key={m.label} className="card-gradient-border rounded-xl p-5 text-center">
                  <div className="font-serif text-3xl font-light mb-1" style={{ color: m.color }}>
                    {m.value}
                  </div>
                  <div className="text-xs text-[#737373] uppercase tracking-wider">{m.label}</div>
                </div>
              ))}
            </div>
            <p className="text-center text-xs text-[#737373] mt-4 font-mono">
              Specificity Engine only · no paper context · no batch context
            </p>
          </div>
        </section>

        {/* ── Built For ────────────────────────────────────────────────── */}
        <section className="relative py-24 px-6 sm:px-8 border-t border-white/5">
          <div className="max-w-4xl mx-auto text-center">
            <span className="margin-tag inline-block mb-6">built for</span>
            <h2 className="font-serif text-3xl md:text-4xl font-light mb-12">
              The people drowning in slop.
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                "PC chairs",
                "area editors",
                "researchers",
                "publishers",
              ].map((role, i) => (
                <div
                  key={role}
                  className="card-gradient-border rounded-lg py-6 px-4 animate-fade-up"
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div className="font-serif italic text-lg">{role}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Footer ───────────────────────────────────────────────────── */}
        <footer className="relative border-t border-white/5 py-12 px-6 sm:px-8 backdrop-blur-sm">
          <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-[#737373]">
            <div className="flex items-center gap-3">
              <span className="font-serif italic">marginalia.</span>
              <span className="text-white/20">·</span>
              <span>find what&apos;s missing.</span>
            </div>
            <div className="flex items-center gap-6">
              <a href="https://slopscan.dev" className="hover:text-white transition-colors">
                slop scan 2026
              </a>
              <a href="https://github.com/marginalia-ai/marginalia" className="hover:text-white transition-colors">
                github
              </a>
              <span className="font-mono text-xs">MIT</span>
            </div>
          </div>
        </footer>
      </main>
    </>
  );
}

/* ── Sub Components ────────────────────────────────────────────────────── */

function Stat({ number, label }: { number: string; label: string }) {
  return (
    <div className="space-y-2">
      <div className="font-serif text-3xl md:text-4xl text-[#facc15]">{number}</div>
      <div className="text-xs text-[#737373] uppercase tracking-wider">{label}</div>
    </div>
  );
}

function FeatureCard({
  index,
  title,
  tag,
  description,
  example,
}: {
  index: string;
  title: string;
  tag: string;
  description: string;
  example: { text: string; type: "anchor" | "fluff" }[];
}) {
  return (
    <div className="card-gradient-border rounded-xl p-7 group">
      <div className="flex items-start justify-between mb-4">
        <span className="font-mono text-xs text-[#facc15]/60">{index}</span>
        <span className="chip">{tag}</span>
      </div>
      <h3 className="font-serif text-2xl mb-3">{title}</h3>
      <p className="text-sm text-[#a3a3a3] leading-relaxed mb-6">{description}</p>
      <div className="space-y-1.5 pt-4 border-t border-white/5">
        {example.map((ex, i) => (
          <div
            key={i}
            className={`text-xs font-mono px-2 py-1 rounded ${
              ex.type === "anchor"
                ? "bg-green-500/10 text-green-400/90"
                : "bg-red-500/10 text-red-400/80"
            }`}
          >
            {ex.type === "anchor" ? "✓" : "✗"} {ex.text}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreReadout({
  label,
  value,
  color,
  mono = false,
}: {
  label: string;
  value: string;
  color: string;
  mono?: boolean;
}) {
  return (
    <div className="text-center">
      <div className="text-xs text-[#737373] uppercase tracking-wider mb-1">{label}</div>
      <div
        className={`text-3xl ${mono ? "font-mono text-lg pt-2" : "font-serif"}`}
        style={{ color }}
      >
        {value}
      </div>
    </div>
  );
}

function DecorativeScribbles() {
  return (
    <div className="absolute inset-0 pointer-events-none hidden lg:block">
      {/* Top-left scribble */}
      <svg
        className="absolute top-20 left-12 opacity-30 animate-float-slow"
        width="80"
        height="40"
        viewBox="0 0 80 40"
        fill="none"
      >
        <path
          d="M5 20 Q 20 5, 35 20 T 75 20"
          stroke="#facc15"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
        />
      </svg>

      {/* Top-right asterisk */}
      <div className="absolute top-32 right-16 text-[#facc15]/40 text-2xl animate-float-slow" style={{ animationDelay: "1s" }}>
        ✻
      </div>

      {/* Bottom-left arrow */}
      <svg
        className="absolute bottom-32 left-20 opacity-30 animate-float"
        width="60"
        height="60"
        viewBox="0 0 60 60"
        fill="none"
      >
        <path
          d="M10 50 Q 25 30, 30 35 T 50 15 M 45 12 L 50 15 L 47 22"
          stroke="#facc15"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
        />
      </svg>

      {/* Bottom-right comment marker */}
      <div className="absolute bottom-40 right-24 text-[#facc15]/30 font-serif italic text-sm animate-float-slow" style={{ animationDelay: "2s" }}>
        cf. §3.2
      </div>
    </div>
  );
}
