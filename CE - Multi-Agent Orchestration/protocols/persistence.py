"""Persist protocol run results to Postgres via ce-db.

Gracefully no-ops when Postgres/ce-db is unavailable, so CLI runs
work without a database.

Usage:
    from protocols.persistence import persist_run

    run_id = await persist_run(
        protocol_key="p06_triz",
        question="Should we expand?",
        agent_keys=["ceo", "cfo", "cto"],
        result=triz_result,
        cost_tracker=tracker,
        source="cli",
    )
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime, timezone
from typing import Any

_log = logging.getLogger(__name__)


def _result_to_dict(result: Any) -> dict:
    """Convert a protocol result dataclass to a JSON-serializable dict."""
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: str(v)[:5000] for k, v in result.__dict__.items()}
    return {"raw": str(result)[:5000]}


def _extract_synthesis(result: Any) -> str:
    """Extract human-readable summary from protocol result."""
    for attr in ("synthesis", "final_synthesis", "final_output",
                 "recommendation", "summary", "conclusion"):
        val = getattr(result, attr, None)
        if val and isinstance(val, str):
            return val[:2000]
    return ""


def _extract_agent_outputs(result: Any, agent_keys: list[str]) -> list[dict]:
    """Extract per-agent outputs from result (mirrors api/runner.py patterns)."""
    outputs = []

    # .perspectives (P3)
    if hasattr(result, "perspectives"):
        for p in result.perspectives:
            outputs.append({
                "agent_key": _name_to_key(p.name, agent_keys) if hasattr(p, "name") else "",
                "text": p.response if hasattr(p, "response") else str(p),
            })
        return outputs

    # .rounds (P4 debate)
    if hasattr(result, "rounds") and isinstance(result.rounds, list):
        for ri, rnd in enumerate(result.rounds):
            if hasattr(rnd, "responses"):
                for resp in rnd.responses:
                    name = resp.name if hasattr(resp, "name") else ""
                    outputs.append({
                        "agent_key": _name_to_key(name, agent_keys),
                        "text": resp.response if hasattr(resp, "response") else str(resp),
                        "round": ri + 1,
                    })
        return outputs

    # .agent_contributions (P6 TRIZ)
    if hasattr(result, "agent_contributions") and isinstance(result.agent_contributions, dict):
        for name, text in result.agent_contributions.items():
            outputs.append({
                "agent_key": _name_to_key(name, agent_keys),
                "text": text if isinstance(text, str) else str(text),
            })
        return outputs

    # Generic list attributes
    for attr in ("agent_outputs", "responses", "agent_responses"):
        val = getattr(result, attr, None)
        if val and isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    outputs.append({
                        "agent_key": item.get("agent_key", ""),
                        "text": item.get("text", item.get("response", str(item))),
                    })
                elif hasattr(item, "name"):
                    outputs.append({
                        "agent_key": _name_to_key(item.name, agent_keys),
                        "text": item.response if hasattr(item, "response") else str(item),
                    })
            return outputs

    return outputs


def _name_to_key(name: str, agent_keys: list[str]) -> str:
    name_lower = name.lower().replace(" ", "-")
    for key in agent_keys:
        if key in name_lower or name_lower in key:
            return key
    return name_lower


async def persist_run(
    protocol_key: str,
    question: str,
    agent_keys: list[str],
    result: Any,
    cost_tracker: Any | None = None,
    trace_id: str | None = None,
    source: str = "cli",
    started_at: datetime | None = None,
    error: str | None = None,
) -> str | None:
    """Persist a protocol run to Postgres. Returns run ID or None if unavailable."""
    try:
        from ce_db import get_session, Run, AgentOutput
    except ImportError:
        _log.debug("ce-db not installed — skipping persistence")
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = (started_at.replace(tzinfo=None) if started_at and started_at.tzinfo else started_at) or now

    # Cost data
    total_cost = 0.0
    total_input = 0
    total_output = 0
    if cost_tracker:
        try:
            summary = cost_tracker.summary()
            total_cost = summary.get("total_usd", 0.0)
            for model_data in summary.get("by_model", {}).values():
                total_input += model_data.get("input_tokens", 0)
                total_output += model_data.get("output_tokens", 0)
        except Exception:
            pass

    # Result data
    try:
        result_json = _result_to_dict(result)
    except Exception:
        result_json = {"error": "Could not serialize result"}

    result_summary = _extract_synthesis(result)
    status = "failed" if error else "completed"

    try:
        async with get_session() as session:
            run = Run(
                protocol_key=protocol_key,
                question=question,
                agent_keys=agent_keys,
                source=source,
                status=status,
                result_json=result_json,
                result_summary=result_summary,
                total_cost_usd=total_cost,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                langfuse_trace_id=trace_id,
                error_message=error,
                started_at=start,
                completed_at=now,
            )
            session.add(run)
            await session.flush()  # get run.id

            # Per-agent outputs
            agent_outputs = _extract_agent_outputs(result, agent_keys)
            for ao in agent_outputs:
                session.add(AgentOutput(
                    run_id=run.id,
                    agent_key=ao.get("agent_key", ""),
                    round_number=ao.get("round", 0),
                    output_text=ao.get("text", "")[:10000],
                ))

            run_id = str(run.id)
            _log.info("Persisted run %s for %s", run_id, protocol_key)
            return run_id

    except Exception as e:
        _log.warning("Failed to persist run: %s", e)
        return None
