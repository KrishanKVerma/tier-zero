export default function TermsPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-2xl px-6 py-20">
        <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Legal</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">Terms of Use</h1>
        <p className="mt-2 text-xs text-zinc-500">Last updated: May 2026</p>
        <div className="mt-12 space-y-8 text-sm leading-relaxed text-zinc-300">
          <Section title="What tier-zero is">
            tier-zero is an open-source multi-agent system that produces an AI-generated
            opinion about a public GitHub profile. It is not a hiring tool, credit score,
            or factual statement about any person.
          </Section>
          <Section title="Opinions, not facts">
            All output from tier-zero is an opinion produced by large language models.
            Outputs may be inaccurate, biased, or wrong. tier-zero verdicts must not be
            used as the sole basis for hiring, firing, or any consequential decision
            about a person.
          </Section>
          <Section title="Self-audit only">
            tier-zero v1 only audits the GitHub profile of the authenticated user. You
            may not use tier-zero to audit other people&apos;s profiles without their
            explicit consent.
          </Section>
          <Section title="No warranty">
            tier-zero is provided &quot;as is&quot;, without warranty of any kind. The
            author disclaims all liability for any damages arising from use of this tool.
          </Section>
          <Section title="Acceptable use">
            You agree not to use tier-zero to harass, defame, or harm any person. Abuse
            results in immediate revocation of access. You may not attempt to evade rate
            limits, scrape the service, or run automated audits of other people&apos;s
            profiles at scale.
          </Section>
          <Section title="Removal requests">
            If you wish to have your data excluded from tier-zero analyses, email{" "}
            <a href="mailto:krishnaverma60606@gmail.com" className="text-emerald-400 hover:underline">
              krishnaverma60606@gmail.com
            </a>
            {" "}with the subject line &quot;tier-zero removal request&quot; and your GitHub
            username. Requests are processed within 7 days.
          </Section>
          <Section title="Open source">
            The full source code is available at{" "}
            <a href="https://github.com/KrishanKVerma/tier-zero" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">
              github.com/KrishanKVerma/tier-zero
            </a>
            {" "}under the MIT license. Methodology is fully documented.
          </Section>
          <Section title="Changes">
            These terms may change. Continued use after a change constitutes acceptance
            of the updated terms.
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
