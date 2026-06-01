import Link from "next/link";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Nav } from "@/components/Nav";

export default function MethodologyPage() {
  return (
    <>
      <AnimatedBackground />
      <Nav />

      <main className="relative pt-24 pb-20 px-6 sm:px-8 min-h-screen">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12 animate-fade-up">
            <span className="margin-tag inline-block mb-4">how marginalia works</span>
            <h1 className="font-serif text-4xl md:text-6xl font-light tracking-tight mb-4 leading-tight">
              Detection, <span className="italic text-[#facc15]/90">explained</span>.
            </h1>
            <p className="text-[#a3a3a3] text-lg">
              Three independent signals. One forensic score. Zero LLM-as-judge.
            </p>
          </div>

          <article className="prose prose-invert max-w-none space-y-12 font-serif">
            {/* Layer 1 */}
            <Section index="01" title="Specificity Index" tag="anchor density">
              <p>
                Real peer reviewers cite <em>specifics</em>. AI reviewers don&apos;t.
              </p>
              <p>
                We extract academic anchors from the review text using nine regex
                families: equations, figures, tables, sections, theorems, algorithms,
                appendices, line numbers, and page numbers. Density is computed as
                anchors per 100 words.
              </p>
              <CodeBlock>
                {`anchors_per_100_words = (anchor_count / word_count) * 100
score = sigmoid(k=1.0, x0=2.5) * 100`}
              </CodeBlock>
              <p className="text-sm text-[#a3a3a3]">
                A typical AI review scores 5-30. A typical detailed human review
                scores 70-100.
              </p>
            </Section>

            {/* Layer 2 */}
            <Section index="02" title="Asymmetry Score" tag="content grounding">
              <p>
                AI reviewers are typically fed only the abstract. Their reviews
                reflect that. Real reviewers reference body sections.
              </p>
              <p>
                We embed the review text and paper sections using{" "}
                <code>sentence-transformers/all-MiniLM-L6-v2</code> (384-dim,
                L2-normalized). Cosine similarities to the abstract and to the most
                similar body section are compared.
              </p>
              <CodeBlock>
                {`sim_abstract = cos(review, abstract)
sim_body     = max(cos(review, section_i)) for each body section
asymmetry    = sim_abstract / (sim_abstract + sim_body)`}
              </CodeBlock>
              <p>
                A balanced asymmetry (~0.5) indicates body-grounded reviewing. A
                heavily abstract-skewed ratio (≥0.85) indicates the reviewer never
                read past the abstract.
              </p>
              <p className="text-sm text-[#a3a3a3]">
                Per-sentence hallucination flagging: any review sentence with cosine
                similarity below 0.30 against every paper chunk is marked as
                ungrounded.
              </p>
            </Section>

            {/* Layer 3 */}
            <Section index="03" title="Batch DNA" tag="reviewer fingerprint">
              <p>
                A reviewer with eight assigned papers feeds the same prompt to an
                LLM eight times. The output reviews share structural DNA — paragraph
                count, sentence opener pattern, transition word density,
                punctuation rhythm, sentiment trajectory.
              </p>
              <p>
                We extract 16 numerical features per review, normalize, and cluster
                via union-find on cosine similarity ≥ 0.92. Reviews from the same
                cluster (size ≥ 2) are flagged as a probable AI batch.
              </p>
              <CodeBlock>
                {`features = [paragraph_count, sentence_count, word_count,
            avg_sentence_length, sentence_length_std,
            transition_density, opener_uniformity,
            punct_density × 6, sentiment_trajectory × 3]
cluster  = greedy_agglomerate(cosine, threshold=0.92)`}
              </CodeBlock>
            </Section>

            {/* Aggregator */}
            <Section index="∑" title="Aggregator" tag="ghost score">
              <p>The three layers combine with weight redistribution.</p>
              <CodeBlock>
                {`ghost_score = 0.40 * (100 - specificity)
            + 0.35 * asymmetry
            + 0.25 * batch_dna

(weights redistribute when a layer is unavailable)`}
              </CodeBlock>
              <p>
                Confidence interval scales inversely with review length: a 50-word
                review carries ±20 uncertainty, a 500-word review only ±5.
              </p>
            </Section>

            {/* Why not LLM */}
            <Section index="!" title="Why not LLM-as-judge?" tag="design choice">
              <p>
                Asking an LLM &quot;is this AI-generated?&quot; is delegation, not
                detection. It&apos;s opaque, expensive, and trivially circular when
                the same model wrote the text.
              </p>
              <p>
                Marginalia&apos;s signals are{" "}
                <strong className="text-[#facc15]">structurally hard to fake</strong>:
              </p>
              <ul className="list-none space-y-2 my-4">
                <li className="flex gap-3">
                  <span className="text-[#facc15] font-mono">→</span>
                  <span>Specific anchors require having read the paper</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-[#facc15] font-mono">→</span>
                  <span>Body grounding requires the body, not the abstract</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-[#facc15] font-mono">→</span>
                  <span>Batch DNA requires varied writing within a reviewer&apos;s set</span>
                </li>
              </ul>
              <p>
                Each is verifiable, reproducible, and ungameable without producing
                a fundamentally different artifact.
              </p>
            </Section>

            {/* Stack */}
            <Section index="⚙" title="Tech stack" tag="reproducibility">
              <ul className="list-none space-y-2 text-sm text-[#a3a3a3]">
                <li><strong className="text-white">Backend:</strong> FastAPI · Python 3.11</li>
                <li><strong className="text-white">Embeddings:</strong> sentence-transformers all-MiniLM-L6-v2</li>
                <li><strong className="text-white">Clustering:</strong> Custom union-find · HDBSCAN ready</li>
                <li><strong className="text-white">PDF:</strong> PyMuPDF · GROBID fallback</li>
                <li><strong className="text-white">Data:</strong> OpenReview API · arXiv API · Semantic Scholar</li>
                <li><strong className="text-white">Cache:</strong> Upstash Redis (REST)</li>
                <li><strong className="text-white">Persistence:</strong> Neon Postgres</li>
                <li><strong className="text-white">Frontend:</strong> Next.js 16 · Tailwind v4 · Recharts</li>
              </ul>
            </Section>
          </article>

          <div className="mt-16 text-center">
            <Link href="/analyze" className="btn-primary">
              try it yourself
              <span>→</span>
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}

function Section({
  index,
  title,
  tag,
  children,
}: {
  index: string;
  title: string;
  tag: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card-gradient-border rounded-xl p-7 not-prose">
      <div className="flex items-start justify-between mb-4">
        <span className="font-mono text-sm text-[#facc15]/70">{index}</span>
        <span className="chip">{tag}</span>
      </div>
      <h2 className="font-serif text-3xl mb-5 font-light">{title}</h2>
      <div className="space-y-4 text-base leading-relaxed text-[#d4d4d4]">{children}</div>
    </section>
  );
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-black/40 border border-white/5 rounded-lg p-4 my-3 overflow-x-auto">
      <code className="font-mono text-xs sm:text-sm text-[#a3a3a3] whitespace-pre">{children}</code>
    </pre>
  );
}
