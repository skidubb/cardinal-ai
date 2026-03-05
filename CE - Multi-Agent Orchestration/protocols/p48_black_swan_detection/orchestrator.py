"""P48: Black Swan Detection & Santa Fe Systems Thinking — Agent-agnostic orchestrator.

Five-layer adversarial analysis: causal graphs → threshold scans →
confluence extraction → historical analogues → adversarial memo.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol
from protocols.llm import extract_text, filter_exceptions, parse_json_array

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    CAUSAL_GRAPH_PROMPT,
    THRESHOLD_SCAN_PROMPT,
    CONFLUENCE_PROMPT,
    HISTORICAL_ANALOGUE_PROMPT,
    ADVERSARIAL_MEMO_PROMPT,
)


@dataclass
class BlackSwanResult:
    question: str
    causal_graphs: list[str] = field(default_factory=list)
    threshold_scans: list[str] = field(default_factory=list)
    confluences: list[dict] = field(default_factory=list)
    historical_analogues: list[str] = field(default_factory=list)
    adversarial_memo: str = ""
    timings: dict[str, float] = field(default_factory=dict)


class BlackSwanOrchestrator:
    """Runs the Black Swan Detection protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p48_black_swan_detection")
    async def run(self, question: str) -> BlackSwanResult:
        """Execute the five-layer Black Swan Detection protocol."""
        result = BlackSwanResult(question=question)

        # Layer 1: Causal Graph Construction (parallel agents, Opus)
        print("\nLayer 1: Causal Graph Construction...")
        t0 = time.time()
        result.causal_graphs = await self._parallel_agents(
            CAUSAL_GRAPH_PROMPT.format(question=question)
        )
        result.timings["layer_1_causal_graphs"] = time.time() - t0

        causal_combined = self._combine(result.causal_graphs)

        # Layer 2: Threshold Scanning (parallel agents, Opus)
        print("Layer 2: Threshold & Phase Transition Scanning...")
        t0 = time.time()
        result.threshold_scans = await self._parallel_agents(
            THRESHOLD_SCAN_PROMPT.format(
                question=question, causal_graphs=causal_combined
            )
        )
        result.timings["layer_2_threshold_scans"] = time.time() - t0

        threshold_combined = self._combine(result.threshold_scans)

        # Layer 3: Confluence Extraction (single mechanical call, Haiku)
        print("Layer 3: Confluence Extraction...")
        t0 = time.time()
        result.confluences = await self._confluence_extract(threshold_combined)
        result.timings["layer_3_confluences"] = time.time() - t0

        confluences_text = json.dumps(result.confluences, indent=2)

        # Layer 4: Historical Analogue Mining (parallel agents, Opus)
        print("Layer 4: Historical Analogue Mining...")
        t0 = time.time()
        result.historical_analogues = await self._parallel_agents(
            HISTORICAL_ANALOGUE_PROMPT.format(
                question=question, confluences=confluences_text
            )
        )
        result.timings["layer_4_historical_analogues"] = time.time() - t0

        analogues_combined = self._combine(result.historical_analogues)

        # Layer 5: Adversarial Memo Synthesis (single call, Opus)
        print("Layer 5: Adversarial Memo Synthesis...")
        t0 = time.time()
        result.adversarial_memo = await self._synthesize(
            question, causal_combined, threshold_combined,
            confluences_text, analogues_combined,
        )
        result.timings["layer_5_adversarial_memo"] = time.time() - t0

        return result

    async def _parallel_agents(self, prompt: str) -> list[str]:
        """Run prompt across all agents in parallel using thinking model."""
        async def query_agent(agent: dict) -> str:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return extract_text(response)

        responses = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        return filter_exceptions(responses, label="p48_black_swan_detection")

    async def _confluence_extract(self, threshold_scans: str) -> list[dict]:
        """Layer 3: Mechanical confluence extraction using orchestration model."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": CONFLUENCE_PROMPT.format(threshold_scans=threshold_scans),
            }],
        )
        return parse_json_array(extract_text(response))

    async def _synthesize(
        self,
        question: str,
        causal_graphs: str,
        threshold_scans: str,
        confluences: str,
        historical_analogues: str,
    ) -> str:
        """Layer 5: Final adversarial memo synthesis using thinking model."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": ADVERSARIAL_MEMO_PROMPT.format(
                    question=question,
                    causal_graphs=causal_graphs,
                    threshold_scans=threshold_scans,
                    confluences=confluences,
                    historical_analogues=historical_analogues,
                ),
            }],
        )
        return extract_text(response)

    def _combine(self, responses: list[str]) -> str:
        """Combine per-agent responses with agent name headers."""
        return "\n\n".join(
            f"=== {agent['name']} ===\n{resp}"
            for agent, resp in zip(self.agents, responses)
        )
