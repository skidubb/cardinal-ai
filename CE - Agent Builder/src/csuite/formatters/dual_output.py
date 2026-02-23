"""
Dual-Audience Artifact Generation for C-Suite.

Every event produces both a deliverable AND a process narrative simultaneously.
The deliverable is client-facing; the process narrative explains the AI reasoning.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from csuite.tracing.graph import CausalGraph, TraceRenderer


class DualArtifact(BaseModel):
    """Combined output: deliverable + process narrative."""

    deliverable: str
    process_narrative: str
    causal_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessNarrativeRenderer:
    """Generates human-readable story of collaborative reasoning from a CausalGraph."""

    @staticmethod
    def render(graph: CausalGraph, event_topic: str = "") -> str:
        """Render process narrative from causal graph."""
        if not graph or not graph.nodes:
            return "_No process trace available._"

        lines = ["## How We Got Here", ""]
        if event_topic:
            lines.append(f"**Topic:** {event_topic}")
            lines.append("")

        # Use TraceRenderer's narrative for the prose
        narrative = TraceRenderer.render_narrative(graph)
        lines.append(narrative)
        lines.append("")

        # Add summary stats
        agent_roles = set(n.agent_role for n in graph.nodes.values())
        action_counts: dict[str, int] = {}
        for node in graph.nodes.values():
            action_counts[node.action_type.value] = (
                action_counts.get(node.action_type.value, 0) + 1
            )

        lines.append("### Process Summary")
        lines.append("")
        lines.append(f"- **Agents involved:** {', '.join(sorted(r.upper() for r in agent_roles))}")
        lines.append(f"- **Total reasoning steps:** {graph.node_count()}")
        for action, count in sorted(action_counts.items()):
            lines.append(f"  - {action}: {count}")

        return "\n".join(lines)


class DeliverableRenderer:
    """Extracts/formats the client-facing deliverable (existing behavior, formalized)."""

    @staticmethod
    def render(
        markdown_output: str,
        synthesis: str | None = None,
    ) -> str:
        """Return the client-facing deliverable content."""
        # The deliverable is the existing markdown output — synthesis appended if separate
        if synthesis and synthesis not in markdown_output:
            return f"{markdown_output}\n\n---\n\n## Executive Synthesis\n\n{synthesis}"
        return markdown_output


def build_dual_artifact(
    markdown_output: str,
    synthesis: str | None,
    graph: CausalGraph | None,
    event_topic: str = "",
    metadata: dict[str, Any] | None = None,
) -> DualArtifact:
    """Build a DualArtifact from event outputs and causal graph."""
    deliverable = DeliverableRenderer.render(markdown_output, synthesis)

    if graph and graph.nodes:
        process_narrative = ProcessNarrativeRenderer.render(graph, event_topic)
        causal_summary = TraceRenderer.render_markdown(graph)
    else:
        process_narrative = "_No process trace was recorded._"
        causal_summary = ""

    return DualArtifact(
        deliverable=deliverable,
        process_narrative=process_narrative,
        causal_summary=causal_summary,
        metadata=metadata or {},
    )
