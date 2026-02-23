"""P45: Whitehead Process-Entity Weights — Agent-agnostic orchestrator.

Weight calibration system. Tracks Agent x Protocol x Problem Type performance.
"CFO-running-ACH" and "CFO-running-Delphi" are DIFFERENT entities.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic

from .prompts import RECOMMEND_SYNTHESIS_PROMPT


WEIGHTS_PATH = os.path.join(os.path.expanduser("~"), ".coordination-lab", "weights.json")
MIN_SAMPLE_SIZE = 10


@dataclass
class WeightResult:
    mode: str  # "record" or "recommend"
    recorded_entry: dict | None = None
    protocol: str = ""
    problem_type: str = ""
    rankings: list[dict] = field(default_factory=list)
    synthesis: str = ""


def _load_weights() -> dict:
    """Load the weights file, creating it if needed."""
    if not os.path.exists(WEIGHTS_PATH):
        return {"records": []}
    with open(WEIGHTS_PATH) as f:
        return json.load(f)


def _save_weights(data: dict) -> None:
    """Save the weights file, creating the directory if needed."""
    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    with open(WEIGHTS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _extract_text(message) -> str:
    """Pull plain text from an Anthropic message response."""
    parts = []
    for block in message.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)


class WhiteheadOrchestrator:
    """Manages agent performance weights across protocols and problem types."""

    def __init__(
        self,
        agents: list[dict] | None = None,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        self.agents = agents or []
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def record(
        self,
        agent_name: str,
        protocol: str,
        problem_type: str,
        score: float,
    ) -> WeightResult:
        """Record a performance score for an agent-protocol-problem_type combo."""
        entry = {
            "agent": agent_name,
            "protocol": protocol,
            "problem_type": problem_type,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        data = _load_weights()
        data["records"].append(entry)
        _save_weights(data)

        return WeightResult(mode="record", recorded_entry=entry)

    async def recommend(self, protocol: str, problem_type: str) -> WeightResult:
        """Recommend agents for a protocol + problem type based on historical scores."""
        data = _load_weights()

        # Filter and aggregate
        agent_scores: dict[str, list[float]] = {}
        for rec in data["records"]:
            if rec["protocol"] == protocol and rec["problem_type"] == problem_type:
                agent_scores.setdefault(rec["agent"], []).append(rec["score"])

        rankings = []
        for agent, scores in agent_scores.items():
            avg = sum(scores) / len(scores)
            rankings.append({
                "agent": agent,
                "avg_score": round(avg, 2),
                "sample_size": len(scores),
                "confidence": "high" if len(scores) >= MIN_SAMPLE_SIZE else "low",
            })

        rankings.sort(key=lambda r: r["avg_score"], reverse=True)

        # Synthesize with Haiku if there are rankings
        synthesis = ""
        if rankings:
            rankings_text = "\n".join(
                f"  {i+1}. {r['agent']}: avg={r['avg_score']}, n={r['sample_size']}, confidence={r['confidence']}"
                for i, r in enumerate(rankings)
            )
            prompt = RECOMMEND_SYNTHESIS_PROMPT.format(
                protocol=protocol,
                problem_type=problem_type,
                rankings_text=rankings_text,
            )
            msg = await self.client.messages.create(
                model=self.orchestration_model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            synthesis = _extract_text(msg)

        return WeightResult(
            mode="recommend",
            protocol=protocol,
            problem_type=problem_type,
            rankings=rankings,
            synthesis=synthesis,
        )

    async def run(self, question: str) -> WeightResult:
        """CLI compatibility — interpret question as a recommend query.

        Expected format: "protocol:problem_type" e.g. "p16_ach:diagnostic"
        """
        parts = question.split(":", 1)
        protocol = parts[0].strip()
        problem_type = parts[1].strip() if len(parts) > 1 else "general"
        return await self.recommend(protocol, problem_type)
