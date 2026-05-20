<div align="center">

# tier-zero

### Tier-zero engineering review for any GitHub profile.

*A multi-agent system that evaluates developer GitHub profiles the way a senior engineer would — in 60 seconds.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-in%20development-orange)]()

[How it works](#how-it-works) · [Run locally](#run-locally) · [Roadmap](#roadmap)

</div>

---

## The problem

Every recruiter, hiring manager, and engineer looking at a GitHub profile asks the same question:

> *Is this real work, or tutorial follows wearing a portfolio costume?*

Surface metrics lie. Stars, streaks, and pinned repos can be gamed. A senior engineer takes two hours to give a real verdict on a profile — reading commits, scanning READMEs, checking depth versus breadth, sniffing out copy-paste tutorials, cross-checking claims against code.

**tier-zero does that review in 60 seconds.**

---

## What it does

Point it at any GitHub username. Five specialized agents analyze the profile across independent dimensions, then debate the verdict.

### The five agents

| Agent | What it does |
|-------|-------------|
| **Forensics** | Originality detection — fork ratio, commit pattern analysis, signs of streak farming, tutorial clusters |
| **Depth** | Technical depth signals — language breadth vs depth, repo quality, presence of tests/CI/docs/deploys |
| **Claims** | Cross-checks the profile bio against actual code. If bio says "RAG / Agents / Fine-tuning" — does the code show it, or just LangChain hello-worlds? |
| **Senior Reviewer** | Synthesizes a verdict the way a Staff Engineer would |
| **Critic** | Pushes back on the verdict. Forces sharper takes. Prevents shallow praise. |

The agents run in a graph, not a chain. They debate until verdict converges.

---

## Output

A structured report containing:

- **Verdict** — overall hire-ability signal (0-100) with one-line summary
- **Three strengths** — what this profile is doing right
- **Three concerns** — what would worry a senior engineer
- **Originality forensics** — fork ratio, tutorial-cluster detection, streak-farming indicators
- **Depth signals** — language portfolio, repo quality distribution, production-readiness markers
- **Claims vs evidence** — bio claims mapped against actual repository evidence
- **What to fix** — actionable improvements ranked by impact

---

## How it works

```
                ┌──────────────────────────┐
                │  Orchestrator (LangGraph)│
                └────────────┬─────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │Forensics│          │  Depth  │          │ Claims  │
   │  Agent  │          │  Agent  │          │  Agent  │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                   ┌──────────────────┐
                   │ Senior Reviewer  │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │     Critic       │
                   └────────┬─────────┘
                            │
                            ▼
                      Final Report
```

See [architecture.md](architecture.md) for the full design.

---

## Tech stack

- **Agent orchestration** — LangGraph
- **LLMs** — Claude (primary), GPT-4o (fallback)
- **Code analysis** — tree-sitter, Python AST
- **GitHub data** — PyGithub + GraphQL API
- **Backend** — FastAPI + Celery + Redis
- **Frontend** — Next.js + Tailwind + shadcn/ui
- **Observability** — Langfuse
- **Eval** — custom ground-truth set of 20 profiles, scored against senior engineer labels

---

## Run locally

```bash
# Clone
git clone git@github.com:KrishanKVerma/tier-zero.git
cd tier-zero

# Configure
cp .env.example .env
# Add ANTHROPIC_API_KEY or OPENAI_API_KEY

# Install
pip install -e .

# Run
python -m apps.api.main --username some-github-user
```

---

## Roadmap

- [x] Architecture defined
- [x] Repo scaffold
- [x] GitHub data fetching
- [x] Forensics Agent
- [x] Depth Agent
- [x] Claims Agent
- [ ] Senior Reviewer + Critic
- [ ] LangGraph orchestration
- [ ] Eval set + benchmarks
- [ ] FastAPI backend
- [ ] Next.js frontend
- [ ] Observability + caching
- [ ] Public launch

---

## Eval philosophy

Most AI tools never measure if they work. tier-zero ships with a 20-profile ground-truth set hand-labeled against senior engineer judgment. Every PR runs against the eval. Performance is tracked in [evals/results/](evals/results/).

---

## Contributing

Issues and PRs welcome. See [docs/](docs/) for design rationale before opening a PR.

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

*Built by [Krishan Kumar Verma](https://github.com/KrishanKVerma) — open to remote roles and freelance.*

</div>