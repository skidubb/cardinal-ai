"""
Causal Trace Observation Layer for C-Suite.

Builds a DAG of TraceNodes during events, debates, and agent interactions.
Every decision traces back through: who proposed it, what evidence supported it,
what constraints shaped it, what alternatives were rejected.
"""

from csuite.tracing.graph import CausalGraph, TraceNode, TraceRenderer

__all__ = ["CausalGraph", "TraceNode", "TraceRenderer"]
