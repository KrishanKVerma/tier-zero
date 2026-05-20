"""Claims Agent — cross-checks profile bio claims against repository evidence.

Two-step pipeline:
1. Extract structured claims from the profile bio + README.
2. For each claim, verify against repo evidence.

This is the agent that detects "tutorial-finishers wearing portfolio costume".
"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from apps.api.tools.github_client import (
    RepoSnapshot,
    get_profile,
    get_repo_details,
    get_repos,
)

load_dotenv()


# ---------- Output schemas ----------


class ExtractedClaim(BaseModel):
    claim: str = Field(description="A single, atomic technical claim from the bio. E.g. 'RAG', 'LangGraph', 'fine-tuning'.")
    source_text: str = Field(description="The exact phrase from the bio/README that produced this claim.")


class ExtractedClaims(BaseModel):
    claims: list[ExtractedClaim] = Field(
        description="List of distinct technical claims. Skip generic things like 'Python' "
        "or 'open to work'. Only include specific tech/skills the bio is signaling expertise in."
    )


class VerifiedClaim(BaseModel):
    claim: str
    verdict: Literal["supported", "weakly_supported", "unsupported"]
    confidence: Literal["low", "medium", "high"]
    supporting_repos: list[str] = Field(
        description="Repo full_names that back the claim. Empty if unsupported."
    )
    reasoning: str = Field(
        description="One-to-two sentences explaining the verdict, citing what was/wasn't found."
    )


class ClaimsReport(BaseModel):
    claims: list[VerifiedClaim]
    overall_alignment_score: int = Field(
        description="0-100. How well do the bio claims match the code evidence? "
        "100 = every claim has strong supporting work. 0 = bio is mostly aspirational."
    )
    bio_credibility: Literal["high", "moderate", "low", "no_claims_to_check"]
    summary: str = Field(description="One sentence on the bio-vs-evidence alignment.")


# ---------- LLM setup ----------


def _make_llm(temperature: float = 0.1) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Add it to .env.")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        api_key=api_key,
    )


# ---------- Step 1: Claim extraction ----------


_EXTRACT_SYSTEM_PROMPT = """You extract technical CLAIMS from a developer's GitHub bio and profile README.

A claim is a specific technology, framework, technique, or domain expertise the person signals they work with.

EXTRACT: RAG, LangGraph, fine-tuning, computer vision, distributed systems, Kubernetes, multi-agent orchestration, fraud detection, LLM evaluation

SKIP: generic languages (Python, JavaScript), employment status ("open to work"), location, school year, soft skills ("passionate"), vague phrases ("AI engineer").

Output ONLY the structured schema. Be conservative — better to extract 3 sharp claims than 10 fuzzy ones."""


_EXTRACT_USER_TEMPLATE = """Extract technical claims from this profile.

## Bio
{bio}

## Profile README excerpt
{profile_readme}

Return the claims list."""


_extract_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _EXTRACT_SYSTEM_PROMPT),
        ("user", _EXTRACT_USER_TEMPLATE),
    ]
)


def _extract_claims(bio: str | None, profile_readme: str | None) -> ExtractedClaims:
    llm = _make_llm().with_structured_output(ExtractedClaims)
    result = llm.invoke(
        _extract_prompt.format_messages(
            bio=bio or "(no bio)",
            profile_readme=profile_readme or "(no profile README)",
        )
    )
    assert isinstance(result, ExtractedClaims)
    return result


# ---------- Step 2: Claim verification ----------


_VERIFY_SYSTEM_PROMPT = """You are a senior engineer fact-checking a developer's bio against their actual code.

For EACH claim listed, decide:
- supported = clear evidence in repos (real implementation, not just imports). Confidence high.
- weakly_supported = some evidence but shallow (a tutorial follow, a few-line script, mentioned in README but no real code). Confidence medium.
- unsupported = nothing in the repos shows this claim. Confidence high if you scanned thoroughly.

CRITICAL rules:
1. Importing a library is NOT evidence. The code must DO something with it.
   - `import langchain` in a 20-line script = weakly_supported at best
   - A full RAG pipeline with retrieval + reranking + generation = supported
2. Bio claim "Fine-tuning" requires actual training code (LoRA, SFT, scripts that call .train()), not just inference.
3. README mentions are not evidence — code is. README claims can be checked against the file tree to confirm code exists.
4. Be honest. A bio with 5 claims but only 1-2 backed should land low on overall_alignment_score.

Cite repo full_names in supporting_repos. Empty list if unsupported.

Output ONLY the structured schema."""


_VERIFY_USER_TEMPLATE = """Verify each claim against this developer's repository evidence.

## Claims to verify
{claims}

## Repository overview (non-fork, top {repo_count})
{repos_overview}

## Detailed repo content (READMEs + file trees for top {sampled_count} active repos)
{repo_details}

Return the structured ClaimsReport now."""


_verify_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _VERIFY_SYSTEM_PROMPT),
        ("user", _VERIFY_USER_TEMPLATE),
    ]
)


# ---------- Data formatting ----------


def _format_claims_for_verification(claims: list[ExtractedClaim]) -> str:
    if not claims:
        return "(no claims extracted)"
    return "\n".join(f"- {c.claim} (from: \"{c.source_text}\")" for c in claims)


def _format_repos_overview(repos: list[RepoSnapshot]) -> str:
    lines = []
    for r in repos:
        if r.is_fork or r.is_archived:
            continue
        lines.append(
            f"- {r.full_name} ({r.primary_language or 'unknown'}, "
            f"{r.size_kb}KB, pushed {r.last_pushed_at[:10]}): "
            f"{r.description or '(no description)'}"
        )
    return "\n".join(lines) if lines else "(no non-fork repos)"


def _format_repo_details(details_list: list[dict]) -> str:
    if not details_list:
        return "(no repo details available)"
    sections = []
    for d in details_list:
        snap = d["snapshot"]
        readme = d["readme"] or "(no README)"
        readme_excerpt = readme[:1500] + ("..." if len(readme) > 1500 else "")
        tree = d["tree"][:80]
        tree_str = "\n  ".join(tree) if tree else "(empty)"
        sections.append(
            f"### {snap['full_name']}\n"
            f"language={snap['primary_language']}, size_kb={snap['size_kb']}, "
            f"commits={d['commit_count']}\n\n"
            f"**README excerpt:**\n{readme_excerpt}\n\n"
            f"**File tree:**\n  {tree_str}"
        )
    return "\n\n---\n\n".join(sections)


# ---------- Public entry point ----------


def run_claims(username: str) -> ClaimsReport:
    """Run the Claims Agent on a GitHub username."""
    profile = get_profile(username)
    repos = get_repos(username, limit=50)

    # Try to fetch the profile README (special repo with same name as username)
    profile_readme: str | None = None
    try:
        profile_repo = get_repo_details(f"{username}/{username}")
        profile_readme = profile_repo.get("readme")
    except RuntimeError:
        pass

    # Step 1: extract claims
    extracted = _extract_claims(profile.bio, profile_readme)

    # Early exit: no claims means nothing to verify
    if not extracted.claims:
        return ClaimsReport(
            claims=[],
            overall_alignment_score=0,
            bio_credibility="no_claims_to_check",
            summary="No specific technical claims found in the bio or profile README.",
        )

    # Step 2: fetch repo details for top active non-fork repos
    active_repos = [r for r in repos if not r.is_fork and not r.is_archived][:5]
    details_list: list[dict] = []
    for repo in active_repos:
        try:
            details_list.append(get_repo_details(repo.full_name))
        except RuntimeError:
            continue

    # Verify
    llm = _make_llm().with_structured_output(ClaimsReport)
    chain = _verify_prompt | llm

    result = chain.invoke(
        {
            "claims": _format_claims_for_verification(extracted.claims),
            "repo_count": len(repos),
            "repos_overview": _format_repos_overview(repos),
            "sampled_count": len(details_list),
            "repo_details": _format_repo_details(details_list),
        }
    )
    assert isinstance(result, ClaimsReport)
    return result