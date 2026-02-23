"""
Blind Opus judge for multi-agent evaluation.

Scores anonymized outputs on 7 dimensions without knowing which mode produced them.
"""

from __future__ import annotations

import json
import random

import anthropic
from pydantic import BaseModel, Field

from csuite.config import get_settings

DIMENSIONS = [
    "specificity",
    "internal_consistency",
    "tension_surfacing",
    "constraint_awareness",
    "actionability",
    "reasoning_depth",
    "completeness",
]

DIMENSION_DESCRIPTIONS = {
    "specificity": "Are recommendations concrete enough to act on tomorrow?",
    "internal_consistency": (
        "Do the financial, operational, and strategic recommendations align?"
    ),
    "tension_surfacing": (
        "Does the output identify genuine trade-offs, not just list perspectives?"
    ),
    "constraint_awareness": (
        "Does the recommendation acknowledge real-world limits "
        "(budget, timeline, headcount)?"
    ),
    "actionability": "Is there a clear first step, owner, and timeline?",
    "reasoning_depth": (
        "Are claims supported by evidence or reasoning chains, not assertions?"
    ),
    "completeness": (
        "Are all relevant functional perspectives "
        "(finance, ops, tech, marketing, product, revenue) addressed?"
    ),
}

JUDGE_SYSTEM_PROMPT = """You are a senior strategy consultant evaluating \
strategic recommendations for a $5-40M professional services firm.

You will receive multiple responses to the same strategic question. Each is \
labeled only as "Response A", "Response B", etc. You do NOT know how they \
were generated.

Score each response on these 7 dimensions (1-5 scale):

1. **Specificity** (1-5): Are recommendations concrete enough to act on tomorrow?
2. **Internal Consistency** (1-5): Do financial, operational, and strategic recommendations align?
3. **Tension Surfacing** (1-5): Does the output identify genuine trade-offs,
   not just list perspectives?
4. **Constraint Awareness** (1-5): Does it acknowledge real-world limits
   (budget, timeline, headcount)?
5. **Actionability** (1-5): Is there a clear first step, owner, and timeline?
6. **Reasoning Depth** (1-5): Are claims supported by evidence or reasoning chains?
7. **Completeness** (1-5): Are all relevant functional perspectives addressed?

After scoring, provide a forced ranking: if you had to present ONE of \
these responses to a $15M company's CEO, which would you pick? Rank all \
responses from best to worst.

Respond ONLY with valid JSON in this exact format:
{
  "scores": {
    "Response A": {"specificity": N, "internal_consistency": N, \
"tension_surfacing": N, "constraint_awareness": N, "actionability": N, \
"reasoning_depth": N, "completeness": N},
    "Response B": {...},
    ...
  },
  "ranking": ["Response X", "Response Y", ...],
  "reasoning": "Brief explanation of key differences between top and bottom responses."
}"""


class JudgeResult(BaseModel):
    """Result from blind evaluation."""

    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    """Keyed by mode -> dimension -> score."""
    ranking: list[str] = Field(default_factory=list)
    """Modes ranked best to worst."""
    judge_reasoning: str = ""
    label_to_mode: dict[str, str] = Field(default_factory=dict)
    """Maps "Response A" -> actual mode name."""


class BlindJudge:
    """Scores anonymized outputs on 7 dimensions."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def evaluate(self, responses: dict[str, str]) -> JudgeResult:
        """Evaluate a dict of {mode: output_text} with blind scoring.

        Returns JudgeResult with scores mapped back to original mode names.
        """
        # Randomize order and assign anonymous labels
        modes = list(responses.keys())
        random.shuffle(modes)
        labels = [f"Response {chr(65 + i)}" for i in range(len(modes))]
        label_to_mode = dict(zip(labels, modes))

        # Build prompt with anonymized outputs
        parts = []
        for label, mode in zip(labels, modes):
            text = _strip_metadata(responses[mode])
            parts.append(f"## {label}\n\n{text}")

        user_prompt = (
            "Please evaluate the following strategic recommendations.\n\n"
            + "\n\n---\n\n".join(parts)
        )

        response = self.client.messages.create(
            model=self.settings.default_model,
            max_tokens=2048,
            temperature=0.0,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text
        return _parse_judge_response(raw, label_to_mode)


def _strip_metadata(text: str) -> str:
    """Remove mode-identifying metadata from output text."""
    import re
    # Remove common identifiers
    pattern = r"(?i)(debate|negotiation|synthesis|single agent|multi-agent)\s*(mode|approach)"
    text = re.sub(pattern, "", text)
    text = re.sub(r"Debate ID:\s*\S+", "", text)
    text = re.sub(r"Constraint[s]?:\s*\d+", "", text)
    return text.strip()


def _parse_judge_response(raw: str, label_to_mode: dict[str, str]) -> JudgeResult:
    """Parse the judge's JSON response and map labels back to modes."""
    # Extract JSON from response (handle markdown code blocks)
    import re
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return JudgeResult(judge_reasoning=f"Failed to parse judge response: {raw[:200]}")

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return JudgeResult(judge_reasoning=f"Invalid JSON from judge: {raw[:200]}")

    # Map scores from labels to mode names
    scores: dict[str, dict[str, float]] = {}
    for label, mode in label_to_mode.items():
        if label in data.get("scores", {}):
            scores[mode] = data["scores"][label]

    # Map ranking from labels to mode names
    ranking: list[str] = []
    for label in data.get("ranking", []):
        if label in label_to_mode:
            ranking.append(label_to_mode[label])

    return JudgeResult(
        scores=scores,
        ranking=ranking,
        judge_reasoning=data.get("reasoning", ""),
        label_to_mode=label_to_mode,
    )
