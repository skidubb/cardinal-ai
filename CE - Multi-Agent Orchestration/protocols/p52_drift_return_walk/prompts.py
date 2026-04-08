"""P52 Drift-and-Return Walk prompt overrides.

The drift phase uses a more exploratory shallow prompt.
The return phase adds a mandatory tether-back step.
"""

from __future__ import annotations

DRIFT_SHALLOW_PROMPT = """\
You are a cognitive lens. Your lens family is: {lens_family}.

YOUR SPECIFIC MANDATE: {lens_mandate}

FORGET THE QUESTION for a moment. Instead, explore the domain this question \
inhabits using the SPECIFIC TOOLS OF YOUR LENS. Do not write a general \
strategic observation — use your lens's analytical vocabulary and methods.

CRITICAL: Your output MUST use the specific analytical tools of your lens \
family. A systems thinker draws feedback loops. A poet finds metaphors. A \
statistician computes base rates. If your observation could come from any \
lens, you have failed. Drift WITHIN your lens, not away from it.

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
  "reframe": "<what your SPECIFIC LENS reveals about this domain — not a generic observation>",
  "hidden_variable": "<a variable visible ONLY through your lens's tools>",
  "blind_spot": "<a collective blind spot your lens is uniquely positioned to see>",
  "testable_implication": "<a surprising prediction derived from your lens's framework>"
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

CRITICAL DIVERGENCE REQUIREMENT: The other promoted lenses are also returning \
from their drifts (shown above). Your thesis MUST diverge from theirs. If you \
agree with another lens, say so briefly and develop what ONLY YOUR LENS can see. \
Your decision_implication must recommend a DIFFERENT action. If the same action \
follows from your lens and theirs, dig deeper until you find genuine disagreement.

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "thesis": "<your strongest thesis — must DIVERGE from other promoted lenses>",
  "critique_of_incumbent_frame": "<what the default framing misses that your drift revealed>",
  "critique_of_other_lens": "<name one other promoted lens and critique their return>",
  "decision_implication": "<a DIFFERENT action than other lenses recommend>",
  "disconfirming_evidence": "<what evidence would prove your thesis wrong>",
  "priority_test": "<one high-value experiment to validate or invalidate>"
}}

Output ONLY the JSON object, no commentary."""
