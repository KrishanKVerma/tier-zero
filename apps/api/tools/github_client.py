"""GitHub data fetching tool layer.

Agents call these functions. All HTTP, auth, and error handling lives here.
Every public function degrades gracefully on empty/weird/missing data rather
than crashing — see the edge-case notes inline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from github import Auth, Github, GithubException
from github.NamedUser import NamedUser
from github.Repository import Repository

load_dotenv()


_client_instance: Github | None = None


def _get_client() -> Github:
    """Lazy client init — only fails when actually called, not on import."""
    global _client_instance
    if _client_instance is not None:
        return _client_instance
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN not set. Add it to .env (see .env.example)."
        )
    _client_instance = Github(auth=Auth.Token(token), per_page=100)
    return _client_instance


# ---------- Data shapes ----------


@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    username: str
    name: str | None
    bio: str | None
    company: str | None
    location: str | None
    blog: str | None
    email: str | None
    public_repos: int
    public_gists: int
    followers: int
    following: int
    account_created_at: str
    last_updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepoSnapshot:
    name: str
    full_name: str
    description: str | None
    is_fork: bool
    is_archived: bool
    primary_language: str | None
    stars: int
    forks: int
    open_issues: int
    size_kb: int
    created_at: str
    last_pushed_at: str
    default_branch: str
    topics: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------- Public functions ----------


def get_profile(username: str) -> ProfileSnapshot:
    """Fetch a user's public profile."""
    try:
        user: NamedUser = _get_client().get_user(username)
        return ProfileSnapshot(
            username=user.login,
            name=user.name,
            bio=user.bio,
            company=user.company,
            location=user.location,
            blog=user.blog,
            email=user.email,
            public_repos=user.public_repos or 0,
            public_gists=user.public_gists or 0,
            followers=user.followers or 0,
            following=user.following or 0,
            account_created_at=_iso(user.created_at),
            last_updated_at=_iso(user.updated_at),
        )
    except GithubException as exc:
        raise _wrap_error(exc, f"Failed to fetch profile for '{username}'") from exc


def get_repos(username: str, limit: int = 50) -> list[RepoSnapshot]:
    """Fetch up to `limit` public repos for a user, sorted by most recently pushed.

    Returns [] if the user has no repos. Skips any single repo that errors
    rather than failing the whole fetch.
    """
    try:
        user = _get_client().get_user(username)
        repos = user.get_repos(sort="pushed", direction="desc")
    except GithubException as exc:
        raise _wrap_error(exc, f"Failed to fetch repos for '{username}'") from exc

    out: list[RepoSnapshot] = []
    try:
        for repo in repos:
            if len(out) >= limit:
                break
            try:
                out.append(_to_repo_snapshot(repo))
            except GithubException:
                # One bad repo shouldn't sink the whole list.
                continue
    except GithubException:
        # Lazy pagination can throw mid-iteration on weird accounts; return what we have.
        pass
    return out


def get_repo_details(full_name: str) -> dict[str, Any]:
    """Fetch deeper details for a single repo: README text, file tree, commit count.

    Degrades gracefully: missing README/tree/commits return empty, never crash.
    """
    try:
        repo = _get_client().get_repo(full_name)
    except GithubException as exc:
        raise _wrap_error(exc, f"Failed to fetch repo '{full_name}'") from exc

    try:
        snapshot = _to_repo_snapshot(repo).to_dict()
    except GithubException:
        snapshot = {"full_name": full_name}

    return {
        "snapshot": snapshot,
        "readme": _safe_readme(repo),
        "tree": _shallow_tree(repo),
        "commit_count": _commit_count(repo),
    }


def get_recent_commits(full_name: str, limit: int = 30) -> list[dict[str, Any]]:
    """Fetch the most recent commits on a repo's default branch.

    Returns [] for empty repos (GitHub 409) or any commit-fetch failure.
    """
    try:
        repo = _get_client().get_repo(full_name)
        commits = repo.get_commits()
    except GithubException as exc:
        # 409 = empty repo (no commits). Treat as "no commits" rather than failing.
        if exc.status == 409:
            return []
        raise _wrap_error(exc, f"Failed to fetch commits for '{full_name}'") from exc

    out: list[dict[str, Any]] = []
    try:
        for commit in commits:
            if len(out) >= limit:
                break
            message = commit.commit.message or "" if commit.commit else ""
            out.append(
                {
                    "sha": commit.sha[:7] if commit.sha else "",
                    "message_first_line": message.split("\n", 1)[0][:200],
                    "message_length": len(message),
                    "author": (
                        commit.commit.author.name
                        if commit.commit and commit.commit.author
                        else None
                    ),
                    "authored_at": (
                        _iso(commit.commit.author.date)
                        if commit.commit and commit.commit.author
                        else ""
                    ),
                    "additions": commit.stats.additions if commit.stats else 0,
                    "deletions": commit.stats.deletions if commit.stats else 0,
                    "files_changed": commit.files.totalCount if commit.files else 0,
                }
            )
    except GithubException:
        # Empty repo / mid-iteration failure — return whatever we gathered.
        pass
    return out


def rate_limit_remaining() -> int:
    """How many GitHub API calls we have left this hour."""
    rl = _get_client().get_rate_limit()
    # PyGithub >=2.x exposes .resources.core; older versions exposed .core directly.
    core = getattr(rl, "core", None) or rl.resources.core
    return core.remaining


# ---------- Internals ----------


def _to_repo_snapshot(repo: Repository) -> RepoSnapshot:
    # get_topics() is a network call that can fail; guard it.
    try:
        topics = list(repo.get_topics())
    except GithubException:
        topics = []
    return RepoSnapshot(
        name=repo.name,
        full_name=repo.full_name,
        description=repo.description,
        is_fork=bool(repo.fork),
        is_archived=bool(repo.archived),
        primary_language=repo.language,
        stars=repo.stargazers_count or 0,
        forks=repo.forks_count or 0,
        open_issues=repo.open_issues_count or 0,
        size_kb=repo.size or 0,
        created_at=_iso(repo.created_at),
        last_pushed_at=_iso(repo.pushed_at),
        default_branch=repo.default_branch or "main",
        topics=topics,
    )


def _safe_readme(repo: Repository) -> str | None:
    try:
        content = repo.get_readme().decoded_content
        return content.decode("utf-8", errors="replace")
    except GithubException:
        return None


def _shallow_tree(repo: Repository, max_entries: int = 200) -> list[str]:
    """Return top-level + one-level-deep file paths for quick repo shape sensing."""
    try:
        root = _get_client().get_repo(repo.full_name).get_contents("")
    except GithubException:
        return []

    if not isinstance(root, list):
        root = [root]

    paths: list[str] = []
    for item in root:
        paths.append(item.path)
        if item.type == "dir" and len(paths) < max_entries:
            try:
                children = repo.get_contents(item.path)
                if isinstance(children, list):
                    child_count = 0
                    for child in children:
                        if child_count >= 20:
                            break
                        paths.append(child.path)
                        child_count += 1
            except GithubException:
                continue
        if len(paths) >= max_entries:
            break
    return paths


def _commit_count(repo: Repository) -> int:
    try:
        return repo.get_commits().totalCount
    except GithubException:
        return 0


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _wrap_error(exc: GithubException, context: str) -> RuntimeError:
    return RuntimeError(f"{context}: status={exc.status} data={exc.data}")