"""QualityJudge — scores synthesis quality as a post-synthesis gate.

Uses Sonnet (BALANCED_MODEL / L3) to keep cost reasonable. Returns a
structured JudgeVerdict, not prose.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from protocols.config import BALANCED_MODEL
from protocols.llm import agent_complete, parse_json_object


# Loaded lazily to avoid circular imports
_JUDGE_AGENT: dict | None = None


def _get_judge_agent() -> dict:
    global _JUDGE_AGENT
    if _JUDGE_AGENT is None:
        from protocols.agents import META_AGENTS
        _JUDGE_AGENT = META_AGENTS["judge"]
    return _JUDGE_AGENT


JUDGE_PROMPT = """\
You are evaluating the quality of a multi-agent synthesis. Score it against \
the original agent contributions.

ORIGINAL QUESTION:
{question}

AGENT OUTPUTS:
{agent_outputs}

SYNTHESIS:
{synthesis}

Score each dimension 1-5:
- completeness: Did the synthesis capture all key insights from the agents?
- consistency: Does it contradict any agent's factual claims?
- actionability: Can a decision-maker act on this?
- overall: Holistic quality score

Also provide:
- flags: List of specific issues found (empty list if none)
- recommendation: "accept" or "revise"

Respond with ONLY a JSON object:
{{"completeness": int, "consistency": int, "actionability": int, "overall": int, "flags": [str], "recommendation": "accept"|"revise"}}"""


@dataclass
class JudgeVerdict:
    completeness: int = 0
    consistency: int = 0
    actionability: int = 0
    overall: int = 0
    flags: list[str] = field(default_factory=list)
    recommendation: str = "accept"

    def as_dict(self) -> dict:
        return {
            "completeness": self.completeness,
            "consistency": self.consistency,
            "actionability": self.actionability,
            "overall": self.overall,
            "flags": self.flags,
            "recommendation": self.recommendation,
        }


class QualityJudge:
    """Evaluates synthesis quality against agent outputs.

    Args:
        client: Anthropic AsyncAnthropic client.
        model: Model for judging (defaults to Sonnet / BALANCED_MODEL).
    """

    def __init__(self, client, model: str = BALANCED_MODEL):
        self.client = client
        self.model = model

    async def evaluate(
        self,
        question: str,
        agent_outputs: str,
        synthesis: str,
    ) -> JudgeVerdict:
        """Score synthesis against agent outputs.

        Args:
            question: Original question.
            agent_outputs: Formatted string of all agent contributions.
            synthesis: The synthesis text to evaluate.

        Returns:
            JudgeVerdict with scores and recommendation.
        """
        prompt = JUDGE_PROMPT.format(
            question=question,
            agent_outputs=agent_outputs,
            synthesis=synthesis,
        )

        agent = _get_judge_agent()
        raw = await agent_complete(
            agent=agent,
            fallback_model=self.model,
            messages=[{"role": "user", "content": prompt}],
            thinking_budget=0,
            anthropic_client=self.client,
            no_tools=True,
        )

        data = parse_json_object(raw)
        return JudgeVerdict(
            completeness=int(data.get("completeness", 0)),
            consistency=int(data.get("consistency", 0)),
            actionability=int(data.get("actionability", 0)),
            overall=int(data.get("overall", 0)),
            flags=data.get("flags", []),
            recommendation=data.get("recommendation", "accept"),
        )
