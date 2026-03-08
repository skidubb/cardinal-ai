"""Salience scoring, lens promotion, wildcard logic, and cross-exam pairings."""

from __future__ import annotations

import json
import logging

from protocols.llm import extract_text, llm_complete, parse_json_object
from protocols.walk_shared.schemas import (
    FrameArtifact,
    SalienceArtifact,
    SalienceScore,
    ShallowWalkOutput,
)

_log = logging.getLogger(__name__)


# ── Salience scoring (LLM call) ─────────────────────────────────────────────

async def score_salience(
    shallow_outputs: list[ShallowWalkOutput],
    frame: FrameArtifact,
    client,
    model: str,
) -> SalienceArtifact:
    """Have the Salience Judge score all shallow outputs.

    Uses llm_complete (L2 tier) — rule-based scoring against explicit criteria.
    Returns a SalienceArtifact with ranked outputs and promoted agent list.
    """
    from protocols.walk_shared.prompts import SALIENCE_JUDGE_PROMPT

    prompt = SALIENCE_JUDGE_PROMPT.format(
        shallow_outputs_json=json.dumps(
            [s.model_dump() for s in shallow_outputs], indent=2
        ),
        frame_json=json.dumps(frame.model_dump(), indent=2),
    )

    response = await llm_complete(
        client,
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        agent_name="walk-salience-judge",
    )
    text = extract_text(response)

    # Parse the JSON response
    data = parse_json_object(text)

    # Build SalienceScore objects from parsed data
    scores: list[SalienceScore] = []
    for item in data.get("ranked_outputs", data.get("scores", [])):
        scores.append(SalienceScore.model_validate(item))

    # Sort by composite descending
    scores.sort(key=lambda s: s.composite, reverse=True)

    return SalienceArtifact(
        ranked_outputs=scores,
        top_tensions=data.get("top_tensions", []),
        candidate_hypotheses=data.get("candidate_hypotheses", []),
        promoted_agents=[s.agent_key for s in scores[:4]],
    )


# ── Promotion logic (pure function) ─────────────────────────────────────────

def select_promoted(
    scores: list[SalienceScore],
    top_n: int = 4,
    include_wildcard: bool = False,
) -> list[str]:
    """Pick top N agents by composite score.

    If include_wildcard=True, preserve one high-cognitive-distance lens that
    isn't already in the top N (maximally orthogonal to promote diversity).
    """
    if not scores:
        return []

    # Sort by composite descending
    ranked = sorted(scores, key=lambda s: s.composite, reverse=True)
    promoted = [s.agent_key for s in ranked[:top_n]]

    if include_wildcard:
        # Find the agent with highest cognitive_distance not already promoted
        remaining = [s for s in ranked if s.agent_key not in promoted]
        if remaining:
            wildcard = max(remaining, key=lambda s: s.cognitive_distance)
            promoted.append(wildcard.agent_key)

    return promoted


# ── Cross-examination pairings ───────────────────────────────────────────────

def build_cross_exam_pairings(promoted_keys: list[str]) -> list[tuple[str, str]]:
    """Generate round-robin (challenger, target) pairs.

    Each promoted agent challenges exactly one other agent.
    """
    n = len(promoted_keys)
    if n < 2:
        return []

    pairings: list[tuple[str, str]] = []
    for i, challenger in enumerate(promoted_keys):
        target = promoted_keys[(i + 1) % n]
        pairings.append((challenger, target))

    return pairings
