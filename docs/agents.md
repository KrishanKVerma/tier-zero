# Agents

Detailed contracts for each agent. Read this before modifying agent code.

---

## Forensics Agent

**Goal:** Determine how much of the profile is original work vs. tutorial follows, forks, and gaming.

**Signals it computes:**
- Fork ratio (forked repos / total public repos)
- Originality score per repo (commit count, lines of unique code, commit message variance)
- Tutorial-cluster score — semantic similarity of repo content to known tutorial repos
- Streak-farming indicators — single-line commits, near-identical commit messages, weekend-only patterns
- Last meaningful commit recency

**Output schema:**
```python
{
    "fork_ratio": float,
    "originality_score": float,  # 0-100
    "tutorial_clusters": list[dict],  # repos suspected of being tutorial follows
    "streak_farming_flags": list[str],
    "last_meaningful_commit": str,  # ISO date
    "evidence": list[dict],  # specific repos/commits citing each finding
}
```

---

## Depth Agent

**Goal:** Determine whether the profile shows depth in a few areas or spread thin across many.

**Signals it computes:**
- Language portfolio with line counts per language
- Repo quality distribution (Bronze / Silver / Gold based on README, tests, CI, docs, deploys)
- Production-readiness markers — presence of `Dockerfile`, `.github/workflows`, `tests/`, deployment configs
- "Real work" indicator — repos with > N commits, > M files, non-trivial content

**Output schema:**
```python
{
    "language_portfolio": dict[str, int],
    "repo_quality_distribution": {"gold": int, "silver": int, "bronze": int},
    "production_markers_present": dict[str, bool],
    "real_work_repos": list[str],
    "evidence": list[dict],
}
```

---

## Claims Agent

**Goal:** Cross-check what the bio/profile README claims against what the code shows.

**Signals it computes:**
- Bio claims extracted (e.g., "RAG", "Agents", "Fine-tuning")
- For each claim — supporting evidence found in repos (Y/N + repo names)
- Verdict per claim — supported / weakly supported / unsupported

**Output schema:**
```python
{
    "claims": [
        {
            "claim": str,
            "verdict": "supported" | "weakly_supported" | "unsupported",
            "supporting_repos": list[str],
            "reasoning": str,
        }
    ],
}
```

---

## Senior Reviewer Agent

**Goal:** Produce the final verdict from upstream agent outputs.

**Constraints:**
- Must cite evidence from upstream agents — no opinions without a source
- Must use the structured output schema below — no free-form prose
- Strengths and concerns must be specific (not "good projects" — name them)

**Output schema:**
```python
{
    "score": int,  # 0-100
    "one_line_verdict": str,
    "strengths": list[{"point": str, "evidence": str}],
    "concerns": list[{"point": str, "evidence": str}],
    "fixes": list[{"action": str, "impact": "high" | "medium" | "low"}],
}
```

---

## Critic Agent

**Goal:** Make the Senior Reviewer sharper by challenging weak claims.

**Behavior:**
- Reads verdict + all upstream agent evidence
- Flags claims that are vague, unsupported, or contradict the evidence
- Returns either `{"approve": True}` or `{"approve": False, "challenges": list[str]}`
- Caps at 2 challenge rounds to prevent infinite loops

**Output schema:**
```python
{
    "approve": bool,
    "challenges": list[str],  # empty if approve == True
}
```