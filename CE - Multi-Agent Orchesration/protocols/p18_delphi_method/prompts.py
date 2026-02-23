"""Prompts for the P18 Delphi Method protocol."""

INITIAL_ESTIMATE_PROMPT = """\
You are participating in a Delphi estimation exercise.

Question requiring a numerical estimate:
{question}

Your role: {agent_name}
{system_prompt}

Provide your independent estimate for the question above. Think carefully about the factors that drive this number, and provide a confidence interval (low and high bounds).

Respond in JSON:
{{
  "estimate": 42.5,
  "confidence_low": 30.0,
  "confidence_high": 55.0,
  "reasoning": "Detailed explanation of how you arrived at this estimate, what factors you considered, and what assumptions you made."
}}
"""

REVISION_ESTIMATE_PROMPT = """\
You are participating in a Delphi estimation exercise (Round {round_number}).

Question requiring a numerical estimate:
{question}

Your role: {agent_name}
{system_prompt}

## Your Previous Estimate
- Estimate: {previous_estimate}
- Confidence range: {previous_low} to {previous_high}
- Your reasoning: {previous_reasoning}

## Anonymous Group Statistics (Round {previous_round})
- Median estimate: {median}
- Interquartile range: {iqr_low} to {iqr_high}
- Spread (IQR width): {spread}

## Anonymous Reasoning from Other Panelists
{anonymous_reasoning}

Review the group statistics and reasoning above. You may revise your estimate or keep it the same. If your estimate differs significantly from the median, explain why you believe your position is justified.

Respond in JSON:
{{
  "estimate": 42.5,
  "confidence_low": 30.0,
  "confidence_high": 55.0,
  "reasoning": "Updated explanation — what changed or why you held firm."
}}
"""

FINAL_SYNTHESIS_PROMPT = """\
You are synthesizing the results of a Delphi estimation exercise.

Question:
{question}

The panel went through {rounds_used} round(s) of estimation.{convergence_note}

## Final Round Estimates
{estimates_block}

## Final Statistics
- Median: {final_median}
- IQR: {iqr_low} to {iqr_high}
- Spread (IQR width): {spread}

Produce a concise synthesis that explains:
1. The final consensus estimate and what it means
2. Key factors the panelists agreed on
3. Key areas of disagreement or uncertainty
4. How estimates evolved across rounds (if multiple rounds)

Respond in JSON:
{{
  "summary": "Paragraph summarizing the consensus estimate and its meaning.",
  "key_agreements": ["agreement 1", "agreement 2"],
  "key_disagreements": ["disagreement 1", "disagreement 2"],
  "evolution_notes": "How and why estimates shifted across rounds."
}}
"""
