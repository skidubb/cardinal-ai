"""Reports router — PDF export and shareable HTML endpoints.

Endpoints:
    GET /api/reports/{run_id}/pdf  — Download polished PDF of completed run
    GET /share/{run_id}            — Public shareable HTML (no auth required)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

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


def _load_report(run_id: int, session: Session):
    """Load run from DB, reconstruct envelope, transform to ProtocolReport.

    Args:
        run_id: ID of the completed run.
        session: Active SQLModel session.

    Returns:
        ProtocolReport instance.

    Raises:
        HTTPException 404: If run not found or not in completed status.
    """
    run = session.get(Run, run_id)
    if not run or run.status != "completed":
        raise HTTPException(status_code=404, detail="Completed run not found")
    envelope = build_envelope_from_db(run, session)
    verdict = json.loads(run.judge_verdict_json) if run.judge_verdict_json and run.judge_verdict_json != "{}" else None
    return from_envelope(envelope, verdict)


@router.get("/api/reports/{run_id}/pdf")
async def get_run_pdf(run_id: int, session: Session = Depends(get_session)) -> Response:
    """Download a polished PDF report for a completed run.

    Returns:
        PDF bytes with content-type application/pdf.
        501 if WeasyPrint or its system dependencies are not installed.
        404 if run not found or not completed.
    """
    report = _load_report(run_id, session)
    html = _jinja_env.get_template("report.html.j2").render(report=report.as_dict())
    try:
        import weasyprint
        pdf_bytes = await asyncio.to_thread(weasyprint.HTML(string=html).write_pdf)
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="WeasyPrint not installed. Run: pip install weasyprint && brew install pango",
        )
    except OSError as e:
        raise HTTPException(
            status_code=501,
            detail=f"WeasyPrint system dependencies missing: {e}. Run: brew install pango",
        )
    protocol_key = report.metadata.get("protocol_key", "unknown") or "unknown"
    filename = f"ce-report-{protocol_key}-{run_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/share/{run_id}")
def share_run(run_id: int, session: Session = Depends(get_session)) -> HTMLResponse:
    """Serve a read-only styled HTML report for sharing.

    This route is excluded from API key authentication in server.py.

    Returns:
        Full self-contained HTML page with all report sections.
        404 if run not found or not completed.
    """
    report = _load_report(run_id, session)
    html = _jinja_env.get_template("report.html.j2").render(report=report.as_dict())
    return HTMLResponse(content=html)
