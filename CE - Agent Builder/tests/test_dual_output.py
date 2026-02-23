"""Tests for dual-audience artifact generation."""

from csuite.formatters.dual_output import (
    DeliverableRenderer,
    DualArtifact,
    ProcessNarrativeRenderer,
    build_dual_artifact,
)
from csuite.tracing.graph import ActionType, CausalGraph


def test_dual_artifact_model():
    artifact = DualArtifact(
        deliverable="# Report",
        process_narrative="The team discussed...",
        causal_summary="Trace summary",
    )
    assert artifact.deliverable == "# Report"
    assert artifact.process_narrative == "The team discussed..."


def test_deliverable_renderer_passthrough():
    md = "# Strategy Report\n\nContent here."
    result = DeliverableRenderer.render(md)
    assert result == md


def test_deliverable_renderer_appends_synthesis():
    md = "# Report"
    synthesis = "Final recommendation"
    result = DeliverableRenderer.render(md, synthesis)
    assert "Final recommendation" in result
    assert "Executive Synthesis" in result


def test_deliverable_renderer_no_duplicate_synthesis():
    md = "# Report\n\nFinal recommendation"
    synthesis = "Final recommendation"
    result = DeliverableRenderer.render(md, synthesis)
    assert result == md  # Synthesis already in output


def test_process_narrative_renderer():
    graph = CausalGraph()
    graph.add_node("cfo", ActionType.PROPOSE, "Budget plan for Q2")
    graph.add_node("cmo", ActionType.REVISE, "Adjusted marketing spend")

    narrative = ProcessNarrativeRenderer.render(graph, "Q2 Planning")
    assert "Q2 Planning" in narrative
    assert "CFO" in narrative
    assert "CMO" in narrative
    assert "Process Summary" in narrative


def test_process_narrative_empty():
    graph = CausalGraph()
    narrative = ProcessNarrativeRenderer.render(graph)
    assert "No process trace" in narrative


def test_build_dual_artifact_with_graph():
    graph = CausalGraph(event_id="test")
    graph.add_node("ceo", ActionType.PROPOSE, "Expand into AI")
    graph.add_node("cfo", ActionType.CONSTRAIN, "Budget limit $1M")

    dual = build_dual_artifact(
        markdown_output="# Meeting Output",
        synthesis="Consensus reached",
        graph=graph,
        event_topic="AI Expansion",
    )
    assert isinstance(dual, DualArtifact)
    assert "Meeting Output" in dual.deliverable
    assert "Consensus reached" in dual.deliverable
    assert "CEO" in dual.process_narrative
    assert "Causal Trace" in dual.causal_summary


def test_build_dual_artifact_no_graph():
    dual = build_dual_artifact(
        markdown_output="# Report",
        synthesis=None,
        graph=None,
    )
    assert dual.deliverable == "# Report"
    assert "No process trace" in dual.process_narrative
    assert dual.causal_summary == ""
