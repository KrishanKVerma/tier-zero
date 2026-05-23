"""Senior Reviewer Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from apps.api.agents.claims import ClaimsReport
from apps.api.agents.depth import DepthReport
from apps.api.agents.forensics import ForensicsReport

if TYPE_CHECKING:
    from apps.api.agents.critic import CriticResponse

load_dotenv()


class StrengthPoint(BaseModel):
    point: str
    evidence: str


class ConcernPoint(BaseModel):
    point: str
    evidence: str


class FixAction(BaseModel):
    action: str
    impact: Literal["high", "medium", "low"]


class SeniorVerdict(BaseModel):
    score: int
    one_line_verdict: str
    tier: Literal["tier-zero", "strong", "mid", "weak", "red-flag"]
    strengths: list[StrengthPoint]
    concerns: list[ConcernPoint]
    fixes: list[FixAction]


def _make_llm(temperature: float = 0.0):
    from apps.api.tools.llm import make_llm
    return make_llm(temperature=temperature)



_SYSTEM_PROMPT = """You are a staff engineer writing a verdict on a GitHub profile.

Three agents gathered evidence: Forensics (originality), Depth (technical depth), Claims (bio vs code).
Your job: SYNTHESIZE a sharp, specific verdict.

RULES:
1. Every strength and concern must cite specific evidence from agent outputs. Never produce vague praise.
2. Be honest about thin profiles.
3. Tiers are calibrated: tier-zero=90-100, strong=75-89, mid=55-74, weak=30-54, red-flag=0-29.
4. Fixes must be actionable and specific.

Output ONLY the structured schema."""


_FIRST_PASS_USER = """Synthesize a verdict from these agent findings.

## Forensics
{forensics}

## Depth
{depth}

## Claims
{claims}

Produce the SeniorVerdict now."""


_REVISION_USER = """The Critic challenged your previous verdict. Revise it, addressing each challenge.

## Previous verdict
{previous_verdict}

## Critic's challenges
{challenges}

## Original findings
### Forensics
{forensics}

### Depth
{depth}

### Claims
{claims}

Produce the revised SeniorVerdict now."""


_first_pass_prompt = ChatPromptTemplate.from_messages(
    [("system", _SYSTEM_PROMPT), ("user", _FIRST_PASS_USER)]
)

_revision_prompt = ChatPromptTemplate.from_messages(
    [("system", _SYSTEM_PROMPT), ("user", _REVISION_USER)]
)


def run_senior_reviewer(
    forensics: ForensicsReport,
    depth: DepthReport,
    claims: ClaimsReport,
) -> SeniorVerdict:
    """First-pass verdict from upstream agent findings."""
    llm = _make_llm().with_structured_output(SeniorVerdict)
    chain = _first_pass_prompt | llm
    result = chain.invoke(
        {
            "forensics": forensics.model_dump_json(indent=2),
            "depth": depth.model_dump_json(indent=2),
            "claims": claims.model_dump_json(indent=2),
        }
    )
    assert isinstance(result, SeniorVerdict)
    return result


def revise_senior_verdict(
    previous: SeniorVerdict,
    challenges: list[str],
    forensics: ForensicsReport,
    depth: DepthReport,
    claims: ClaimsReport,
) -> SeniorVerdict:
    """Revise the verdict based on Critic's challenges."""
    llm = _make_llm().with_structured_output(SeniorVerdict)
    chain = _revision_prompt | llm
    result = chain.invoke(
        {
            "previous_verdict": previous.model_dump_json(indent=2),
            "challenges": "\n".join(f"- {c}" for c in challenges),
            "forensics": forensics.model_dump_json(indent=2),
            "depth": depth.model_dump_json(indent=2),
            "claims": claims.model_dump_json(indent=2),
        }
    )
    assert isinstance(result, SeniorVerdict)
    return result


def run_debate(
    forensics: ForensicsReport,
    depth: DepthReport,
    claims: ClaimsReport,
    max_revisions: int = 2,
) -> tuple[SeniorVerdict, list["CriticResponse"]]:
    """Run the Reviewer + Critic debate loop."""
    from apps.api.agents.critic import run_critic

    verdict = run_senior_reviewer(forensics, depth, claims)
    critic_history: list[CriticResponse] = []

    for _round in range(max_revisions):
        critic_response = run_critic(verdict, forensics, depth, claims)
        critic_history.append(critic_response)
        if critic_response.approve:
            break
        verdict = revise_senior_verdict(
            previous=verdict,
            challenges=critic_response.challenges,
            forensics=forensics,
            depth=depth,
            claims=claims,
        )

    return verdict, critic_history
