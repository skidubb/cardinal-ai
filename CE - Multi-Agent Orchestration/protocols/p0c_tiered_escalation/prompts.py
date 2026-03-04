"""Prompts for the P0c Tiered Escalation meta-protocol."""

TIER1_AGENT_PROMPT = """\
You are a senior strategic advisor. Answer the following question directly and thoroughly.

Question:
{question}

Provide a clear, well-structured response covering key considerations, risks, and recommendations.
"""

TIER1_CONFIDENCE_PROMPT = """\
You are a response quality evaluator. Given a strategic question and a single agent's response, \
assess how confident you are that this response is complete, accurate, and sufficient.

Question:
{question}

Response:
{response}

Evaluate on these dimensions:
- Completeness: Does it cover all key aspects?
- Accuracy: Are claims well-supported and logical?
- Nuance: Does it handle complexity and tradeoffs?
- Actionability: Does it give concrete guidance?

Respond in JSON:
{{
  "confidence": <0-100>,
  "reasoning": "<2-3 sentences explaining the assessment>"
}}
"""

TIER2_AGENT_PROMPT = """\
You are {agent_name}. {system_prompt}

Answer the following strategic question from your professional perspective.

Question:
{question}

Provide a thorough analysis from your area of expertise.
"""

TIER2_SYNTHESIS_PROMPT = """\
You are a synthesis engine. Given multiple expert perspectives on a strategic question, \
merge them into a single coherent response and assess the degree of consensus.

Question:
{question}

Expert responses:
{responses_block}

Synthesize these perspectives into a unified response. Then assess consensus.

Respond in JSON:
{{
  "synthesis": "<the merged response>",
  "consensus_score": <0.0-1.0, where 1.0 = perfect agreement>,
  "reasoning": "<explain areas of agreement and disagreement>"
}}
"""

TIER3_REBUTTAL_PROMPT = """\
You are {agent_name}. {system_prompt}

You previously answered a strategic question along with other experts. Review the synthesis \
and other perspectives, then provide a rebuttal or refinement.

Question:
{question}

Your previous response:
{own_response}

Synthesis of all responses:
{synthesis}

Other expert responses:
{other_responses_block}

Write a focused rebuttal or refinement. Challenge weak points, reinforce strong ones, \
and add anything that was missed.
"""

TIER3_OVERSIGHT_PROMPT = """\
You are an oversight agent responsible for quality and safety review. Given a strategic question \
and the full deliberation history (individual responses, synthesis, and rebuttals), assess whether \
the final answer is safe to deliver or should be flagged for human review.

Question:
{question}

Tier 1 response:
{tier1_response}

Tier 2 synthesis:
{tier2_synthesis}

Tier 3 rebuttals:
{rebuttals_block}

Check for:
- Factual consistency across tiers
- Unresolved contradictions
- High-risk recommendations without adequate caveats
- Blind spots or missing perspectives

Respond in JSON:
{{
  "passes_safety_check": <true|false>,
  "final_response": "<the best response to deliver, incorporating all tiers>",
  "flag_reason": "<if not passing, explain why human review is needed; null if passing>",
  "confidence": <0-100>
}}
"""
