"""tier-zero HTTP API.

Endpoints:
- POST /api/report          → queue a report, return report_id
- GET  /api/report/{id}     → status + result when ready
- GET  /healthz             → liveness probe

For v1 we use in-memory storage. Production (Day 19/20) swaps to Redis.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException , Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from apps.api.graph import run as run_tier_zero

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import os

load_dotenv()
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger("tier_zero")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


_BLOCKLIST_PATH = Path(__file__).parent / "blocklist.json"


def _load_blocklist() -> set[str]:
    """Load the blocklist fresh each call so admin changes don't need a restart."""
    try:
        data = json.loads(_BLOCKLIST_PATH.read_text())
        return {u.lower() for u in data.get("usernames", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _verify_github_user(token: str) -> str:
    """Call GitHub's /user endpoint with the user's OAuth token.

    Returns the authenticated GitHub username.
    Raises HTTPException on any auth failure.
    """
    try:
        response = httpx.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"GitHub verification failed: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired GitHub token.",
        )

    data = response.json()
    login = data.get("login")
    if not login:
        raise HTTPException(status_code=500, detail="GitHub returned no username.")
    return login


app = FastAPI(
    title="tier-zero",
    description="Tier-zero engineering review for any GitHub profile.",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: allow only known frontend origins.
_allowed_origins = [
    "http://localhost:3000",
]
# Production frontend (set this env var when you deploy to Vercel).
_prod_origin = os.getenv("FRONTEND_ORIGIN")
if _prod_origin:
    _allowed_origins.append(_prod_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------- In-memory storage ----------

# report_id -> ReportRecord
_reports: dict[str, dict[str, Any]] = {}


# ---------- Request / response schemas ----------


class ReportRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    mode: Literal["profile"] = "profile"
    github_token: str = Field(min_length=1, description="GitHub OAuth access token for the requesting user.")


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
@limiter.limit("5/hour;50/day")
def create_report(request: Request, req: ReportRequest, background: BackgroundTasks) -> ReportQueued:
    """Queue a tier-zero report. Returns immediately with a polling URL."""
    if req.username.lower() in _load_blocklist():
        raise HTTPException(
            status_code=403,
            detail=f"User '{req.username}' has requested exclusion from tier-zero analysis.",
        )

    # Verify the OAuth token and enforce self-audit.
    authenticated_user = _verify_github_user(req.github_token)
    if authenticated_user.lower() != req.username.lower():
        raise HTTPException(
            status_code=403,
            detail=(
                f"Self-audit only: you can only audit your own profile "
                f"(@{authenticated_user}). Requested @{req.username}."
            ),
        )

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