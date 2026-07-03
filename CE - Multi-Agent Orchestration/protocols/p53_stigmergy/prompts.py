"""Prompts for the P53 Stigmergy protocol.

Reuses shared fragments so future prompt-fragment upgrades propagate here
automatically. Trace typology and strength scale are protocol-specific.
"""

from __future__ import annotations

from protocols.prompt_fragments import (
    DEFAULT_PROHIBITIONS,
    JSON_ARRAY_INSTRUCTION,
    agent_framing,
)


TRACE_TYPOLOGY = """\
Trace types (choose one per trace):
- risk          — something that could break the plan
- opportunity   — something that could compound value
- constraint    — a hard boundary that limits options
- insight       — a non-obvious reframing or observation
- question      — an unresolved question that others should investigate

Trace strength scale:
- 0.3 — mild signal, worth noting
- 0.6 — clear signal, worth attention
- 0.9 — strong signal, decision-critical

Location is a short kebab-case identifier for the topic-facet the trace attaches
to (e.g. "unit-economics", "regulatory-risk", "team-capacity", "market-timing").
Pick locations that other agents will naturally use — reusing an existing
location amplifies its cumulative strength."""


def initial_wave_prompt(question: str, agent_name: str, agent_role: str) -> str:
    """First-wave prompt: agent seeds the trace field with 2-4 traces."""
    header = agent_framing(agent_name, agent_role)
    return f"""\
{header}

Question:
{question}

You are contributing to a stigmergic decision process. Instead of writing a
recommendation, you drop 2-4 typed traces on locations that matter for this
question. Later agents will read your traces and add their own — the emergent
trace field IS the analysis.

{TRACE_TYPOLOGY}

{DEFAULT_PROHIBITIONS}

Emit 2-4 traces as a JSON array with this exact shape:
[
  {{
    "type": "<risk|opportunity|constraint|insight|question>",
    "location": "<kebab-case topic facet>",
    "strength": <0.3|0.6|0.9>,
    "content": "<one specific sentence — no meta-commentary, no hedging>"
  }},
  ...
]

{JSON_ARRAY_INSTRUCTION}
"""


def reaction_wave_prompt(
    question: str,
    agent_name: str,
    agent_role: str,
    trace_field: str,
    wave_number: int,
) -> str:
    """Later-wave prompt: agent reacts to the accumulated field."""
    header = agent_framing(agent_name, agent_role)
    return f"""\
{header}

Question:
{question}

You are contributing to wave {wave_number} of a stigmergic decision process.
Earlier agents dropped traces on the question — the accumulated field is
below. Trace strength has been decayed by wave count; hot locations are still
strong.

Current trace field (sorted by cumulative strength):
{trace_field}

Your job:
1. Notice which locations are already hot — you may add traces there to amplify
   convergence, or open a new location if you see a genuine blind spot.
2. Notice which trace TYPES are underrepresented for this question and consider
   contributing there (a field with all risks and no constraints, or all
   insights and no questions, is likely incomplete).
3. Drop 2-4 new traces. Do NOT restate anyone else's trace — either amplify
   (same location, different content) or seed a new location.

{TRACE_TYPOLOGY}

{DEFAULT_PROHIBITIONS}

Emit 2-4 traces as a JSON array with the same shape as before:
[
  {{"type": "...", "location": "...", "strength": ..., "content": "..."}},
  ...
]

{JSON_ARRAY_INSTRUCTION}
"""
