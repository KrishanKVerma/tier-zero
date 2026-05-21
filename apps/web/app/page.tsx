"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signIn, signOut } from "next-auth/react";
import { ArrowRight, AtSign, Loader2, LogOut } from "lucide-react";

import { createReport } from "@/lib/api";

export default function HomePage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const githubUsername = (session?.user as { login?: string } | undefined)?.login;

  async function handleAudit() {
    if (!githubUsername) {
      setError("Sign in with GitHub first.");
      return;
    }
    const accessToken = (session as { accessToken?: string } | null)?.accessToken;
    if (!accessToken) {
      setError("No GitHub access token. Sign out and sign in again.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const res = await createReport(githubUsername, accessToken);
      router.push(`/report/${res.report_id}?u=${encodeURIComponent(githubUsername)}`);
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

        <p className="mt-6 max-w-md text-center text-sm text-zinc-400">
          Audit your own GitHub before recruiters do.
        </p>

        <div className="mt-12 w-full max-w-md">
          {status === "loading" ? (
            <div className="flex items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/40 py-4 text-sm text-zinc-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading session
            </div>
          ) : session ? (
            <SignedInPanel
              username={githubUsername}
              submitting={submitting}
              onAudit={handleAudit}
            />
          ) : (
            <SignedOutPanel onSignIn={() => signIn("github")} />
          )}

          {error && <p className="mt-3 text-center text-sm text-rose-400">{error}</p>}

          <p className="mt-4 text-center text-xs text-zinc-500">
            Self-audit only. We never audit other people&apos;s profiles.
          </p>
        </div>

        <div className="mt-20 flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-zinc-600">
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

function SignedOutPanel({ onSignIn }: { onSignIn: () => void }) {
  return (
    <button
      type="button"
      onClick={onSignIn}
      className="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-400/30 bg-gradient-to-b from-emerald-400/10 to-emerald-500/5 py-4 text-sm font-medium text-emerald-200 transition hover:border-emerald-400/60 hover:from-emerald-400/20 hover:to-emerald-500/10"
    >
      <AtSign className="h-4 w-4" />
      Sign in with GitHub to audit your profile
      <ArrowRight className="h-4 w-4" />
    </button>
  );
}

function SignedInPanel({
  username,
  submitting,
  onAudit,
}: {
  username: string | undefined;
  submitting: boolean;
  onAudit: () => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-zinc-300">
          <AtSign className="h-3.5 w-3.5 text-emerald-400" />
          <span className="font-mono">{username ?? "(no username)"}</span>
        </div>
        <button
          type="button"
          onClick={() => signOut()}
          className="inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.18em] text-zinc-500 transition hover:text-zinc-300"
        >
          <LogOut className="h-3 w-3" /> Sign out
        </button>
      </div>
      <button
        type="button"
        onClick={onAudit}
        disabled={submitting || !username}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/30 bg-gradient-to-b from-emerald-400/10 to-emerald-500/5 py-3 text-sm font-medium text-emerald-200 transition hover:border-emerald-400/60 hover:from-emerald-400/20 hover:to-emerald-500/10 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Starting audit
          </>
        ) : (
          <>
            Audit my GitHub profile
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>
    </div>
  );
}