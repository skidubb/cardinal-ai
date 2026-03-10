"""Tests for api/routers/reports.py — PDF export and shareable HTML endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.models import AgentOutput, Run


# ── Helper ─────────────────────────────────────────────────────────────────────


def _create_completed_run(session, judge_verdict_json: str = "{}") -> Run:
    """Create a completed Run with two AgentOutput rows and a synthesis."""
    run = Run(
        protocol_key="p03_parallel_synthesis",
        question="Should we expand into Europe?",
        status="completed",
        cost_usd=0.0123,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        judge_verdict_json=judge_verdict_json,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Agent outputs
    for key, name in [("ceo", "CEO"), ("cfo", "CFO")]:
        out = AgentOutput(
            run_id=run.id,
            agent_key=key,
            model="claude-opus-4-6",
            output_text=f"Agent {name} analysis: This is a comprehensive response from {key}.",
            cost_usd=0.005,
        )
        session.add(out)

    # Synthesis row
    synthesis = AgentOutput(
        run_id=run.id,
        agent_key="_synthesis",
        model="claude-opus-4-6",
        output_text=(
            "The agents concur on key points.\n\n"
            "- Strong alignment on risk-adjusted opportunity\n"
            "- However, the CFO dissents on timing due to market conditions\n"
            "- Resource allocation to be determined\n\n"
            "Both agents agree the fundamentals are sound."
        ),
        cost_usd=0.002,
    )
    session.add(synthesis)
    session.commit()
    return run


# ── PDF endpoint tests ─────────────────────────────────────────────────────────


def _weasyprint_works() -> bool:
    """Return True if WeasyPrint can actually be imported and run (system deps present)."""
    try:
        import weasyprint
        weasyprint.HTML(string="<p>x</p>").write_pdf()
        return True
    except Exception:
        return False


def test_pdf_endpoint_or_501(client, session):
    """GET /api/reports/{id}/pdf returns 200 PDF or 501 if WeasyPrint unavailable."""
    run = _create_completed_run(session)
    resp = client.get(f"/api/reports/{run.id}/pdf")

    if _weasyprint_works():
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 0
    else:
        assert resp.status_code == 501
        detail = resp.json()["detail"]
        assert "WeasyPrint" in detail or "system dep" in detail.lower() or "brew install" in detail.lower()


def test_pdf_endpoint_with_judge_verdict(client, session):
    """PDF endpoint works with a judge verdict attached to the run."""
    import json
    verdict = json.dumps({"overall": 4, "completeness": 4, "consistency": 5, "actionability": 3, "recommendation": "accept", "flags": []})
    run = _create_completed_run(session, judge_verdict_json=verdict)
    resp = client.get(f"/api/reports/{run.id}/pdf")
    # Either PDF or graceful 501 — both are acceptable
    assert resp.status_code in (200, 501)


def test_pdf_404_for_missing_run(client):
    """GET /api/reports/9999/pdf returns 404 for non-existent run."""
    resp = client.get("/api/reports/9999/pdf")
    assert resp.status_code == 404


def test_pdf_404_for_pending_run(client, session):
    """GET /api/reports/{id}/pdf returns 404 for pending (not completed) run."""
    run = Run(
        protocol_key="p03_parallel_synthesis",
        question="Test question",
        status="pending",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    resp = client.get(f"/api/reports/{run.id}/pdf")
    assert resp.status_code == 404


# ── Shareable HTML endpoint tests ──────────────────────────────────────────────


def test_share_url_returns_html(client, session):
    """GET /share/{id} returns 200 with text/html content-type."""
    run = _create_completed_run(session)
    resp = client.get(f"/share/{run.id}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_share_url_contains_report_content(client, session):
    """Response body contains executive summary and participant agent keys."""
    run = _create_completed_run(session)
    resp = client.get(f"/share/{run.id}")
    assert resp.status_code == 200
    body = resp.text

    # Executive summary extracted from synthesis
    assert "The agents concur" in body or "Strong alignment" in body or "Both agents agree" in body

    # Agent names / keys should appear
    assert "ceo" in body or "CEO" in body
    assert "cfo" in body or "CFO" in body


def test_share_url_contains_protocol_key(client, session):
    """Response body includes protocol key in header metadata."""
    run = _create_completed_run(session)
    resp = client.get(f"/share/{run.id}")
    assert resp.status_code == 200
    body = resp.text
    assert "p03_parallel_synthesis" in body or "P03_PARALLEL_SYNTHESIS" in body


def test_share_url_404_for_missing_run(client):
    """GET /share/9999 returns 404 for non-existent run."""
    resp = client.get("/share/9999")
    assert resp.status_code == 404


def test_share_url_no_auth_required(client, session):
    """GET /share/{id} returns 200 even when auth is enforced.

    Patches SKIP_AUTH=False and API_KEY set to simulate production auth mode.
    The /share/ path must bypass auth middleware.
    """
    from unittest.mock import patch

    run = _create_completed_run(session)

    with patch("api.server.SKIP_AUTH", False), patch("api.server.API_KEY", "secret-key-xyz"):
        resp = client.get(f"/share/{run.id}")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_share_url_has_cardinal_element_branding(client, session):
    """Shareable HTML includes Cardinal Element branding."""
    run = _create_completed_run(session)
    resp = client.get(f"/share/{run.id}")
    assert resp.status_code == 200
    assert "Cardinal Element" in resp.text


def test_share_url_has_section_headings(client, session):
    """Shareable HTML includes expected section headings."""
    run = _create_completed_run(session)
    resp = client.get(f"/share/{run.id}")
    assert resp.status_code == 200
    body = resp.text
    # Check for key section labels from the template
    assert "Executive Summary" in body
    assert "Key Findings" in body
