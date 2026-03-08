"""P52 Drift-and-Return Walk prompt overrides.

The drift phase uses a more exploratory shallow prompt.
The return phase adds a mandatory tether-back step.
"""

from __future__ import annotations

DRIFT_SHALLOW_PROMPT = """\
You are a cognitive lens. Your lens family is: {lens_family}.

FORGET THE QUESTION for a moment. Instead, explore the domain this question \
inhabits. What is the most interesting, surprising, or underappreciated dynamic \
in this space? What would an outsider notice that an insider has normalized?

Do NOT solve anything. Do NOT address the question directly. Drift.

DOMAIN CONTEXT (the question for reference only — do not answer it):
{question}

PROBLEM FRAME:
{frame_json}

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "lens_family": "{lens_family}",
  "reframe": "<the most interesting thing you notice in this domain>",
  "hidden_variable": "<a variable everyone in this domain ignores>",
  "blind_spot": "<a collective blind spot in how this domain thinks>",
  "testable_implication": "<a surprising prediction from your observation>"
}}

Output ONLY the JSON object, no commentary."""

RETURN_DEEP_PROMPT = """\
You are a promoted cognitive lens returning from the drift phase. You explored \
freely — now RETURN to the question. Connect your drift insight back to the \
original problem. Be explicit about what the drift revealed that directed \
analysis would have missed.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

YOUR DRIFT OUTPUT (from the free exploration phase):
{shallow_output_json}

OTHER PROMOTED LENSES:
{other_promoted_json}

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "thesis": "<your strongest thesis, explicitly connecting drift insight to the question>",
  "critique_of_incumbent_frame": "<what the default framing misses that your drift revealed>",
  "critique_of_other_lens": "<name one other promoted lens and critique their return>",
  "decision_implication": "<what would change if your thesis is correct>",
  "disconfirming_evidence": "<what evidence would prove your thesis wrong>",
  "priority_test": "<one high-value experiment to validate or invalidate>"
}}

Output ONLY the JSON object, no commentary."""
