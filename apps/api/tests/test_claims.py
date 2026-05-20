"""Tests for the Claims Agent."""

from __future__ import annotations

import os

import pytest

from apps.api.agents.claims import (
    ClaimsReport,
    ExtractedClaim,
    _format_claims_for_verification,
    _format_repo_details,
    _format_repos_overview,
    run_claims,
)
from apps.api.tools.github_client import RepoSnapshot


# ---------- Factories ----------


def _sample_repo(
    name: str,
    is_fork: bool = False,
    language: str | None = "Python",
) -> RepoSnapshot:
    return RepoSnapshot(
        name=name,
        full_name=f"testuser/{name}",
        description="A test repo",
        is_fork=is_fork,
        is_archived=False,
        primary_language=language,
        stars=0,
        forks=0,
        open_issues=0,
        size_kb=100,
        created_at="2025-01-01T00:00:00+00:00",
        last_pushed_at="2026-05-01T00:00:00+00:00",
        default_branch="main",
        topics=[],
    )


# ---------- Formatter unit tests (fast) ----------


def test_format_claims_handles_empty() -> None:
    text = _format_claims_for_verification([])
    assert "no claims extracted" in text


def test_format_claims_renders_entries() -> None:
    claims = [
        ExtractedClaim(claim="RAG", source_text="building RAG systems"),
        ExtractedClaim(claim="LangGraph", source_text="LangGraph orchestration"),
    ]
    text = _format_claims_for_verification(claims)
    assert "RAG" in text
    assert "LangGraph" in text
    assert "building RAG systems" in text


def test_format_repos_overview_filters_forks() -> None:
    repos = [
        _sample_repo("real-one"),
        _sample_repo("a-fork", is_fork=True),
    ]
    text = _format_repos_overview(repos)
    assert "real-one" in text
    assert "a-fork" not in text


def test_format_repos_overview_handles_empty() -> None:
    text = _format_repos_overview([_sample_repo("only-fork", is_fork=True)])
    assert "no non-fork repos" in text


def test_format_repo_details_handles_empty() -> None:
    text = _format_repo_details([])
    assert "no repo details available" in text


def test_format_repo_details_truncates_long_readme() -> None:
    long_readme = "x" * 5000
    details = [
        {
            "snapshot": {
                "full_name": "testuser/big-readme",
                "size_kb": 100,
                "primary_language": "Python",
            },
            "readme": long_readme,
            "tree": [],
            "commit_count": 1,
        }
    ]
    text = _format_repo_details(details)
    assert "..." in text
    assert len(text) < 3500


# ---------- Integration test (slow, calls Groq) ----------


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("SKIP_LIVE_TESTS") == "1",
    reason="Live LLM test — needs GROQ_API_KEY, skipped via SKIP_LIVE_TESTS=1",
)
def test_run_claims_returns_valid_report() -> None:
    report = run_claims("KrishanKVerma")
    assert isinstance(report, ClaimsReport)
    assert 0 <= report.overall_alignment_score <= 100
    assert report.bio_credibility in {"high", "moderate", "low", "no_claims_to_check"}
    assert report.summary.strip() != ""