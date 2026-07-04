"""Smoke tests for ce-graph.

Two tiers:

* Unit tests (default) -- import + entity-shape only, no FalkorDB needed.
* Integration tests (``-m integration``) -- require running FalkorDB on
  localhost:6379. Spin one up with ``docker compose up -d`` from this dir.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


# ---- Unit tests --------------------------------------------------------


def test_entities_import() -> None:
    from ce_graph import (
        Agent,
        Client,
        Correction,
        Decision,
        Engagement,
        Lesson,
        Protocol,
    )
    assert Client and Engagement and Decision and Correction
    assert Agent and Protocol and Lesson


def test_client_construction() -> None:
    from ce_graph import Client
    from ce_graph.entities import ClientStatus

    c = Client(name="acme corp", display_name="Acme Corp", vertical="B2B SaaS")
    assert c.name == "acme corp"
    assert c.status == ClientStatus.PROSPECT.value


def test_correction_scope_required() -> None:
    from ce_graph import Correction
    from ce_graph.entities import CorrectionScope

    cor = Correction(
        text="Don't pitch Acme aggressive sales tactics; they hate them.",
        scope=CorrectionScope.CLIENT,
        target_id="acme corp",
        reason="Founder explicitly told us in Q4 2025 discovery call.",
        given_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    assert cor.scope == CorrectionScope.CLIENT.value
    assert cor.target_id == "acme corp"


def test_decision_with_protocol() -> None:
    from ce_graph import Decision

    d = Decision(
        summary="Recommend tier-3 pricing restructure for Acme",
        rationale="MEDDPICC analysis showed Champion + Economic Buyer alignment",
        engagement_name="acme-q1-2026-audit",
        protocol_code="P16",
        agent_keys=["cfo", "cmo", "gtm-vp-sales"],
        confidence=0.78,
    )
    assert d.protocol_code == "P16"
    assert "cfo" in d.agent_keys


# ---- Integration tests (require running FalkorDB) ----------------------


@pytest.mark.integration
def test_falkor_connect_and_seed() -> None:
    from ce_graph.falkor_client import FalkorClient

    client = FalkorClient(graph_name="ce_graph_smoke_test")
    client.ensure_indexes()

    client.query("MERGE (c:Client {name: 'smoke-test-co'}) SET c.vertical = 'Test'")
    result = client.query("MATCH (c:Client {name: 'smoke-test-co'}) RETURN c.name")
    assert result.result_set[0][0] == "smoke-test-co"

    client.query("MATCH (c:Client {name: 'smoke-test-co'}) DELETE c")


@pytest.mark.integration
def test_protocol_seeder_runs() -> None:
    """End-to-end: discover protocols and seed them. Idempotent."""
    import asyncio

    from ce_graph.scripts.seed_protocols import seed

    rc = asyncio.run(seed())
    assert rc == 0


@pytest.mark.integration
def test_query_helpers() -> None:
    from ce_graph.falkor_client import FalkorClient
    from ce_graph.queries import GraphQueries

    q = GraphQueries(FalkorClient.for_tenant("cardinal-element"))
    stats = q.graph_stats()
    assert isinstance(stats, dict)
    assert "Protocol" in stats


def test_graph_queries_requires_client() -> None:
    """Regression: GraphQueries must not silently default to cardinal-element."""
    from ce_graph.queries import GraphQueries
    with pytest.raises((TypeError, ValueError)):
        GraphQueries(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        GraphQueries()  # type: ignore[call-arg]
