"""Prompts for P22: Sequential Pipeline Protocol."""

STAGE_PROMPT = """You are stage {stage_number} of {total_stages} in a sequential processing pipeline.

Your role: {agent_name} — {system_prompt}

## Original Question
{question}

## Prior Stage Outputs
{prior_outputs}

## Your Task
Build on the work of prior stages. Do NOT repeat what has already been covered — instead, deepen, challenge, or extend the analysis from your unique perspective. If you are the first stage, lay the foundational analysis.

Clearly label any references to prior stage outputs (e.g., "Building on Stage 1's financial analysis...").

Produce your contribution now."""

QUALITY_GATE_PROMPT = """You are a quality gate for a sequential pipeline that processed the following question:

## Question
{question}

## Full Pipeline Output ({total_stages} stages)
{all_outputs}

## Your Task
Assess whether the pipeline output adequately addresses the question. Consider:
1. Does the combined output thoroughly address the question?
2. Are there any contradictions between stages?
3. Is any critical perspective missing?
4. Did later stages meaningfully build on earlier ones?

Respond with ONLY a JSON object (no markdown fencing):
{{"passes": true or false, "reason": "brief explanation", "failing_stage": null or the stage number (1-indexed) that most needs improvement}}"""

FINAL_SYNTHESIS_PROMPT = """You are the final synthesizer for a sequential pipeline analysis.

## Original Question
{question}

## Stage Outputs (in processing order)
{all_outputs}

## Your Task
Compile all stage outputs into a single cohesive response that:
1. Integrates insights from all stages into a unified analysis
2. Acknowledges the lineage of key insights (e.g., "The financial risk analysis [Stage 2] combined with the technical feasibility assessment [Stage 3] suggests...")
3. Resolves any tensions or contradictions between stages
4. Presents a clear, actionable conclusion

Produce the final synthesized response now."""
