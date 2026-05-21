const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Tier = "tier-zero" | "strong" | "mid" | "weak" | "red-flag";

export interface StrengthPoint {
  point: string;
  evidence: string;
}

export interface ConcernPoint {
  point: string;
  evidence: string;
}

export interface FixAction {
  action: string;
  impact: "high" | "medium" | "low";
}

export interface Verdict {
  score: number;
  one_line_verdict: string;
  tier: Tier;
  strengths: StrengthPoint[];
  concerns: ConcernPoint[];
  fixes: FixAction[];
}

export interface ReportResult {
  verdict: Verdict;
  forensics: Record<string, unknown>;
  depth: Record<string, unknown>;
  claims: Record<string, unknown>;
  critic_rounds: number;
  revisions: number;
}

export type ReportStatus = "queued" | "running" | "complete" | "error";

export interface ReportRecord {
  report_id: string;
  status: ReportStatus;
  current_stage: string | null;
  elapsed_seconds: number | null;
  result: ReportResult | null;
  error: string | null;
}

export interface QueuedResponse {
  report_id: string;
  status: "queued";
  status_url: string;
}

export async function createReport(
  username: string,
  githubToken: string,
): Promise<QueuedResponse> {
  const res = await fetch(`${API_BASE}/api/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, mode: "profile", github_token: githubToken }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getReport(reportId: string): Promise<ReportRecord> {
  const res = await fetch(`${API_BASE}/api/report/${reportId}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}