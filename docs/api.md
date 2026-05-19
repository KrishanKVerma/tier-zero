# API

HTTP interface for tier-zero. Lands fully on Day 16.

---

## Base URL

Local: `http://localhost:8000`

---

## Endpoints

### `POST /api/report`

Generate a report for a GitHub profile.

**Request:**
```json
{
  "username": "some-github-user",
  "mode": "profile"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | yes | GitHub username, no `@` prefix |
| `mode` | enum | no | `profile` (default) or `repo` |

**Response (202 Accepted):**
```json
{
  "report_id": "rpt_a1b2c3",
  "status": "queued",
  "status_url": "/api/report/rpt_a1b2c3"
}
```

Report generation is async. Poll the status URL.

---

### `GET /api/report/{report_id}`

Fetch report status or final result.

**Response — while running (200 OK):**
```json
{
  "report_id": "rpt_a1b2c3",
  "status": "running",
  "current_stage": "depth_agent",
  "progress": 0.4
}
```

**Response — complete (200 OK):**
```json
{
  "report_id": "rpt_a1b2c3",
  "status": "complete",
  "result": {
    "score": 82,
    "one_line_verdict": "Strong builder signal with measurable depth in agent systems.",
    "strengths": [...],
    "concerns": [...],
    "fixes": [...],
    "forensics": {...},
    "depth": {...},
    "claims": {...}
  }
}
```

---

### `GET /healthz`

Liveness probe. Returns `{"status": "ok"}`.

---

## Errors

Standard JSON shape:

```json
{
  "error": {
    "code": "rate_limited",
    "message": "GitHub API rate limit hit. Retry in 540 seconds.",
    "retry_after": 540
  }
}
```

Error codes used: `not_found`, `rate_limited`, `invalid_input`, `internal`.

---

## Rate limits

- Free tier: 10 reports / hour / IP
- Authenticated: 50 reports / hour / user