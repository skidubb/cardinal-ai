"""Write a ``Decision`` node to the active tenant's graph after every run.

This closes the compounding loop. Every protocol execution adds one structured
Decision to the customer's graph -- linked to the Protocol that produced it,
the Agents that contributed, and the Run as the source of provenance. The
next time an agent faces a related question, ``context_assembler`` retrieves
these decisions and feeds them back as institutional memory.

Best-effort by design: graph writes never block a run. If FalkorDB is
unreachable or the tenant's graph isn't provisioned, we log and move on.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _extract_eval_score(envelope: Any) -> float | None:
    """Pull the judge verdict 'overall' score if present."""
    try:
        verdict = getattr(envelope, "judge_verdict", None)
        if verdict and isinstance(verdict, dict):
            overall = verdict.get("overall")
            if overall is not None:
                return float(overall)
    except Exception:
        pass
    return None


def _extract_summary(envelope: Any) -> str:
    """Prefer result_summary; fall back to truncated result_json summary field."""
    try:
        rs = getattr(envelope, "result_summary", None)
        if rs:
            return str(rs)[:2000]
        result = getattr(envelope, "result_json", None)
        if isinstance(result, dict):
            for key in ("synthesis", "summary", "recommendation", "conclusion"):
                v = result.get(key)
                if v:
                    return str(v)[:2000]
    except Exception:
        pass
    return "(no summary)"


async def write_decision(
    tenant_slug: str,
    envelope: Any,
    run_id_source: str | None = None,
) -> None:
    """Write a Decision node + edges for the just-completed run.

    Safe no-op if ce-graph isn't importable or the tenant isn't provisioned.
    """
    try:
        from ce_graph.falkor_client import FalkorClient
        from ce_graph.queries import GraphQueries
        from ce_graph.tenancy import load_tenant
    except ImportError as e:
        logger.warning(
            "graph_writer.import_failed tenant=%s err=%s",
            tenant_slug, e,
        )
        return

    try:
        tenant = load_tenant(tenant_slug)
    except FileNotFoundError:
        logger.warning(
            "graph_writer.tenant_not_provisioned tenant=%s "
            "hint='run cegraph init --tenant %s'",
            tenant_slug, tenant_slug,
        )
        return

    try:
        queries = GraphQueries(FalkorClient(tenant=tenant))

        decision_id = f"decision_{uuid.uuid4().hex[:16]}"
        summary = _extract_summary(envelope)
        protocol_code = str(getattr(envelope, "protocol_code", "") or "").upper() or None
        if not protocol_code:
            key = getattr(envelope, "protocol_key", "") or ""
            if key.startswith("p"):
                protocol_code = key.split("_", 1)[0].upper()
        agent_keys = list(getattr(envelope, "agent_keys", []) or [])
        eval_score = _extract_eval_score(envelope)
        confidence = getattr(envelope, "confidence", None)
        run_source_id = run_id_source or getattr(envelope, "run_id", None) or getattr(envelope, "trace_id", None)

        queries.write_decision(
            decision_id=decision_id,
            summary=summary,
            rationale=None,
            protocol_code=protocol_code,
            agent_keys=agent_keys,
            engagement_name=getattr(envelope, "engagement_name", None),
            confidence=float(confidence) if confidence is not None else None,
            eval_score=eval_score,
            run_source_id=str(run_source_id) if run_source_id else None,
        )
        logger.info(
            "graph_writer.write_decision_ok decision_id=%s graph=%s "
            "tenant=%s protocol=%s agents=%s eval=%s",
            decision_id, tenant.graph_name, tenant_slug, protocol_code,
            agent_keys, eval_score,
        )
    except Exception as e:
        logger.warning(
            "graph_writer.write_decision_failed tenant=%s err=%s",
            tenant_slug, e,
        )


__all__ = ["write_decision"]
