"""
Causal graph: DAG of TraceNodes built during events/debates.

Each node records an agent action (propose, constrain, revise, reject, accept)
with links to evidence sources and parent nodes that caused it.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ActionType(StrEnum):
    PROPOSE = "propose"
    CONSTRAIN = "constrain"
    REVISE = "revise"
    REJECT = "reject"
    ACCEPT = "accept"
    EVIDENCE = "evidence"
    SYNTHESIZE = "synthesize"


class TraceNode(BaseModel):
    """A single node in the causal trace DAG."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_role: str
    action_type: ActionType
    content: str
    evidence_sources: list[str] = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CausalGraph:
    """DAG of TraceNodes built during an event or debate."""

    def __init__(self, event_id: str = ""):
        self.event_id = event_id or uuid.uuid4().hex[:8]
        self.nodes: dict[str, TraceNode] = {}

    def add_node(
        self,
        agent_role: str,
        action_type: ActionType | str,
        content: str,
        evidence_sources: list[str] | None = None,
        parent_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceNode:
        """Add a node to the graph and return it."""
        if isinstance(action_type, str):
            action_type = ActionType(action_type)
        node = TraceNode(
            agent_role=agent_role,
            action_type=action_type,
            content=content[:2000],
            evidence_sources=evidence_sources or [],
            parent_ids=parent_ids or [],
            metadata=metadata or {},
        )
        self.nodes[node.id] = node
        return node

    def get_roots(self) -> list[TraceNode]:
        """Return nodes with no parents (entry points)."""
        return [n for n in self.nodes.values() if not n.parent_ids]

    def get_children(self, node_id: str) -> list[TraceNode]:
        """Return nodes that have node_id as a parent."""
        return [n for n in self.nodes.values() if node_id in n.parent_ids]

    def get_ancestors(self, node_id: str) -> list[TraceNode]:
        """Return all ancestor nodes (transitive parents)."""
        visited: set[str] = set()
        stack = [node_id]
        ancestors: list[TraceNode] = []
        while stack:
            nid = stack.pop()
            node = self.nodes.get(nid)
            if not node:
                continue
            for pid in node.parent_ids:
                if pid not in visited and pid in self.nodes:
                    visited.add(pid)
                    ancestors.append(self.nodes[pid])
                    stack.append(pid)
        return ancestors

    def node_count(self) -> int:
        return len(self.nodes)

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph for storage."""
        return {
            "event_id": self.event_id,
            "nodes": {nid: n.model_dump(mode="json") for nid, n in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CausalGraph:
        """Deserialize graph from storage."""
        graph = cls(event_id=data.get("event_id", ""))
        for nid, ndata in data.get("nodes", {}).items():
            node = TraceNode(**ndata)
            graph.nodes[nid] = node
        return graph


class TraceRenderer:
    """Renders a CausalGraph into human-readable narratives."""

    @staticmethod
    def render_markdown(graph: CausalGraph) -> str:
        """Generate a markdown narrative from the causal DAG."""
        if not graph.nodes:
            return "_No causal trace recorded._"

        lines = ["## Causal Trace", ""]

        # Group by agent
        by_agent: dict[str, list[TraceNode]] = {}
        for node in sorted(graph.nodes.values(), key=lambda n: n.timestamp):
            by_agent.setdefault(node.agent_role, []).append(node)

        # Build narrative
        sorted_nodes = sorted(graph.nodes.values(), key=lambda n: n.timestamp)
        for node in sorted_nodes:
            role_label = node.agent_role.upper()
            action = node.action_type.value

            parent_context = ""
            if node.parent_ids:
                parent_nodes = [graph.nodes[pid] for pid in node.parent_ids if pid in graph.nodes]
                if parent_nodes:
                    refs = [f"{p.agent_role.upper()} ({p.action_type.value})" for p in parent_nodes]
                    parent_context = f" [responding to: {', '.join(refs)}]"

            evidence_context = ""
            if node.evidence_sources:
                evidence_context = f" [evidence: {', '.join(node.evidence_sources[:3])}]"

            summary = node.content[:200] + ("..." if len(node.content) > 200 else "")
            lines.append(
                f"- **{role_label}** [{action}]{parent_context}"
                f"{evidence_context}: {summary}"
            )

        lines.append("")
        lines.append(f"_Trace contains {graph.node_count()} nodes across "
                      f"{len(by_agent)} agents._")
        return "\n".join(lines)

    @staticmethod
    def render_narrative(graph: CausalGraph) -> str:
        """Generate a prose narrative suitable for non-technical audiences."""
        if not graph.nodes:
            return "No reasoning trace was recorded for this event."

        sorted_nodes = sorted(graph.nodes.values(), key=lambda n: n.timestamp)
        paragraphs: list[str] = []

        for node in sorted_nodes:
            role = node.agent_role.upper()
            action = node.action_type.value

            if action == "evidence":
                sources = (
                    ", ".join(node.evidence_sources[:3])
                    if node.evidence_sources else "knowledge base"
                )
                paragraphs.append(
                    f"The {role} gathered evidence from {sources}: {node.content[:150]}"
                )
            elif action == "propose":
                paragraphs.append(f"The {role} proposed: {node.content[:200]}")
            elif action == "constrain":
                paragraphs.append(f"The {role} flagged a constraint: {node.content[:200]}")
            elif action == "revise":
                parent_roles = []
                for pid in node.parent_ids:
                    parent = graph.nodes.get(pid)
                    if parent:
                        parent_roles.append(parent.agent_role.upper())
                trigger = f" in response to {', '.join(parent_roles)}" if parent_roles else ""
                paragraphs.append(
                    f"The {role} revised their position{trigger}: {node.content[:200]}"
                )
            elif action == "accept":
                paragraphs.append(f"The {role} accepted: {node.content[:200]}")
            elif action == "reject":
                paragraphs.append(f"The {role} rejected: {node.content[:200]}")
            elif action == "synthesize":
                paragraphs.append(f"Final synthesis: {node.content[:300]}")

        return " ".join(paragraphs)
