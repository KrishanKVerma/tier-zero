export default function AboutPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-2xl px-6 py-20">
        <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">About</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">What is tier-zero?</h1>

        <div className="mt-12 space-y-8 text-sm leading-relaxed text-zinc-300">
          <Section title="The product">
            tier-zero is an open-source multi-agent system that audits a GitHub profile
            and produces an opinion in the voice of a staff engineer. It is built for
            engineers who want an honest mirror of how their public work reads to a
            senior reviewer.
          </Section>

          <Section title="How it works">
            Five specialised agents run in a graph: Forensics (originality and authenticity),
            Depth (technical depth and production markers), Claims (bio versus code alignment),
            Senior Reviewer (verdict synthesis), and Critic (adversarial review). The Critic
            challenges the Reviewer until the verdict survives scrutiny, capped at two
            revision rounds.
          </Section>

          <Section title="What it isn&apos;t">
            tier-zero is not a hiring decision, a credit score, or a factual statement
            about any person. Every output is an opinion produced by a large language
            model and must not be relied on as ground truth. tier-zero may be wrong.
          </Section>

          <Section title="Self-audit only">
            v1 only audits the GitHub profile of the user requesting the audit. Auditing
            other people&apos;s profiles is restricted by design. We open up other modes
            only when we are confident the safety guarantees hold.
          </Section>

          <Section title="Open source">
            Methodology, prompts, eval set, and source code are all public at{" "}
            <a
            
              href="https://github.com/KrishanKVerma/tier-zero"
              target="_blank"
              rel="noreferrer"
              className="text-emerald-400 hover:underline"
            >
              github.com/KrishanKVerma/tier-zero
            </a>
            . You can read exactly how a verdict is produced.
          </Section>

          <Section title="Author">
            tier-zero is built by Krishan Kumar Verma, a final-year B.Tech student. The
            project is in active development and the verdicts are not always sharp.
            Feedback welcome.
          </Section>

          <Section title="Contact">
            <a
            
              href="mailto:krishnaverma60606@gmail.com"
              className="text-emerald-400 hover:underline"
            >
              krishnaverma60606@gmail.com
            </a>
          </Section>
        </div>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-base font-medium text-zinc-100">{title}</h2>
      <div className="text-zinc-400">{children}</div>
    </section>
  );
}
