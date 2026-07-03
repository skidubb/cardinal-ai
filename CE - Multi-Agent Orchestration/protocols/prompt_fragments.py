"""Shared prompt fragments used across multiple protocols.

Every protocol was re-declaring the same JSON-envelope instructions, C/I/N scales,
"PROHIBITED" headers, and agent-framing boilerplate. This module consolidates the
reusable pieces so prompts stay consistent and drift is bounded to one file.

Usage in a protocol's `prompts.py`:

    from protocols.prompt_fragments import (
        JSON_ONLY_INSTRUCTION,
        CIN_SCALE_SCORING,
        PROHIBITED_HEADER,
        agent_framing,
    )

    MY_PROMPT = f\"\"\"You are analyzing X.

    {PROHIBITED_HEADER}
    - Do not fabricate data.
    - Do not exceed 200 words.

    {CIN_SCALE_SCORING}

    {JSON_ONLY_INSTRUCTION}
    \"\"\"

Never edit prompts by concatenating this module's constants into the body of a
larger prompt with format-string interpolation without escaping — braces in these
fragments are literal, not template placeholders.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Output-format instructions
# ---------------------------------------------------------------------------

JSON_ONLY_INSTRUCTION = (
    "Respond ONLY with a JSON object. No prose before or after. No markdown fences."
)

JSON_ARRAY_INSTRUCTION = (
    "Respond ONLY with a JSON array. No prose before or after. No markdown fences."
)

STRUCTURED_THEN_PROSE_INSTRUCTION = (
    "Respond with a JSON object on the first line, then a blank line, "
    "then a short prose summary. The JSON must be parseable independently."
)


# ---------------------------------------------------------------------------
# Scoring scales
# ---------------------------------------------------------------------------

CIN_SCALE_SCORING = """\
Score each item on the C/I/N scale:
- C (Consistency): 1-5. 1 = contradicts known evidence, 5 = strongly consistent.
- I (Impact): 1-5. 1 = negligible, 5 = decision-changing.
- N (Novelty): 1-5. 1 = restates the obvious, 5 = surfaces a new frame.
Use integers only. Do not use half-points."""

ONE_TO_FIVE_SCALE = (
    "Score on a 1-5 integer scale where 1 is the weakest and 5 is the strongest. "
    "Do not use half-points."
)

CONFIDENCE_SCALE = (
    "Report confidence as an integer 0-100. "
    "0 = pure guess. 50 = balanced. 100 = certain and defensible."
)


# ---------------------------------------------------------------------------
# Constraint blocks
# ---------------------------------------------------------------------------

PROHIBITED_HEADER = "PROHIBITED (following any of these voids the response):"

REQUIRED_HEADER = "REQUIRED (all of the following must hold):"

# Default prohibitions that apply to almost every agent call.
DEFAULT_PROHIBITIONS = f"""\
{PROHIBITED_HEADER}
- Do not fabricate quantitative claims. If you don't know a number, say so.
- Do not restate the question back at the user.
- Do not add caveats about "as an AI" or "I don't have access to real-time data".
- Do not exceed the specified length or output structure."""


# ---------------------------------------------------------------------------
# Agent framing
# ---------------------------------------------------------------------------

def agent_framing(agent_name: str, agent_role: str, context: str | None = None) -> str:
    """Standard opening block for a per-agent prompt.

    Keeps role framing consistent across protocols so a synthesizer that inspects
    multiple agent outputs can rely on the same header shape.
    """
    parts = [f"You are {agent_name}, {agent_role}."]
    if context:
        parts.append(f"\nContext:\n{context}")
    return "\n".join(parts)


def role_scoped(prompt_body: str, role: str) -> str:
    """Wrap a prompt body with an explicit role scope header.

    Useful when the same body is reused across roles and the only difference is the
    lens ("as CFO", "as CTO", …). Keeps the role prefix consistent so downstream
    parsers can strip it.
    """
    return f"[Role: {role}]\n{prompt_body.strip()}"


# ---------------------------------------------------------------------------
# Synthesis framing
# ---------------------------------------------------------------------------

SYNTHESIS_PREAMBLE = """\
You are synthesizing outputs from multiple independent agents. Your job is not to
average their answers — it is to identify:
  1. Points of agreement (what they converge on and why)
  2. Points of disagreement (what they contest and what evidence would resolve it)
  3. Blind spots (what none of them addressed but should have)
  4. The best-supported recommendation, with named dissenters."""


ADVERSARIAL_PREAMBLE = """\
You are running an adversarial verification pass. Your default is to REFUTE the
claim under review — the burden of proof is on the claim, not on the refutation.
State the strongest concrete counterexample or failure mode you can construct."""
