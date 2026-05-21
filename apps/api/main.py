"""tier-zero HTTP API.

Endpoints:
- POST /api/report          → queue a report, return report_id
- GET  /api/report/{id}     → status + result when ready
- GET  /healthz             → liveness probe

For v1 we use in-memory storage. Production (Day 19/20) swaps to Redis.
"""

from __future__ import annotations

import logging
import time
import traceback
import uuid
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from apps.api.graph import run as run_tier_zero

load_dotenv()

logger = logging.getLogger("tier_zero")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title="tier-zero",
    description="Tier-zero engineering review for any GitHub profile.",
    version="0.1.0",
)

# CORS — frontend (Day 17-18) will live on a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v1 dev: open. Day 20: lock to your prod frontend URL.
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------- In-memory storage ----------

# report_id -> ReportRecord
_reports: dict[str, dict[str, Any]] = {}


# ---------- Request / response schemas ----------


class ReportRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    mode: Literal["profile"] = "profile"  # "repo" mode comes later


class ReportQueued(BaseModel):
    report_id: str
    status: Literal["queued"]
    status_url: str


class ReportStatus(BaseModel):
    report_id: str
    status: Literal["queued", "running", "complete", "error"]
    current_stage: str | None = None
    elapsed_seconds: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


# ---------- Background worker ----------


def _worker(report_id: str, username: str) -> None:
    """Run tier-zero on a username. Updates the in-memory store as it progresses."""
    started = time.time()
    _reports[report_id].update(status="running", current_stage="fetch_evidence")
    logger.info(f"[{report_id}] starting tier-zero for {username}")

    try:
        state = run_tier_zero(username)
        verdict = state["verdict"]

        _reports[report_id].update(
            status="complete",
            elapsed_seconds=round(time.time() - started, 2),
            current_stage=None,
            result={
                "verdict": verdict.model_dump(),
                "forensics": state["forensics"].model_dump(),
                "depth": state["depth"].model_dump(),
                "claims": state["claims"].model_dump(),
                "critic_rounds": len(state.get("critic_history", [])),
                "revisions": state.get("revision_round", 0),
            },
        )
        logger.info(
            f"[{report_id}] complete in {_reports[report_id]['elapsed_seconds']}s, "
            f"tier={verdict.tier}, score={verdict.score}"
        )
    except Exception as exc:  # noqa: BLE001
        _reports[report_id].update(
            status="error",
            elapsed_seconds=round(time.time() - started, 2),
            error=f"{type(exc).__name__}: {exc}",
        )
        logger.error(f"[{report_id}] failed: {exc}\n{traceback.format_exc()}")


# ---------- Endpoints ----------


@app.post("/api/report", response_model=ReportQueued, status_code=202)
def create_report(req: ReportRequest, background: BackgroundTasks) -> ReportQueued:
    """Queue a tier-zero report. Returns immediately with a polling URL."""
    report_id = f"rpt_{uuid.uuid4().hex[:10]}"
    _reports[report_id] = {
        "report_id": report_id,
        "username": req.username,
        "status": "queued",
        "current_stage": None,
        "elapsed_seconds": None,
        "result": None,
        "error": None,
    }
    background.add_task(_worker, report_id, req.username)
    return ReportQueued(
        report_id=report_id,
        status="queued",
        status_url=f"/api/report/{report_id}",
    )


@app.get("/api/report/{report_id}", response_model=ReportStatus)
def get_report(report_id: str) -> ReportStatus:
    """Get status + final result for a report."""
    record = _reports.get(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"report not found: {report_id}")
    return ReportStatus(**record)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "tier-zero",
        "description": "Tier-zero engineering review for any GitHub profile.",
        "docs": "/docs",
        "health": "/healthz",
    }
