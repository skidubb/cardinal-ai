"""Knowledge graph layer for Cardinal Element.

Built on Graphiti (temporal knowledge graphs for agent memory) backed by
FalkorDB (sub-10ms graph queries). Provides Cardinal-Element-specific
entity types and Cypher query helpers for the C-Suite agents to share
institutional memory across engagements.

Quick start:
    from ce_graph import GraphClient, Client, Engagement, Decision

    graph = await GraphClient.connect()
    await graph.upsert(Client(name="Acme Corp", vertical="SaaS"))
    decisions = await graph.find_decisions_for_client("Acme Corp")
"""

from ce_graph.entities import (
    Agent,
    Client,
    Correction,
    Decision,
    Deliverable,
    Engagement,
    Lesson,
    Person,
    Protocol,
    Source,
    Vertical,
)
from ce_graph.falkor_client import FalkorClient
from ce_graph.graphiti_client import GraphClient

__all__ = [
    "Agent",
    "Client",
    "Correction",
    "Decision",
    "Deliverable",
    "Engagement",
    "FalkorClient",
    "GraphClient",
    "Lesson",
    "Person",
    "Protocol",
    "Source",
    "Vertical",
]

__version__ = "0.1.0"
