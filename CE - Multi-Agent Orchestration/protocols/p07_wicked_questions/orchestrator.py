"""P7: Wicked Questions Protocol — Agent-agnostic orchestrator.

"Surface irresolvable paradoxes to sharpen strategic tensions."
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL, BALANCED_MODEL
from protocols.llm import extract_text, llm_complete, parse_json_array, filter_exceptions

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
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p07_wicked_questions")
    async def run(self, topic: str) -> WickedQuestionsResult:
        """Execute the full Wicked Questions protocol."""
        result = WickedQuestionsResult(topic=topic)

        # Stage 1: All agents generate tension pairs (parallel)
        print("Stage 1: Generating tension pairs...")
        span = create_span("stage:tension_generation", {"agent_count": len(self.agents)})
        try:
            raw_tensions = await self._generate_tensions(topic)
            result.agent_contributions = {
                agent["name"]: raw_tensions[i]
                for i, agent in enumerate(self.agents)
            }
            end_span(span, output=f"{len(raw_tensions)} tension sets")
        except Exception:
            end_span(span, error="tension_generation failed")
            raise

        # Stage 2: Apply wickedness test
        print("Stage 2: Applying wickedness test...")
        span = create_span("stage:wickedness_test", {"tension_count": len(raw_tensions)})
        try:
            all_text = "\n\n".join(
                f"=== {agent['name']} ===\n{raw}"
                for agent, raw in zip(self.agents, raw_tensions)
            )
            tested = await self._wickedness_test(all_text)
            wicked = [t for t in tested if t.get("is_wicked")]
            result.all_tensions_count = len(tested)
            result.wicked_count = len(wicked)
            result.rejected_count = len(tested) - len(wicked)
            end_span(span, output=f"{len(wicked)} wicked of {len(tested)} total")
        except Exception:
            end_span(span, error="wickedness_test failed")
            raise

        if not wicked:
            result.synthesis = "No tension pairs passed the wickedness test. The topic may need reframing to surface deeper paradoxes."
            return result

        # Stage 3: Rank by strategic relevance
        print("Stage 3: Ranking by strategic relevance...")
        span = create_span("stage:ranking", {"wicked_count": len(wicked)})
        try:
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
            end_span(span, output=f"{len(ranked)} ranked questions")
        except Exception:
            end_span(span, error="ranking failed")
            raise

        # Stage 4: Synthesize
        print("Stage 4: Synthesizing strategic briefing...")
        span = create_span("stage:synthesis", {"ranked_count": len(ranked)})
        try:
            result.synthesis = await self._synthesize(topic, ranked)
            end_span(span, output=f"synthesis {len(result.synthesis)} chars")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _generate_tensions(self, topic: str) -> list[str]:
        """Stage 1: All agents generate tension pairs in parallel."""
        prompt = TENSION_GENERATION_PROMPT.format(question=topic)

        async def query_agent(agent: dict) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=2048,
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent["name"],
            )
            return extract_text(response)

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p07_wicked_questions")
        return _results

    async def _wickedness_test(self, all_tensions: str) -> list[dict]:
        """Stage 2: Apply 3-part wickedness test.

        Uses Sonnet for this stage — needs structured evaluation with large output.
        """
        response = await llm_complete(
            self.client,
            model=BALANCED_MODEL,
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": WICKEDNESS_TEST_PROMPT.format(all_tensions=all_tensions),
            }],
            agent_name="wickedness_test",
        )
        text = extract_text(response)
        return parse_json_array(text)

    async def _rank(self, wicked_questions: str) -> list[dict]:
        """Stage 3: Rank by strategic relevance."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": RANKING_PROMPT.format(wicked_questions=wicked_questions),
            }],
            agent_name="ranking",
        )
        return parse_json_array(extract_text(response))

    async def _synthesize(self, topic: str, ranked: list[dict]) -> str:
        """Stage 4: Produce final strategic briefing."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=topic,
                    ranked_results=json.dumps(ranked, indent=2),
                ),
            }],
            agent_name="synthesis",
        )
        return extract_text(response)




