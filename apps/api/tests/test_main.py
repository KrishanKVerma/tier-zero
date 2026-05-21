"""Tests for the FastAPI app."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import _reports, app


@pytest.fixture(autouse=True)
def _clear_reports():
    """Wipe the in-memory store between tests so they don't leak state."""
    _reports.clear()
    yield
    _reports.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------- Health endpoints ----------


def test_healthz_returns_ok(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root_returns_metadata(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "tier-zero"
    assert "docs" in body


# ---------- Report endpoints ----------


def test_create_report_returns_202_and_id(client: TestClient) -> None:
    with patch("apps.api.main._worker") as mock_worker, \
         patch("apps.api.main._verify_github_user", return_value="torvalds"):
        r = client.post(
            "/api/report",
            json={"username": "torvalds", "github_token": "fake-test-token"},
        )
    assert r.status_code == 202
    body = r.json()
    assert body["report_id"].startswith("rpt_")
    assert body["status"] == "queued"
    assert body["status_url"] == f"/api/report/{body['report_id']}"
    mock_worker.assert_called_once()


def test_create_report_rejects_empty_username(client: TestClient) -> None:
    r = client.post(
        "/api/report",
        json={"username": "", "github_token": "fake-test-token"},
    )
    assert r.status_code == 422


def test_get_report_returns_404_for_unknown_id(client: TestClient) -> None:
    r = client.get("/api/report/rpt_does_not_exist")
    assert r.status_code == 404


def test_get_report_returns_queued_record_immediately(client: TestClient) -> None:
    with patch("apps.api.main._worker"), \
         patch("apps.api.main._verify_github_user", return_value="torvalds"):
        post = client.post(
            "/api/report",
            json={"username": "torvalds", "github_token": "fake-test-token"},
        )
    report_id = post.json()["report_id"]

    get = client.get(f"/api/report/{report_id}")
    assert get.status_code == 200
    body = get.json()
    assert body["report_id"] == report_id
    assert body["status"] == "queued"
    assert body["result"] is None


def test_worker_updates_status_to_complete_on_success(client: TestClient) -> None:
    from apps.api.main import _worker

    rid = "rpt_test123"
    _reports[rid] = {
        "report_id": rid,
        "username": "x",
        "status": "queued",
        "current_stage": None,
        "elapsed_seconds": None,
        "result": None,
        "error": None,
    }

    fake_state = _fake_graph_state()
    with patch("apps.api.main.run_tier_zero", return_value=fake_state):
        _worker(rid, "x")

    assert _reports[rid]["status"] == "complete"
    assert _reports[rid]["result"] is not None
    assert _reports[rid]["result"]["verdict"]["tier"] == "strong"


def test_worker_records_error_on_exception() -> None:
    from apps.api.main import _worker

    rid = "rpt_err"
    _reports[rid] = {
        "report_id": rid,
        "username": "x",
        "status": "queued",
        "current_stage": None,
        "elapsed_seconds": None,
        "result": None,
        "error": None,
    }

    with patch("apps.api.main.run_tier_zero", side_effect=RuntimeError("boom")):
        _worker(rid, "x")

    assert _reports[rid]["status"] == "error"
    assert "boom" in _reports[rid]["error"]


def _fake_graph_state() -> dict:
    from apps.api.agents.claims import ClaimsReport
    from apps.api.agents.depth import (
        DepthReport,
        ProductionMarkers,
        QualityDistribution,
    )
    from apps.api.agents.forensics import Evidence, ForensicsReport
    from apps.api.agents.senior_reviewer import SeniorVerdict

    return {
        "forensics": ForensicsReport(
            fork_ratio=0.0,
            originality_score=90,
            tutorial_clusters=[],
            streak_farming_flags=[],
            last_meaningful_commit="2026-05-01T00:00:00+00:00",
            evidence=[Evidence(finding="real work", source="repo")],
            summary="original.",
        ),
        "depth": DepthReport(
            language_portfolio={"Python": 95.0},
            repo_quality_distribution=QualityDistribution(gold=1, silver=0, bronze=0),
            production_markers_present=ProductionMarkers(
                readme=1, tests=1, ci=1, docker=0, license=1
            ),
            top_real_work_repos=["x/y"],
            depth_score=80,
            breadth_vs_depth="depth-focused",
            summary="focused.",
        ),
        "claims": ClaimsReport(
            claims=[],
            overall_alignment_score=70,
            bio_credibility="moderate",
            summary="ok.",
        ),
        "verdict": SeniorVerdict(
            score=85,
            one_line_verdict="Strong builder.",
            tier="strong",
            strengths=[],
            concerns=[],
            fixes=[],
        ),
        "critic_history": [],
        "revision_round": 0,
    }


_ = time