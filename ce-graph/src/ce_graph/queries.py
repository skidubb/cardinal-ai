"""Cypher query helpers for the Cardinal Element graph.

These are deterministic Cypher queries (no LLM in the path) that the
C-Suite agents can call to look up structured facts. For semantic
retrieval use ``GraphClient.search`` instead.
"""

from __future__ import annotations

from typing import Any

from ce_graph.falkor_client import FalkorClient


def _rows(result: Any) -> list[dict[str, Any]]:
    """Convert FalkorDB result_set to list of dicts using header names."""
    if not result or not getattr(result, "result_set", None):
        return []
    headers = [h[1] if isinstance(h, (list, tuple)) else str(h) for h in (result.header or [])]
    return [dict(zip(headers, row)) for row in result.result_set]


class GraphQueries:
    """Reusable Cypher queries against a tenant graph.

    Always pass a tenant-scoped FalkorClient. We deliberately do not default
    to ``FalkorClient()`` here because that would silently fall through to
    the cardinal-element reference graph -- a cross-tenant data risk.
    """

    def __init__(self, client: FalkorClient) -> None:
        if client is None:
            raise ValueError(
                "GraphQueries requires an explicit FalkorClient. "
                "Use FalkorClient.for_tenant(slug) to scope to a tenant."
            )
        self.client = client

    def all_clients(self) -> list[dict[str, Any]]:
        return _rows(self.client.query("MATCH (c:Client) RETURN c.name AS name, c.vertical AS vertical, c.status AS status ORDER BY c.name"))

    def all_engagements_for_client(self, client_name: str) -> list[dict[str, Any]]:
        return _rows(
            self.client.query(
                """
                MATCH (e:Engagement)-[:FOR_CLIENT]->(c:Client {name: $name})
                RETURN e.name AS name, e.type AS type, e.status AS status,
                       e.started_at AS started_at, e.value_usd AS value_usd
                ORDER BY e.started_at DESC
                """,
                {"name": client_name},
            )
        )

    def decisions_using_protocol(self, protocol_code: str) -> list[dict[str, Any]]:
        return _rows(
            self.client.query(
                """
                MATCH (d:Decision)-[:USING_PROTOCOL]->(p:Protocol {code: $code})
                OPTIONAL MATCH (d)-[:IN_ENGAGEMENT]->(e:Engagement)
                RETURN d.summary AS summary, d.rationale AS rationale,
                       d.eval_score AS eval_score, e.name AS engagement
                ORDER BY d.decided_at DESC
                """,
                {"code": protocol_code},
            )
        )

    def corrections_applicable_to_client(self, client_name: str) -> list[dict[str, Any]]:
        """Every correction the agents should consider before working on this client."""
        return _rows(
            self.client.query(
                """
                MATCH (cor:Correction)
                WHERE cor.scope = 'global'
                   OR (cor.scope = 'client' AND cor.target_id = $name)
                RETURN cor.text AS text, cor.scope AS scope,
                       cor.given_by AS given_by, cor.given_at AS given_at,
                       cor.reason AS reason
                ORDER BY cor.given_at DESC
                """,
                {"name": client_name},
            )
        )

    def lessons_for_vertical(self, vertical: str) -> list[dict[str, Any]]:
        return _rows(
            self.client.query(
                """
                MATCH (l:Lesson)-[:APPLIES_TO_VERTICAL]->(v:Vertical {name: $vertical})
                RETURN l.statement AS statement, l.confidence AS confidence
                ORDER BY l.confidence DESC
                """,
                {"vertical": vertical},
            )
        )

    def graph_stats(self) -> dict[str, int]:
        """Top-level cardinality. Useful for the architecture diagram."""
        labels = ["Client", "Engagement", "Protocol", "Decision", "Deliverable",
                  "Correction", "Lesson", "Person", "Agent", "Source", "Vertical"]
        out: dict[str, int] = {}
        for label in labels:
            try:
                r = self.client.query(f"MATCH (n:{label}) RETURN count(n) AS n")
                out[label] = int(r.result_set[0][0]) if r.result_set else 0
            except Exception:
                out[label] = 0
        return out

    # ------------------------------------------------------------------
    # M5 — context assembly helpers
    # ------------------------------------------------------------------

    def active_corrections(
        self,
        scope_targets: dict[str, str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return Corrections that apply to the given scopes.

        ``scope_targets`` maps a ``Correction.scope`` value to the target to
        match, e.g. ``{"client": "acme", "protocol": "P04"}``. A GLOBAL
        correction (no target_id) always matches. Corrections with valid_to in
        the past are excluded.
        """
        if scope_targets is None:
            scope_targets = {}
        clauses = ["cor.scope = 'global'"]
        params: dict[str, Any] = {}
        for i, (scope, target) in enumerate(scope_targets.items()):
            if not target:
                continue
            key = f"t{i}"
            clauses.append(f"(cor.scope = '{scope}' AND cor.target_id = ${key})")
            params[key] = str(target).lower()
        where = " OR ".join(clauses)
        q = (
            f"MATCH (cor:Correction) "
            f"WHERE ({where}) AND (cor.valid_to IS NULL OR cor.valid_to > timestamp()) "
            f"RETURN cor.text AS text, cor.scope AS scope, cor.target_id AS target_id, "
            f"       cor.reason AS reason, cor.given_by AS given_by, cor.given_at AS given_at "
            f"ORDER BY cor.given_at DESC LIMIT {int(limit)}"
        )
        return _rows(self.client.query(q, params))

    def recent_decisions_for_context(
        self, vertical: str | None = None, client_name: str | None = None, limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recent decisions relevant to the active context -- for in-context recall."""
        params: dict[str, Any] = {}
        wheres: list[str] = []
        if client_name:
            wheres.append("(d)-[:IN_ENGAGEMENT]->(:Engagement)-[:FOR_CLIENT]->(:Client {name: $client})")
            params["client"] = str(client_name).lower()
        if vertical:
            wheres.append("(:Client {vertical: $vertical})<-[:FOR_CLIENT]-(:Engagement)<-[:IN_ENGAGEMENT]-(d)")
            params["vertical"] = vertical
        match_extra = ""
        if wheres:
            match_extra = " AND EXISTS { " + " } AND EXISTS { ".join(wheres) + " }"
        q = (
            "MATCH (d:Decision) "
            f"WHERE d.summary IS NOT NULL{match_extra} "
            "OPTIONAL MATCH (d)-[:USING_PROTOCOL]->(p:Protocol) "
            "RETURN d.summary AS summary, d.rationale AS rationale, "
            "       d.eval_score AS eval_score, p.code AS protocol_code, "
            "       d.decided_at AS decided_at "
            "ORDER BY d.decided_at DESC LIMIT "
            f"{int(limit)}"
        )
        return _rows(self.client.query(q, params))

    def lessons_for_vertical_and_client(
        self, vertical: str | None = None, client_name: str | None = None, limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Lessons tagged to this vertical, plus lessons derived from this client's decisions."""
        params: dict[str, Any] = {}
        ors: list[str] = []
        if vertical:
            ors.append("l.applies_to_vertical = $vertical")
            params["vertical"] = vertical
        if client_name:
            ors.append(
                "EXISTS { (l)-[:DERIVED_FROM]->(:Decision)-[:IN_ENGAGEMENT]->"
                "(:Engagement)-[:FOR_CLIENT]->(:Client {name: $client}) }"
            )
            params["client"] = str(client_name).lower()
        if not ors:
            return []
        where = " OR ".join(ors)
        q = (
            f"MATCH (l:Lesson) WHERE {where} "
            "RETURN l.statement AS statement, l.confidence AS confidence, "
            "       l.applies_to_vertical AS vertical "
            "ORDER BY l.confidence DESC NULLS LAST LIMIT "
            f"{int(limit)}"
        )
        return _rows(self.client.query(q, params))

    def related_entities_for_text(self, text: str, limit: int = 10) -> dict[str, list[str]]:
        """Surface Client / Engagement names present in the text. Lightweight --
        substring match, not NLP. Good enough for the memory-brief preview."""
        text_lc = text.lower()
        out: dict[str, list[str]] = {"clients": [], "engagements": []}
        try:
            clients = _rows(self.client.query(
                "MATCH (c:Client) RETURN c.name AS name, c.vertical AS vertical"
            ))
            for row in clients:
                name = row.get("name") or ""
                if name and name.lower() in text_lc:
                    out["clients"].append(name)
            engagements = _rows(self.client.query(
                "MATCH (e:Engagement) RETURN e.name AS name"
            ))
            for row in engagements:
                name = row.get("name") or ""
                if name and name.lower() in text_lc:
                    out["engagements"].append(name)
        except Exception:
            pass
        out["clients"] = out["clients"][:limit]
        out["engagements"] = out["engagements"][:limit]
        return out

    # ------------------------------------------------------------------
    # M5 -- Decision writer (called from protocols/graph_writer.py)
    # ------------------------------------------------------------------

    def write_decision(
        self,
        decision_id: str,
        summary: str,
        rationale: str | None,
        protocol_code: str | None,
        agent_keys: list[str],
        engagement_name: str | None,
        confidence: float | None,
        eval_score: float | None,
        run_source_id: str | None,
    ) -> None:
        """MERGE a Decision node + edges to Protocol, Agents, Engagement, Source."""
        self.client.query(
            "MERGE (d:Decision {id: $id}) "
            "SET d.summary = $summary, d.rationale = $rationale, "
            "    d.confidence = $confidence, d.eval_score = $eval_score, "
            "    d.decided_at = timestamp()",
            {
                "id": decision_id,
                "summary": summary,
                "rationale": rationale or "",
                "confidence": confidence if confidence is not None else 0.0,
                "eval_score": eval_score if eval_score is not None else 0.0,
            },
        )
        if protocol_code:
            self.client.query(
                "MATCH (d:Decision {id: $id}), (p:Protocol {code: $code}) "
                "MERGE (d)-[:USING_PROTOCOL]->(p)",
                {"id": decision_id, "code": protocol_code},
            )
        for agent_key in agent_keys or []:
            self.client.query(
                "MERGE (a:Agent {key: $key}) "
                "MERGE (d:Decision {id: $id}) "
                "MERGE (d)-[:MADE_BY]->(a)",
                {"id": decision_id, "key": agent_key},
            )
        if engagement_name:
            self.client.query(
                "MERGE (e:Engagement {name: $eng}) "
                "MERGE (d:Decision {id: $id}) "
                "MERGE (d)-[:IN_ENGAGEMENT]->(e)",
                {"id": decision_id, "eng": engagement_name},
            )
        if run_source_id:
            self.client.query(
                "MERGE (s:Source {identifier: $sid, type: 'protocol_run'}) "
                "MERGE (d:Decision {id: $id}) "
                "MERGE (d)-[:SOURCED_FROM]->(s)",
                {"id": decision_id, "sid": run_source_id},
            )

    def write_correction(
        self,
        correction_id: str,
        text: str,
        scope: str,
        target_id: str | None,
        reason: str | None,
        given_by: str,
    ) -> None:
        """MERGE a Correction node. Target scopes: global, client, engagement, protocol, agent, decision."""
        self.client.query(
            "MERGE (cor:Correction {id: $id}) "
            "SET cor.text = $text, cor.scope = $scope, cor.target_id = $target_id, "
            "    cor.reason = $reason, cor.given_by = $given_by, "
            "    cor.given_at = timestamp(), cor.valid_to = NULL",
            {
                "id": correction_id,
                "text": text,
                "scope": scope,
                "target_id": (target_id or "").lower() if target_id else None,
                "reason": reason or "",
                "given_by": given_by,
            },
        )

    def retire_correction(self, correction_id: str) -> None:
        """Set valid_to=now so queries filter it out."""
        self.client.query(
            "MATCH (cor:Correction {id: $id}) SET cor.valid_to = timestamp()",
            {"id": correction_id},
        )

    def list_corrections(self, active_only: bool = True, limit: int = 100) -> list[dict[str, Any]]:
        where = "WHERE cor.valid_to IS NULL OR cor.valid_to > timestamp()" if active_only else ""
        return _rows(
            self.client.query(
                f"MATCH (cor:Correction) {where} "
                "RETURN cor.id AS id, cor.text AS text, cor.scope AS scope, "
                "       cor.target_id AS target_id, cor.reason AS reason, "
                "       cor.given_by AS given_by, cor.given_at AS given_at, "
                "       cor.valid_to AS valid_to "
                "ORDER BY cor.given_at DESC LIMIT "
                f"{int(limit)}"
            )
        )


__all__ = ["GraphQueries"]
