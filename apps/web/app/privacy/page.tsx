export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-2xl px-6 py-20">
        <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Legal</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">Privacy Policy</h1>
        <p className="mt-2 text-xs text-zinc-500">Last updated: May 2026</p>
        <div className="mt-12 space-y-8 text-sm leading-relaxed text-zinc-300">
          <Section title="What we collect">
            tier-zero collects only what is strictly required to produce a report:
            the GitHub username you submit, public data fetched from GitHub&apos;s
            public API, and the resulting AI-generated verdict.
          </Section>
          <Section title="What we don&apos;t collect">
            No tracking cookies, no analytics, no fingerprinting, no advertising IDs.
            We do not collect or store your IP address beyond what is required for
            short-term rate limiting.
          </Section>
          <Section title="How long we keep data">
            Reports are stored in memory only. They are lost when the server restarts.
            We do not persist verdicts, GitHub data, or user activity to disk or to
            any database.
          </Section>
          <Section title="Third parties">
            tier-zero calls the GitHub public API, the Groq API, and the OpenRouter API
            to function. Their privacy policies apply to data sent through those
            services. We send only the minimum required: GitHub username and public
            profile/repo data.
          </Section>
          <Section title="Your rights">
            You may request removal of any data about you at any time by emailing{" "}
            <a href="mailto:krishnaverma60606@gmail.com" className="text-emerald-400 hover:underline">
              krishnaverma60606@gmail.com
            </a>
            {" "}with the subject &quot;tier-zero removal request&quot;.
          </Section>
          <Section title="Open source">
            All code is public at{" "}
            <a href="https://github.com/KrishanKVerma/tier-zero" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">
              github.com/KrishanKVerma/tier-zero
            </a>
            . You can verify exactly how your data is handled.
          </Section>
          <Section title="Contact">
            Privacy questions:{" "}
            <a href="mailto:krishnaverma60606@gmail.com" className="text-emerald-400 hover:underline">
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
