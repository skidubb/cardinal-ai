"""P7: Wicked Questions Protocol — Agent-agnostic orchestrator.

"Surface irresolvable paradoxes to sharpen strategic tensions."
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    RANKING_PROMPT,
    SYNTHESIS_PROMPT,
    TENSION_GENERATION_PROMPT,
    WICKEDNESS_TEST_PROMPT,
)


@dataclass
class WickedQuestion:
    id: int
    side_a: str
    side_b: str
    wicked_question: str
    urgency: int = 0
    impact: int = 0
    hiddenness: int = 0
    composite: int = 0
    strategic_implication: str = ""


@dataclass
class WickedQuestionsResult:
    topic: str
    all_tensions_count: int = 0
    wicked_count: int = 0
    rejected_count: int = 0
    wicked_questions: list[WickedQuestion] = field(default_factory=list)
    synthesis: str = ""
    agent_contributions: dict[str, str] = field(default_factory=dict)


class WickedQuestionsOrchestrator:
    """Runs the Wicked Questions protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    async def run(self, topic: str) -> WickedQuestionsResult:
        """Execute the full Wicked Questions protocol."""
        result = WickedQuestionsResult(topic=topic)

        # Stage 1: All agents generate tension pairs (parallel)
        print("Stage 1: Generating tension pairs...")
        raw_tensions = await self._generate_tensions(topic)
        result.agent_contributions = {
            agent["name"]: raw_tensions[i]
            for i, agent in enumerate(self.agents)
        }

        # Stage 2: Apply wickedness test
        print("Stage 2: Applying wickedness test...")
        all_text = "\n\n".join(
            f"=== {agent['name']} ===\n{raw}"
            for agent, raw in zip(self.agents, raw_tensions)
        )
        tested = await self._wickedness_test(all_text)
        wicked = [t for t in tested if t.get("is_wicked")]
        result.all_tensions_count = len(tested)
        result.wicked_count = len(wicked)
        result.rejected_count = len(tested) - len(wicked)

        if not wicked:
            result.synthesis = "No tension pairs passed the wickedness test. The topic may need reframing to surface deeper paradoxes."
            return result

        # Stage 3: Rank by strategic relevance
        print("Stage 3: Ranking by strategic relevance...")
        wicked_for_ranking = json.dumps(
            [{"id": w["id"], "wicked_question": w["wicked_question"]} for w in wicked],
            indent=2,
        )
        ranked = await self._rank(wicked_for_ranking)
        result.wicked_questions = [
            WickedQuestion(
                id=r["id"],
                side_a=next((w["side_a"] for w in wicked if w["id"] == r["id"]), ""),
                side_b=next((w["side_b"] for w in wicked if w["id"] == r["id"]), ""),
                wicked_question=r["wicked_question"],
                urgency=r.get("urgency", 0),
                impact=r.get("impact", 0),
                hiddenness=r.get("hiddenness", 0),
                composite=r.get("composite", 0),
                strategic_implication=r.get("strategic_implication", ""),
            )
            for r in ranked
        ]

        # Stage 4: Synthesize
        print("Stage 4: Synthesizing strategic briefing...")
        result.synthesis = await self._synthesize(topic, ranked)

        return result

    async def _generate_tensions(self, topic: str) -> list[str]:
        """Stage 1: All agents generate tension pairs in parallel."""
        prompt = TENSION_GENERATION_PROMPT.format(question=topic)

        async def query_agent(agent: dict) -> str:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=2048,
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        return await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )

    async def _wickedness_test(self, all_tensions: str) -> list[dict]:
        """Stage 2: Apply 3-part wickedness test.

        Uses Sonnet for this stage — needs structured evaluation with large output.
        """
        response = await self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": WICKEDNESS_TEST_PROMPT.format(all_tensions=all_tensions),
            }],
        )
        text = _extract_text(response)
        return _parse_json_array(text)

    async def _rank(self, wicked_questions: str) -> list[dict]:
        """Stage 3: Rank by strategic relevance."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": RANKING_PROMPT.format(wicked_questions=wicked_questions),
            }],
        )
        return _parse_json_array(_extract_text(response))

    async def _synthesize(self, topic: str, ranked: list[dict]) -> str:
        """Stage 4: Produce final strategic briefing."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=topic,
                    ranked_results=json.dumps(ranked, indent=2),
                ),
            }],
        )
        return _extract_text(response)


def _extract_text(response) -> str:
    """Get text from an Anthropic response, handling multiple content blocks."""
    for block in response.content:
        if hasattr(block, "text") and block.text:
            return block.text
    # Debug: show what we got
    block_info = []
    for b in response.content:
        info = type(b).__name__
        if hasattr(b, "text"):
            info += f"(text={repr(b.text)[:100]})"
        block_info.append(info)
    raise RuntimeError(
        f"No text in response. Stop: {response.stop_reason}, "
        f"usage: in={response.usage.input_tokens} out={response.usage.output_tokens}, "
        f"blocks: {block_info}"
    )


def _parse_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM output that may contain markdown fences."""
    original = text
    text = text.strip()
    # Try to extract from markdown fences (handles truncated output too)
    match = re.search(r"```(?:json)?\s*\n(.*?)(?:```|$)", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    # Find the JSON array brackets
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        elif start != -1:
            # Truncated — try to repair by closing the array
            text = text[start:]
            # Find last complete object (ends with })
            last_brace = text.rfind("}")
            if last_brace != -1:
                text = text[:last_brace + 1]
                # Remove trailing comma if present
                text = text.rstrip().rstrip(",") + "]"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"JSON parse failed. First 500 chars of raw response:\n{original[:500]}")
        raise
