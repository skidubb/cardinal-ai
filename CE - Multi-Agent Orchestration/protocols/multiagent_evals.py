"""Programmatic multi-agent evals — scores trace-level dynamics in Langfuse.

Evaluates dimensions that require seeing all agent outputs together:
- Perspective Diversity: Did agents provide meaningfully different analyses?
- Synthesis Fidelity: Did synthesis capture all agents' key insights?
- Emergence: Did the collective produce insights absent from any single agent?
- Constructive Tension: Did agents challenge each other's reasoning?

Runs a single cheap LLM call (Haiku) per protocol run, then pushes 4 scores
to the Langfuse trace via score_trace(). Zero Langfuse UI config needed.

Usage:
    Automatically called by @trace_protocol decorator after orchestrator.run().
    Can also be called manually:

        from protocols.multiagent_evals import evaluate_multiagent
        scores = await evaluate_multiagent(result, agent_keys, trace_id)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_log = logging.getLogger(__name__)

EVAL_MODEL = os.getenv("EVAL_MODEL", "claude-haiku-4-5-20251001")

# Minimum agent outputs to run multi-agent evals (single-agent runs skip)
MIN_AGENTS = 2

EVAL_PROMPT = """\
You are scoring the quality of a multi-agent strategic analysis. Multiple AI \
agents (each with a distinct role) independently analyzed a question, and \
their outputs were synthesized into a final recommendation.

Score each dimension 0.0-1.0:

1. PERSPECTIVE_DIVERSITY — Did agents bring meaningfully different analyses, \
or did they echo each other?
- 0.0-0.2: Near-identical outputs, interchangeable perspectives
- 0.3-0.4: Some overlap but minor differences in emphasis
- 0.5-0.6: Distinct viewpoints with some unique insights per agent
- 0.7-0.8: Clear role-differentiated analysis with unique frameworks
- 0.9-1.0: Strongly differentiated — each agent surfaces concerns/opportunities others missed

2. SYNTHESIS_FIDELITY — Did the synthesis accurately capture all agents' key \
insights without distortion or omission?
- 0.0-0.2: Synthesis ignores most agent contributions
- 0.3-0.4: Captures one agent's view, drops others
- 0.5-0.6: Covers main points but misses nuances or specific recommendations
- 0.7-0.8: Faithfully integrates all perspectives with appropriate weighting
- 0.9-1.0: Perfect integration — every key insight preserved, conflicts acknowledged

3. EMERGENCE — Did the multi-agent process produce insights absent from any \
single agent's output? (The whole > sum of parts)
- 0.0-0.2: Synthesis is just a concatenation, no new insight
- 0.3-0.4: Minor connections drawn between agents but no real emergence
- 0.5-0.6: Some novel framing that combines agent perspectives
- 0.7-0.8: Clear emergent insights — trade-offs, tensions, or opportunities \
only visible when comparing agents
- 0.9-1.0: Synthesis reveals non-obvious strategic implications that no \
individual agent identified

4. CONSTRUCTIVE_TENSION — Did agents productively disagree or surface tensions \
that improved the analysis?
- 0.0-0.2: Complete agreement (groupthink) or no interaction
- 0.3-0.4: Minor differences acknowledged but not explored
- 0.5-0.6: Some genuine disagreement that adds depth
- 0.7-0.8: Clear productive tension — agents flag risks others overlooked
- 0.9-1.0: Strong dialectic — disagreements drive deeper analysis and \
better recommendations

QUESTION:
{question}

AGENT OUTPUTS:
{agent_outputs}

SYNTHESIS:
{synthesis}

Respond with ONLY a JSON object:
{{"perspective_diversity": <float>, "synthesis_fidelity": <float>, \
"emergence": <float>, "constructive_tension": <float>, \
"reasoning": "<1-2 sentence summary of key observations>"}}"""


async def evaluate_multiagent(
    result: Any,
    agent_keys: list[str],
    trace_id: str | None = None,
) -> dict[str, float] | None:
    """Run multi-agent evals and push scores to Langfuse.

    Args:
        result: Protocol result object (any dataclass with agent outputs + synthesis).
        agent_keys: List of agent key strings.
        trace_id: Langfuse trace ID to attach scores to.

    Returns:
        Dict of dimension scores, or None if evals were skipped.
    """
    from protocols.run_envelope import extract_agent_outputs, extract_synthesis

    agent_outputs = extract_agent_outputs(result, agent_keys)
    synthesis = extract_synthesis(result)

    # Skip if too few agents or no synthesis
    real_outputs = [ao for ao in agent_outputs if ao.agent_key != "_result"]
    if len(real_outputs) < MIN_AGENTS:
        _log.debug("Skipping multi-agent evals: only %d agent outputs", len(real_outputs))
        return None
    if not synthesis.strip():
        _log.debug("Skipping multi-agent evals: no synthesis found")
        return None

    question = getattr(result, "question", "") or ""
    if not question and hasattr(result, "challenge"):
        question = result.challenge

    # Format agent outputs for the eval prompt
    agent_text_parts = []
    for ao in real_outputs:
        label = ao.agent_name or ao.agent_key
        text = ao.text[:3000]  # Cap per-agent to keep prompt reasonable
        agent_text_parts.append(f"=== {label} ===\n{text}")
    agent_outputs_str = "\n\n".join(agent_text_parts)

    prompt = EVAL_PROMPT.format(
        question=question[:2000],
        agent_outputs=agent_outputs_str,
        synthesis=synthesis[:3000],
    )

    try:
        import anthropic

        client = anthropic.AsyncAnthropic()
        response = await client.messages.create(
            model=EVAL_MODEL,
            max_tokens=500,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        # Parse scores
        from protocols.llm import parse_json_object
        scores = parse_json_object(text)

        if not scores:
            _log.warning("Multi-agent eval returned empty scores")
            return None

        dimensions = [
            "perspective_diversity",
            "synthesis_fidelity",
            "emergence",
            "constructive_tension",
        ]

        result_scores: dict[str, float] = {}
        for dim in dimensions:
            val = scores.get(dim)
            if val is not None:
                try:
                    result_scores[dim] = float(val)
                except (ValueError, TypeError):
                    continue

        reasoning = scores.get("reasoning", "")

        # Push scores to Langfuse
        if trace_id:
            from protocols.langfuse_tracing import score_trace

            for dim, val in result_scores.items():
                score_trace(
                    name=dim,
                    value=val,
                    comment=reasoning[:200] if reasoning else None,
                    trace_id=trace_id,
                )
            _log.info(
                "Multi-agent eval scores pushed to trace %s: %s",
                trace_id[:12],
                {k: round(v, 2) for k, v in result_scores.items()},
            )

        return result_scores

    except Exception as e:
        _log.warning("Multi-agent eval failed (non-fatal): %s", e)
        return None
