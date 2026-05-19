"""Tests for the Forensics Agent.

Strategy:
- Unit-test the formatters (fast, no LLM calls).
- One integration test for the full agent, marked `live` so CI can skip it.
"""

from __future__ import annotations

import os

import pytest

from apps.api.agents.forensics import (
    ForensicsReport,
    _format_commits,
    _format_profile,
    _format_repos,
    run_forensics,
)
from apps.api.tools.github_client import ProfileSnapshot, RepoSnapshot


# ---------- Formatter unit tests (fast) ----------


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


def _sample_repo(name: str, is_fork: bool = False) -> RepoSnapshot:
    return RepoSnapshot(
        name=name,
        full_name=f"testuser/{name}",
        description="A test repo",
        is_fork=is_fork,
        is_archived=False,
        primary_language="Python",
        stars=0,
        forks=0,
        open_issues=0,
        size_kb=100,
        created_at="2025-01-01T00:00:00+00:00",
        last_pushed_at="2026-05-01T00:00:00+00:00",
        default_branch="main",
        topics=[],
    )


def test_format_profile_contains_username_and_bio() -> None:
    text = _format_profile(_sample_profile())
    assert "testuser" in text
    assert "Builds things" in text


def test_format_repos_marks_forks() -> None:
    repos = [_sample_repo("real-repo"), _sample_repo("forked-repo", is_fork=True)]
    text = _format_repos(repos)
    assert "real-repo" in text
    assert "forked-repo" in text
    assert "FORK" in text


def test_format_repos_handles_empty() -> None:
    text = _format_repos([])
    assert "no repos" in text


def test_format_commits_handles_empty() -> None:
    text = _format_commits({})
    assert "no commit samples" in text


def test_format_commits_renders_entries() -> None:
    commits = {
        "testuser/real-repo": [
            {
                "sha": "abc1234",
                "message_first_line": "Initial commit",
                "message_length": 14,
                "author": "Test User",
                "authored_at": "2026-05-01T12:00:00+00:00",
                "additions": 42,
                "deletions": 0,
                "files_changed": 3,
            }
        ]
    }
    text = _format_commits(commits)
    assert "abc1234" in text
    assert "Initial commit" in text
    assert "+42" in text


# ---------- Integration test (slow, calls Groq) ----------


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("SKIP_LIVE_TESTS") == "1",
    reason="Live LLM test — needs GROQ_API_KEY, skipped via SKIP_LIVE_TESTS=1",
)
def test_run_forensics_returns_valid_report() -> None:
    report = run_forensics("torvalds")
    assert isinstance(report, ForensicsReport)
    assert 0 <= report.originality_score <= 100
    assert 0.0 <= report.fork_ratio <= 1.0
    assert len(report.evidence) >= 1
    assert report.summary.strip() != ""