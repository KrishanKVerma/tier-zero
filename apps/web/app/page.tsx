"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, AtSign, Loader2 } from "lucide-react";

import { createReport } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = username
      .trim()
      .replace(/^@/, "")
      .replace(/^https?:\/\/github\.com\//, "");
    if (!clean) {
      setError("Enter a GitHub username.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const res = await createReport(clean);
      router.push(`/report/${res.report_id}?u=${encodeURIComponent(clean)}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start report.";
      setError(message);
      setSubmitting(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <div className="grid-bg pointer-events-none absolute inset-0" />
      <div
        className="pointer-events-none absolute left-1/2 top-1/4 h-[600px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-20 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(52,211,153,0.4) 0%, rgba(52,211,153,0) 70%)",
        }}
      />

      <div className="relative mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 py-24">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-zinc-800/80 bg-zinc-900/60 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-zinc-400 backdrop-blur">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
          </span>
          tier-zero
        </div>

        <h1 className="text-center text-[2.75rem] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-6xl md:text-7xl">
          The senior engineer review
          <br />
          <span className="gradient-text">every GitHub profile deserves.</span>
        </h1>

        <form onSubmit={handleSubmit} className="mt-14 w-full max-w-xl">
          <div className="focus-glow group relative flex items-center rounded-xl border border-zinc-800 bg-zinc-900/40 backdrop-blur transition">
            <AtSign className="pointer-events-none absolute left-4 h-4 w-4 text-zinc-500 transition group-focus-within:text-emerald-400" />
            <input
              type="text"
              placeholder="GitHub username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={submitting}
              autoFocus
              spellCheck={false}
              autoCapitalize="off"
              className="h-14 flex-1 bg-transparent pl-11 pr-32 font-mono text-base text-zinc-100 placeholder:font-sans placeholder:text-zinc-500 outline-none disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={submitting}
              className="absolute right-2 inline-flex h-10 items-center gap-1.5 rounded-lg border border-emerald-400/20 bg-gradient-to-b from-emerald-400/10 to-emerald-500/5 px-4 text-sm font-medium text-emerald-300 transition hover:border-emerald-400/50 hover:from-emerald-400/20 hover:to-emerald-500/10 hover:text-emerald-200 disabled:opacity-60"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Running
                </>
              ) : (
                <>
                  Audit
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>
          {error ? (
            <p className="mt-3 text-sm text-rose-400">{error}</p>
          ) : (
            <p className="mt-3 text-center text-xs tracking-wide text-zinc-500">
              Public profiles only &middot; 60&ndash;180 seconds
            </p>
          )}
        </form>

        <div className="mt-24 flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-zinc-600">
          <span className="h-px w-12 bg-zinc-800" />
          Open source
          <span className="h-px w-12 bg-zinc-800" />
        </div>
        <a
        
          href="https://github.com/KrishanKVerma/tier-zero"
          target="_blank"
          rel="noreferrer"
          className="mt-2 font-mono text-xs text-zinc-500 underline-offset-4 transition hover:text-zinc-300 hover:underline"
        >
          github.com/KrishanKVerma/tier-zero
        </a>
      </div>
    </main>
  );
}