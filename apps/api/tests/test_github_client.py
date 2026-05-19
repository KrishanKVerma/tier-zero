"""Tests for the GitHub client tool layer.

These hit the real GitHub API using a stable public account, so they require
GITHUB_TOKEN to be set. Marked as `live` so CI can opt out if needed.
"""

from __future__ import annotations

import pytest

from apps.api.tools.github_client import (
    ProfileSnapshot,
    RepoSnapshot,
    get_profile,
    get_repos,
    get_repo_details,
    rate_limit_remaining,
)

# A stable, well-known GitHub account used as a fixture. Torvalds will not
# delete his account or rename it. Safe to depend on.
STABLE_USER = "torvalds"
STABLE_REPO = "torvalds/linux"


# ---------- get_profile ----------


def test_get_profile_returns_snapshot() -> None:
    profile = get_profile(STABLE_USER)
    assert isinstance(profile, ProfileSnapshot)
    assert profile.username == STABLE_USER
    assert profile.followers > 0
    assert profile.public_repos > 0
    assert profile.account_created_at != ""


def test_get_profile_unknown_user_raises() -> None:
    with pytest.raises(RuntimeError, match="Failed to fetch profile"):
        get_profile("this-user-should-not-exist-9q8w7e6r5t")


# ---------- get_repos ----------


def test_get_repos_returns_list_of_snapshots() -> None:
    repos = get_repos(STABLE_USER, limit=5)
    assert len(repos) > 0
    assert len(repos) <= 5
    assert all(isinstance(r, RepoSnapshot) for r in repos)


def test_get_repos_respects_limit() -> None:
    repos = get_repos(STABLE_USER, limit=3)
    assert len(repos) <= 3


def test_get_repos_unknown_user_raises() -> None:
    with pytest.raises(RuntimeError, match="Failed to fetch repos"):
        get_repos("this-user-should-not-exist-9q8w7e6r5t")


# ---------- get_repo_details ----------


def test_get_repo_details_returns_full_shape() -> None:
    details = get_repo_details(STABLE_REPO)
    assert "snapshot" in details
    assert "readme" in details
    assert "tree" in details
    assert "commit_count" in details
    assert details["snapshot"]["full_name"] == STABLE_REPO
    assert isinstance(details["tree"], list)


# ---------- rate_limit_remaining ----------


def test_rate_limit_remaining_returns_int() -> None:
    remaining = rate_limit_remaining()
    assert isinstance(remaining, int)
    assert remaining >= 0


def test_get_recent_commits_returns_dicts() -> None:
    from apps.api.tools.github_client import get_recent_commits

    commits = get_recent_commits(STABLE_REPO , limit = 5)
    assert len(commits) > 0
    assert len(commits) <= 5
    first = commits[0]
    assert "sha" in first
    assert "message_first_line" in first
    assert "authored_at" in first
    assert isinstance(first["additions"], int)