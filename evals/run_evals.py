"""Run tier-zero against the ground-truth dataset and score the results.

Outputs:
- JSON results file at evals/results/<timestamp>.json
- Summary table to stdout
- Non-zero exit code if any "must-pass" assertion fails

Used both for local benchmarking and by CI (.github/workflows/eval.yml).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.api.graph import run as run_tier_zero

GROUND_TRUTH_PATH = Path("evals/ground_truth/profiles.json")
RESULTS_DIR = Path("evals/results")

# Tier accuracy tolerates being one tier off (we award partial credit).
TIER_ORDER = ["red-flag", "weak", "mid", "strong", "tier-zero"]


# ---------- Scoring helpers ----------


def _tier_distance(predicted: str, expected: str) -> int:
    """0 = exact match, 1 = one tier off, ... 4 = opposite ends."""
    try:
        return abs(TIER_ORDER.index(predicted) - TIER_ORDER.index(expected))
    except ValueError:
        return 99


def _score_in_range(predicted: int, expected_range: list[int]) -> bool:
    lo, hi = expected_range
    return lo <= predicted <= hi


def _keyword_overlap(text: str, keywords: list[str]) -> float:
    """Fraction of expected keywords that appear (case-insensitively) in text."""
    if not keywords:
        return 1.0
    lowered = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lowered)
    return hits / len(keywords)


# ---------- Per-profile eval ----------


def evaluate_profile(profile_spec: dict[str, Any]) -> dict[str, Any]:
    """Run tier-zero on one profile and score it against the spec."""
    username = profile_spec["username"]
    started = time.time()

    try:
        state = run_tier_zero(username)
        elapsed = time.time() - started
    except Exception as exc:  # noqa: BLE001 — we want to record any failure
        elapsed = time.time() - started
        return {
            "username": username,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "elapsed_seconds": round(elapsed, 2),
        }

    verdict = state["verdict"]
    forensics = state["forensics"]

    # Strength text for keyword scoring
    strengths_text = " ".join(s.point for s in verdict.strengths)
    concerns_text = " ".join(c.point for c in verdict.concerns)

    tier_dist = _tier_distance(verdict.tier, profile_spec["expected_tier"])
    score_in_range = _score_in_range(verdict.score, profile_spec["expected_score_range"])
    strength_recall = _keyword_overlap(
        strengths_text, profile_spec.get("expected_strengths_keywords", [])
    )
    concern_recall = _keyword_overlap(
        concerns_text, profile_spec.get("expected_concerns_keywords", [])
    )

    return {
        "username": username,
        "status": "ok",
        "elapsed_seconds": round(elapsed, 2),
        "predicted": {
            "tier": verdict.tier,
            "score": verdict.score,
            "one_line_verdict": verdict.one_line_verdict,
        },
        "expected": {
            "tier": profile_spec["expected_tier"],
            "score_range": profile_spec["expected_score_range"],
        },
        "scoring": {
            "tier_distance": tier_dist,
            "tier_exact_match": tier_dist == 0,
            "tier_within_one": tier_dist <= 1,
            "score_in_range": score_in_range,
            "strength_keyword_recall": round(strength_recall, 2),
            "concern_keyword_recall": round(concern_recall, 2),
        },
        "forensics_originality_score": forensics.originality_score,
        "critic_rounds": len(state.get("critic_history", [])),
        "revisions": state.get("revision_round", 0),
    }


# ---------- Suite aggregation ----------


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in results if r["status"] == "ok"]
    n = len(ok)
    if n == 0:
        return {"status": "no_successful_runs", "total": len(results)}

    tier_exact = sum(1 for r in ok if r["scoring"]["tier_exact_match"]) / n
    tier_within_one = sum(1 for r in ok if r["scoring"]["tier_within_one"]) / n
    score_in_range = sum(1 for r in ok if r["scoring"]["score_in_range"]) / n
    avg_strength_recall = statistics.mean(r["scoring"]["strength_keyword_recall"] for r in ok)
    avg_latency = statistics.mean(r["elapsed_seconds"] for r in ok)
    p95_latency = (
        statistics.quantiles((r["elapsed_seconds"] for r in ok), n=20)[18]
        if n >= 2
        else avg_latency
    )

    return {
        "status": "complete",
        "total_profiles": len(results),
        "successful": n,
        "errors": len(results) - n,
        "metrics": {
            "tier_exact_accuracy": round(tier_exact, 2),
            "tier_within_one_accuracy": round(tier_within_one, 2),
            "score_in_range_accuracy": round(score_in_range, 2),
            "avg_strength_keyword_recall": round(avg_strength_recall, 2),
            "avg_latency_seconds": round(avg_latency, 2),
            "p95_latency_seconds": round(p95_latency, 2),
        },
    }


def print_table(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    print()
    print(f"{'username':<20} {'expected':<12} {'predicted':<12} {'score':<8} {'in_range':<10} {'lat(s)':<8}")
    print("-" * 80)
    for r in results:
        if r["status"] != "ok":
            print(f"{r['username']:<20} ERROR: {r['error']}")
            continue
        p = r["predicted"]
        e = r["expected"]
        s = r["scoring"]
        in_range = "✓" if s["score_in_range"] else "✗"
        print(
            f"{r['username']:<20} {e['tier']:<12} {p['tier']:<12} "
            f"{p['score']:<8} {in_range:<10} {r['elapsed_seconds']:<8}"
        )

    print()
    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


# ---------- CLI ----------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ground-truth", type=Path, default=GROUND_TRUTH_PATH, help="Ground truth JSON file."
    )
    parser.add_argument(
        "--results-dir", type=Path, default=RESULTS_DIR, help="Where to write results JSON."
    )
    parser.add_argument(
        "--min-tier-within-one",
        type=float,
        default=0.75,
        help="Fail if tier-within-one accuracy < this threshold.",
    )
    args = parser.parse_args()

    data = json.loads(args.ground_truth.read_text())
    profiles = data["profiles"]
    print(f"Loaded {len(profiles)} ground-truth profiles from {args.ground_truth}")

    results = []
    for i, spec in enumerate(profiles, 1):
        print(f"\n[{i}/{len(profiles)}] Evaluating {spec['username']}...")
        results.append(evaluate_profile(spec))

    summary = summarize(results)
    print_table(results, summary)

    # Persist
    args.results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = args.results_dir / f"{timestamp}.json"
    output_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "ground_truth_version": data.get("version"),
                "summary": summary,
                "results": results,
            },
            indent=2,
        )
    )
    print(f"\nResults written to {output_path}")

    # Gate
    if summary.get("status") != "complete":
        print("FAIL: no successful runs")
        return 1
    within_one = summary["metrics"]["tier_within_one_accuracy"]
    if within_one < args.min_tier_within_one:
        print(
            f"FAIL: tier_within_one_accuracy {within_one} < threshold {args.min_tier_within_one}"
        )
        return 1
    print(f"\nPASS: tier_within_one_accuracy {within_one} >= {args.min_tier_within_one}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
