"""Critic Agent — adversarially reviews the Senior Reviewer's verdict.

Pushes back on vague claims, unsupported assertions, and shallow takes.
Returns either approval, or specific challenges sent back for revision.

The debate loop caps at 2 revision rounds to prevent infinite arguments.
"""

from __future__ import annotations


from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from apps.api.agents.claims import ClaimsReport
from apps.api.agents.depth import DepthReport
from apps.api.agents.forensics import ForensicsReport
from apps.api.agents.senior_reviewer import SeniorVerdict

load_dotenv()


# ---------- Output schema ----------


class CriticResponse(BaseModel):
    approve: bool = Field(
        description="True if the verdict is sharp and well-supported. "
        "False if specific challenges need addressing."
    )
    challenges: list[str] = Field(
        description="Specific, actionable challenges to the verdict. Empty list if approve=True. "
        "Each challenge must reference what to fix, not just say 'weak'."
    )
    reasoning: str = Field(
        description="One paragraph: why the verdict needs revision, or why it's solid as-is."
    )


# ---------- LLM setup ----------


def _make_llm(temperature: float = 0.0):
    from apps.api.tools.llm import make_llm
    return make_llm(temperature=temperature)



# ---------- Prompt ----------


_SYSTEM_PROMPT = """You are an adversarial Critic of a Senior Reviewer's verdict on a GitHub profile.

Your job is to push back. The Reviewer wrote a verdict. You scrutinize it against the underlying evidence and flag weaknesses.

CHALLENGE the verdict if you find ANY of these:
1. A "strength" that doesn't cite specific repos or is just generic praise ("good projects", "active developer")
2. A "concern" not grounded in upstream agent evidence
3. A tier that doesn't match the score range, or doesn't match the evidence strength
4. Missing acknowledgment of a clear red flag in the evidence (unsupported claims, fork ratio issues, tutorial clusters)
5. Vague fixes ("add more tests" without saying which repo or which kind of tests)
6. Overgenerous tier — calling someone 'strong' when only 1-2 small repos exist
7. Overharsh tier — calling someone 'weak' when evidence shows real production work

APPROVE if every strength/concern is specific, evidence-cited, and the tier honestly reflects the data.

DO NOT challenge for stylistic preferences. Only substance issues.

DO NOT propose your own verdict. You only challenge or approve.

Be specific in challenges: "Strength #2 says 'good code quality' — no repo cited. Replace with a named repo + what's good about it."

Output ONLY the structured schema."""


_USER_TEMPLATE = """Critique this verdict against the underlying evidence.

## Senior Reviewer's Verdict
{verdict}

## Underlying evidence

### Forensics findings
{forensics}

### Depth findings
{depth}

### Claims findings
{claims}

Approve or challenge. Be specific."""


_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("user", _USER_TEMPLATE),
    ]
)


# ---------- Public entry point ----------


def run_critic(
    verdict: SeniorVerdict,
    forensics: ForensicsReport,
    depth: DepthReport,
    claims: ClaimsReport,
) -> CriticResponse:
    """Run the Critic against a verdict + the underlying agent evidence."""
    llm = _make_llm().with_structured_output(CriticResponse)
    chain = _prompt | llm
    result = chain.invoke(
        {
            "verdict": verdict.model_dump_json(indent=2),
            "forensics": forensics.model_dump_json(indent=2),
            "depth": depth.model_dump_json(indent=2),
            "claims": claims.model_dump_json(indent=2),
        }
    )
    assert isinstance(result, CriticResponse)
    return result