"""Tests for the tier-zero LangGraph orchestration."""

from __future__ import annotations

import os

import pytest

from apps.api.agents.claims import ClaimsReport
from apps.api.agents.critic import CriticResponse
from apps.api.agents.depth import DepthReport
from apps.api.agents.forensics import ForensicsReport
from apps.api.agents.senior_reviewer import SeniorVerdict
from apps.api.graph import (
    MAX_REVISION_ROUNDS,
    TierZeroState,
    _after_critic,
    build_graph,
    run,
)


def _approving_critic() -> CriticResponse:
    return CriticResponse(approve=True, challenges=[], reasoning="Solid verdict.")


def _challenging_critic() -> CriticResponse:
    return CriticResponse(
        approve=False,
        challenges=["Strength #1 lacks evidence."],
        reasoning="Needs sharper citations.",
    )


def test_after_critic_ends_on_approve() -> None:
    state: TierZeroState = {"critic_history": [_approving_critic()], "revision_round": 0}
    assert _after_critic(state) == "end"


def test_after_critic_revises_when_challenged_under_cap() -> None:
    state: TierZeroState = {"critic_history": [_challenging_critic()], "revision_round": 0}
    assert _after_critic(state) == "revise"


def test_after_critic_ends_when_at_revision_cap() -> None:
    state: TierZeroState = {
        "critic_history": [_challenging_critic()],
        "revision_round": MAX_REVISION_ROUNDS,
    }
    assert _after_critic(state) == "end"


def test_build_graph_compiles() -> None:
    graph = build_graph()
    assert graph is not None


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("SKIP_LIVE_TESTS") == "1",
    reason="Live LLM test needs GROQ_API_KEY",
)
def test_run_produces_full_state() -> None:
    state = run("torvalds")

    assert "verdict" in state
    assert isinstance(state["verdict"], SeniorVerdict)
    assert isinstance(state["forensics"], ForensicsReport)
    assert isinstance(state["depth"], DepthReport)
    assert isinstance(state["claims"], ClaimsReport)
    assert len(state["critic_history"]) >= 1
    assert state.get("revision_round", 0) <= MAX_REVISION_ROUNDS
