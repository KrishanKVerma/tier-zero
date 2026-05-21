"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";

import { getReport, type ReportRecord } from "@/lib/api";
import { TIER_META, impactColor } from "@/lib/tier-styles";

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ u?: string }>;
}

export default function ReportPage({ params, searchParams }: PageProps) {
  const { id } = use(params);
  const { u: username } = use(searchParams);

  const [record, setRecord] = useState<ReportRecord | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const data = await getReport(id);
        if (cancelled) return;
        setRecord(data);
        if (data.status === "queued" || data.status === "running") {
          timer = setTimeout(poll, 3000);
        }
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Failed to load report.";
        setPollError(message);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  return (
    <main className="relative min-h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <div className="grid-bg pointer-events-none absolute inset-0" />

      <div className="relative mx-auto max-w-3xl px-6 py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs uppercase tracking-[0.18em] text-zinc-500 transition hover:text-zinc-300"
        >
          <ArrowLeft className="h-3 w-3" />
          New audit
        </Link>

        <div className="mt-10 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200/80">
          <span className="font-medium uppercase tracking-[0.18em] text-amber-300/90">Notice</span>
          {" "}&middot;{" "}
          This is an AI-generated opinion, not a factual statement. Outputs may be wrong.
          Do not use as the sole basis for hiring decisions.{" "}
          <a href="/terms" className="underline-offset-4 hover:underline">Terms</a>.
        </div>

        <div className="mt-12">
          <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
            Audit target
          </p>
          <h1 className="mt-1 font-mono text-3xl font-medium text-zinc-100 sm:text-4xl">
            @{username || "unknown"}
          </h1>
        </div>

        {pollError && <ErrorBlock message={pollError} />}
        {!record && !pollError && <LoadingBlock stage="queued" />}
        {record && record.status !== "complete" && record.status !== "error" && (
          <LoadingBlock stage={record.status} currentStage={record.current_stage} />
        )}
        {record && record.status === "error" && (
          <ErrorBlock message={record.error || "Report failed."} />
        )}
        {record && record.status === "complete" && record.result && (
          <VerdictView result={record.result} />
        )}
      </div>
    </main>
  );
}

function LoadingBlock({
  stage,
  currentStage,
}: {
  stage: string;
  currentStage?: string | null;
}) {
  const stages = [
    { key: "fetch_evidence", label: "Gathering evidence" },
    { key: "senior_reviewer", label: "Synthesizing verdict" },
    { key: "critic", label: "Adversarial review" },
    { key: "revise", label: "Revising verdict" },
  ];
  const active = currentStage ?? "fetch_evidence";

  return (
    <div className="mt-16 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-8 backdrop-blur">
      <div className="flex items-center gap-3">
        <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
        <p className="text-sm uppercase tracking-[0.18em] text-zinc-400">
          {stage === "queued" ? "Queued" : "Running"}
        </p>
      </div>
      <p className="mt-4 text-zinc-300">
        Five agents are auditing the profile. 60&ndash;180 seconds.
      </p>
      <ul className="mt-6 space-y-2 font-mono text-xs">
        {stages.map((s) => {
          const isActive = s.key === active;
          return (
            <li
              key={s.key}
              className={`flex items-center gap-2 ${
                isActive ? "text-emerald-300" : "text-zinc-600"
              }`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  isActive ? "animate-pulse bg-emerald-400" : "bg-zinc-700"
                }`}
              />
              {s.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="mt-16 rounded-xl border border-rose-900/40 bg-rose-950/20 p-8 backdrop-blur">
      <p className="text-sm uppercase tracking-[0.18em] text-rose-400">Error</p>
      <p className="mt-3 font-mono text-xs text-rose-300/80">{message}</p>
    </div>
  );
}

function VerdictView({ result }: { result: NonNullable<ReportRecord["result"]> }) {
  const { verdict } = result;
  const meta = TIER_META[verdict.tier];

  return (
    <div className="mt-12 space-y-8">
      {/* Scorecard */}
      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-8 backdrop-blur">
        <div className="flex items-start justify-between gap-6">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
              Verdict
            </p>
            <p className="mt-2 text-lg text-zinc-100">{verdict.one_line_verdict}</p>
            <p className="mt-3 text-xs text-zinc-500">{meta.description}</p>
          </div>
          <div className="text-right">
            <p className={`font-mono text-5xl font-medium ${meta.scoreClass}`}>
              {verdict.score}
            </p>
            <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-zinc-500">
              / 100
            </p>
          </div>
        </div>
        <div className="mt-6">
          <span
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] ${meta.badgeClass}`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {meta.label}
          </span>
        </div>
      </div>

      {/* Strengths */}
      <Section title="Strengths">
        {verdict.strengths.length === 0 ? (
          <Empty>No notable strengths surfaced.</Empty>
        ) : (
          verdict.strengths.map((s, i) => (
            <PointBlock key={i} point={s.point} evidence={s.evidence} />
          ))
        )}
      </Section>

      {/* Concerns */}
      <Section title="Concerns">
        {verdict.concerns.length === 0 ? (
          <Empty>No concerns raised.</Empty>
        ) : (
          verdict.concerns.map((c, i) => (
            <PointBlock key={i} point={c.point} evidence={c.evidence} />
          ))
        )}
      </Section>

      {/* Fixes */}
      <Section title="Recommended fixes">
        {verdict.fixes.length === 0 ? (
          <Empty>Nothing actionable.</Empty>
        ) : (
          verdict.fixes.map((f, i) => (
            <div
              key={i}
              className="rounded-lg border border-zinc-800/60 bg-zinc-900/30 p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <p className="text-sm text-zinc-200">{f.action}</p>
                <span
                  className={`shrink-0 font-mono text-[10px] uppercase tracking-[0.18em] ${impactColor(
                    f.impact
                  )}`}
                >
                  {f.impact}
                </span>
              </div>
            </div>
          ))
        )}
      </Section>

      {/* Meta */}
      <div className="flex flex-wrap gap-6 border-t border-zinc-900 pt-6 font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-600">
        <span>Critic rounds: {result.critic_rounds}</span>
        <span>Revisions: {result.revisions}</span>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="mb-4 text-[11px] uppercase tracking-[0.18em] text-zinc-500">
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function PointBlock({ point, evidence }: { point: string; evidence: string }) {
  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-900/30 p-4">
      <p className="text-sm text-zinc-200">{point}</p>
      <p className="mt-2 font-mono text-[11px] text-zinc-500">{evidence}</p>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-zinc-600">{children}</p>;
}
