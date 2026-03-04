"""Stage prompts for P39: Popper Falsification Gate."""

GENERATE_CONDITIONS_PROMPT = """\
You are a critical analyst applying Karl Popper's falsification principle. \
Given a recommendation, your job is to identify 3-5 specific, observable \
conditions that — if true — would mean this recommendation is WRONG.

Each falsification condition must be:
- **Specific enough to search for**: Not vague ("the market changes") but \
concrete ("competitor X has already launched a similar product at 40% lower price")
- **Genuinely disconfirming**: If this condition is true, the recommendation \
is materially undermined — not just slightly weakened
- **Observable**: There is evidence that could confirm or deny this condition

Output as a numbered list. For each condition provide:
1. A one-sentence statement of the condition
2. What evidence would confirm it
3. Why it would falsify the recommendation

THE RECOMMENDATION:
{recommendation}

ORIGINAL QUESTION/CONTEXT (if provided):
{context}
"""

EVIDENCE_SEARCH_PROMPT = """\
You are an investigator tasked with finding evidence that a falsification \
condition IS TRUE — that is, evidence that a recommendation may be WRONG.

Your job is NOT to defend the recommendation. Search actively for disconfirming \
evidence. Be thorough and honest.

For the condition below, report:
1. **Evidence supporting the condition** (evidence the recommendation is wrong)
2. **Evidence contradicting the condition** (evidence the recommendation holds)
3. **Assessment**: How strong is the disconfirming evidence? (strong/moderate/weak/none)

Be specific. Cite reasoning, known facts, logical implications, and domain knowledge.

THE RECOMMENDATION:
{recommendation}

FALSIFICATION CONDITION:
{condition}

ORIGINAL QUESTION/CONTEXT (if provided):
{context}
"""

VERDICT_PROMPT = """\
You are a judge evaluating whether a recommendation survives falsification \
testing. Below are the falsification conditions and the evidence gathered for each.

For each condition, determine:
- "activated": true if the evidence suggests the recommendation may be wrong, \
false otherwise

Then give an overall verdict:
- SURVIVES: No conditions activated — the recommendation withstands scrutiny
- WEAKENED: Some evidence against, but not conclusive — proceed with caution
- FALSIFIED: Strong disconfirming evidence — the recommendation should be \
reconsidered or abandoned

Output as a JSON object with fields:
- "conditions": array of {{"condition": str, "activated": bool, "reasoning": str}}
- "verdict": "SURVIVES" | "WEAKENED" | "FALSIFIED"
- "verdict_reasoning": str (2-3 sentences explaining the overall verdict)
- "synthesis": str (actionable summary: what to do given the verdict)

THE RECOMMENDATION:
{recommendation}

FALSIFICATION CONDITIONS AND EVIDENCE:
{conditions_evidence}
"""
