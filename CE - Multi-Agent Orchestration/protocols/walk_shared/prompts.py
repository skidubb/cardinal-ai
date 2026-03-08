"""Shared prompt templates for the Walk protocol family (P49-P52).

Six stage prompts used across all Walk variants. Individual variants
can override these in their own prompts.py.
"""

from __future__ import annotations

# ── Stage 0: Frame ───────────────────────────────────────────────────────────

FRAME_PROMPT = """\
You are a problem framing specialist. Decompose the following question into \
its structural components. Do NOT solve the problem. Only clarify what it is.

QUESTION:
{question}

Produce a JSON object with exactly these fields:
{{
  "question": "<the original question>",
  "objective": "<what a good answer would achieve>",
  "constraints": ["<real constraints>"],
  "assumptions": ["<assumptions embedded in the question>"],
  "known_dead_ends": ["<approaches that have already failed or are off the table>"],
  "ambiguity_map": ["<areas of genuine ambiguity or multiple interpretation>"],
  "unresolved_tensions": ["<contradictions or trade-offs within the problem>"]
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 1: Shallow Walk ────────────────────────────────────────────────────

SHALLOW_WALK_PROMPT = """\
You are a cognitive lens. Your lens family is: {lens_family}.

Your task: reframe the problem below through your specific lens. \
Do NOT solve the problem. Reframe it. Surface what the default framing misses.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "lens_family": "{lens_family}",
  "reframe": "<one reframing of the problem through your lens>",
  "hidden_variable": "<one variable the incumbent frame ignores>",
  "blind_spot": "<one blind spot in the current framing>",
  "testable_implication": "<one falsifiable prediction from your reframing>"
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 2: Salience Scoring ────────────────────────────────────────────────

SALIENCE_JUDGE_PROMPT = """\
You are a meta-cognitive salience judge. Score each lens output below on four \
dimensions (1-10 scale):

- **novelty**: Does this say something the obvious analysis would miss?
- **explanatory_power**: Does this account for more evidence than the default frame?
- **actionability**: Does this lead to concretely different decisions?
- **cognitive_distance**: How far is this perspective from the default frame?

Composite = 0.30 * novelty + 0.25 * explanatory_power + 0.25 * actionability + 0.20 * cognitive_distance

PROBLEM FRAME:
{frame_json}

SHALLOW LENS OUTPUTS:
{shallow_outputs_json}

Produce a JSON object with exactly these fields:
{{
  "ranked_outputs": [
    {{
      "agent_key": "<key>",
      "novelty": <1-10>,
      "explanatory_power": <1-10>,
      "actionability": <1-10>,
      "cognitive_distance": <1-10>,
      "composite": <weighted score>,
      "rationale": "<1-2 sentence justification>"
    }}
  ],
  "top_tensions": ["<tensions between the most interesting outputs>"],
  "candidate_hypotheses": ["<hypotheses worth testing in deep walk>"]
}}

Sort ranked_outputs by composite descending. Output ONLY the JSON object."""

# ── Stage 3: Deep Walk ──────────────────────────────────────────────────────

DEEP_WALK_PROMPT = """\
You are a promoted cognitive lens. You scored high enough in the shallow walk \
to earn a deep exploration. Now go deeper.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

YOUR SHALLOW OUTPUT:
{shallow_output_json}

OTHER PROMOTED LENSES (for cross-reference):
{other_promoted_json}

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "thesis": "<your strongest thesis from this lens>",
  "critique_of_incumbent_frame": "<what the default framing gets wrong>",
  "critique_of_other_lens": "<name one other promoted lens and critique it>",
  "decision_implication": "<what would change if your thesis is correct>",
  "disconfirming_evidence": "<what evidence would prove your thesis wrong>",
  "priority_test": "<one high-value experiment to validate or invalidate>"
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 4: Cross-Examination ──────────────────────────────────────────────

CROSS_EXAM_PROMPT = """\
You are the challenger lens ({challenger_key}). Your job is to cross-examine \
the target lens's deep output. Find its weakest assumption and attack it.

TARGET LENS DEEP OUTPUT:
{target_deep_output_json}

YOUR OWN DEEP OUTPUT (for context):
{challenger_deep_output_json}

Produce a JSON object with exactly these fields:
{{
  "challenger_key": "{challenger_key}",
  "target_key": "{target_key}",
  "strongest_opposing_claim": "<the strongest argument against the target's thesis>",
  "settling_evidence": "<what evidence would resolve this disagreement>",
  "concession": "<what you concede the target lens gets right>"
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 5: Synthesis ──────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """\
You are the Walk Synthesizer. You have seen a problem explored through \
multiple cognitive lenses — from systems thinking to poetry to statistics. \
Now synthesize.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

SHALLOW WALK OUTPUTS:
{shallow_outputs_json}

SALIENCE RANKINGS:
{salience_json}

DEEP WALK OUTPUTS:
{deep_outputs_json}

CROSS-EXAMINATIONS:
{cross_exam_json}

Produce a JSON object with exactly these fields:
{{
  "best_current_interpretation": "<the most defensible interpretation given all lenses>",
  "competing_interpretations": ["<other plausible interpretations that remain live>"],
  "walk_added_value": "<what this walk surfaced that a narrower expert stack would miss>",
  "decision_changes": ["<concrete decisions that change based on the walk>"],
  "experiments": ["<high-value experiments to run>"],
  "success_signals": ["<what success looks like if the best interpretation is correct>"],
  "kill_criteria": ["<conditions under which the best interpretation should be abandoned>"],
  "what_would_change_view": "<what evidence would fundamentally change the conclusion>"
}}

Output ONLY the JSON object.

Then, after the JSON, write a prose synthesis (2-4 paragraphs) that a \
decision-maker could read without seeing the JSON. Start the prose section \
with "---PROSE---" on its own line."""
