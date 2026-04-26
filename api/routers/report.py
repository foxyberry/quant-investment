"""
Portfolio Daily Report Router.

Endpoints:
  POST /api/portfolio/report/generate            — SSE stream: generate a new report
  POST /api/portfolio/report/generate-background — fire-and-forget generation
  GET  /api/portfolio/report/status              — is_generating bool
  GET  /api/portfolio/report/                    — list recent reports (summary)
  GET  /api/portfolio/report/latest              — latest report detail
  GET  /api/portfolio/report/{id}                — specific report detail
  POST /api/portfolio/report/{id}/slack          — dispatch report to Slack

NOTE: All literal-string GET routes (/status, /latest) MUST be registered before
the wildcard /{report_id} route to avoid FastAPI coercing "status"/"latest" as int
and returning 422 Unprocessable Entity.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/portfolio/report", tags=["report"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────


class ReportSummary(BaseModel):
    id: int
    generated_at: datetime
    trigger: str
    duration_sec: Optional[float]
    content_preview: str  # content[:200]

    class Config:
        from_attributes = True


class ReportDetail(ReportSummary):
    content: str


# ── Guard helper ───────────────────────────────────────────────────────────────


def _require_api_key() -> None:
    """Raise 503 if ANTHROPIC_API_KEY is not available."""
    try:
        from api.config import get_settings
        key = get_settings().anthropic_api_key
    except Exception:
        key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured. Report generation is unavailable.",
        )


# ── Literal-string routes (must precede wildcard /{report_id}) ────────────────


@router.post("/generate", summary="Generate a new daily portfolio report (SSE stream)")
async def generate_report() -> StreamingResponse:
    """
    Start generating a daily portfolio report.

    Returns a Server-Sent Events stream. Each event is a JSON payload:
    - {"type": "text", "content": "..."}
    - {"type": "tool_start", "name": "...", "input": {...}}
    - {"type": "tool_end", "name": "..."}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    _require_api_key()

    from api.services.report_service import stream_report

    return StreamingResponse(
        stream_report("manual"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-background", summary="Start background report generation (fire-and-forget)")
def generate_background() -> dict:
    """
    Start report generation in a background thread and return immediately.
    Use GET /status to poll whether generation is in progress.
    """
    _require_api_key()
    from api.services.report_service import start_background_report

    started = start_background_report("manual")
    return {"started": started, "already_running": not started}


@router.get("/status", summary="Get generation status")
def get_status() -> dict:
    """Return whether a report is currently being generated."""
    from api.services.report_service import get_generation_status

    return {"is_generating": get_generation_status()}


@router.get("/", response_model=List[ReportSummary], summary="List recent reports")
def list_reports(limit: int = Query(30, ge=1, le=100)) -> List[ReportSummary]:
    """Return the most recent reports (summary only, content truncated to 200 chars)."""
    from api.services.report_service import list_reports as _list

    rows = _list(limit=limit)
    return [ReportSummary(**r) for r in rows]


@router.get("/latest", response_model=ReportDetail, summary="Get the latest report")
def get_latest_report() -> ReportDetail:
    """Return the most recently generated report in full detail."""
    from api.services.report_service import get_latest_report as _get_latest

    report = _get_latest()
    if not report:
        raise HTTPException(status_code=404, detail="No reports found.")
    return ReportDetail(**report)


# ── Wildcard route (must be last among GET routes) ────────────────────────────


@router.get("/{report_id}", response_model=ReportDetail, summary="Get a specific report")
def get_report(report_id: int) -> ReportDetail:
    """Return full detail for a specific report by id."""
    from api.services.report_service import get_report as _get

    report = _get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
    return ReportDetail(**report)


@router.post("/{report_id}/slack", summary="Send a report to Slack")
def send_to_slack(report_id: int) -> dict:
    """Dispatch the specified report's content to the configured Slack webhook."""
    from api.services.report_service import get_report as _get, send_report_to_slack

    report = _get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")

    success = send_report_to_slack(report_id)
    return {"success": success}
