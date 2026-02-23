"""P10: Heard-Seen-Respected — Empathy & perspective translation orchestrator."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    BRIDGE_SYNTHESIS_PROMPT,
    REFLECT_BACK_PROMPT,
    STAKEHOLDER_NARRATIVE_PROMPT,
)


@dataclass
class AgentSpec:
    """Minimal agent definition — name + system prompt."""
    name: str
    system_prompt: str


@dataclass
class Reflection:
    """One agent's reflection of another's narrative."""
    reflector: str
    reflected_on: str
    reflection: str


@dataclass
class HSRResult:
    """Complete result from a Heard-Seen-Respected run."""
    question: str
    narratives: dict[str, str]
    reflections: list[dict[str, str]]
    common_ground: str
    key_differences: str
    translation_guide: str
    timings: dict[str, float] = field(default_factory=dict)
    model_calls: dict[str, int] = field(default_factory=dict)


def _extract_text(response) -> str:
    """Pull plain text from an Anthropic API response."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


class HSROrchestrator:
    """Runs the Heard-Seen-Respected empathy protocol."""

    def __init__(
        self,
        agents: list[AgentSpec],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _generate_narrative(self, agent: AgentSpec, question: str) -> str:
        """Phase 1: Agent writes experiential narrative from their perspective."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            system=agent.system_prompt,
            messages=[
                {"role": "user", "content": STAKEHOLDER_NARRATIVE_PROMPT.format(question=question)},
            ],
        )
        return _extract_text(response)

    async def _reflect_back(
        self, reflector: AgentSpec, narrator_name: str, narrative: str, question: str
    ) -> str:
        """Phase 2: One agent reflects back another's narrative."""
        prompt = REFLECT_BACK_PROMPT.format(
            question=question,
            narrator_name=narrator_name,
            narrative=narrative,
        )
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=8_000,
            system=reflector.system_prompt,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        return _extract_text(response)

    async def _bridge_synthesis(self, question: str, narratives_and_reflections: str) -> str:
        """Phase 3: Produce common ground, key differences, and translation guide."""
        prompt = BRIDGE_SYNTHESIS_PROMPT.format(
            question=question,
            narratives_and_reflections=narratives_and_reflections,
        )
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        return _extract_text(response)

    @staticmethod
    def _build_reflection_pairs(agents: list[AgentSpec]) -> list[tuple[AgentSpec, AgentSpec]]:
        """Pair agents for reflection: A reflects B, B reflects A, etc.

        For N agents, produces N pairs. Each agent reflects exactly one other.
        If odd count, the last agent reflects the first (wrapping around).
        """
        pairs = []
        n = len(agents)
        for i in range(n):
            reflector = agents[i]
            # Each agent reflects the next agent's narrative (circular)
            narrator = agents[(i + 1) % n]
            pairs.append((reflector, narrator))
        return pairs

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def run(self, question: str) -> HSRResult:
        t0 = time.time()
        model_calls: dict[str, int] = {}
        timings: dict[str, float] = {}

        def _count(model: str, n: int = 1):
            model_calls[model] = model_calls.get(model, 0) + n

        # --- Phase 1: Share — narrative generation (parallel, Opus) ---
        t_phase1 = time.time()
        narrative_tasks = [self._generate_narrative(a, question) for a in self.agents]
        narrative_texts = await asyncio.gather(*narrative_tasks)
        _count(self.thinking_model, len(self.agents))
        timings["phase1_share"] = round(time.time() - t_phase1, 2)

        narratives: dict[str, str] = {}
        for agent, text in zip(self.agents, narrative_texts):
            narratives[agent.name] = text

        # --- Phase 2: Reflect — paired reflections (parallel, Haiku) ---
        t_phase2 = time.time()
        reflection_pairs = self._build_reflection_pairs(self.agents)

        reflect_tasks = []
        reflect_meta = []
        for reflector, narrator in reflection_pairs:
            reflect_tasks.append(
                self._reflect_back(reflector, narrator.name, narratives[narrator.name], question)
            )
            reflect_meta.append({"reflector": reflector.name, "reflected_on": narrator.name})

        reflect_texts = await asyncio.gather(*reflect_tasks)
        _count(self.orchestration_model, len(reflection_pairs))
        timings["phase2_reflect"] = round(time.time() - t_phase2, 2)

        reflections: list[dict[str, str]] = []
        for meta, text in zip(reflect_meta, reflect_texts):
            reflections.append({
                "reflector": meta["reflector"],
                "reflected_on": meta["reflected_on"],
                "reflection": text,
            })

        # --- Phase 3: Bridge — synthesis (Opus) ---
        t_phase3 = time.time()

        # Build the combined block for the synthesis prompt
        blocks = []
        for agent in self.agents:
            block = f"### {agent.name}'s Narrative\n{narratives[agent.name]}"
            # Find reflections OF this agent
            for r in reflections:
                if r["reflected_on"] == agent.name:
                    block += f"\n\n**{r['reflector']}'s Reflection of {agent.name}:**\n{r['reflection']}"
            blocks.append(block)

        narratives_and_reflections = "\n\n---\n\n".join(blocks)

        bridge_text = await self._bridge_synthesis(question, narratives_and_reflections)
        _count(self.thinking_model)
        timings["phase3_bridge"] = round(time.time() - t_phase3, 2)

        # Parse bridge output into sections
        common_ground = ""
        key_differences = ""
        translation_guide = ""

        current_section = ""
        for line in bridge_text.split("\n"):
            lower = line.lower().strip()
            if "common ground" in lower and line.strip().startswith("#"):
                current_section = "common_ground"
                continue
            elif "key difference" in lower and line.strip().startswith("#"):
                current_section = "key_differences"
                continue
            elif "translation guide" in lower and line.strip().startswith("#"):
                current_section = "translation_guide"
                continue

            if current_section == "common_ground":
                common_ground += line + "\n"
            elif current_section == "key_differences":
                key_differences += line + "\n"
            elif current_section == "translation_guide":
                translation_guide += line + "\n"

        # Fallback: if parsing didn't find sections, put everything in common_ground
        if not common_ground and not key_differences and not translation_guide:
            common_ground = bridge_text

        timings["total"] = round(time.time() - t0, 2)

        return HSRResult(
            question=question,
            narratives=narratives,
            reflections=reflections,
            common_ground=common_ground.strip(),
            key_differences=key_differences.strip(),
            translation_guide=translation_guide.strip(),
            timings=timings,
            model_calls=model_calls,
        )
