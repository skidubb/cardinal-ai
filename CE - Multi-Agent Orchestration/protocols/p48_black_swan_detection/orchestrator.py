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
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions, parse_json_array
from protocols.hierarchical import (
    Decomposition,
    SubResult,
    delegate,
    format_results_for_synthesis,
    parse_decomposition,
)

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    CAUSAL_GRAPH_PROMPT,
    THRESHOLD_SCAN_PROMPT,
    CONFLUENCE_PROMPT,
    HISTORICAL_ANALOGUE_PROMPT,
    ADVERSARIAL_MEMO_PROMPT,
    DECOMPOSITION_PROMPT,
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
    # Hierarchical mode outputs — empty when hierarchical=False.
    decomposition: dict = field(default_factory=dict)
    sub_task_results: list[dict] = field(default_factory=list)


class BlackSwanOrchestrator:
    """Runs the Black Swan Detection protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
        hierarchical: bool = False,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.hierarchical = hierarchical
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p48_black_swan_detection")
    async def run(self, question: str) -> BlackSwanResult:
        """Execute the five-layer Black Swan Detection protocol.

        In hierarchical mode, an additional Layer 0 runs first: a coordinator
        decomposes the question into typed fragility sub-tasks, each
        dispatched to a specialized agent. Layer 1 then receives the
        aggregated sub-task findings as context, so causal graphs are
        informed by the specific fragilities of THIS question.
        """
        result = BlackSwanResult(question=question)
        prior_findings = ""

        # Layer 0 (optional): Coordinator decomposition + hierarchical delegation
        if self.hierarchical:
            print("\nLayer 0: Coordinator decomposition + hierarchical delegation...")
            t0 = time.time()
            span = create_span("stage:hierarchical_decomposition", {})
            try:
                decomposition, sub_results = await self._hierarchical_layer(question)
                result.decomposition = decomposition.as_dict()
                result.sub_task_results = [r.as_dict() for r in sub_results]
                prior_findings = format_results_for_synthesis(sub_results)
                result.timings["layer_0_hierarchical"] = time.time() - t0
                end_span(
                    span,
                    output=(
                        f"{len(decomposition.sub_tasks)} sub-tasks, "
                        f"{sum(1 for r in sub_results if r.succeeded)} successful"
                    ),
                )
            except Exception:
                end_span(span, error="hierarchical_decomposition failed")
                raise

        # Layer 1: Causal Graph Construction (parallel agents, Opus)
        print("\nLayer 1: Causal Graph Construction...")
        t0 = time.time()
        span = create_span("stage:causal_graphs", {"agent_count": len(self.agents)})
        try:
            causal_prompt = CAUSAL_GRAPH_PROMPT.format(question=question)
            if prior_findings:
                causal_prompt = (
                    causal_prompt
                    + "\n\nPRIOR FRAGILITY FINDINGS (from Layer 0 hierarchical "
                    "delegation — use these to focus your causal graph on the "
                    "specific fragilities most relevant to this question):\n"
                    + prior_findings
                )
            result.causal_graphs = await self._parallel_agents(causal_prompt)
            result.timings["layer_1_causal_graphs"] = time.time() - t0
            end_span(span, output=f"{len(result.causal_graphs)} causal graphs")
        except Exception:
            end_span(span, error="causal_graphs failed")
            raise

        causal_combined = self._combine(result.causal_graphs)

        # Layer 2: Threshold Scanning (parallel agents, Opus)
        print("Layer 2: Threshold & Phase Transition Scanning...")
        t0 = time.time()
        span = create_span("stage:threshold_scans", {"agent_count": len(self.agents)})
        try:
            result.threshold_scans = await self._parallel_agents(
                THRESHOLD_SCAN_PROMPT.format(
                    question=question, causal_graphs=causal_combined
                )
            )
            result.timings["layer_2_threshold_scans"] = time.time() - t0
            end_span(span, output=f"{len(result.threshold_scans)} threshold scans")
        except Exception:
            end_span(span, error="threshold_scans failed")
            raise

        threshold_combined = self._combine(result.threshold_scans)

        # Layer 3: Confluence Extraction (single mechanical call, Haiku)
        print("Layer 3: Confluence Extraction...")
        t0 = time.time()
        span = create_span("stage:confluence_extraction", {})
        try:
            result.confluences = await self._confluence_extract(threshold_combined)
            result.timings["layer_3_confluences"] = time.time() - t0
            end_span(span, output=f"{len(result.confluences)} confluences")
        except Exception:
            end_span(span, error="confluence_extraction failed")
            raise

        confluences_text = json.dumps(result.confluences, indent=2)

        # Layer 4: Historical Analogue Mining (parallel agents, Opus)
        print("Layer 4: Historical Analogue Mining...")
        t0 = time.time()
        span = create_span("stage:historical_analogues", {"agent_count": len(self.agents)})
        try:
            result.historical_analogues = await self._parallel_agents(
                HISTORICAL_ANALOGUE_PROMPT.format(
                    question=question, confluences=confluences_text
                )
            )
            result.timings["layer_4_historical_analogues"] = time.time() - t0
            end_span(span, output=f"{len(result.historical_analogues)} analogues")
        except Exception:
            end_span(span, error="historical_analogues failed")
            raise

        analogues_combined = self._combine(result.historical_analogues)

        # Layer 5: Adversarial Memo Synthesis (single call, Opus)
        print("Layer 5: Adversarial Memo Synthesis...")
        t0 = time.time()
        span = create_span("stage:adversarial_memo", {})
        try:
            result.adversarial_memo = await self._synthesize(
                question, causal_combined, threshold_combined,
                confluences_text, analogues_combined,
            )
            result.timings["layer_5_adversarial_memo"] = time.time() - t0
            end_span(span, output="adversarial memo synthesized")
        except Exception:
            end_span(span, error="adversarial_memo failed")
            raise

        return result

    async def _hierarchical_layer(
        self, question: str
    ) -> tuple[Decomposition, list[SubResult]]:
        """Layer 0: coordinator decomposes → typed sub-tasks → routed workers.

        Uses the hierarchical primitive so the same pattern is available to
        every protocol. If the coordinator fails to emit a valid
        decomposition, returns an empty one and no sub-results — Layer 1
        continues without prior findings.
        """
        # Coordinator call — orchestration model, single completion.
        coord_response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": DECOMPOSITION_PROMPT.format(question=question),
            }],
            agent_name="hierarchical_coordinator",
        )
        decomposition = parse_decomposition(extract_text(coord_response))
        if not decomposition.sub_tasks:
            return decomposition, []

        # Sort by priority so higher-signal sub-tasks come first in the field.
        decomposition.sub_tasks.sort(key=lambda t: t.priority, reverse=True)

        # Worker runner: each specialized agent answers its typed sub-question.
        async def runner(sub_task, worker: dict) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=worker.get("system_prompt", ""),
                messages=[{
                    "role": "user",
                    "content": (
                        f"You are investigating the {sub_task.category} axis of "
                        f"this Black Swan analysis.\n\n"
                        f"Root question:\n{question}\n\n"
                        f"Your sub-question:\n{sub_task.question}\n\n"
                        "Focus specifically on your axis. Do NOT restate the "
                        "full analysis — deliver 3-5 concrete findings a "
                        "coordinator can weave into a broader causal graph."
                    ),
                }],
                agent_name=f"worker:{worker.get('key', worker.get('name', 'agent'))}",
            )
            return extract_text(response)

        sub_results = await delegate(decomposition, self.agents, runner)
        return decomposition, sub_results

    async def _parallel_agents(self, prompt: str) -> list[str]:
        """Run prompt across all agents in parallel using thinking model."""
        async def query_agent(agent: dict) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent.get("name"),
            )
            return extract_text(response)

        responses = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        return filter_exceptions(responses, label="p48_black_swan_detection")

    async def _confluence_extract(self, threshold_scans: str) -> list[dict]:
        """Layer 3: Mechanical confluence extraction using orchestration model."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": CONFLUENCE_PROMPT.format(threshold_scans=threshold_scans),
            }],
            agent_name="confluence_extraction",
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
        response = await llm_complete(
            self.client,
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
            agent_name="adversarial_memo",
        )
        return extract_text(response)

    def _combine(self, responses: list[str]) -> str:
        """Combine per-agent responses with agent name headers."""
        return "\n\n".join(
            f"=== {agent['name']} ===\n{resp}"
            for agent, resp in zip(self.agents, responses)
        )
