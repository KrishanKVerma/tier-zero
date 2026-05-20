"""Tests for Senior Reviewer + Critic + the debate loop."""

from __future__ import annotations

import os

import pytest

from apps.api.agents.claims import ClaimsReport, VerifiedClaim
from apps.api.agents.critic import CriticResponse
from apps.api.agents.depth import (
    DepthReport,
    ProductionMarkers,
    QualityDistribution,
)
from apps.api.agents.forensics import Evidence, ForensicsReport
from apps.api.agents.senior_reviewer import (
    SeniorVerdict,
    run_debate,
    run_senior_reviewer,
)


def _forensics() -> ForensicsReport:
    return ForensicsReport(
        fork_ratio=0.0,
        originality_score=90,
        tutorial_clusters=[],
        streak_farming_flags=[],
        last_meaningful_commit="2026-05-01T00:00:00+00:00",
        evidence=[
            Evidence(finding="Real work in tier-zero repo", source="KrishanKVerma/tier-zero"),
            Evidence(finding="Authored multi-agent system", source="commit fc012ed"),
            Evidence(finding="Sustained commit cadence", source="last 14 days"),
        ],
        summary="Original work, no streak farming.",
    )


def _depth() -> DepthReport:
    return DepthReport(
        language_portfolio={"Python": 95.0, "other": 5.0},
        repo_quality_distribution=QualityDistribution(gold=1, silver=0, bronze=1),
        production_markers_present=ProductionMarkers(
            readme=2, tests=1, ci=1, docker=0, license=1
        ),
        top_real_work_repos=["KrishanKVerma/tier-zero"],
        depth_score=70,
        breadth_vs_depth="depth-focused",
        summary="Focused Python depth with one production-grade repo.",
    )


def _claims() -> ClaimsReport:
    return ClaimsReport(
        claims=[
            VerifiedClaim(
                claim="AI agents",
                verdict="supported",
                confidence="high",
                supporting_repos=["KrishanKVerma/tier-zero"],
                reasoning="Multi-agent system clearly implemented.",
            ),
            VerifiedClaim(
                claim="autonomous systems",
                verdict="unsupported",
                confidence="medium",
                supporting_repos=[],
                reasoning="No autonomous agent code found.",
            ),
        ],
        overall_alignment_score=50,
        bio_credibility="moderate",
        summary="Half the bio is backed; half is aspirational.",
    )


def test_senior_verdict_score_range_enforced() -> None:
    v = SeniorVerdict(
        score=85,
        one_line_verdict="Strong builder.",
        tier="strong",
        strengths=[],
        concerns=[],
        fixes=[],
    )
    assert v.score == 85


def test_critic_response_schema_valid() -> None:
    r = CriticResponse(
        approve=False,
        challenges=["Strength #1 lacks evidence."],
        reasoning="Vague strength claim.",
    )
    assert r.approve is False
    assert len(r.challenges) == 1


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("SKIP_LIVE_TESTS") == "1",
    reason="Live LLM test needs GROQ_API_KEY",
)
def test_run_senior_reviewer_returns_valid_verdict() -> None:
    verdict = run_senior_reviewer(_forensics(), _depth(), _claims())
    assert isinstance(verdict, SeniorVerdict)
    assert 0 <= verdict.score <= 100
    assert verdict.tier in {"tier-zero", "strong", "mid", "weak", "red-flag"}
    assert verdict.one_line_verdict.strip() != ""


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("SKIP_LIVE_TESTS") == "1",
    reason="Live LLM test needs GROQ_API_KEY",
)
def test_run_debate_returns_verdict_and_history() -> None:
    verdict, history = run_debate(_forensics(), _depth(), _claims(), max_revisions=1)
    assert isinstance(verdict, SeniorVerdict)
    assert len(history) >= 1
    assert len(history) <= 1
