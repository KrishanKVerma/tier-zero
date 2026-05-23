"""tier-zero orchestration graph (LangGraph).

Wires all 5 agents into a stateful graph:
  fetch_evidence (parallel: Forensics + Depth + Claims)
       ↓
  senior_reviewer (first-pass verdict)
       ↓
  critic (challenges or approves)
       ↓
  revise (if challenged, max 2 rounds) → back to critic
       ↓
  END
"""

from __future__ import annotations

import concurrent.futures
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from apps.api.agents.claims import ClaimsReport, run_claims
from apps.api.agents.critic import CriticResponse, run_critic
from apps.api.agents.depth import DepthReport, run_depth
from apps.api.agents.forensics import ForensicsReport, run_forensics
from apps.api.agents.senior_reviewer import (
    SeniorVerdict,
    revise_senior_verdict,
    run_senior_reviewer,
)


# ---------- Graph state ----------


MAX_REVISION_ROUNDS = 2


def _append(left: list, right: list) -> list:
    """Reducer for list fields — appends new items rather than replacing."""
    return left + right


class TierZeroState(TypedDict, total=False):
    """State that flows through the graph.

    `total=False` means all fields are optional at graph start.
    Each node fills in what it produces.
    """

    username: str
    forensics: ForensicsReport
    depth: DepthReport
    claims: ClaimsReport
    verdict: SeniorVerdict
    critic_history: Annotated[list[CriticResponse], _append]
    revision_round: int


# ---------- Nodes ----------


def _fetch_evidence(state: TierZeroState) -> dict:
    """Run Forensics, Depth, and Claims in parallel."""
    username = state["username"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        forensics_future = pool.submit(run_forensics, username)
        depth_future = pool.submit(run_depth, username)
        claims_future = pool.submit(run_claims, username)

        return {
            "forensics": forensics_future.result(),
            "depth": depth_future.result(),
            "claims": claims_future.result(),
            "revision_round": 0,
        }


def _senior_reviewer(state: TierZeroState) -> dict:
    verdict = run_senior_reviewer(
        forensics=state["forensics"],
        depth=state["depth"],
        claims=state["claims"],
    )
    return {"verdict": verdict}


def _critic(state: TierZeroState) -> dict:
    response = run_critic(
        verdict=state["verdict"],
        forensics=state["forensics"],
        depth=state["depth"],
        claims=state["claims"],
    )
    return {"critic_history": [response]}


def _revise(state: TierZeroState) -> dict:
    last_critic = state["critic_history"][-1]
    new_verdict = revise_senior_verdict(
        previous=state["verdict"],
        challenges=last_critic.challenges,
        forensics=state["forensics"],
        depth=state["depth"],
        claims=state["claims"],
    )
    return {
        "verdict": new_verdict,
        "revision_round": state.get("revision_round", 0) + 1,
    }


# ---------- Conditional edge ----------


def _after_critic(state: TierZeroState) -> str:
    """Decide what to do after the Critic runs."""
    last_critic = state["critic_history"][-1]
    if last_critic.approve:
        return "end"
    if state.get("revision_round", 0) >= MAX_REVISION_ROUNDS:
        return "end"
    return "revise"


# ---------- Graph compilation ----------


def build_graph() -> StateGraph:
    """Construct the tier-zero graph. Compile and return."""
    g = StateGraph(TierZeroState)

    g.add_node("fetch_evidence", _fetch_evidence)
    g.add_node("senior_reviewer", _senior_reviewer)
    g.add_node("critic", _critic)
    g.add_node("revise", _revise)

    g.add_edge(START, "fetch_evidence")
    g.add_edge("fetch_evidence", "senior_reviewer")
    g.add_edge("senior_reviewer", "critic")

    g.add_conditional_edges(
        "critic",
        _after_critic,
        {
            "end": END,
            "revise": "revise",
        },
    )
    g.add_edge("revise", "critic")

    return g.compile()


# ---------- Public entry point ----------

def _langfuse_callbacks() -> list:
    """Return a Langfuse callback handler if keys are set, else empty list.

    Observability is optional — the pipeline runs fine without it.
    """
    import os

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler()]
    except Exception:  # noqa: BLE001 — observability must never break the pipeline
        return []


def run(username: str) -> dict:
    """Run the full tier-zero pipeline on a GitHub username.

    Returns the final state dict containing all intermediate findings + verdict.
    """
    graph = build_graph()
    config = {"callbacks": _langfuse_callbacks(), "metadata": {"username": username}}
    final_state = graph.invoke({"username": username}, config=config)
    return final_state