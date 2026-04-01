"""Reports router — PDF export and shareable HTML endpoints.

Endpoints:
    GET /api/reports/{run_id}/pdf  — Download polished PDF of completed run
    GET /share/{run_id}            — Public shareable HTML (no auth required)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import markdown as _md
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session

from api.database import get_session
from api.models import Run
from api.report_helpers import build_envelope_from_db
from protocols.protocol_report import from_envelope

router = APIRouter(tags=["reports"])

_template_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=True)

# Markdown converter with table and code support
_md_extensions = ["tables", "fenced_code", "nl2br"]


def _md_render(text: str) -> str:
    """Convert markdown text to HTML."""
    if not text:
        return ""
    return _md.markdown(text, extensions=_md_extensions)


def _prepare_report_for_template(report_dict: dict[str, Any]) -> dict[str, Any]:
    """Convert markdown fields to rendered HTML for the template."""
    d = dict(report_dict)

    # Render main text fields
    d["synthesis_html"] = _md_render(d.get("synthesis", ""))
    d["executive_summary_html"] = _md_render(d.get("executive_summary", ""))

    # Render each agent contribution's text
    if d.get("agent_contributions"):
        for contrib in d["agent_contributions"]:
            contrib["text_html"] = _md_render(contrib.get("text", ""))

    return d


def _load_report(run_id: int, session: Session):
    run = session.get(Run, run_id)
    if not run or run.status != "completed":
        raise HTTPException(status_code=404, detail="Completed run not found")
    envelope = build_envelope_from_db(run, session)
    verdict = json.loads(run.judge_verdict_json) if run.judge_verdict_json and run.judge_verdict_json != "{}" else None
    report = from_envelope(envelope, verdict)
    return _prepare_report_for_template(report.as_dict())


def _render_report_html(report: dict[str, Any]) -> str:
    return _jinja_env.get_template("report.html.j2").render(report=report)


@router.get("/api/reports/{run_id}/pdf")
async def get_run_pdf(run_id: int, session: Session = Depends(get_session)) -> Response:
    report = _load_report(run_id, session)
    html = _render_report_html(report)
    try:
        import weasyprint
        pdf_bytes = await asyncio.to_thread(weasyprint.HTML(string=html).write_pdf)
    except ImportError:
        raise HTTPException(status_code=501, detail="WeasyPrint not installed")
    except OSError as e:
        raise HTTPException(status_code=501, detail=f"WeasyPrint system deps missing: {e}")
    protocol_key = report.get("metadata", {}).get("protocol_key", "report") or "report"
    filename = f"ce-report-{protocol_key}-{run_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/share/{run_id}")
def share_run(run_id: int, session: Session = Depends(get_session)) -> HTMLResponse:
    report = _load_report(run_id, session)
    html = _render_report_html(report)
    return HTMLResponse(content=html)
