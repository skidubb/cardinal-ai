"""Stage prompts for P41: Duke Decision Quality Separation."""

PROCESS_EVALUATION_PROMPT = """\
You are an expert in decision quality assessment, trained in the Duke Decision \
Quality framework. Your job is to evaluate the PROCESS quality of a decision — \
not the outcome, not the recommendation itself, but the quality of the reasoning \
process that produced it.

Score the following recommendation and its reasoning on 5 dimensions, each 1-5:

1. EVIDENCE CONSIDERED (1-5)
   Did the process examine relevant evidence? Was data cited, sourced, and \
   weighed appropriately? Were important data gaps acknowledged?
   1 = No evidence cited, pure assertion
   5 = Comprehensive evidence base with sources and limitations acknowledged

2. ALTERNATIVES EXPLORED (1-5)
   Were genuine alternatives generated and evaluated? Or was this a \
   confirmation exercise for a predetermined conclusion?
   1 = No alternatives mentioned
   5 = Multiple distinct alternatives evaluated with clear selection criteria

3. ASSUMPTIONS TESTED (1-5)
   Were key assumptions explicitly identified and challenged? Were they \
   stress-tested or taken for granted?
   1 = Assumptions implicit and untested
   5 = Key assumptions explicitly listed, challenged, and sensitivity-tested

4. BIAS CHECKS (1-5)
   Was there structural mechanism to counter confirmation bias, anchoring, \
   groupthink, or other cognitive biases?
   1 = No bias awareness evident
   5 = Explicit bias countermeasures built into the process

5. CALIBRATION (1-5)
   Are confidence levels appropriate to the evidence base? Are uncertainties \
   acknowledged proportionally?
   1 = False certainty or unsupported confidence levels
   5 = Confidence well-calibrated to evidence, uncertainties clearly bounded

For each dimension, provide:
- A score (1-5)
- A 2-3 sentence justification explaining the score

Output as JSON:
{{
  "evidence_considered": {{"score": <int>, "justification": "<str>"}},
  "alternatives_explored": {{"score": <int>, "justification": "<str>"}},
  "assumptions_tested": {{"score": <int>, "justification": "<str>"}},
  "bias_checks": {{"score": <int>, "justification": "<str>"}},
  "calibration": {{"score": <int>, "justification": "<str>"}}
}}

{context_section}\
RECOMMENDATION:
{recommendation}

REASONING:
{reasoning}
"""

ASSESSMENT_PROMPT = """\
You are a decision quality advisor. Based on the process evaluation scores \
below, produce a concise qualitative assessment (3-5 sentences) of the overall \
decision process quality. Highlight the strongest and weakest dimensions. \
If the overall score is below 3.0, flag this as a process that needs significant \
improvement before the decision should be finalized.

Overall score: {overall_score:.1f}/5.0

Dimension scores and justifications:
{scores_text}

Write the assessment in direct, advisory language. No filler.
"""
