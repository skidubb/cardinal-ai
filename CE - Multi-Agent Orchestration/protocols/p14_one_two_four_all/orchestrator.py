"""P14: 1-2-4-All — Progressive merging orchestrator."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    FINAL_SYNTHESIS_PROMPT,
    PAIR_MERGE_PROMPT,
    QUAD_MERGE_PROMPT,
    SOLO_IDEATION_PROMPT,
)


@dataclass
class AgentSpec:
    """Minimal agent definition — name + system prompt."""
    name: str
    system_prompt: str


@dataclass
class MergeRecord:
    """Tracks one merge operation."""
    stage: str
    inputs: list[str]
    output: str
    model: str


@dataclass
class OneTwoFourAllResult:
    """Complete result from a 1-2-4-All run."""
    question: str
    solo_outputs: dict[str, str]
    pair_outputs: list[dict[str, Any]]
    quad_outputs: list[dict[str, Any]]
    final_synthesis: str
    merge_lineage: list[MergeRecord] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    model_calls: dict[str, int] = field(default_factory=dict)




class OneTwoFourAllOrchestrator:
    """Runs the 1-2-4-All progressive merging protocol."""

    def __init__(
        self,
        agents: list[AgentSpec],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
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

    async def _solo_ideate(self, agent: AgentSpec, question: str) -> str:
        """Stage 1: single agent generates ideas independently."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            system=agent.system_prompt,
            messages=[
                {"role": "user", "content": SOLO_IDEATION_PROMPT.format(question=question)},
            ],
            agent_name=agent.name,
        )
        return extract_text(response)

    async def _merge(self, question: str, ideas_a: str, ideas_b: str, prompt_template: str) -> str:
        """Generic merge using orchestration model (Haiku)."""
        prompt = prompt_template.format(
            question=question,
            ideas_a=ideas_a,
            ideas_b=ideas_b,
        )
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=8_000,
            messages=[
                {"role": "user", "content": prompt},
            ],
            agent_name="merge",
        )
        return extract_text(response)

    @staticmethod
    def _make_pairs(items: list) -> list[tuple]:
        """Pair items; if odd count, last item carries forward solo."""
        pairs = []
        for i in range(0, len(items) - 1, 2):
            pairs.append((items[i], items[i + 1]))
        return pairs

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    @trace_protocol("p14_one_two_four_all")
    async def run(self, question: str) -> OneTwoFourAllResult:
        t0 = time.time()
        model_calls: dict[str, int] = {}

        def _count(model: str, n: int = 1):
            model_calls[model] = model_calls.get(model, 0) + n

        lineage: list[MergeRecord] = []

        # --- Stage 1: Solo ideation (parallel, Opus) ---
        span = create_span("stage:solo_ideation", {"agent_count": len(self.agents)})
        try:
            solo_tasks = [self._solo_ideate(a, question) for a in self.agents]
            solo_texts = await asyncio.gather(*solo_tasks, return_exceptions=True)
            solo_texts = filter_exceptions(solo_texts, label="p14_one_two_four_all")
            _count(self.thinking_model, len(self.agents))
            end_span(span, output=f"{len(solo_texts)} solo outputs")
        except Exception:
            end_span(span, error="solo_ideation failed")
            raise

        solo_outputs: dict[str, str] = {}
        tagged: list[dict[str, Any]] = []
        for agent, text in zip(self.agents, solo_texts):
            solo_outputs[agent.name] = text
            tagged.append({"names": [agent.name], "text": text})

        # --- Stage 2: Pair merge (parallel, Haiku) ---
        current = tagged
        pair_outputs: list[dict[str, Any]] = []
        pairs = self._make_pairs(current)
        carry_forward = current[-1] if len(current) % 2 == 1 else None

        span = create_span("stage:pair_merge", {"pair_count": len(pairs)})
        try:
            merge_tasks = []
            pair_meta = []
            for a, b in pairs:
                merge_tasks.append(self._merge(question, a["text"], b["text"], PAIR_MERGE_PROMPT))
                pair_meta.append({"names": a["names"] + b["names"]})

            pair_texts = await asyncio.gather(*merge_tasks, return_exceptions=True)
            pair_texts = filter_exceptions(pair_texts, label="p14_one_two_four_all")
            _count(self.orchestration_model, len(pairs))
            end_span(span, output=f"{len(pair_texts)} pair merges completed")
        except Exception:
            end_span(span, error="pair_merge failed")
            raise

        next_stage = []
        for meta, text in zip(pair_meta, pair_texts):
            entry = {"names": meta["names"], "text": text}
            pair_outputs.append(entry)
            next_stage.append(entry)
            lineage.append(MergeRecord("pair", meta["names"], text, self.orchestration_model))

        if carry_forward:
            next_stage.append(carry_forward)

        # --- Stage 3: Quad merge (parallel, Haiku) ---
        current = next_stage
        quad_outputs: list[dict[str, Any]] = []
        pairs = self._make_pairs(current)
        carry_forward = current[-1] if len(current) % 2 == 1 else None

        span = create_span("stage:quad_merge", {"pair_count": len(pairs)})
        try:
            merge_tasks = []
            quad_meta = []
            for a, b in pairs:
                merge_tasks.append(self._merge(question, a["text"], b["text"], QUAD_MERGE_PROMPT))
                quad_meta.append({"names": a["names"] + b["names"]})

            quad_texts = await asyncio.gather(*merge_tasks, return_exceptions=True)
            quad_texts = filter_exceptions(quad_texts, label="p14_one_two_four_all")
            _count(self.orchestration_model, len(pairs))
            end_span(span, output=f"{len(quad_texts)} quad merges completed")
        except Exception:
            end_span(span, error="quad_merge failed")
            raise

        final_inputs = []
        for meta, text in zip(quad_meta, quad_texts):
            entry = {"names": meta["names"], "text": text}
            quad_outputs.append(entry)
            final_inputs.append(entry)
            lineage.append(MergeRecord("quad", meta["names"], text, self.orchestration_model))

        if carry_forward:
            final_inputs.append(carry_forward)

        # --- Stage 4: Final synthesis (Opus) ---
        span = create_span("stage:final_synthesis", {"input_count": len(final_inputs)})
        try:
            quad_block = "\n\n---\n\n".join(
                f"**Group ({', '.join(fi['names'])}):**\n{fi['text']}" for fi in final_inputs
            )
            prompt = FINAL_SYNTHESIS_PROMPT.format(question=question, quad_outputs=quad_block)
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=16_000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                },
                messages=[
                    {"role": "user", "content": prompt},
                ],
                agent_name="final_synthesis",
            )
            final_text = extract_text(response)
            _count(self.thinking_model)
            end_span(span, output="final synthesis completed")
        except Exception:
            end_span(span, error="final_synthesis failed")
            raise

        return OneTwoFourAllResult(
            question=question,
            solo_outputs=solo_outputs,
            pair_outputs=pair_outputs,
            quad_outputs=quad_outputs,
            final_synthesis=final_text,
            merge_lineage=lineage,
            elapsed_seconds=round(time.time() - t0, 2),
            model_calls=model_calls,
        )
