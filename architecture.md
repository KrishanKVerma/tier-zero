# Architecture

## Design principles

1. **Agents, not chains.** Independent agents own dimensions. They debate, not pipeline.
2. **Evidence over opinion.** Every claim in the verdict cites specific repos, commits, or files.
3. **Eval-driven.** No agent ships without measurable performance against ground truth.
4. **Cheap by default.** Aggressive caching, model fallback, batch GitHub API calls.

## The five agents

### Forensics Agent
**Role:** Detects originality and authenticity signals.
**Inputs:** Profile metadata, repo list, commit history samples.
**Outputs:** Fork-vs-original ratio, tutorial-cluster detection, streak-farming indicators, commit-quality score.
**Tools:** `github_client.get_repos`, `github_client.get_commits`, `pattern_detector.detect_tutorial_match`.

### Depth Agent
**Role:** Measures technical depth across repos.
**Inputs:** Top N repos by activity, their READMEs, file trees.
**Outputs:** Language portfolio, repo-quality distribution, production-readiness markers (tests, CI, docs, deploys).
**Tools:** `github_client.get_repo_tree`, `code_parser.scan_repo_quality`.

### Claims Agent
**Role:** Cross-checks bio claims against code evidence.
**Inputs:** Profile bio, README, top repos' content.
**Outputs:** Per-claim verification — supported / weakly supported / unsupported.
**Tools:** `code_parser.search_pattern`, LLM-based semantic match.

### Senior Reviewer Agent
**Role:** Synthesizes a verdict from the three analysis agents.
**Inputs:** Outputs of Forensics, Depth, Claims agents.
**Outputs:** Structured verdict — score, strengths, concerns, fixes.
**Tools:** None (pure reasoning).

### Critic Agent
**Role:** Pushes back on the Senior Reviewer to prevent shallow takes.
**Inputs:** Senior Reviewer's verdict + all evidence.
**Outputs:** Either approval, or specific challenges sent back for revision.
**Tools:** None.

## Control flow

The graph runs Forensics, Depth, Claims in parallel. Senior Reviewer waits for all three, drafts verdict. Critic reviews. If Critic challenges, Senior Reviewer revises with the challenge as context. Loop caps at 2 revision rounds to prevent infinite debate.

## Models

| Agent | Primary | Fallback | Reasoning |
|-------|---------|----------|-----------|
| Forensics | Claude Haiku | GPT-4o-mini | Pattern detection, fast & cheap |
| Depth | Claude Sonnet | GPT-4o | Needs deeper code understanding |
| Claims | Claude Sonnet | GPT-4o | Semantic claim-evidence matching |
| Senior Reviewer | Claude Opus | GPT-4o | Highest reasoning load |
| Critic | Claude Opus | GPT-4o | Adversarial reasoning |

## Caching

GitHub data is cached for 24 hours per profile. Agent outputs are cached by content hash — re-running the same profile is near-free.

## Observability

Every agent call traces to Langfuse with: input, output, latency, cost, model used. Failed runs are surfaced. Eval runs auto-attach scores.

## Out of scope (v1)

- Web app — handled separately under `apps/web`
- Auth, paid tiers, batch evaluations
- Multi-repo deep code review
- Private repos