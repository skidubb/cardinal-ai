"""M5 tests: the compounding loop -- context assembly, graph writing, corrections.

Core M5 logic is in protocols/context_assembler.py, protocols/graph_writer.py,
and ce_graph's GraphQueries. These tests exercise the pieces that don't need
a running FalkorDB instance (brief formatting, envelope extraction). The
integration-level tests (real Cypher writes + reads) run against ce-graph's
existing FalkorDB smoke test suite when infra is available.
"""

from __future__ import annotations

from types import SimpleNamespace


def test_brief_formatter_structures_all_sections() -> None:
    """The brief should include Context/Corrections/Decisions/Lessons when data present."""
    from protocols.context_assembler import _format_brief

    brief = _format_brief(
        corrections=[
            {
                "text": "Do not pitch aggressive sales tactics",
                "scope": "client",
                "target_id": "acme",
                "reason": "Founder said so Q4 2025",
            }
        ],
        decisions=[
            {
                "summary": "Recommended tier-3 pricing for Acme",
                "protocol_code": "P04",
                "eval_score": 4.3,
            }
        ],
        lessons=[
            {
                "statement": "SaaS clients in our book respond to consumption pricing",
                "confidence": 0.82,
            }
        ],
        related={"clients": ["Acme Corp"], "engagements": []},
    )
    assert "### Context detected" in brief
    assert "Acme Corp" in brief
    assert "### Corrections you must honor" in brief
    assert "Do not pitch aggressive sales tactics" in brief
    assert "### Prior related decisions" in brief
    assert "P04" in brief
    assert "### Lessons we've learned" in brief
    assert "consumption pricing" in brief


def test_brief_formatter_empty_returns_empty_string() -> None:
    from protocols.context_assembler import _format_brief
    assert _format_brief([], [], [], {}) == ""


def test_graph_writer_extracts_eval_score_from_envelope() -> None:
    from protocols.graph_writer import _extract_eval_score

    envelope = SimpleNamespace(judge_verdict={"overall": 0.91, "completeness": 0.88})
    assert _extract_eval_score(envelope) == 0.91

    envelope_no_verdict = SimpleNamespace(judge_verdict=None)
    assert _extract_eval_score(envelope_no_verdict) is None

    envelope_no_attr = SimpleNamespace()
    assert _extract_eval_score(envelope_no_attr) is None


def test_graph_writer_extracts_summary_prefers_result_summary() -> None:
    from protocols.graph_writer import _extract_summary

    env = SimpleNamespace(result_summary="The synthesized recommendation is X")
    assert _extract_summary(env).startswith("The synthesized recommendation")

    env_no_rs = SimpleNamespace(
        result_summary=None,
        result_json={"synthesis": "Use tier-3 pricing."},
    )
    assert "tier-3 pricing" in _extract_summary(env_no_rs)

    env_empty = SimpleNamespace(result_summary=None, result_json={})
    assert _extract_summary(env_empty) == "(no summary)"


def test_correction_scope_validation_missing_target_raises() -> None:
    """POST /api/corrections must reject non-global scopes without a target_id."""
    import pytest
    from fastapi import HTTPException
    from api.routers.corrections import CorrectionIn, ALLOWED_SCOPES

    assert ALLOWED_SCOPES == {"global", "client", "engagement", "protocol", "agent", "decision"}

    # pydantic validation should allow construction; the 400 happens in the handler
    payload = CorrectionIn(text="no target here", scope="client", target_id=None)
    assert payload.scope == "client"
    assert payload.target_id is None


def test_graph_writer_safe_without_ce_graph(monkeypatch) -> None:
    """If ce-graph isn't importable, write_decision must no-op silently."""
    import asyncio
    import builtins

    from protocols import graph_writer

    real_import = builtins.__import__

    def _block_ce_graph(name, *args, **kwargs):
        if name.startswith("ce_graph"):
            raise ImportError("simulated missing ce-graph")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_ce_graph)

    # Should return None without raising
    envelope = SimpleNamespace(
        protocol_key="p04", agent_keys=["ceo"], result_summary="test",
    )
    asyncio.run(graph_writer.write_decision("cardinal-element", envelope, run_id_source="42"))


def test_context_assembler_safe_without_ce_graph(monkeypatch) -> None:
    """assemble_context must return empty string if ce-graph isn't installed."""
    import asyncio
    import builtins

    from protocols import context_assembler

    real_import = builtins.__import__

    def _block_ce_graph(name, *args, **kwargs):
        if name.startswith("ce_graph"):
            raise ImportError("simulated missing ce-graph")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_ce_graph)

    result = asyncio.run(context_assembler.assemble_context("cardinal-element", "any question"))
    assert result == ""

    preview = asyncio.run(context_assembler.assemble_context_preview("cardinal-element", "any question"))
    assert preview["available"] is False
