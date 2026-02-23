"""Stage prompts for P43: Leibniz Auditable Chain."""

DECOMPOSE_PROMPT = """\
You are a reasoning auditor. Your job is to decompose the following \
recommendation and its supporting reasoning into discrete, independently \
verifiable steps.

For each step, produce a JSON object with:
- "step_number" (int starting at 1)
- "input": What information or premise was received as input for this step
- "operation": What reasoning operation was performed (e.g., causal inference, \
analogy, cost-benefit comparison, assumption, data interpretation)
- "output": The conclusion or intermediate result produced
- "verifiable": (boolean) Can an auditor seeing ONLY this step — with no \
prior or subsequent context — determine if the operation was valid?

Output a JSON array of these objects. Aim for 5-15 steps depending on the \
complexity of the reasoning.

RECOMMENDATION:
{recommendation}

REASONING:
{reasoning}
"""

AUDIT_PROMPT = """\
You are an independent reasoning auditor. Below are decomposed reasoning steps \
from a strategic recommendation. For each step, evaluate:

1. Is the input clearly stated?
2. Is the operation logically valid?
3. Does the output follow from the input + operation?
4. Are there hidden assumptions not made explicit?

For any step that has issues, produce a JSON object with:
- "step_number" (int matching the step)
- "finding": A concise description of the issue
- "severity": "critical" | "moderate" | "minor"

Output a JSON array of findings. If a step passes all checks, do NOT include \
it in the output. An empty array [] means all steps passed.

DECOMPOSED STEPS:
{steps_json}
"""

VERDICT_PROMPT = """\
You are producing a final audit verdict. Given the decomposed steps and audit \
findings below, determine the overall auditability and produce a synthesis.

Verdict rules:
- AUDITABLE: All steps passed audit (no findings, or only minor findings)
- PARTIALLY_AUDITABLE: Some steps have moderate issues but no critical failures
- OPAQUE: One or more steps have critical issues

Output exactly this JSON structure:
{{
  "verdict": "AUDITABLE" | "PARTIALLY_AUDITABLE" | "OPAQUE",
  "synthesis": "A 2-4 sentence summary of the audit: what was sound, what was \
problematic, and what would need to change for full auditability."
}}

DECOMPOSED STEPS:
{steps_json}

AUDIT FINDINGS:
{findings_json}
"""
