"""Prompts for the P16 Analysis of Competing Hypotheses protocol."""

HYPOTHESIS_GENERATION_PROMPT = """\
You are participating in an Analysis of Competing Hypotheses (ACH) exercise.

Question under analysis:
{question}

Your role: {agent_name}
{system_prompt}

Generate 2-3 plausible, mutually distinguishable hypotheses that could explain or answer the question above. Each hypothesis should be a substantive claim, not a vague possibility.

Respond in JSON:
{{
  "hypotheses": [
    {{"id": "H1", "label": "short label", "description": "one-sentence description"}},
    {{"id": "H2", "label": "short label", "description": "one-sentence description"}}
  ]
}}
"""

EVIDENCE_LISTING_PROMPT = """\
You are participating in an Analysis of Competing Hypotheses (ACH) exercise.

Question under analysis:
{question}

Your role: {agent_name}
{system_prompt}

The team has consolidated the following hypotheses:
{hypotheses_block}

Identify 3-5 key evidence items (facts, observations, trends, data points) that are relevant to evaluating these hypotheses. Focus on evidence that helps DIFFERENTIATE between hypotheses rather than evidence consistent with all of them.

Respond in JSON:
{{
  "evidence": [
    {{"id": "E1", "description": "concise description of the evidence item"}},
    {{"id": "E2", "description": "concise description of the evidence item"}}
  ]
}}
"""

MATRIX_SCORING_PROMPT = """\
You are scoring an evidence-hypothesis matrix for an ACH exercise.

Question under analysis:
{question}

Evidence item:
{evidence_description}

Hypotheses:
{hypotheses_block}

For this evidence item, score its relationship to EACH hypothesis as:
- C (Consistent): the evidence supports or is expected under this hypothesis
- I (Inconsistent): the evidence contradicts or is unlikely under this hypothesis
- N (Neutral): the evidence neither supports nor contradicts this hypothesis

Respond in JSON:
{{
  "scores": [
    {{"hypothesis_id": "H1", "score": "C", "reasoning": "brief explanation"}},
    {{"hypothesis_id": "H2", "score": "I", "reasoning": "brief explanation"}}
  ]
}}
"""

SENSITIVITY_SYNTHESIS_PROMPT = """\
You are the lead analyst synthesizing an Analysis of Competing Hypotheses (ACH) exercise.

Question under analysis:
{question}

The ACH matrix has been scored and analyzed. Here are the results:

## Hypotheses (ranked by survival):
{surviving_block}

## Eliminated Hypotheses:
{eliminated_block}

## Evidence-Hypothesis Matrix:
{matrix_block}

## Most Diagnostic Evidence:
{diagnostic_block}

Produce a final assessment that includes:
1. **Conclusion**: Which hypothesis is best supported and why (focus on which had the LEAST inconsistent evidence, per ACH methodology)
2. **Confidence Level**: High / Medium / Low with justification
3. **Key Uncertainties**: What evidence, if obtained, would change the assessment
4. **Sensitivity Notes**: Which pieces of evidence were most diagnostic (differentiated between hypotheses) and how sensitive is the conclusion to re-evaluating them

Respond in JSON:
{{
  "conclusion": "paragraph summarizing the most supported hypothesis",
  "winning_hypothesis_id": "H#",
  "confidence": "High|Medium|Low",
  "confidence_reasoning": "why this confidence level",
  "key_uncertainties": ["uncertainty 1", "uncertainty 2"],
  "sensitivity_notes": "paragraph on diagnostic evidence and sensitivity"
}}
"""
