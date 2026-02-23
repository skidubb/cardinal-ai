"""Tests for the causal trace observation layer."""

from csuite.tracing.graph import ActionType, CausalGraph, TraceNode, TraceRenderer


def test_causal_graph_add_and_count():
    graph = CausalGraph(event_id="test-001")
    node1 = graph.add_node("cfo", ActionType.PROPOSE, "Budget should be $1M")
    node2 = graph.add_node("cmo", ActionType.PROPOSE, "Marketing needs $500K")
    assert graph.node_count() == 2
    assert node1.id in graph.nodes
    assert node2.id in graph.nodes


def test_causal_graph_parent_links():
    graph = CausalGraph()
    n1 = graph.add_node("cfo", ActionType.PROPOSE, "Budget cap at $1M")
    n2 = graph.add_node("cmo", ActionType.REVISE, "Revised to $800K", parent_ids=[n1.id])
    children = graph.get_children(n1.id)
    assert len(children) == 1
    assert children[0].id == n2.id


def test_causal_graph_ancestors():
    graph = CausalGraph()
    n1 = graph.add_node("cfo", ActionType.EVIDENCE, "Q4 revenue data")
    n2 = graph.add_node("cfo", ActionType.PROPOSE, "Budget plan", parent_ids=[n1.id])
    n3 = graph.add_node("cmo", ActionType.REVISE, "Revised marketing", parent_ids=[n2.id])
    ancestors = graph.get_ancestors(n3.id)
    ancestor_ids = {a.id for a in ancestors}
    assert n1.id in ancestor_ids
    assert n2.id in ancestor_ids


def test_causal_graph_roots():
    graph = CausalGraph()
    n1 = graph.add_node("cfo", ActionType.PROPOSE, "Root node")
    n2 = graph.add_node("cmo", ActionType.REVISE, "Child", parent_ids=[n1.id])
    roots = graph.get_roots()
    assert len(roots) == 1
    assert roots[0].id == n1.id


def test_causal_graph_serialization():
    graph = CausalGraph(event_id="test-serial")
    graph.add_node("ceo", ActionType.PROPOSE, "Strategy X")
    graph.add_node("cfo", ActionType.CONSTRAIN, "Budget limit", evidence_sources=["Q4 report"])

    data = graph.to_dict()
    assert data["event_id"] == "test-serial"
    assert len(data["nodes"]) == 2

    restored = CausalGraph.from_dict(data)
    assert restored.node_count() == 2
    assert restored.event_id == "test-serial"


def test_trace_renderer_markdown():
    graph = CausalGraph()
    graph.add_node("cfo", ActionType.PROPOSE, "Keep budget under $1M")
    graph.add_node("cmo", ActionType.REVISE, "Adjusted spend to $900K")
    md = TraceRenderer.render_markdown(graph)
    assert "CFO" in md
    assert "CMO" in md
    assert "2 nodes" in md


def test_trace_renderer_narrative():
    graph = CausalGraph()
    graph.add_node("ceo", ActionType.EVIDENCE, "Market is growing 20% YoY",
                    evidence_sources=["industry report"])
    graph.add_node("ceo", ActionType.PROPOSE, "We should expand into AI consulting")
    narrative = TraceRenderer.render_narrative(graph)
    assert "CEO" in narrative
    assert "proposed" in narrative


def test_trace_renderer_empty_graph():
    graph = CausalGraph()
    assert "No causal trace" in TraceRenderer.render_markdown(graph)
    assert "No reasoning trace" in TraceRenderer.render_narrative(graph)


def test_action_type_from_string():
    graph = CausalGraph()
    node = graph.add_node("cfo", "propose", "Test string action type")
    assert node.action_type == ActionType.PROPOSE
