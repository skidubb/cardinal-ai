"""Per-turn context assembly from the tenant's knowledge graph.

Before a protocol runs, we look at the question + inferred entities and pull:
  * Corrections that apply (scope: global, client, engagement, protocol, agent)
  * Recent Decisions for the active client/vertical
  * Lessons for the vertical
  * Related Client / Engagement entities

We format this as a compact markdown brief and inject it as each agent's
``institutional_memory``. ServerAgent's ``_build_system_prompt`` already
appends that field as "Institutional Memory -- Past Protocol Insights", so
no changes to the agent are required.

Safe no-op if ce-graph isn't importable or the tenant isn't provisioned.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _format_brief(
    corrections: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
    related: dict[str, list[str]],
) -> str:
    """Format the assembled context as a compact markdown brief for agents."""
    sections: list[str] = []

    if related.get("clients") or related.get("engagements"):
        sections.append("### Context detected")
        if related.get("clients"):
            sections.append(f"- Client(s) referenced: {', '.join(related['clients'])}")
        if related.get("engagements"):
            sections.append(f"- Engagement(s) referenced: {', '.join(related['engagements'])}")

    if corrections:
        sections.append("### Corrections you must honor")
        for c in corrections[:15]:
            scope = c.get("scope", "global")
            target = c.get("target_id") or ""
            text = (c.get("text") or "").strip()
            reason = (c.get("reason") or "").strip()
            line = f"- [{scope}{':' + target if target else ''}] {text}"
            if reason:
                line += f"  (_why: {reason}_)"
            sections.append(line)

    if decisions:
        sections.append("### Prior related decisions")
        for d in decisions[:10]:
            summary = (d.get("summary") or "").strip()
            protocol = d.get("protocol_code") or ""
            eval_score = d.get("eval_score")
            eval_tag = f" (eval {eval_score:.2f})" if eval_score else ""
            sections.append(f"- {protocol}: {summary[:240]}{eval_tag}")

    if lessons:
        sections.append("### Lessons we've learned")
        for l in lessons[:8]:
            statement = (l.get("statement") or "").strip()
            conf = l.get("confidence")
            conf_tag = f" (conf {conf:.2f})" if conf else ""
            sections.append(f"- {statement[:240]}{conf_tag}")

    if not sections:
        return ""
    return "\n\n".join(sections)


async def assemble_context(
    tenant_slug: str,
    question: str,
    agent_keys: list[str] | None = None,
) -> str:
    """Build the memory brief for the upcoming run. Returns "" on failure.

    All agents in the same run currently share the same brief. Per-agent
    differentiation (e.g. CFO-specific vs CMO-specific corrections) is a
    future enhancement.
    """
    try:
        from ce_graph.falkor_client import FalkorClient
        from ce_graph.queries import GraphQueries
        from ce_graph.tenancy import load_tenant
    except ImportError:
        return ""

    try:
        tenant = load_tenant(tenant_slug)
    except FileNotFoundError:
        return ""

    try:
        q = GraphQueries(FalkorClient(tenant=tenant))
        related = q.related_entities_for_text(question)
        client_name = related["clients"][0] if related.get("clients") else None

        # Resolve vertical if we have a client match
        vertical: str | None = None
        if client_name:
            try:
                r = q.client.query(
                    "MATCH (c:Client {name: $name}) RETURN c.vertical AS v LIMIT 1",
                    {"name": client_name.lower()},
                )
                if r.result_set:
                    vertical = r.result_set[0][0] or None
            except Exception:
                pass

        scope_targets: dict[str, str] = {}
        if client_name:
            scope_targets["client"] = client_name
        for agent in agent_keys or []:
            scope_targets[f"agent_{agent}"] = agent  # distinct keys so they don't collide
        # Build a proper per-agent filter instead of the key-collision hack:
        scope_targets = {k: v for k, v in scope_targets.items() if not k.startswith("agent_")}
        # Corrections query matches any agent in the set:
        agent_scopes: dict[str, Any] = {}
        for i, a in enumerate(agent_keys or []):
            agent_scopes[f"agent"] = a  # last wins; we'll do a union below

        corrections = q.active_corrections(scope_targets=scope_targets, limit=25)
        # Agent-scoped corrections: fetch per agent and dedupe
        seen_ids: set[str] = set()
        all_corrections: list[dict] = []
        for c in corrections:
            key = (c.get("scope"), c.get("target_id"), c.get("text"))
            if key not in seen_ids:
                seen_ids.add(key)  # type: ignore[arg-type]
                all_corrections.append(c)
        for agent in agent_keys or []:
            for c in q.active_corrections(scope_targets={"agent": agent}, limit=10):
                key = (c.get("scope"), c.get("target_id"), c.get("text"))
                if key not in seen_ids:
                    seen_ids.add(key)  # type: ignore[arg-type]
                    all_corrections.append(c)

        decisions = q.recent_decisions_for_context(
            vertical=vertical, client_name=client_name, limit=10,
        )
        lessons = q.lessons_for_vertical_and_client(
            vertical=vertical, client_name=client_name, limit=8,
        )

        brief = _format_brief(all_corrections, decisions, lessons, related)
        if brief:
            logger.info(
                "Context assembled for %s: %d corrections, %d decisions, %d lessons",
                tenant_slug, len(all_corrections), len(decisions), len(lessons),
            )
        return brief
    except Exception as e:
        logger.warning("Context assembly failed for %s: %s", tenant_slug, e)
        return ""


async def assemble_context_preview(
    tenant_slug: str,
    question: str,
) -> dict[str, Any]:
    """Portal endpoint returns the structured preview (not the formatted brief).

    Used by /api/context/preview to show "what the graph knows" before a run.
    """
    try:
        from ce_graph.falkor_client import FalkorClient
        from ce_graph.queries import GraphQueries
        from ce_graph.tenancy import load_tenant
    except ImportError:
        return {"available": False, "reason": "ce-graph not installed"}

    try:
        tenant = load_tenant(tenant_slug)
    except FileNotFoundError:
        return {"available": False, "reason": f"tenant {tenant_slug} not provisioned"}

    try:
        q = GraphQueries(FalkorClient(tenant=tenant))
        related = q.related_entities_for_text(question)
        client_name = related["clients"][0] if related.get("clients") else None
        vertical = None
        if client_name:
            try:
                r = q.client.query(
                    "MATCH (c:Client {name: $name}) RETURN c.vertical AS v LIMIT 1",
                    {"name": client_name.lower()},
                )
                if r.result_set:
                    vertical = r.result_set[0][0] or None
            except Exception:
                pass
        corrections = q.active_corrections(
            scope_targets={"client": client_name} if client_name else {},
            limit=10,
        )
        decisions = q.recent_decisions_for_context(
            vertical=vertical, client_name=client_name, limit=5,
        )
        lessons = q.lessons_for_vertical_and_client(
            vertical=vertical, client_name=client_name, limit=5,
        )
        return {
            "available": True,
            "tenant_slug": tenant_slug,
            "detected": {"clients": related["clients"], "engagements": related["engagements"], "vertical": vertical},
            "applicable_corrections": corrections,
            "recent_decisions": decisions,
            "lessons": lessons,
            "summary": {
                "corrections": len(corrections),
                "decisions": len(decisions),
                "lessons": len(lessons),
            },
        }
    except Exception as e:
        return {"available": False, "reason": str(e)[:200]}


__all__ = ["assemble_context", "assemble_context_preview"]
