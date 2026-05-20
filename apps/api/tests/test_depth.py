"""Tests for the Depth Agent."""

from __future__ import annotations

import os

import pytest

from apps.api.agents.depth import (
    DepthReport,
    _format_profile,
    _format_repo_details,
    _format_repos,
    run_depth,
)
from apps.api.tools.github_client import ProfileSnapshot, RepoSnapshot


# ---------- Factories ----------


def _sample_profile() -> ProfileSnapshot:
    return ProfileSnapshot(
        username="testuser",
        name="Test User",
        bio="Builds things",
        company=None,
        location=None,
        blog=None,
        email=None,
        public_repos=3,
        public_gists=0,
        followers=10,
        following=5,
        account_created_at="2024-01-01T00:00:00+00:00",
        last_updated_at="2026-05-01T00:00:00+00:00",
    )


def _sample_repo(
    name: str,
    is_fork: bool = False,
    is_archived: bool = False,
    size_kb: int = 100,
    language: str | None = "Python",
) -> RepoSnapshot:
    return RepoSnapshot(
        name=name,
        full_name=f"testuser/{name}",
        description="A test repo",
        is_fork=is_fork,
        is_archived=is_archived,
        primary_language=language,
        stars=0,
        forks=0,
        open_issues=0,
        size_kb=size_kb,
        created_at="2025-01-01T00:00:00+00:00",
        last_pushed_at="2026-05-01T00:00:00+00:00",
        default_branch="main",
        topics=[],
    )


# ---------- Formatter unit tests (fast) ----------


def test_format_profile_contains_username() -> None:
    text = _format_profile(_sample_profile())
    assert "testuser" in text
    assert "Public repos: 3" in text


def test_format_repos_excludes_forks_and_archived() -> None:
    repos = [
        _sample_repo("real-repo"),
        _sample_repo("forked-repo", is_fork=True),
        _sample_repo("dead-repo", is_archived=True),
    ]
    text = _format_repos(repos)
    assert "real-repo" in text
    assert "forked-repo" not in text
    assert "dead-repo" not in text


def test_format_repos_handles_all_filtered() -> None:
    repos = [_sample_repo("only-fork", is_fork=True)]
    text = _format_repos(repos)
    assert "no non-fork repos" in text


def test_format_repo_details_handles_empty() -> None:
    text = _format_repo_details([])
    assert "no repo details available" in text


def test_format_repo_details_renders_entry() -> None:
    details = [
        {
            "snapshot": {
                "full_name": "testuser/real-repo",
                "size_kb": 200,
                "primary_language": "Python",
            },
            "readme": "# Real Repo\n\nA real project.",
            "tree": ["README.md", "src/main.py", "tests/test_main.py"],
            "commit_count": 42,
        }
    ]
    text = _format_repo_details(details)
    assert "testuser/real-repo" in text
    assert "Real Repo" in text
    assert "tests/test_main.py" in text


def test_format_repo_details_truncates_long_readme() -> None:
    long_readme = "x" * 5000
    details = [
        {
            "snapshot": {
                "full_name": "testuser/long-readme",
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
    assert len(text) < 3000  # capped, not full 5000


# ---------- Integration test (slow, calls Groq) ----------


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("SKIP_LIVE_TESTS") == "1",
    reason="Live LLM test — needs GROQ_API_KEY, skipped via SKIP_LIVE_TESTS=1",
)
def test_run_depth_returns_valid_report() -> None:
    report = run_depth("torvalds")
    assert isinstance(report, DepthReport)
    assert 0 <= report.depth_score <= 100
    assert report.breadth_vs_depth in {"depth-focused", "balanced", "breadth-focused"}
    assert report.summary.strip() != ""
    assert len(report.language_portfolio) >= 1