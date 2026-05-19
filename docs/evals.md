# Evals

Most AI tools never measure if they work. tier-zero treats evals as non-negotiable.

---

## Why evals exist here

LLM outputs feel correct even when they're wrong. Without measurement, every change is a guess. With a ground-truth set, every PR has a number attached: did this make the system better or worse?

---

## The ground-truth set

20 hand-picked GitHub profiles, each labeled by a human senior engineer with:

- **Tier label** — `tier-zero` (top-tier senior signal), `strong`, `mid`, `weak`, `red-flag`
- **Three real strengths** — what a senior would actually point out
- **Three real concerns** — what would worry a senior in interview
- **Originality verdict** — `original`, `mixed`, `tutorial-heavy`
- **Notes** — free-form senior commentary

Profiles span the spectrum intentionally:
- 4 profiles of staff/principal-tier engineers (real, public)
- 4 profiles of strong mid-level engineers
- 4 profiles of clearly-junior but original builders
- 4 profiles of tutorial-heavy / streak-farmed accounts
- 4 profiles with obvious red flags (claims mismatch, AI-generated repos, etc.)

Stored in `evals/ground_truth/profiles.json`.

---

## Metrics

| Metric | What it measures |
|--------|------------------|
| **Tier accuracy** | % of profiles where predicted tier matches ground truth (with ±1 tier tolerance) |
| **Strength precision** | Of strengths the system surfaces, what % match a ground-truth strength |
| **Concern precision** | Of concerns the system surfaces, what % match a ground-truth concern |
| **Originality F1** | F1 score on the originality verdict |
| **Cost per report** | USD spend per full report run |
| **Latency p50 / p95** | Median and 95th-percentile end-to-end report time |

Target for v1 launch:
- Tier accuracy ≥ 80%
- Strength precision ≥ 60%
- Concern precision ≥ 60%
- Cost per report < $0.15
- p95 latency < 90s

---

## How evals run

```bash
python evals/run_evals.py
```

Outputs to `evals/results/<timestamp>.json` and a summary table to stdout.

CI runs evals on every PR via `.github/workflows/eval.yml`. Score regressions block merges.

---

## Adding a new ground-truth profile

1. Append to `evals/ground_truth/profiles.json` with the schema above.
2. Label honestly. If the profile is ambiguous, label "mid" and add notes — don't force a tier.
3. Run evals locally to confirm no regression on the existing 20.