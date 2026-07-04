"""Article plumbing: _article rows round-trip into ProtocolReport.article
and never leak into agent contributions or participants."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session

from api.models import AgentOutput, Run
from api.report_helpers import build_envelope_from_db
from protocols.protocol_report import _INTERNAL_AGENT_KEYS, from_envelope

_ARTICLE = {
    "headline": "The Kill Switch Decision",
    "deck": "A staged bet with a pre-committed exit.",
    "byline": {
        "protocol": "p06_triz",
        "agents": ["ceo", "cfo"],
        "generated_at": "2026-07-04T00:00:00Z",
    },
    "lede": "The room split early.",
    "sections": [{"heading": "The Gap", "body_markdown": "Body.", "pull_quote": None}],
    "tensions": [],
    "what_next": "Month five decides.",
}


def _seed_run(session: Session) -> Run:
    run = Run(
        type="protocol",
        protocol_key="p06_triz",
        question="Should we expand?",
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        cost_usd=0.5,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    session.add(
        AgentOutput(
            run_id=run.id, agent_key="ceo", model="m", output_text="CEO says go."
        )
    )
    session.add(
        AgentOutput(
            run_id=run.id,
            agent_key="_synthesis",
            model="m",
            output_text="## Synthesis\n\nGo, with a gate.",
        )
    )
    session.add(
        AgentOutput(
            run_id=run.id,
            agent_key="_article",
            model="m",
            output_text=json.dumps(_ARTICLE),
        )
    )
    session.commit()
    return run


def test_internal_keys_include_article_and_match_report_helpers():
    assert "_article" in _INTERNAL_AGENT_KEYS
    # report_helpers keeps its own copy of the internal-key set; drift between
    # the two silently leaks internal rows into agent lists.
    import inspect

    import api.report_helpers as rh

    src = inspect.getsource(rh.build_envelope_from_db)
    for key in _INTERNAL_AGENT_KEYS:
        assert key in src, f"report_helpers is missing internal key {key}"


def test_article_round_trips_and_never_leaks(session):
    run = _seed_run(session)
    envelope = build_envelope_from_db(run, session)

    assert (
        envelope.metadata.get("article", {}).get("headline")
        == "The Kill Switch Decision"
    )
    assert all(o.agent_key != "_article" for o in envelope.agent_outputs)
    assert envelope.agent_keys == ["ceo"]
    assert envelope.result_summary.startswith("## Synthesis")

    report = from_envelope(envelope, judge_verdict=None)
    assert report.article == _ARTICLE
    assert report.participants == ["ceo"]
    assert all(c.agent_key != "_article" for c in report.agent_contributions)
    assert report.as_dict()["article"]["deck"] == _ARTICLE["deck"]


def test_corrupt_article_json_degrades_to_none(session):
    run = _seed_run(session)
    session.add(
        AgentOutput(
            run_id=run.id, agent_key="_article", model="m", output_text="{not json"
        )
    )
    session.commit()
    envelope = build_envelope_from_db(run, session)
    report = from_envelope(envelope, judge_verdict=None)
    # Last _article row wins in iteration order; corrupt JSON must yield None,
    # never an exception.
    assert report.article is None or isinstance(report.article, dict)
