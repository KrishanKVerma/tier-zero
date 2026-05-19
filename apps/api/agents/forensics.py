"""Forensics Agent - detects originality and authenticity signals on a Github profile.
Inputs (pre-fetched): profile snapshot, repos, sample commits.
Output: structured forensics report with evidence-cited findings.

This agent uses prompt + structured output. No tool calls — all data is passed in.
"""


from __future__ import annotations
import os
from typing import Any , Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel , Field

from apps.api.tools.github_client import (
    ProfileSnapshot,
    RepoSnapshot,
    get_profile,
    get_recent_commits,
    get_repos,
)

load_dotenv()

class TutorialCluster(BaseModel):
    repo_name: str = Field(description= "Full name of the suspect repo.")
    reason: str = Field(description= "Specific reason this looks like a tutorial follow.")
    confidence: Literal["low" , "medium" , "high"]

class Evidence(BaseModel):
    finding: str = Field(description= "What was observed.")
    source: str = Field(description= "Where in the data this was observed (repo , commit sha, etc.).")

class ForensicsReport(BaseModel):
    fork_ratio: float = Field(description= "Number between 0.0 and 1.0.")
    originality_score: int = Field(description= "Overall originality on a 0-100 scale. "
        "100 = clearly original work, 0 = pure tutorial follows / forks.")
    tutorial_clusters: list[TutorialCluster] = Field(description= "Repos that show signs of being tutorial follows. Empty list if none.")
    streak_farming_flags: list[str] = Field(
        description="Specific patterns suggesting fake activity. Empty list if none."
    )
    last_meaningful_commit: str = Field(
        description="ISO date of the most recent commit that looks like real work. "
        "Empty string if cannot determine."
    )
    evidence: list[Evidence] = Field(
        description="Specific citations supporting the findings. Minimum 3 items."
    )
    summary: str = Field(
        description="One-sentence summary of what a senior engineer would notice first."
    )         


def _make_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Add it to .env")
    return ChatGroq(
        model = "llama-3.3-70b-versatile",
        temperature= 0.1,
        api_key=api_key,
    )


_SYSTEM_PROMPT = """You are a senior staff engineer reviewing a GitHub profile for hire-ability signals.

Your job is FORENSICS — detecting originality and authenticity. You do not judge skill or depth here. Other agents handle that.

Focus on:
1. Fork ratio — how much of this profile is original vs cloned/forked work
2. Tutorial-cluster detection — repos that look like step-by-step tutorial follows. Signals: generic names like "django-todo-app" or "react-weather-app", README that reads like tutorial output, predictable file structure, small uniform commits like "Step 1" / "Step 2" / "Add chapter 3 changes"
3. Streak farming — patterns suggesting fake activity. Signals: many tiny commits like "update readme" / "fix typo", commits exactly once per day for weeks, commit messages that are near-identical
4. Meaningful work recency — when did this person last do something that looks like real engineering vs. cosmetic activity

Be EVIDENCE-BASED. Every finding must cite a specific repo or commit. If you cannot find evidence for a concern, do not raise it.

Be CALIBRATED. Not every profile is suspicious. An originality score of 80+ should be your default unless evidence pulls it down.

Output ONLY the structured schema provided. No prose outside the schema."""


_USER_PROMPT_TEMPLATE = """Analyze this GitHub profile.

## Profile

{profile}

## Repos (sorted by recent push, top {repo_count})

{repos}

## Recent commits sampled from top 3 active repos

{commits}

Produce the forensics report now."""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("user" , _USER_PROMPT_TEMPLATE),
])


def _format_profile(p: ProfileSnapshot) -> str:
    return (
        f"Username: {p.username}\n"
        f"Name: {p.name or '(not set)'}\n"
        f"Bio: {p.bio or '(not set)'}\n"
        f"Account created: {p.account_created_at}\n"
        f"Public repos: {p.public_repos}\n"
        f"Followers: {p.followers}\n"
        f"Following: {p.following}"
    )

def _format_repos(repos: list[RepoSnapshot]) -> str:
    lines = []
    for r in repos:
        flags =[]
        if r.is_fork:
            flags.append("FORK")
        if r.is_archived:
            flags.append("ARCHIVED") 
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"- {r.full_name}{flag_str}\n"
            f"  language={r.primary_language or 'none'}, "
            f"stars={r.stars}, size_kb={r.size_kb}, "
            f"created={r.created_at[:10]}, pushed={r.last_pushed_at[:10]}\n"
            f"  description: {r.description or '(none)'}"
        )
    return "\n".join(lines) if lines else "(no repos)"

def _format_commits(commits_by_repo: dict[str , list[dict[str , Any]]]) -> str:
    if not commits_by_repo:
        return "(no commit samples available)"
    sections = []
    for repo_name , commits in commits_by_repo.items():
        lines = [f"### {repo_name}"]
        for c in commits:
            lines.append(
                f"  {c['sha']} {c['authored_at'][:10]} "
                f"+{c['additions']}/-{c['deletions']} "
                f"\"{c['message_first_line']}\""
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)
                  
def run_forensics(username: str) -> ForensicsReport:
    """Run the Forensics Agent on a GitHub username.

    Pre-fetches all required data, then invokes the LLM with structured output.
    """
    profile = get_profile(username)
    repos = get_repos(username , limit = 50)

    active_repos = [r for r in repos if not r.is_fork and not r.is_archived][:3]
    commits_by_repo: dict[str , list[dict[str , Any]]] = {}
    for repo in active_repos:
        try:
            commits_by_repo[repo.full_name] = get_recent_commits(repo.full_name , limit= 10)
        except RuntimeError:
            continue

    llm = _make_llm().with_structured_output(ForensicsReport) 
    chain = _prompt | llm

    result = chain.invoke(
        {
            "profile": _format_profile(profile),
            "repo_count": len(repos),
            "repos": _format_repos(repos),
            "commits": _format_commits(commits_by_repo),
        }
    )  


    assert isinstance(result , ForensicsReport)
    return result                  