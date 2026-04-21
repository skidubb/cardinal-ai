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


__all__ = ["GraphQueries"]
