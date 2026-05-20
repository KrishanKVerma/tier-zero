"""Depth Agent — measures technical depth across a developer's repos.

Inputs (pre-fetched): profile snapshot, repos, sampled repo details (README, file tree).
Output: structured depth report with production-readiness markers.

Uses prompt + structured output. No tool calls — all data is passed in.
"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from apps.api.tools.github_client import (
    ProfileSnapshot,
    RepoSnapshot,
    get_profile,
    get_repo_details,
    get_repos,
)

load_dotenv()


# ---------- Output schema ----------


class QualityDistribution(BaseModel):
    gold: int = Field(description="Repos with most production markers present.")
    silver: int = Field(description="Repos with some production markers.")
    bronze: int = Field(description="Repos with few or no production markers.")


class ProductionMarkers(BaseModel):
    readme: int = Field(description="Repos with a non-trivial README (>200 chars).")
    tests: int = Field(description="Repos with a tests/ folder or test files.")
    ci: int = Field(description="Repos with .github/workflows or other CI config.")
    docker: int = Field(description="Repos with a Dockerfile or docker-compose.")
    license: int = Field(description="Repos with a LICENSE file.")


class DepthReport(BaseModel):
    language_portfolio: dict[str, float] = Field(
        description="Map of language name to its percentage share (0-100) of total code "
        "across non-fork repos. Languages summing to <5% may be grouped as 'other'."
    )
    repo_quality_distribution: QualityDistribution
    production_markers_present: ProductionMarkers
    top_real_work_repos: list[str] = Field(
        description="Repo full_names that look like genuine engineering work — "
        "non-trivial size, sustained activity, production markers present. Max 5."
    )
    depth_score: int = Field(
        description="0-100. 100 = clear depth in a focused area with production discipline. "
        "0 = wide-shallow tutorial collection."
    )
    breadth_vs_depth: Literal["depth-focused", "balanced", "breadth-focused"]
    summary: str = Field(
        description="One sentence a senior engineer would write about this profile's depth."
    )


# ---------- LLM setup ----------


def _make_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Add it to .env.")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        api_key=api_key,
    )


# ---------- Prompt ----------


_SYSTEM_PROMPT = """You are a senior staff engineer evaluating a developer's technical DEPTH.

Forensics handles originality. Claims handles bio-vs-evidence. Your job is exclusively depth — does this person go deep, or only wide?

Depth signals:
1. Language portfolio focused or scattered — 1-3 languages with substantial code is depth, 10 languages with tiny snippets is breadth
2. Production-readiness markers — READMEs over 200 chars, tests, CI, Docker, LICENSE
3. Repo quality tiers:
   - GOLD = README + tests + CI + (docker or deploy)
   - SILVER = README + (tests OR CI)
   - BRONZE = anything less
4. Real-work repos — non-trivial size (>50 KB), sustained pushes, not abandoned

Be CALIBRATED. A focused 4-repo portfolio with 3 gold-tier projects beats 30 bronze-tier repos. Reward focus.

Be EVIDENCE-BASED. Cite specific repos in top_real_work_repos. Do not invent markers — only mark CI present if a workflow file appears in the data given to you.

Be HONEST about thin profiles. A profile with 1-2 trivial repos is not "depth-focused" — it's "insufficient data, leans shallow". Score accordingly.

Output ONLY the structured schema. No prose outside it."""


_USER_PROMPT_TEMPLATE = """Evaluate the depth of this GitHub profile.

## Profile

{profile}

## Repos (non-fork, sorted by recent push)

{repos}

## Sampled repo details (READMEs + file trees for top {sampled_count} active repos)

{repo_details}

Produce the depth report now."""


_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("user", _USER_PROMPT_TEMPLATE),
    ]
)


# ---------- Data formatting ----------


def _format_profile(p: ProfileSnapshot) -> str:
    return (
        f"Username: {p.username}\n"
        f"Public repos: {p.public_repos}\n"
        f"Followers: {p.followers}\n"
        f"Account created: {p.account_created_at[:10]}"
    )


def _format_repos(repos: list[RepoSnapshot]) -> str:
    lines = []
    for r in repos:
        if r.is_fork or r.is_archived:
            continue
        lines.append(
            f"- {r.full_name}\n"
            f"  language={r.primary_language or 'none'}, "
            f"size_kb={r.size_kb}, stars={r.stars}, "
            f"pushed={r.last_pushed_at[:10]}, "
            f"topics={','.join(r.topics) or 'none'}\n"
            f"  description: {r.description or '(none)'}"
        )
    return "\n".join(lines) if lines else "(no non-fork repos)"


def _format_repo_details(details_list: list[dict]) -> str:
    if not details_list:
        return "(no repo details available)"

    sections = []
    for d in details_list:
        snap = d["snapshot"]
        readme = d["readme"] or "(no README)"
        readme_excerpt = readme[:1200] + ("..." if len(readme) > 1200 else "")
        tree = d["tree"][:60]
        tree_str = "\n  ".join(tree) if tree else "(empty)"

        sections.append(
            f"### {snap['full_name']}\n"
            f"size_kb={snap['size_kb']}, language={snap['primary_language']}, "
            f"commits={d['commit_count']}\n\n"
            f"**README excerpt:**\n{readme_excerpt}\n\n"
            f"**File tree (top 60 entries):**\n  {tree_str}"
        )
    return "\n\n---\n\n".join(sections)


# ---------- Public entry point ----------


def run_depth(username: str) -> DepthReport:
    """Run the Depth Agent on a GitHub username."""
    profile = get_profile(username)
    repos = get_repos(username, limit=50)

    # Sample full details for top 5 active non-fork repos
    active_repos = [r for r in repos if not r.is_fork and not r.is_archived][:5]
    details_list: list[dict] = []
    for repo in active_repos:
        try:
            details_list.append(get_repo_details(repo.full_name))
        except RuntimeError:
            continue

    llm = _make_llm().with_structured_output(DepthReport)
    chain = _prompt | llm

    result = chain.invoke(
        {
            "profile": _format_profile(profile),
            "repos": _format_repos(repos),
            "sampled_count": len(details_list),
            "repo_details": _format_repo_details(details_list),
        }
    )
    assert isinstance(result, DepthReport)
    return result